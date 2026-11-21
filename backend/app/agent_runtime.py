"""Prompt-driven background agent runtime for Orqentra."""
from __future__ import annotations

import asyncio
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .browser_agent import BrowserAutomationAgent, ALIASES, suggest_field_mappings
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
            past = store.get_run_insights(service, limit=5)
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
        submit_authorized = any(x in goal_l for x in ("apply for me", "submit the application", "complete and submit", "apply on my behalf", "register me")) or bool(re.search(r"\b(apply for|apply to|submit|register for|enroll in|enrol in|renew my)\b", goal_l))
        wf = {"id": wid, "goal": message, "service": intent["service"], "task": intent["task"],
              "status": "running", "plan": plan, "active_step": "understand", "pending_input": None,
              "portal_candidates": [], "portal_url": None, "documents": [], "submit_authorized": submit_authorized,
              "created_at": None, "last_error": None, "current_page": None, "user_id": user_id}
        self.store.save_workflow(wf)
        self.store.add_message(wid, "user", message)
        for key, value in self._parse_prompt_facts(message).items():
            self.store.save_profile_value(key, value, f"prompt:{wid}")
        self._say(wid, "I’ve received your request. I’m identifying the application, checking your saved information and documents, and looking for the official portal. I’ll ask here only when I need something from you.")
        self._event(wid, "workflow_created", "Application request received", {"service": intent["service"]})
        self._schedule(wid, self._initial(wid))
        return wf

    async def chat(self, wid: str, message: str) -> dict:
        wf = self._workflow(wid)
        pending = wf.get("pending_input") or {}
        # OTPs are routed directly to the browser and deliberately never stored as chat messages/events.
        if pending.get("kind") == "otp":
            result = await self.browser.submit_otp(wid, message.strip())
            wf["pending_input"] = None
            wf["status"] = "running"
            self._save(wf)
            self._say(wid, "The OTP was entered into the portal. I’m checking the result and continuing the application.")
            self._event(wid, "otp_entered", "OTP entered through the secure chat input; value not retained")
            self._schedule(wid, self._continue_form(wid))
            return {"workflow": wf, "result": result}

        self.store.add_message(wid, "user", message)
        low = message.strip().lower()
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
            action = "login"
            if any(x in low for x in ("register", "signup", "sign up", "new user", "new registration", "create")):
                action = "register"
            elif any(x in low for x in ("apply", "application", "start")):
                action = "apply"
            elif any(x in low for x in ("login", "log in", "sign in", "signin", "existing")):
                action = "login"
            else:
                action = message.strip()
            return await self.submit_action_choice(wid, action)
        elif pending.get("kind") in {"login_ready", "credentials"}:
            if any(x in low for x in ("ready", "logged in", "log in", "login", "continue", "done", "ok", "okay", "signed in", "proceed", "i logged in", "i am logged in", "im logged in")):
                wf["pending_input"] = None; wf["status"] = "running"; self._save(wf)
                self._say(wid, "Thanks. I’m inspecting the current application page and matching its fields against your saved information.")
                self._schedule(wid, self._continue_form(wid))
            elif ":" in message or " " in message:
                parts = message.split(":", 1) if ":" in message else message.split(None, 1)
                u, p = parts[0].strip(), parts[1].strip()
                if len(p) >= 3:
                    return await self.submit_credentials(wid, u, p)
                else:
                    self._say(wid, "Please enter your username and password in the secure login box below, or sign in directly in the opened browser and type **ready**.")
            else:
                self._say(wid, "Please enter your login username and password in the secure login box below, or sign in directly on the official portal and type **ready** here.")
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
                self.store.save_profile_value(key, "", "user-skipped")
                self._say(wid, f"I’ve marked {pending.get('label', key)} as unavailable for now. I’ll check whether the portal allows it to be left blank.")
            else:
                parsed = self._parse_details(message, [key])
                value = parsed.get(key) or message.strip()
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
                memories = self.store.search_memory(query)
                wf["retrieved_memory"] = memories[:8]
                profile = self.store.get_profile()
                uid = wf.get("user_id", "")
                if uid:
                    try:
                        user_profile = self.store.get_user_profile(uid)
                        profile = {**profile, **user_profile}
                    except Exception:
                        pass
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
            popup_closed = result.get("popup_dismissed", False)
            popup_note = "I automatically closed the advisory/announcement popup. " if popup_closed else ""
            if popup_closed:
                self._event(wid, "popup_dismissed", "Dismissed advisory/announcement modal popup")

            # Detect all choices on the portal (Login, Register, Apply, etc.) and ask user to choose
            choices = await self.browser.detect_page_actions(wid)
            wf["status"] = "waiting_user"
            wf["pending_input"] = {"kind": "portal_action_choice", "choices": choices}
            self._step(wf, "requirements", "waiting", "Options available on official portal.")
            choices_text = "\n".join(f"• **{c['label']}**" for c in choices)
            self._say(wid, f"I opened the official portal and {popup_note}found the following options available on the portal:\n\n{choices_text}\n\nPlease choose which option you want to proceed with.")
            self._save(wf)
            self._save(wf)
        except Exception as exc:
            await self._fail(wid, f"I couldn’t open the portal: {str(exc)[:360]}. Check Playwright/Chromium installation and the portal address, then send ‘retry’ or a different HTTPS link.")

    async def _continue_form(self, wid: str, depth: int = 0):
        if depth > 12:
            await self._wait_manual(wid, "I’ve processed 12 application pages in this run. Please review the current page and type **ready** to continue.")
            return
        async with self._lock(wid):
            wf = self._workflow(wid)
            try:
                self._step(wf, "requirements", "running", "Inspecting the current form and identifying missing required details and documents.")
                inspected = await self.browser.inspect(wid)
                wf["current_page"] = {"url": inspected["url"], "title": inspected["title"], "field_count": len(inspected["fields"])}
                fields = inspected["fields"]
                challenge = inspected.get("challenge") or {}
                if challenge.get("captcha") or challenge.get("hasBiometric"):
                    reason = "The portal is requesting a CAPTCHA or biometric verification."
                    wf["status"] = "waiting_user"; wf["pending_input"] = {"kind": "manual_action"}
                    self._step(wf, "verification", "waiting", reason)
                    self._say(wid, reason + " Complete it directly on the official portal, then type **ready** here.")
                    self._save(wf); return
                otp_fields = [f for f in fields if not f.get("disabled") and not f.get("readonly") and re.search(r"\b(otp|one.?time password|verification code|security code)\b", str(f.get("label", "") + " " + f.get("name", "")), re.I)]
                if otp_fields:
                    wf["status"] = "waiting_user"; wf["pending_input"] = {"kind": "otp"}
                    self._step(wf, "verification", "waiting", "The official portal requested an OTP.")
                    self._say(wid, "The portal has requested an OTP. Enter it in the OTP response box in this chat. It will be sent directly to the browser and will not be saved in chat history or memory.", "otp_request")
                    self._save(wf); return

                other_sensitive = [f for f in fields if f.get("sensitive") and not f.get("disabled") and not f.get("readonly") and not re.search(r"\b(otp|one.?time password|verification code|security code)\b", str(f.get("label", "") + " " + f.get("name", "")), re.I)]
                if other_sensitive:
                    labels = ", ".join(str(f.get("label") or f.get("name") or "protected field") for f in other_sensitive[:3])
                    wf["status"] = "waiting_user"; wf["pending_input"] = {"kind": "manual_action"}
                    self._step(wf, "verification", "waiting", f"A protected field needs direct user handling: {labels}.")
                    self._say(wid, f"The portal is showing a protected field ({labels}). For safety, enter passwords, CAPTCHA answers, payment details or legal declarations directly on the official website, not in chat. When finished, type **ready** here and I’ll continue.")
                    self._save(wf); return

                profile = self.store.get_profile()
                # Merge encrypted user profile if user_id is available (higher priority)
                uid = wf.get("user_id", "")
                if uid:
                    try:
                        user_profile = self.store.get_user_profile(uid)
                        # User profile takes precedence over legacy profile
                        merged = {**profile, **user_profile}
                        profile = merged
                    except Exception:
                        pass
                suggestions = suggest_field_mappings(fields, profile)
                auto = [x for x in suggestions if x["confidence"] >= 0.88]
                if auto:
                    result = await self.browser.fill(wid, [{"field_index": x["field_index"], "value": x["value"], "profile_key": x["profile_key"], "expected_label": x["field_label"]} for x in auto])
                    self._event(wid, "fields_auto_filled", f"Auto-filled {len(result['filled'])} confidently matched field(s)", {"field_count": len(result["filled"])})
                    self._say(wid, f"I matched and filled **{len(result['filled'])}** field(s) from your saved profile. I’m checking for missing required items.")

                # Upload matching previously shared documents where the portal exposes a named file field.
                docs = self.store.get_documents()
                uploaded_field_indexes = set()
                for field in fields:
                    if str(field.get("type", "")).lower() != "file" or field.get("disabled"):
                        continue
                    label = str(field.get("label") or field.get("name") or "document").lower()
                    if not field.get("required"):
                        continue
                    match = self._match_document(label, docs)
                    if match:
                        try:
                            await self.browser.upload_file(wid, int(field["index"]), match["path"])
                            uploaded_field_indexes.add(int(field["index"]))
                            self._event(wid, "document_attached", f"Attached saved document {match['filename']} to {label}")
                            self._say(wid, f"I found and attached your previously uploaded **{match['filename']}** to the {label} field.")
                        except Exception as exc:
                            self._event(wid, "document_upload_skipped", str(exc)[:250])

                missing_docs = [f for f in fields if str(f.get("type", "")).lower() == "file" and f.get("required") and int(f["index"]) not in uploaded_field_indexes]
                if missing_docs:
                    field = missing_docs[0]
                    label = str(field.get("label") or field.get("name") or "required document")
                    wf["status"] = "waiting_user"; wf["pending_input"] = {"kind": "document", "label": label, "field_index": field["index"]}
                    self._step(wf, "requirements", "waiting", f"Waiting for required document: {label}.")
                    self._say(wid, f"The application requires **{label}**, and I couldn’t find a matching document in your saved vault. Please upload it using the document upload space below. I’ll attach it and resume automatically.", "document_request")
                    self._save(wf); return

                missing_fields = []
                filled_indexes = {int(x["field_index"]) for x in (result.get("filled", []) if auto else [])}
                for field in fields:
                    if not field.get("required") or field.get("disabled") or field.get("readonly"):
                        continue
                    typ = str(field.get("type", "text")).lower()
                    if typ not in {"text", "email", "tel", "date", "number", "url", "search", "textarea", "select", "radio", "checkbox"}:
                        continue
                    if field.get("sensitive") or int(field["index"]) in filled_indexes:
                        continue
                    label = str(field.get("group_label") or field.get("label") or field.get("name") or field.get("id") or "required field")
                    missing_fields.append((field, label, self._key_from_label(label)))
                if missing_fields:
                    field, label, key = missing_fields[0]
                    options = field.get("options") or []
                    opt_str = ""
                    opt_list = []
                    if options:
                        opt_list = [str(o.get("label") or o.get("value") or "").strip() for o in options if (o.get("label") or o.get("value"))]
                        opt_list = [x for x in opt_list if x][:8]
                        if opt_list:
                            opt_str = "\n\nAvailable portal choices:\n" + "\n".join(f"• {x}" for x in opt_list)
                    wf["status"] = "waiting_user"
                    wf["pending_input"] = {"kind": "detail", "label": label, "key": key, "field_index": field["index"], "options": opt_list}
                    self._step(wf, "requirements", "waiting", f"Waiting for required detail: {label}.")
                    self._say(wid, f"I need one detail to continue: **{label}**.{opt_str}\n\nPlease reply with your value or choice here. I’ll save it to your profile and fill it in.", "detail_request")
                    self._save(wf); return

                self._step(wf, "requirements", "completed", f"Inspected {len(fields)} visible fields and found no unmatched required ordinary fields or missing required documents.")
                self._step(wf, "form", "running", "Filling high-confidence fields from the local applicant profile and document vault.")
                # Advance only with a clear Next/Continue button; loop to inspect the next page.
                next_result = await self.browser.click_next(wid)
                if next_result.get("advanced"):
                    self._event(wid, "page_advanced", "Advanced to the next application page", {"url": next_result.get("url")})
                    self._step(wf, "form", "completed", "Current page populated; moved to next page.")
                    self._save(wf)
                    # Release lock before recursive call.
                    self._tasks[wid] = asyncio.create_task(self._continue_form(wid, depth + 1))
                    return

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
        wf = self._workflow(wid)
        text, method = DocumentIntelligenceAgent().extract_text(file_path)
        doc_type = self._classify_document(original_name, text)
        doc_id = str(uuid.uuid4())
        self.store.add_document(doc_id, wid, original_name, str(file_path), text, doc_type)
        # Save simple explicitly-labelled facts; never infer identity fields from arbitrary strings.
        extracted = self._regex_extract(text)
        for key, value in extracted.items():
            if key not in self.store.get_profile():
                self.store.save_profile_value(key, value, f"document:{original_name}")
        if not extracted and text and self.llm.enabled:
            fallback = self.llm.extract_profile(text, ["full_name", "email", "phone", "date_of_birth", "address_line_1", "city", "state", "postal_code", "education_level", "institution", "graduation_year", "annual_income"])
            for key, value in fallback.items():
                if key not in self.store.get_profile(): self.store.save_profile_value(key, value, f"llama:{original_name}")
        report = {"id": doc_id, "filename": original_name, "doc_type": doc_type, "stored": True,
                  "extraction_method": method, "characters_extracted": len(text), "preview": text[:700],
                  "status": "available" if text else "stored_text_unavailable"}
        wf.setdefault("documents", []).append(report)
        self._save(wf)
        self._event(wid, "document_uploaded", f"Document received: {original_name}", {"doc_type": doc_type, "method": method, "characters": len(text)})
        self._say(wid, f"I received **{original_name}** and added it to your local document vault. {('I extracted ' + str(len(text)) + ' characters and will search them when filling the form.') if text else 'I stored the file; text extraction was not available for this file.'}")
        if (wf.get("pending_input") or {}).get("kind") == "document":
            wf["pending_input"] = None; wf["status"] = "running"; self._save(wf)
            self._schedule(wid, self._continue_form(wid))
        return report

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
        action_clean = action.lower()
        if any(x in action_clean for x in ("reg", "signup", "sign up", "new")):
            action_type = "register"
        elif "apply" in action_clean:
            action_type = "apply"
        else:
            action_type = "login"

        self._say(wid, f"Navigating to **{action_type.title()}** on the portal...")
        self._event(wid, "action_selected", f"User selected portal action: {action_type}")
        result = await self.browser.navigate_action(wid, action_type)
        if result.get("next_step") == "credentials":
            wf["status"] = "waiting_user"
            wf["pending_input"] = {"kind": "credentials", "action": action_type}
            self._save(wf)
            self._say(wid, f"I have opened the **{action_type.title()}** page. Please enter your credentials in the secure box below to proceed, or complete it in the browser and send **ready**.")
        else:
            wf["status"] = "running"
            wf["pending_input"] = None
            self._save(wf)
            self._schedule(wid, self._continue_form(wid))
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
            value = re.sub(r"^(?:my\s+)?e-?mail(?:\s+address)?\s+is\s+", "", value, flags=re.I) if key == "email" else value
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
