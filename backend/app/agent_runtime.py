"""Prompt-driven background agent runtime for Orqentra."""
from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .browser_agent import (ALIASES, ALLOWED_INPUT_TYPES, BrowserAutomationAgent, _clean,
                            field_label, portal_origin, suggest_field_mappings)
from .document_extractor import extract_profile_from_text
from .llm import OptionalLlama
from .orchestrator import IntentAgent, DocumentIntelligenceAgent


PORTAL_HINTS = [
    {"keys": ("passport",), "country": "india", "title": "Passport Seva — Government of India", "url": "https://www.passportindia.gov.in/", "confidence": 0.99},
    {"keys": ("scholarship", "national scholarship", "student scholarship"), "country": "india", "title": "National Scholarship Portal", "url": "https://scholarships.gov.in/", "confidence": 0.98},
    {"keys": ("employment", "job seeker", "government job", "job application"), "country": "india", "title": "National Career Service", "url": "https://www.ncs.gov.in/", "confidence": 0.93},
    {"keys": ("gst registration", "gst"), "country": "india", "title": "Goods and Services Tax Portal", "url": "https://www.gst.gov.in/", "confidence": 0.96},
    {"keys": ("company registration", "incorporate company", "business incorporation", "mca"), "country": "india", "title": "Ministry of Corporate Affairs", "url": "https://www.mca.gov.in/", "confidence": 0.96},
    {"keys": ("pan card", "permanent account number"), "country": "india", "title": "Income Tax e-Filing Portal", "url": "https://www.incometax.gov.in/", "confidence": 0.94},
    {"keys": ("driving licence", "driving license", "learner licence", "learner license"), "country": "india", "title": "Parivahan — Sarathi Services", "url": "https://sarathi.parivahan.gov.in/", "confidence": 0.95},
]

PORTAL_DETAILS = {"login_id", "login_id_same_as_email", "registration_office"}


class PortalDiscovery:
    def __init__(self):
        import os
        self.country = os.getenv("ORQENTRA_COUNTRY", "India").lower()

    async def discover(self, goal: str, service: str) -> list[dict[str, Any]]:
        text = goal.lower()
        known = [x for x in PORTAL_HINTS if x["country"] == self.country and any(k in text for k in x["keys"])]
        if known:
            return known[:3]
        query = f"official {goal[:150]} application portal {self.country}"
        try:
            return await asyncio.to_thread(self._search, query)
        except Exception:
            return []

    @staticmethod
    def _search(query: str) -> list[dict[str, Any]]:
        try:
            from ddgs import DDGS
        except ImportError:
            return []
        found = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=8):
                url = item.get("href") or item.get("url") or ""
                if not url.startswith("https://"):
                    continue
                host = (urlparse(url).hostname or "").lower()
                title = item.get("title") or host
                body = item.get("body") or ""
                score = 0.35
                if host.endswith((".gov", ".gov.in", ".gov.uk", ".gov.au", ".gov.ca")):
                    score += 0.35
                if "official" in (title + " " + body).lower():
                    score += 0.12
                if any(term in (title + " " + body + " " + host).lower() for term in ("apply", "application", "portal", "admission", "registration")):
                    score += 0.12
                found.append({"title": title, "url": url, "host": host, "confidence": round(min(score, 0.94), 2), "snippet": body[:240], "source": "web search"})
        found.sort(key=lambda x: x["confidence"], reverse=True)
        # De-duplicate by host.
        unique, seen = [], set()
        for item in found:
            if item["host"] not in seen:
                seen.add(item["host"]); unique.append(item)
        return unique[:5]




class OptimizerAgent:
    """Patent Claim 6: Analyzes outcomes of completed and failed tasks, stores run history
    in vector memory, and feeds performance insights back to the orchestrator to improve
    subsequent task runs, thereby forming a continuous feedback loop."""

    def run(self, store, wf: dict) -> dict:
        """Record run outcome and return performance insights for future orchestration."""
        service = wf.get("service", "unknown")
        status = wf.get("status", "unknown")
        plan = wf.get("plan", [])
        completed_steps = sum(1 for s in plan if s.get("status") == "completed")
        error_steps = sum(1 for s in plan if s.get("status") == "error")
        pages_visited = len(wf.get("current_page", {}) and [wf["current_page"]] or [])
        insights = {
            "completed_steps": completed_steps,
            "total_steps": len(plan),
            "completion_rate": round(completed_steps / max(1, len(plan)), 2),
            "had_error": status == "error",
            "portal_url": wf.get("portal_url", ""),
            "goal_summary": wf.get("goal", "")[:200],
        }
        try:
            store.save_run_outcome(
                workflow_id=wf["id"],
                goal=wf.get("goal", ""),
                service=service,
                status=status,
                fields_filled=completed_steps,
                pages_visited=pages_visited,
                error_count=error_steps,
                insights=insights,
            )
        except Exception:
            pass  # Optimizer failures must never block the main pipeline.

        # Fetch past outcomes for this service to generate actionable insights.
        try:
            past = store.get_run_insights(service, limit=5, user_id=wf.get("user_id", ""))
        except Exception:
            past = []

        tips = []
        if past:
            success_rate = sum(1 for r in past if r.get("status") == "completed") / len(past)
            if success_rate < 0.5:
                tips.append(f"Low success rate ({int(success_rate*100)}%) for {service} — consider checking portal URL accuracy.")
            avg_errors = sum(r.get("error_count", 0) for r in past) / len(past)
            if avg_errors > 2:
                tips.append(f"High average errors ({avg_errors:.1f}) — profile data for {service} may be incomplete.")

        return {"service": service, "insights": insights, "tips": tips, "past_runs_analyzed": len(past)}


class AgentRuntime:
    def __init__(self, store, browser: BrowserAutomationAgent, upload_dir: Path):
        self.store = store
        self.browser = browser
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.discovery = PortalDiscovery()
        self.llm = OptionalLlama()
        self.optimizer = OptimizerAgent()
        self._tasks: dict[str, asyncio.Task] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, wid: str) -> asyncio.Lock:
        return self._locks.setdefault(wid, asyncio.Lock())

    def _workflow(self, wid: str) -> dict:
        wf = self.store.get_workflow(wid)
        if not wf:
            raise KeyError(wid)
        return wf

    def _save(self, wf: dict):
        self.store.save_workflow(wf)

    def _say(self, wid: str, content: str, kind: str = "text"):
        self.store.add_message(wid, "assistant", content, kind)

    def _event(self, wid: str, kind: str, message: str, details=None):
        self.store.event(wid, kind, message, details or {})

    def _step(self, wf: dict, step_id: str, state: str, detail: str = ""):
        for step in wf.get("plan", []):
            if step["id"] == step_id:
                step["status"] = state
                if detail:
                    step["detail"] = detail
        wf["active_step"] = step_id
        wf["updated_note"] = detail or state.replace("_", " ")
        self._save(wf)
        self._event(wf["id"], "step_" + state, detail or step_id.replace("_", " "), {"step_id": step_id})

    def _schedule(self, wid: str, coro):
        existing = self._tasks.get(wid)
        if existing and not existing.done():
            coro.close()
            return
        task = asyncio.create_task(coro)
        self._tasks[wid] = task

    async def start_chat(self, message: str, user_id: str = "") -> dict:
        intent = IntentAgent().run(message)
        wid = str(uuid.uuid4())
        plan = [
            {"id": "understand", "title": "Understand the request", "agent": "Orchestrator Agent", "status": "running"},
            {"id": "memory", "title": "Search saved information and documents", "agent": "Orchestrator Agent · RAG Memory", "status": "queued"},
            {"id": "portal", "title": "Find and open the application portal", "agent": "Execution Agent · Portal Discovery", "status": "queued"},
            {"id": "requirements", "title": "Inspect requirements and collect missing items", "agent": "Execution Agent · Requirements", "status": "queued"},
            {"id": "form", "title": "Complete the application form", "agent": "Execution Agent · Browser Automation", "status": "queued"},
            {"id": "verification", "title": "Handle verification and validate entries", "agent": "Monitoring Agent · Verification", "status": "queued"},
            {"id": "submission", "title": "Submit and save acknowledgement", "agent": "Optimizer Agent · Submission", "status": "queued"},
        ]
        goal_l = message.lower()
        submit_authorized = any(x in goal_l for x in ("apply for me", "submit the application", "complete and submit", "apply on my behalf", "register me")) or bool(re.search(r"\b(apply for|apply to|submit|register for|enroll in|enrol in|renew my)\b|^register\b", goal_l))
        wf = {"id": wid, "goal": message, "service": intent["service"], "task": intent["task"],
              "status": "running", "plan": plan, "active_step": "understand", "pending_input": None,
              "portal_candidates": [], "portal_url": None, "documents": [], "submit_authorized": submit_authorized,
              "created_at": None, "last_error": None, "current_page": None, "user_id": user_id}
        self.store.save_workflow(wf)
        self.store.add_message(wid, "user", message)
        facts = self._parse_prompt_facts(message)
        if user_id:
            self.store.save_user_fields_bulk(user_id, facts, source=f"prompt:{wid}")
        else:
            for key, value in facts.items():
                self.store.save_profile_value(key, value, f"prompt:{wid}")
        self._say(wid, "I’ve received your request. I’m identifying the application, checking your saved information and documents, and looking for the official portal. I’ll ask here only when I need something from you.")
        self._event(wid, "workflow_created", "Application request received", {"service": intent["service"]})
        self._schedule(wid, self._initial(wid))
        return wf

    async def chat(self, wid: str, message: str, *, reply_to: str | None = None) -> dict:
        wf = self._workflow(wid)
        pending = wf.get("pending_input") or {}
        if reply_to and pending.get("id") != reply_to:
            raise ValueError("That question has changed. Reply to the latest question.")
        if pending.get("kind") == "password":
            self._say(wid, "Enter the portal password in the masked password box in this chat.", "password_request")
            return {"workflow": wf}
        if pending.get("kind") == "detail" and pending.get("field"):
            return await self._answer_detail(wid, pending["id"], message)
        low = message.strip().lower()
        if pending.get("kind") in {"login_ready", "credentials", "manual_verification"}:
            if low in {"ready", "done", "continue", "resume"}:
                self._resume(wf)
            else:
                self._say(wid, "Use the requested verification control and reply **ready** when you’re done." if
                          pending["kind"] == "manual_verification" else "Reply **ready** to continue field by field in chat.")
            return {"workflow": wf}
        if pending.get("kind") == "otp":
            result = await self.submit_otp(wid, message.strip())
            return {"workflow": self._workflow(wid), "result": result}
        if pending.get("kind") == "submit_registration":
            if low in {"submit registration", "submit", "yes", "confirm"}:
                wf["registration_authorized"] = pending["url"]
                self._resume(wf)
            else:
                self._say(wid, "Reply **submit registration** when you want me to send the completed form.")
            return {"workflow": wf}

        self.store.add_message(wid, "user", message)
        if pending.get("kind") == "portal_confirmation":
            candidate_url = self._extract_url(message) or (wf.get("portal_candidates") or [{}])[0].get("url")
            if any(x in low for x in ("yes", "open", "use it", "correct", "proceed")) and candidate_url:
                wf["portal_url"] = candidate_url
                wf["pending_input"] = None
                wf["status"] = "running"
                self._save(wf)
                self._say(wid, f"I’m opening the portal you selected: {candidate_url}")
                self._schedule(wid, self._open_portal(wid, candidate_url))
            else:
                url = self._extract_url(message)
                if url:
                    wf["portal_url"] = url; wf["pending_input"] = None; wf["status"] = "running"; self._save(wf)
                    self._say(wid, "I’ll use the portal address you provided and check that it is HTTPS before opening it.")
                    self._schedule(wid, self._open_portal(wid, url))
                else:
                    self._say(wid, "Please reply **open portal** to use the suggested result, or paste the official HTTPS portal address you want me to use.")
        elif pending.get("kind") == "portal_action_choice":
            if any(x in low for x in ("register", "signup", "sign up", "new user", "new registration", "create")):
                action = "register"
            elif any(x in low for x in ("login", "log in", "sign in", "signin", "existing")):
                action = "login"
            elif any(x in low for x in ("apply", "application", "start")):
                action = "apply"
            else:
                action = message.strip()
            return await self.submit_action_choice(wid, action)
        elif pending.get("kind") == "approval":
            if any(x in low for x in ("yes", "approve", "approved", "confirm", "proceed", "continue", "looks good", "ok", "okay")):
                wf["pending_input"] = None; wf["status"] = "running"; self._save(wf)
                self._say(wid, "Options approved. I'm filling the choices and continuing the application.")
                self._schedule(wid, self._continue_form(wid))
            else:
                self._say(wid, "Please review the proposed choices above and click **Approve** or tell me what options you prefer.")
        elif pending.get("kind") == "detail":
            key = pending.get("key") or self._key_from_label(pending.get("label", ""))
            if low in {"skip", "i don't know", "dont know", "not available", "unknown"}:
                self._say(wid, f"I’ve marked {pending.get('label', key)} as unavailable for now. I’ll check whether the portal allows it to be left blank.")
            else:
                parsed = self._parse_details(message, [key])
                value = parsed.get(key) or message.strip()
                if wf.get("user_id"):
                    self.store.save_user_field(wf["user_id"], key, value, source="user-chat")
                else:
                    self.store.save_profile_value(key, value, "user-chat")
                self._say(wid, f"Saved **{pending.get('label', key)}** to your local applicant profile. I’m resuming the form.")
            wf["pending_input"] = None; wf["status"] = "running"; self._save(wf)
            self._schedule(wid, self._continue_form(wid))
        elif pending.get("kind") == "document":
            url = self._extract_url(message)
            self._say(wid, f"Please upload **{pending.get('label', 'the requested document')}** using the upload area below. {('I can also use this secure document URL: ' + url) if url else ''}")
        elif pending.get("kind") == "manual_action":
            if any(x in low for x in ("ready", "done", "completed", "continue")):
                wf["pending_input"] = None; wf["status"] = "running"; self._save(wf)
                self._say(wid, "Continuing from the current portal page.")
                self._schedule(wid, self._continue_form(wid))
            else:
                self._say(wid, "Complete the requested action in the browser, then type **ready** here.")
        elif wf.get("status") == "error" and low in {"retry", "resume", "continue", "ready"}:
            wf["status"] = "running"; wf["last_error"] = None; self._save(wf)
            if wf.get("portal_url") and wf["id"] not in self.browser._sessions:
                self._schedule(wid, self._open_portal(wid, wf["portal_url"]))
            else:
                self._schedule(wid, self._continue_form(wid))
            self._say(wid, "Retrying the interrupted agent step.")
        else:
            if low in {"start", "resume", "continue", "ready"}:
                wf["status"] = "running"; self._save(wf)
                self._schedule(wid, self._continue_form(wid))
            else:
                self._say(wid, "I’ve added that to the conversation. I’m currently waiting for the previous step to be completed; please follow the question above or upload the requested document.")
        return {"workflow": self._workflow(wid)}

    async def _initial(self, wid: str):
        async with self._lock(wid):
            wf = self._workflow(wid)
            try:
                intent = IntentAgent().run(wf["goal"])
                wf["service"] = intent["service"]; wf["task"] = intent["task"]
                self._step(wf, "understand", "completed", f"Identified this as a {intent['service'].replace('_', ' ')} {intent['task']}.")
                query = wf["goal"] + " " + intent["service"]
                uid = wf.get("user_id", "")
                memories = self.store.search_memory(query, user_id=uid)
                profile = self.store.get_user_profile(uid) if uid else self.store.get_profile()
                self._step(wf, "memory", "completed", f"Searched local RAG memory; found {len(memories)} relevant saved profile/document items and {len(profile)} reusable profile fields.")
                direct_url = self._extract_url(wf["goal"])
                candidates = ([{"title": "Portal link supplied in your request", "url": direct_url,
                               "host": urlparse(direct_url).hostname or "", "confidence": 1.0, "source": "user supplied"}]
                              if direct_url else await self.discovery.discover(wf["goal"], intent["service"]))
                wf["portal_candidates"] = candidates
                if not candidates:
                    wf["status"] = "waiting_user"
                    wf["pending_input"] = {"kind": "portal_confirmation"}
                    self._step(wf, "portal", "waiting", "No sufficiently reliable portal match was found.")
                    self._say(wid, "I couldn’t identify a sufficiently reliable official portal from the request. Please paste the official HTTPS application portal link, and I’ll continue.")
                    self._save(wf); return
                candidate = candidates[0]
                if candidate.get("confidence", 0) >= 0.94 and candidate.get("source") != "web search":
                    wf["portal_url"] = candidate["url"]
                    self._step(wf, "portal", "running", f"Matched a known official service portal: {candidate['title']}.")
                    self._say(wid, f"I found the likely official portal: **{candidate['title']}** ([open portal]({candidate['url']})). I’m opening it now.")
                    self._save(wf)
                    await self._open_portal_locked(wf, candidate["url"])
                else:
                    wf["status"] = "waiting_user"
                    wf["pending_input"] = {"kind": "portal_confirmation"}
                    self._step(wf, "portal", "waiting", "Found a possible portal; user confirmation is needed before opening it.")
                    choices = "\n".join(f"{i+1}. [{x['title']}]({x['url']}) — {x.get('host','')}" for i, x in enumerate(candidates[:3]))
                    self._say(wid, "I found these possible portals. Please check the official site and reply **open portal** to use the first result, or paste the correct HTTPS link.\n\n" + choices)
                    self._save(wf)
            except Exception as exc:
                await self._fail(wid, f"I couldn’t complete the initial research step: {str(exc)[:300]}")

    async def confirm_portal(self, wid: str, url: str):
        wf = self._workflow(wid)
        wf["portal_url"] = url; wf["pending_input"] = None; wf["status"] = "running"; self._save(wf)
        self._say(wid, f"Portal selected: {url}. Opening it now.")
        self._schedule(wid, self._open_portal(wid, url))
        return wf

    async def _open_portal(self, wid: str, url: str):
        async with self._lock(wid):
            await self._open_portal_locked(self._workflow(wid), url)

    async def _open_portal_locked(self, wf: dict, url: str):
        wid = wf["id"]
        try:
            result = await self.browser.open_portal(wid, url)
            wf["portal_url"] = result["url"]
            navigation = await self.browser.navigate_to_application(wid, wf.get("goal", "application"))
            self._step(wf, "portal", "completed", f"Opened {result['title'] or result['url']} in Chromium.")
            if result.get("popup_dismissed"):
                self._event(wid, "popup_dismissed", "Dismissed advisory/announcement modal popup")

            # Detect all choices on the portal (Login, Register, Apply, etc.) and ask user to choose
            choices = [] if navigation.get("has_form") else await self.browser.detect_page_actions(wid)
            goal = wf["goal"]
            register = re.search(r"\b(register|sign up|create)\b.{0,40}\b(account|new user)\b|^register\b", goal, re.I)
            login = re.search(r"\b(log in|login|sign in)\b", goal, re.I)
            requested_action = None
            if not re.search(r"\b(don.t|not|unsure)\b", goal, re.I):
                if register and not login:
                    requested_action = "register"
                elif login and not register:
                    requested_action = "login"
            if requested_action and any(choice["action"] == requested_action for choice in choices):
                await self.browser.navigate_action(wid, requested_action)
                wf["portal_action"] = requested_action
                self._save(wf)
                self._tasks[wid] = asyncio.create_task(self._continue_form(wid))
                return
            if not choices:
                if requested_action:
                    wf["portal_action"] = requested_action
                    self._save(wf)
                self._tasks[wid] = asyncio.create_task(self._continue_form(wid))
                return
            wf["status"] = "waiting_user"
            wf["pending_input"] = {"kind": "portal_action_choice", "choices": choices}
            self._step(wf, "requirements", "waiting", "Options available on official portal.")
            self._say(wid, "I opened the portal. Choose how you’d like to continue.")
            self._save(wf)
        except Exception as exc:
            await self._fail(wid, f"I couldn’t open the portal: {str(exc)[:360]}. Check Playwright/Chromium installation and the portal address, then send ‘retry’ or a different HTTPS link.")

    def _resume(self, wf: dict):
        wf["pending_input"] = None
        wf["status"] = "running"
        self._save(wf)
        self._schedule(wf["id"], self._continue_form(wf["id"]))

    def _profile_for_page(self, wf: dict, url: str) -> dict:
        uid = wf.get("user_id")
        if not uid:
            return self.store.get_profile()
        account = self.store.get_user_by_id(uid) or {}
        saved = {key: value for key, value in self.store.get_user_profile(uid).items()
                 if value and value != "[decryption error]"}
        profile = {**{key: account.get(key, "") for key in ("full_name", "email")}, **saved}
        origin = portal_origin(url)
        if origin:
            profile.update(self.store.get_portal_values(uid, origin))
        if _clean(profile.get("login_id_same_as_email")) == "yes" and profile.get("email"):
            profile["login_id"] = profile["email"]
        return profile

    @staticmethod
    def _field_mapping(field: dict, url: str, **values) -> dict:
        return {"field_index": int(field["index"]), "expected_url": url, "expected_label": field_label(field),
                "field_id": field.get("id", ""), "field_name": field.get("name", ""),
                "expected_type": field.get("type", "text"), **values}

    @staticmethod
    def _radio_group(field: dict) -> str:
        return str(field.get("name") or field.get("group_label") or field["index"])

    @classmethod
    def _radio_options(cls, field: dict, fields: list[dict]) -> list[dict]:
        return [option for option in fields if option.get("type") == "radio" and not option.get("disabled")
                and not option.get("sensitive") and cls._radio_group(option) == cls._radio_group(field)]

    @staticmethod
    def _form_value(field: dict, value: str) -> str:
        if field.get("type") == "date":
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(value, fmt).date().isoformat()
                except ValueError:
                    continue
        return value

    async def _fill_saved_values(self, wid: str, inspected: dict, profile: dict) -> tuple[dict, dict]:
        url = inspected["url"]
        filled = {}
        for _ in range(6):
            fields = inspected["fields"]
            selected_groups = {self._radio_group(field) for field in fields
                               if field.get("type") == "radio" and field.get("has_value")}
            empty = {int(field["index"]): field for field in fields
                     if not (field.get("has_value") and field.get("valid", True))
                     and (field.get("type") != "radio" or self._radio_group(field) not in selected_groups)}
            mappings = [self._field_mapping(
                empty[item["field_index"]], url, profile_key=item["profile_key"],
                value=self._form_value(empty[item["field_index"]], item["value"]),
            ) for item in suggest_field_mappings(list(empty.values()), profile) if item["confidence"] >= 0.88]
            if not mappings:
                break
            result = await self.browser.fill(wid, mappings)
            filled.update((item["field_index"], empty[item["field_index"]]) for item in result.get("filled", []))
            inspected = await self.browser.inspect(wid)
            if inspected["url"] != url or inspected["fields"] == fields:
                break
        if filled:
            self._event(wid, "fields_auto_filled", f"Filled {len(filled)} field(s) from your saved profile")
        return inspected, filled

    def _ask_field(self, wf: dict, url: str, field: dict, fields: list[dict], *, remember_password: bool = False):
        label = field.get("group_label") if field.get("type") == "radio" else None
        label = label or field_label(field)
        secret = field.get("type") == "password"
        options = field.get("options") or []
        if field.get("type") == "radio":
            options = [{"label": item.get("option_label") or field_label(item)} for item in self._radio_options(field, fields)]
        if field.get("type") == "checkbox":
            options = [{"label": "Yes"}, {"label": "No"}]
        wf["pending_input"] = {"kind": "password" if secret else "detail", "id": uuid.uuid4().hex,
                               "field": self._field_mapping(field, url), "label": label,
                               "key": self._key_from_label(label),
                               "options": [str(item.get("label") or item.get("value")) for item in options],
                               "remember": remember_password, "portal": portal_origin(url)}
        wf["status"] = "waiting_user"
        self._step(wf, "requirements", "waiting", f"Waiting for {label}.")
        instructions = ("Use the masked password box in this chat." if secret else
                        "Choose an option below or reply with your choice." if options else "Reply with the value here.")
        self._say(wf["id"], f"I need **{label}**. {instructions}", "password_request" if secret else "detail_request")

    async def _answer_detail(self, wid: str, question_id: str, message: str) -> dict:
        async with self._lock(wid):
            wf = self._workflow(wid)
            pending = wf.get("pending_input") or {}
            if pending.get("id") != question_id or pending.get("kind") != "detail":
                raise ValueError("That question has changed. Reply to the latest question.")
            target = pending["field"]
            inspected = await self.browser.inspect(wid)
            fields = inspected["fields"]
            field = next((item for item in fields if self._field_mapping(item, inspected["url"]) == target), None)
            if field is None or field.get("disabled") or field.get("readonly") or field.get("sensitive"):
                self._say(wid, "The portal form changed. I’ll check it again before using your reply.")
                self._resume(wf)
                return {"workflow": wf}
            key = pending["key"]
            answer = self._parse_details(message, [key]).get(key, "").strip()
            if not answer or answer.lower() in {"skip", "i don't know", "not available"}:
                raise ValueError("The portal requires this field. Enter a value to continue.")
            value = self._form_value(field, answer)
            if field.get("type") == "radio":
                option = next((item for item in self._radio_options(field, fields)
                               if _clean(item.get("option_label") or field_label(item)) == _clean(answer)), None)
                if option is None:
                    raise ValueError("Choose one of the options shown in chat.")
                target = self._field_mapping(option, inspected["url"])
                answer = option.get("option_label") or field_label(option)
                value = "true"
            result = await self.browser.fill(wid, [{**target, "value": value, "profile_key": key}])
            if not result.get("filled"):
                raise ValueError("The portal didn’t accept that value. Check the field format or choose an available option.")
            uid = wf.get("user_id")
            origin = portal_origin(inspected["url"])
            if uid and key in ALIASES and key not in PORTAL_DETAILS:
                self.store.save_user_field(uid, key, answer, source="user-chat")
            elif uid and origin:
                self.store.save_portal_value(uid, origin, key, answer)
            elif not uid:
                self.store.save_profile_value(key, answer, "user-chat")
            self.store.add_message(wid, "user", answer)
            self._say(wid, f"I filled **{pending['label']}** and will check the remaining fields.")
            self._resume(wf)
            return {"workflow": wf}

    async def answer_password(self, wid: str, question_id: str, password: str, remember: bool) -> dict:
        if not password or len(password) > 512:
            raise ValueError("Enter a portal password up to 512 characters.")
        async with self._lock(wid):
            wf = self._workflow(wid)
            pending = wf.get("pending_input") or {}
            if pending.get("kind") != "password" or pending.get("id") != question_id:
                raise ValueError("That password request has changed. Use the latest question.")
            if not await self.browser.fill_password(wid, pending["field"], password):
                raise ValueError("The portal could not use that password. Check its password requirements and try again.")
            if remember and pending.get("remember"):
                self.store.save_portal_value(wf["user_id"], pending["portal"], "password", password)
            inspected = await self.browser.inspect(wid)
            confirm = re.compile(r"\b(confirm|repeat|re[ -]?enter)\b", re.I)
            password_fields = [field for field in inspected["fields"] if field.get("type") == "password"
                               and not field.get("disabled")]
            primary_passwords = [field for field in password_fields if not confirm.search(field_label(field))]
            if (inspected["url"] == pending["field"]["expected_url"] and len(primary_passwords) == 1
                    and not confirm.search(pending["label"])):
                for field in password_fields:
                    if not field.get("has_value") and confirm.search(field_label(field)):
                        await self.browser.fill_password(wid, self._field_mapping(field, inspected["url"]), password)
            self._say(wid, "I filled the portal password and will check the remaining fields.")
            self._resume(wf)
            return {"workflow": wf}

    def _registration_completed(self, wf: dict, url: str):
        wf["status"] = "completed"
        wf["pending_input"] = None
        self._step(wf, "requirements", "completed", "The portal confirmed registration.")
        self._step(wf, "form", "completed")
        self._step(wf, "verification", "completed")
        self._step(wf, "submission", "completed", "The portal confirmed registration.")
        self._say(wf["id"], "The portal confirmed your registration. Check your email for any activation instructions.")
        self._event(wf["id"], "registration_confirmed", "The portal displayed a registration confirmation", {"url": url})

    async def _continue_form(self, wid: str, depth: int = 0):
        if depth > 12:
            await self._wait_manual(wid, "I’ve processed 12 application pages in this run. Please review the current page and type **ready** to continue.")
            return
        async with self._lock(wid):
            wf = self._workflow(wid)
            try:
                self._step(wf, "requirements", "running", "Inspecting the current form and identifying missing required details and documents.")
                inspected = await self.browser.inspect(wid)
                url = inspected["url"]
                if wf.get("registration_page") and inspected.get("registration_confirmed"):
                    self._registration_completed(wf, url)
                    return
                inspected, filled = await self._fill_saved_values(wid, inspected, self._profile_for_page(wf, url))
                if inspected["url"] != url:
                    self._tasks[wid] = asyncio.create_task(self._continue_form(wid, depth + 1))
                    return

                fields = inspected["fields"]
                wf["current_page"] = {"url": url, "title": inspected["title"], "field_count": len(fields)}
                visible = [field for field in fields if not field.get("disabled") and not field.get("readonly")]
                complete = {int(field["index"]) for field in fields
                            if (field.get("has_value") and field.get("valid", True))
                            or ("has_value" not in field and filled.get(int(field["index"])) == field)}
                selected_groups = {self._radio_group(field) for field in fields
                                   if field.get("type") == "radio" and int(field["index"]) in complete}
                challenge = inspected.get("challenge") or {}
                captcha_fields = [field for field in visible if re.search(
                    r"captcha|characters (?:shown )?in the image", field_label(field), re.I
                )]
                otp_fields = [field for field in visible if re.search(
                    r"\b(otp|one[ -]?time password|verification code)\b",
                    f"{field_label(field)} {field.get('name', '')}", re.I
                ) and field not in captcha_fields]
                has_captcha = challenge.get("captcha") or captcha_fields
                uid = wf.get("user_id", "")
                origin = portal_origin(url)
                page_kind = f"{urlparse(url).path} {inspected['title']}"
                registration = bool(re.search(r"register|registration|sign[ -]?up", page_kind, re.I))
                if registration:
                    wf["registration_page"] = url
                login = not registration and bool(re.search(r"sign[ -]?in|log[ -]?in", page_kind, re.I))
                auth_form = registration or login
                can_remember = bool(uid and origin and auth_form)
                portal_password = (self.store.get_portal_values(uid, origin, password=True).get("password")
                                   if can_remember else None)
                docs = None

                for field in visible:
                    index = int(field["index"])
                    typ = field.get("type", "text")
                    if index in complete or (typ == "radio" and self._radio_group(field) in selected_groups):
                        continue
                    if field in captcha_fields or field in otp_fields:
                        continue
                    if typ == "password":
                        credential_field = bool(re.search(r"\b(password|passwd|pwd)\b", _clean(
                            f"{field_label(field)} {field.get('name', '')} {field.get('autocomplete', '')}"
                        )))
                        if (credential_field and portal_password
                                and await self.browser.fill_password(wid, self._field_mapping(field, url), portal_password)):
                            continue
                        self._ask_field(wf, url, field, fields, remember_password=can_remember and credential_field)
                        return
                    if field.get("sensitive") or not field.get("required"):
                        continue
                    if typ == "file":
                        label = field_label(field)
                        if docs is None:
                            docs = self.store.get_documents(uid, include_text=False)
                        match = self._match_document(label, docs)
                        if match:
                            try:
                                await self.browser.upload_file(wid, index, match["path"])
                                self._event(wid, "document_attached", f"Attached {match['filename']} to {label}")
                                continue
                            except Exception:
                                self._event(wid, "document_upload_skipped", "A saved document could not be attached")
                        wf["status"] = "waiting_user"
                        wf["pending_input"] = {"kind": "document", "label": label, "field_index": index,
                                               "field": self._field_mapping(field, url)}
                        self._step(wf, "requirements", "waiting", f"Waiting for {label}.")
                        self._say(wid, f"Please upload **{label}** in this chat so I can attach it and continue.", "document_request")
                        return
                    if typ in ALLOWED_INPUT_TYPES:
                        self._ask_field(wf, url, field, fields)
                        return

                if has_captcha or challenge.get("hasBiometric"):
                    reason = ("I’ve filled the available details. Complete the CAPTCHA or biometric check in the portal window "
                              "and use its verification button if required. Then click **Continue in chat** here.")
                    if registration and has_captcha:
                        reason = ("I’ve filled the registration form. Complete the CAPTCHA on the portal. "
                                  "If it verifies the CAPTCHA when you click Register, review and submit the form there. "
                                  "Then click **Continue in chat**.")
                    wf["status"] = "waiting_user"
                    wf["pending_input"] = {"kind": "manual_verification"}
                    self._step(wf, "verification", "waiting", "The portal requires manual verification.")
                    self._say(wid, reason, "manual_verification")
                    return
                if otp_fields:
                    wf["status"] = "waiting_user"
                    wf["pending_input"] = {"kind": "otp"}
                    self._step(wf, "verification", "waiting", "The portal requested an OTP.")
                    self._say(wid, "Enter the verification code in the OTP box in this chat.", "otp_request")
                    return
                remaining_protected = [field for field in visible if field.get("sensitive")
                                       and field.get("type") != "password" and int(field["index"]) not in complete]
                if remaining_protected:
                    label = field_label(remaining_protected[0])
                    wf["status"] = "waiting_user"
                    wf["pending_input"] = {"kind": "manual_verification"}
                    self._step(wf, "verification", "waiting", f"{label} requires direct review.")
                    self._say(wid, f"Review **{label}** on the portal, then reply **ready** in chat.", "manual_verification")
                    return

                self._step(wf, "requirements", "completed", f"Inspected {len(fields)} visible fields and found no unmatched required ordinary fields or missing required documents.")
                self._step(wf, "form", "running", "Filling high-confidence fields from the local applicant profile and document vault.")
                passwords = [field for field in visible if field.get("type") == "password"]
                if login and passwords:
                    login_result = await self.browser.click_next(wid, login=True)
                    if login_result.get("advanced"):
                        after_login = await self.browser.inspect(wid)
                        retry = next((field for field in after_login["fields"] if field.get("type") == "password"
                                      and not field.get("disabled") and not field.get("readonly")), None)
                        if after_login["url"] == url and retry:
                            self._say(wid, "The portal is still asking you to sign in. Check your login ID and password.")
                            self._ask_field(wf, url, retry, after_login["fields"], remember_password=can_remember)
                            return
                        await self.browser.navigate_to_application(wid, wf["goal"])
                        self._tasks[wid] = asyncio.create_task(self._continue_form(wid, depth + 1))
                        return
                # Advance only with a clear Next/Continue button; loop to inspect the next page.
                next_result = await self.browser.click_next(wid)
                if next_result.get("advanced"):
                    self._event(wid, "page_advanced", "Advanced to the next application page", {"url": next_result.get("url")})
                    self._step(wf, "form", "completed", "Current page populated; moved to next page.")
                    self._save(wf)
                    # Release lock before recursive call.
                    self._tasks[wid] = asyncio.create_task(self._continue_form(wid, depth + 1))
                    return

                if registration:
                    authorized = wf.get("registration_authorized") == url or bool(
                        wf.get("submit_authorized") and re.search(r"\b(register|registration|sign up)\b", wf["goal"], re.I)
                    )
                    if not authorized:
                        wf["pending_input"] = {"kind": "submit_registration", "url": url}
                        wf["status"] = "waiting_user"
                        self._step(wf, "submission", "waiting", "Waiting for confirmation to submit registration.")
                        self._say(wid, "The registration form is ready. Confirm here when you want me to submit it.")
                        return
                    if wf.get("registration_submitted_url") != url:
                        submit_result = await self.browser.submit_application(wid, True, registration=True)
                        if submit_result.get("submitted"):
                            wf["registration_submitted_url"] = url
                            confirmed = await self.browser.inspect(wid)
                            if confirmed.get("registration_confirmed"):
                                self._registration_completed(wf, confirmed["url"])
                                return
                            wf["status"] = "waiting_user"
                            wf["pending_input"] = {"kind": "manual_verification"}
                            self._step(wf, "submission", "waiting", "Waiting for the portal’s registration confirmation.")
                            self._say(wid, "The form was sent. Check the portal for a result, then click **Continue in chat**.")
                            return
                    else:
                        wf["status"] = "waiting_user"
                        wf["pending_input"] = {"kind": "manual_verification"}
                        self._step(wf, "submission", "waiting", "The portal has not confirmed registration.")
                        self._say(wid, "I’m still waiting for the portal’s registration confirmation.")
                        return
                else:
                    submit_result = await self.browser.submit_application(wid, bool(wf.get("submit_authorized")))
                if submit_result.get("submitted"):
                    wf["status"] = "completed"; wf["pending_input"] = None
                    self._step(wf, "form", "completed", "Application fields completed.")
                    self._step(wf, "verification", "completed", "Portal accepted the final action; confirmation content captured for review.")
                    self._step(wf, "submission", "completed", "Final submission control was activated; check the official portal acknowledgement.")
                    self._say(wid, "The application submission control was activated. Please check the official portal confirmation shown in the browser. I’ve captured the visible confirmation text for your records. If the portal issues an acknowledgement number or receipt, upload/download it and I’ll add it to your document vault.")
                    self._event(wid, "application_submitted", "Final application submit control was clicked", {"url": submit_result.get("url"), "confirmation_preview": submit_result.get("confirmation_text", "")[:500]})
                else:
                    reason = submit_result.get("reason", "No safe automatic next action was found.")
                    if "payment" in reason.lower() or "declaration" in reason.lower() or "consent" in reason.lower():
                        wf["status"] = "waiting_user"; wf["pending_input"] = {"kind": "manual_action"}
                        self._step(wf, "verification", "waiting", reason)
                        self._say(wid, reason + " Please review and complete that action on the official portal, then type **ready** here.")
                    else:
                        wf["status"] = "waiting_user"; wf["pending_input"] = {"kind": "manual_action"}
                        self._step(wf, "form", "waiting", "Form fields were processed; no safe next control was found.")
                        self._say(wid, "I’ve processed the current page. I couldn’t identify a safe next or final-submit control, so please review the page. If you need to navigate or click a site-specific control, do that in the browser and type **ready** here so I can continue.")
                self._save(wf)
            except KeyError:
                await self._fail(wid, "The browser session is no longer available. Reopen the portal and continue from the current application page.")
            except Exception as exc:
                await self._fail(wid, f"I paused because the current application page could not be processed: {str(exc)[:300]}")

    async def handle_upload(self, wid: str, file_path: Path, original_name: str) -> dict:
        stored = False
        try:
            async with self._lock(wid):
                wf = self._workflow(wid)
                uid = wf.get("user_id", "")
                text, method = DocumentIntelligenceAgent().extract_text(file_path)
                doc_type = self._classify_document(original_name, text)
                if uid:
                    doc_id = self.store.add_user_document(
                        uid, original_name, doc_type, str(file_path), text,
                        metadata={"method": method, "characters": len(text), "workflow_id": wid},
                    )
                else:
                    doc_id = str(uuid.uuid4())
                    self.store.add_document(doc_id, wid, original_name, str(file_path), text, doc_type)
                stored = True

                extracted = self._regex_extract(text)
                source = f"document:{original_name}"
                if uid:
                    extracted.update(extract_profile_from_text(text, original_name))
                if not extracted and text and self.llm.enabled:
                    extracted = self.llm.extract_profile(text, ["full_name", "email", "phone", "date_of_birth", "address_line_1", "city", "state", "postal_code", "education_level", "institution", "graduation_year", "annual_income"])
                    source = f"llama:{original_name}"
                if uid:
                    self.store.save_user_fields_bulk(uid, extracted, category="workflow_doc", source=source)
                else:
                    profile = self.store.get_profile()
                    for key, value in extracted.items():
                        if key not in profile:
                            self.store.save_profile_value(key, value, source)

                report = {"id": doc_id, "filename": original_name, "doc_type": doc_type, "stored": True,
                          "extraction_method": method, "characters_extracted": len(text),
                          "status": "available" if text else "stored_text_unavailable"}
                wf.setdefault("documents", []).append(report)
                pending = wf.get("pending_input") or {}
                resume = pending.get("kind") == "document"
                if resume and pending.get("field"):
                    try:
                        await self.browser.upload_file(wid, pending["field_index"], str(file_path), expected=pending["field"])
                        self._event(wid, "document_attached", f"Attached {original_name} to {pending['label']}")
                    except Exception:
                        self._event(wid, "document_upload_skipped", "The requested document field could not be updated")
                if resume:
                    wf["pending_input"] = None
                    wf["status"] = "running"
                self._save(wf)
                self._event(wid, "document_uploaded", f"Document received: {original_name}", {"doc_type": doc_type, "method": method, "characters": len(text)})
                self._say(wid, f"I received **{original_name}** and added it to your local document vault. {('I extracted ' + str(len(text)) + ' characters and will search them when filling the form.') if text else 'I stored the file; text extraction was not available for this file.'}")
                if resume:
                    self._schedule(wid, self._continue_form(wid))
                return report
        finally:
            if not stored:
                file_path.unlink(missing_ok=True)

    async def submit_otp(self, wid: str, otp: str):
        wf = self._workflow(wid)
        if (wf.get("pending_input") or {}).get("kind") != "otp":
            raise ValueError("Orqentra is not currently waiting for an OTP.")
        # Don't log OTP values in any route, store or audit event.
        result = await self.browser.submit_otp(wid, otp)
        wf["pending_input"] = None; wf["status"] = "running"; self._save(wf)
        self._say(wid, "The OTP was entered into the portal. I’m checking the response and continuing.")
        self._event(wid, "otp_entered", "OTP entered through secure chat field; value not retained")
        self._schedule(wid, self._continue_form(wid))
        return result

    async def submit_credentials(self, wid: str, username: str, password: str, action_type: str = "login"):
        wf = self._workflow(wid)
        if (wf.get("pending_input") or {}).get("kind") != "credentials":
            raise ValueError("Reply to the current question in chat.")
        self._event(wid, "credentials_provided", f"User submitted portal credentials for {action_type}; password not stored")
        self._say(wid, f"Attempting {action_type} on the portal in the background with provided credentials...")
        result = await self.browser.perform_login(wid, username, password, action_type)
        if result.get("success"):
            wf["pending_input"] = None
            wf["status"] = "running"
            self._save(wf)
            self._say(wid, f"Successfully authenticated on the portal in the background! Continuing to the application page...")
            self._schedule(wid, self._continue_form(wid))
        else:
            if result.get("captcha_detected"):
                wf["pending_input"] = {"kind": "manual_action"}
                wf["status"] = "waiting_user"
                self._save(wf)
                self._say(wid, "Credentials entered, but the portal displayed a CAPTCHA. Please solve it in the browser window, then type **ready** here.")
            else:
                reason = result.get("reason", "Could not complete login.")
                wf["status"] = "waiting_user"
                wf["pending_input"] = {"kind": "credentials", "action": action_type}
                self._save(wf)
                self._say(wid, f"Login result: {reason} Please verify your username and password, or complete sign-in in the open browser and send **ready**.")
        return {"workflow": self._workflow(wid), "result": result}

    async def submit_approval(self, wid: str, approved: bool, overrides: dict = None):
        wf = self._workflow(wid)
        if approved:
            wf["pending_input"] = None
            wf["status"] = "running"
            self._save(wf)
            self._say(wid, "Options approved. Continuing form processing in the background.")
            self._event(wid, "options_approved", "User approved proposed choices")
            self._schedule(wid, self._continue_form(wid))
        else:
            self._say(wid, "Approval cancelled. Please let me know what options or values you would like me to change.")
        return {"workflow": self._workflow(wid)}

    async def submit_action_choice(self, wid: str, action: str) -> dict:
        wf = self._workflow(wid)
        action_type = action.strip().lower()
        pending = wf.get("pending_input") or {}
        if pending.get("kind") != "portal_action_choice" or not any(
                choice["action"] == action_type for choice in pending.get("choices", [])):
            raise ValueError("Choose one of the portal options shown in chat.")

        self._say(wid, f"Navigating to **{action_type.title()}** on the portal...")
        self._event(wid, "action_selected", f"User selected portal action: {action_type}")
        result = await self.browser.navigate_action(wid, action_type)
        wf["portal_action"] = action_type
        self._resume(wf)
        return {"workflow": self._workflow(wid), "result": result}

    async def _wait_manual(self, wid: str, message: str):
        wf = self._workflow(wid); wf["status"] = "waiting_user"; wf["pending_input"] = {"kind": "manual_action"}; self._save(wf)
        self._say(wid, message)

    async def _fail(self, wid: str, message: str):
        wf = self._workflow(wid); wf["status"] = "error"; wf["last_error"] = message; self._save(wf)
        self._event(wid, "agent_error", message)
        self._say(wid, message)
        # Optimizer agent: record failure outcome for feedback loop (Claim 6).
        try:
            self.optimizer.run(self.store, wf)
        except Exception:
            pass

    @staticmethod
    def _extract_url(text: str) -> str | None:
        match = re.search(r"https://[^\s<>]+", text)
        return match.group(0).rstrip(".,);]") if match else None

    @staticmethod
    def _key_from_label(label: str) -> str:
        clean = re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()
        # Prefer the longest alias so "father name" cannot collapse to generic "name".
        candidates = []
        for key, aliases in ALIASES.items():
            for alias in aliases:
                normalized = re.sub(r"[^a-z0-9]+", " ", alias.lower()).strip()
                if normalized and re.search(r"(?:^| )" + re.escape(normalized) + r"(?: |$)", clean):
                    candidates.append((len(normalized), key))
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
        return "_".join(clean.split())[:80] or "additional_detail"

    def _parse_details(self, message: str, allowed_keys: list[str]) -> dict:
        result = {}
        for line in message.splitlines():
            if ":" not in line: continue
            label, value = line.split(":", 1)
            key = self._key_from_label(label)
            if key in allowed_keys and value.strip(): result[key] = value.strip()
        if not result and len(allowed_keys) == 1 and message.strip():
            key = allowed_keys[0]
            value = message.strip()
            value = re.sub(r"^(?:my\s+)?(?:full\s+)?name\s+is\s+", "", value, flags=re.I) if key == "full_name" else value
            value = re.sub(r"^(?:my\s+)?e-?mail(?:\s+(?:address|id))?\s+is\s+", "", value, flags=re.I) if key == "email" else value
            value = re.sub(r"^(?:my\s+)?(?:mobile|phone)(?:\s+number)?\s+is\s+", "", value, flags=re.I) if key == "phone" else value
            result[key] = value.strip().strip(".,")
        return result

    @staticmethod
    def _parse_prompt_facts(message: str) -> dict:
        """Extract only a few explicitly expressed, non-secret profile facts from the first prompt."""
        facts = {}
        patterns = {
            "full_name": r"(?i)\b(?:my\s+)?(?:full\s+)?name\s+is\s+([A-Za-z][A-Za-z .'-]{1,70}?)(?=,|;|\.|\band\b|$)",
            "email": r"(?i)\b(?:my\s+)?e-?mail(?:\s+address)?\s+is\s+([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
            "phone": r"(?i)\b(?:my\s+)?(?:mobile|phone)(?:\s+number)?\s+is\s+(\+?[0-9][0-9 ()-]{7,}[0-9])",
            "date_of_birth": r"(?i)\b(?:my\s+)?(?:date of birth|dob)\s*(?:is|:)\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, message)
            if match:
                value = match.group(1).strip()
                if value and not re.search(r"password|otp|pin|secret|token", key, re.I): facts[key] = value
        # Also accept explicit labelled facts in the prompt, e.g. "Gender: Female".
        for line in message.splitlines():
            for part in re.split(r";", line):
                if ":" not in part:
                    continue
                label, value = part.split(":", 1)
                key = AgentRuntime._key_from_label(label)
                if key in {"full_name", "given_name", "surname", "date_of_birth", "gender", "nationality", "marital_status", "email", "phone", "address_line_1", "address_line_2", "city", "district", "state", "postal_code", "country", "father_name", "mother_name", "occupation", "annual_income", "education_level", "institution", "course", "graduation_year", "grade", "employer", "years_experience", "organization", "registration_number", "passport_number", "visa_type", "travel_purpose"} and value.strip():
                    facts[key] = value.strip()
        return facts

    @staticmethod
    def _classify_document(filename: str, text: str) -> str:
        sample = (filename + " " + text[:1200]).lower()
        types = {
            "income_certificate": ("income certificate", "income proof", "salary certificate"),
            "identity_proof": ("aadhaar", "passport", "identity card", "national id", "identity proof", "id proof"),
            "address_proof": ("address proof", "utility bill", "residential address"),
            "education_certificate": ("mark sheet", "marksheet", "transcript", "degree certificate", "education certificate", "school certificate"),
            "photo": ("passport size photo", "photograph", "photo"),
            "signature": ("signature", "specimen signature"),
            "resume": ("resume", "curriculum vitae", "cv"),
            "bank_document": ("bank statement", "passbook", "cancelled cheque"),
        }
        for label, terms in types.items():
            if any(term in sample for term in terms): return label
        return "general_document"

    @staticmethod
    def _match_document(label: str, docs: list[dict]) -> dict | None:
        normalized = re.sub(r"[^a-z0-9]+", " ", label.lower())
        categories = {
            "income_certificate": ("income", "salary", "annual income"),
            "identity_proof": ("identity", "aadhaar", "passport", "national id", "id proof"),
            "address_proof": ("address", "residence", "utility bill"),
            "education_certificate": ("education", "marksheet", "mark sheet", "transcript", "degree", "academic"),
            "photo": ("photo", "photograph"),
            "signature": ("signature",),
            "resume": ("resume", "curriculum vitae", "cv"),
            "bank_document": ("bank", "passbook", "cancelled cheque"),
        }
        matched_types = [kind for kind, terms in categories.items() if any(term in normalized for term in terms)]
        if len(matched_types) != 1:
            return None
        expected = matched_types[0]
        for doc in docs:
            if doc.get("doc_type") == expected:
                return doc
            source = (doc["filename"] + " " + doc["doc_type"]).lower().replace("_", " ")
            if any(term in source for term in categories[expected]):
                return doc
        return None

    @staticmethod
    def _regex_extract(text: str) -> dict:
        values = {}
        for key, pattern in {
            "email": r"(?i)(?:e-?mail(?:\s+address)?\s*[:\-]?\s*)([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
            "phone": r"(?i)(?:mobile|phone|telephone)(?:\s+number)?\s*[:\-]?\s*(\+?[0-9][0-9 ()-]{7,}[0-9])",
            "full_name": r"(?im)^\s*(?:applicant\s+)?name\s*[:\-]\s*([A-Za-z][A-Za-z .'-]{2,80})\s*$",
            "date_of_birth": r"(?i)(?:date of birth|dob)\s*[:\-]?\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
            "postal_code": r"(?i)(?:pin code|postal code|zip code)\s*[:\-]?\s*([A-Z0-9 -]{4,10})",
        }.items():
            match = re.search(pattern, text)
            if match: values[key] = match.group(1).strip()
        return values
