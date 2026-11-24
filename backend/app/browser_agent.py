"""Playwright browser controls for Orqentra. Sensitive actions have separate methods."""
from __future__ import annotations

import asyncio
import ipaddress
import os
import re
from difflib import SequenceMatcher
from urllib.parse import urljoin, urlparse
from typing import Any

# Broad aliases for common fields across public services, education, employment,
# travel, housing, membership, business and other web application workflows.
ALIASES: dict[str, tuple[str, ...]] = {
    "full_name": ("full name", "applicant name", "name of applicant", "candidate name", "legal name", "complete name", "name"),
    "given_name": ("given name", "first name", "forename"),
    "middle_name": ("middle name", "middle initial"),
    "surname": ("surname", "last name", "family name"),
    "date_of_birth": ("date of birth", "dob", "birth date", "birthday"),
    "place_of_birth": ("place of birth", "birth place"),
    "gender": ("gender", "sex"),
    "nationality": ("nationality", "citizenship", "country of citizenship"),
    "marital_status": ("marital status", "marriage status"),
    "email": ("email", "email address", "email id", "e-mail", "e-mail id", "contact email"),
    "login_id": ("login id", "user id", "username", "user name", "username or email", "user id or email"),
    "login_id_same_as_email": ("do you want your login id to be same as e-mail id", "use email as login id"),
    "registration_office": ("register to apply at",),
    "phone": ("phone", "mobile number", "phone number", "contact number", "telephone", "mobile", "cell number"),
    "alternate_phone": ("alternate phone", "alternate mobile", "secondary phone"),
    "address_line_1": ("address line 1", "address line one", "house number and street", "street address", "address", "residential address"),
    "address_line_2": ("address line 2", "address line two", "apartment", "unit number"),
    "city": ("city", "town", "village", "municipality"),
    "post_office": ("post office", "postal office"),
    "district": ("district", "county"),
    "state": ("state", "province", "region"),
    "postal_code": ("postal code", "pin code", "pincode", "zip code", "postcode"),
    "country": ("country", "country of residence"),
    "permanent_address": ("permanent address", "home address"),
    "current_address": ("current address", "present address", "residential address"),
    "father_name": ("father name", "father's name", "name of father"),
    "mother_name": ("mother name", "mother's name", "name of mother"),
    "spouse_name": ("spouse name", "husband or wife name", "name of spouse"),
    "emergency_contact_name": ("emergency contact name", "name of emergency contact"),
    "emergency_contact_phone": ("emergency contact phone", "emergency contact number"),
    "occupation": ("occupation", "profession", "job title", "current employment"),
    "employer": ("employer", "company name", "organization name", "workplace"),
    "employment_status": ("employment status", "work status"),
    "annual_income": ("annual income", "yearly income", "income per annum", "annual household income"),
    "tax_id": ("tax identification number", "tax id", "taxpayer identification"),
    "national_id": ("national identification number", "national id", "identity number", "government id number"),
    "guardian_name": ("guardian name", "parent or guardian", "name of guardian"),
    "education_level": ("education level", "highest qualification", "highest education"),
    "institution": ("institution", "school name", "college name", "university name", "educational institution"),
    "course": ("course", "program", "programme", "degree", "study program"),
    "field_of_study": ("field of study", "major", "subject", "subjects", "specialization"),
    "graduation_year": ("graduation year", "year of passing", "year completed"),
    "years_experience": ("years of experience", "work experience", "experience in years"),
    "previous_employer": ("previous employer", "previous company", "last employer"),
    "current_salary": ("current salary", "present salary", "current ctc"),
    "expected_salary": ("expected salary", "salary expectation", "expected ctc"),
    "skills": ("skills", "key skills", "technical skills"),
    "grade": ("grade", "cgpa", "gpa", "percentage", "marks"),
    "application_id": ("application id", "application number", "reference number"),
    "service_type": ("service type", "application type", "type of service"),
    "purpose": ("purpose", "purpose of application", "reason for application"),
    "organization": ("organization", "company", "business name", "institution name"),
    "registration_number": ("registration number", "company registration number", "business registration number"),
    "website": ("website", "website url", "web address"),
    "accommodation_address": ("accommodation address", "hotel address", "place of stay"),
    "accommodation_name": ("accommodation name", "hotel name", "place of stay name"),
    "passport_number": ("passport number", "previous passport number", "existing passport number"),
    "visa_type": ("visa type", "type of visa"),
    "travel_purpose": ("travel purpose", "purpose of visit"),
    "arrival_date": ("arrival date", "date of arrival"),
    "departure_date": ("departure date", "date of departure"),
}

BLOCKED_WORDS = {
    "password", "passcode", "otp", "one time password", "captcha", "verification code",
    "security code", "characters shown in the image", "characters in the image",
    "payment", "card number", "cvv", "pin number",
    "signature", "bank account", "account number", "routing number", "ifsc", "swift code",
    "agree to terms", "terms and conditions", "declaration", "consent", "i agree",
}
ALLOWED_INPUT_TYPES = {"text", "email", "tel", "date", "number", "url", "search", "textarea", "select", "radio", "checkbox"}
FORM_CONTROLS = 'input:not([type="hidden"]), textarea, select'
FIELD_METADATA = r"""(el, index) => {
    const text = node => (node?.innerText || node?.textContent || '').trim();
    const labels = Array.from(el.labels || []);
    const ariaLabel = el.getAttribute('aria-label') || '';
    const referenced = (el.getAttribute('aria-labelledby') || '').split(/\s+/)
        .map(id => text(document.getElementById(id))).filter(Boolean).join(' ');
    const type = el.tagName === 'SELECT' ? 'select' : (el.type || el.tagName).toLowerCase();
    const option = ['radio', 'checkbox'].includes(type);
    const group = el.closest('[role="radiogroup"], [role="group"], fieldset');
    const groupReference = (group?.getAttribute('aria-labelledby') || '').split(/\s+/)
        .map(id => text(document.getElementById(id))).filter(Boolean).join(' ');
    const adjacentLabel = node => node?.matches('label, .form-label') ? text(node) : '';
    const nearbyLabel = adjacentLabel(el.previousElementSibling) ||
        (el.parentElement?.querySelectorAll('input,select,textarea').length === 1 ?
            adjacentLabel(el.parentElement.previousElementSibling) : '');
    const optionLabel = labels.map(text).filter(Boolean).join(' ') || ariaLabel || referenced;
    let radioLabel = '';
    if (type === 'radio' && el.name) {
        for (let parent = el.parentElement; parent && parent !== el.form; parent = parent.parentElement) {
            const radios = Array.from(parent.querySelectorAll('input[type="radio"]'));
            if (radios.length < 2) continue;
            if (radios.every(radio => radio.name === el.name)) {
                radioLabel = text(parent.querySelector('label:not([for]):not(:has(input)), .form-label')) ||
                    adjacentLabel(parent.previousElementSibling);
                if (radioLabel) break;
            } else break;
        }
    }
    const groupLabel = text(group?.querySelector('legend')) || group?.getAttribute('aria-label') ||
        groupReference || text(el.closest('tr')?.querySelector('th')) || radioLabel || '';
    const comboControl = el.closest('[class*="-control"]');
    const combo = el.getAttribute('role') === 'combobox' && comboControl;
    const comboLabel = (/^(state|city)$/i.test(comboControl?.parentElement?.id || '') ? comboControl.parentElement.id : '') ||
        (/^subjectsInput$/i.test(el.id) ? 'Subjects' : '') ||
        text(comboControl?.querySelector('[class*="-placeholder"]'));
    const label = optionLabel || nearbyLabel || comboLabel || el.placeholder || el.name || el.id || '';
    const birthPicker = type === 'text' && !!el.closest('.react-datepicker-wrapper') &&
        /date[ _-]*of[ _-]*birth|\bdob\b/i.test(label + ' ' + el.id);
    const dateDefault = birthPicker && el.value === el.defaultValue &&
        new Date(el.value).toDateString() === new Date().toDateString();
    const digitHint = (label + ' ' + el.placeholder).match(/\b(\d{1,2})[ -]*digits?\b/i);
    const patternLength = (el.getAttribute('pattern') || '').match(/^\^?(?:\\d|\[0-9\])\{(\d{1,2})\}\$?$/);
    const phone = type === 'tel' || /\b(mobile|phone|telephone|contact number)\b/i.test(label);
    const digits = phone ? Number(digitHint?.[1] || patternLength?.[1] || (el.maxLength === 10 ? 10 : 0)) : 0;
    const displayed = !!el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
    const required = el.required || el.getAttribute('aria-required') === 'true' ||
        group?.getAttribute('aria-required') === 'true' ||
        ((option ? groupLabel + ' ' + label : label).includes('*'));
    return {index, type, label: label.replace(/\s*\*\s*$/, '').trim(),
        option_label: option ? (optionLabel || el.value) : '', group_label: groupLabel.replace(/\s*\*\s*$/, '').trim(),
        name: el.name || '', id: el.id || '', placeholder: el.placeholder || '',
        autocomplete: el.getAttribute('autocomplete') || '', required: !!required,
        disabled: el.matches(':disabled') || !displayed, readonly: !!el.readOnly,
        form_action: el.form?.action || '',
        digits, combo: !!combo, birth_picker: birthPicker,
        has_value: option ? el.checked : combo ?
            !!comboControl.querySelector('[class*="-singleValue"], [class*="-multiValue"], [class*="-multi-value"], [role="button"][aria-label^="Remove"]') :
            !!el.value && !dateDefault,
        valid: el.validity?.valid !== false && el.getAttribute('aria-invalid') !== 'true' &&
            (!digits || new RegExp('^\\d{' + digits + '}$').test(el.value)),
        options: type === 'select' ? Array.from(el.options).filter(o => o.value && !o.disabled)
            .map(o => ({label: o.text, value: o.value})) : []};
}"""


def _clean(value: str) -> str:
    raw = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value or ""))
    return re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip()


def is_sensitive(label: str, input_type: str = "") -> bool:
    haystack = f" {_clean(label)} {_clean(input_type)} "
    return any(f" {word} " in haystack for word in BLOCKED_WORDS)


def portal_origin(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        return ""
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    return f"https://{host}" + (f":{parsed.port}" if parsed.port not in {None, 443} else "")


def field_label(field: dict[str, Any]) -> str:
    return str(field.get("label") or field.get("name") or field.get("id") or f"Field {int(field['index']) + 1}")


def allowed_host(url: str, allowlist: list[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(host)
        if not address.is_global:
            return False
    except ValueError:
        pass
    if "*" in allowlist:
        return True
    for allowed in allowlist:
        domain = allowed.strip().lower().lstrip(".").rstrip(".")
        if domain and (host == domain or host.endswith("." + domain)):
            return True
    return False


def _flatten_profile(profile: dict[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for key, value in profile.items():
        full_key = f"{prefix}_{key}" if prefix else str(key)
        if isinstance(value, dict):
            rows.extend(_flatten_profile(value, full_key))
        elif value is not None:
            rows.append((full_key, value))
    return rows


def _score_alias(searchable: str, alias: str) -> float:
    a = _clean(alias)
    if not a:
        return 0.0
    if searchable == a:
        return 1.0
    if a == "name" and searchable != "name":
        return 0.0
    if re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", searchable):
        return 0.96 if len(a.split()) > 1 else 0.89
    ratio = SequenceMatcher(None, a, searchable).ratio()
    return ratio * 0.9 if ratio >= 0.84 else 0.0


def suggest_field_mappings(fields: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Suggest conservative mappings for ordinary form controls.

    The background runtime auto-fills only high-confidence, non-sensitive matches.
    The manual browser API can also return these suggestions for explicit approval.
    Radio options are matched to the saved profile value; checkbox values require
    an explicit boolean or selected value.
    """
    suggestions: list[dict[str, Any]] = []
    selected_groups: set[str] = set()
    profile_items = [(key, value) for key, value in _flatten_profile(profile)
                     if str(value).strip() not in {"", "[decryption error]"}]

    # Process explicit option matches first so e.g. gender='Female' can map to
    # the corresponding radio option rather than only matching the group label.
    for field in fields:
        input_type = str(field.get("type") or "text").lower()
        if input_type not in {"radio", "checkbox"} or field.get("disabled") or field.get("readonly") or field.get("sensitive"):
            continue
        option = _clean(str(field.get("option_label") or field.get("label") or ""))
        group = _clean(str(field.get("group_label") or field.get("name") or ""))
        group_key = str(field.get("name") or group or field["index"])
        if input_type == "radio" and group_key in selected_groups:
            continue
        if is_sensitive(f"{group} {option}", input_type):
            continue
        best = None
        for key, value in profile_items:
            if is_sensitive(key):
                continue
            tail = key.split("_")[-1] if key not in ALIASES else key
            aliases = (key.replace("_", " "), tail.replace("_", " ")) + ALIASES.get(key, ()) + ALIASES.get(tail, ())
            key_score = max((_score_alias(group, alias) for alias in aliases), default=0.0)
            value_texts = [str(x) for x in value] if isinstance(value, list) else [str(value)]
            value_match = max((1.0 for v in value_texts if _clean(v) == option and option), default=0.0)
            if input_type == "radio" and value_match and key_score >= 0.35:
                score = min(0.99, 0.90 + key_score * 0.09)
                if best is None or score > best[0]:
                    best = (score, key, "true")
            elif input_type == "checkbox":
                if isinstance(value, bool) and key_score >= 0.82 and _clean(key.replace("_", " ")) == option:
                    best = (0.96, key, "true" if value else "false")
                elif isinstance(value, list) and value_match and key_score >= 0.35:
                    best = (0.96, key, "true")
        if best:
            if input_type == "radio":
                selected_groups.add(group_key)
            suggestions.append({
                "field_index": int(field["index"]), "field_label": str(field.get("label") or field.get("option_label") or f"Field {field['index'] + 1}"),
                "input_type": input_type, "profile_key": best[1], "value": best[2], "confidence": round(best[0], 2),
            })

    for field in fields:
        input_type = str(field.get("type") or "text").lower()
        if input_type in {"radio", "checkbox"} or field.get("disabled") or field.get("readonly"):
            continue
        if input_type not in ALLOWED_INPUT_TYPES or field.get("sensitive") or is_sensitive(field_label(field), input_type):
            continue
        labels = [_clean(str(field.get(k) or "")) for k in ("label", "name", "id", "placeholder", "autocomplete")]
        searchable = _clean(" ".join(labels))
        best: tuple[float, str, Any] | None = None
        for key, value in profile_items:
            if isinstance(value, (dict, list)) or is_sensitive(key):
                continue
            tail = key.split("_")[-1] if key not in ALIASES else key
            aliases = (key.replace("_", " "), tail.replace("_", " ")) + ALIASES.get(key, ()) + ALIASES.get(tail, ())
            score = max((_score_alias(label, alias) for label in [*labels, searchable] for alias in aliases), default=0.0)
            if best is None or score > best[0]:
                best = (score, key, value)
        if best and best[0] >= 0.82:
            suggestions.append({
                "field_index": int(field["index"]),
                "field_label": str(field.get("label") or field.get("name") or field.get("id") or f"Field {field['index'] + 1}"),
                "input_type": input_type, "profile_key": best[1], "value": str(best[2]), "confidence": round(best[0], 2),
            })
    return sorted(suggestions, key=lambda item: item["field_index"])


class BrowserAutomationAgent:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _allowlist() -> list[str]:
        raw = os.getenv("ORQENTRA_ALLOWED_PORTAL_HOSTS", "*")
        return [x.strip() for x in raw.split(",") if x.strip()]

    @classmethod
    def config(cls) -> dict[str, Any]:
        hosts = cls._allowlist()
        return {"allowed_hosts": hosts, "allow_any_https_host": "*" in hosts,
                "headless": os.getenv("ORQENTRA_HEADLESS", "false").lower() in {"1", "true", "yes"}}

    async def open_portal(self, workflow_id: str, url: str) -> dict[str, Any]:
        if not allowed_host(url, self._allowlist()):
            raise ValueError("This HTTPS host is not allowed. Set ORQENTRA_ALLOWED_PORTAL_HOSTS=* for any HTTPS website, or add the exact host to the allow-list, then restart Orqentra.")
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed. In the active virtual environment run: python -m pip install -r requirements.txt && python -m playwright install chromium") from exc

        await self.close(workflow_id)
        async with self._lock:
            playwright = await async_playwright().start()
            headless = self.config()["headless"]
            browser = None
            try:
                browser = await playwright.chromium.launch(headless=headless)
                context = await browser.new_context(viewport={"width": 1440, "height": 1000})
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                if not allowed_host(page.url, self._allowlist()):
                    await context.close()
                    await browser.close()
                    raise ValueError("The site redirected to a host outside the allow-list. Add that login/identity-provider host and restart Orqentra.")
                # Auto-dismiss announcement / ad modal popups immediately after page load
                await page.wait_for_timeout(1000)
                popup_dismissed = await self._dismiss_popups(page)
                self._sessions[workflow_id] = {"playwright": playwright, "browser": browser, "context": context, "page": page}
                return {"workflow_id": workflow_id, "url": page.url, "title": await page.title(), "headless": headless,
                        "popup_dismissed": popup_dismissed,
                        "message": "Website opened and announcement/ad popups dismissed."}
            except Exception as exc:
                if browser:
                    try: await browser.close()
                    except Exception: pass
                try: await playwright.stop()
                except Exception: pass
                if isinstance(exc, ValueError):
                    raise
                detail = str(exc)
                if "Executable doesn't exist" in detail or "browserType.launch" in detail:
                    detail = "Chromium is not installed for this Python environment. Run: python -m playwright install chromium"
                elif "Timeout" in detail or "timed out" in detail.lower():
                    detail = "The site did not finish loading within 60 seconds. Check your internet connection, try the portal homepage, or use a less restrictive network."
                elif "CERT" in detail or "SSL" in detail:
                    detail = "The HTTPS certificate could not be verified. Check the computer date, network proxy, and portal URL. Orqentra will not bypass certificate errors."
                raise RuntimeError(detail[:500]) from exc

    def _page(self, workflow_id: str):
        session = self._sessions.get(workflow_id)
        if not session:
            raise KeyError("No browser session. Open the website first.")
        return session["page"]

    async def _dismiss_popups(self, page) -> bool:
        """Close visible announcements and ads using their own dismiss controls."""
        overlays = page.locator(
            '.modal:visible, dialog:visible, [role="dialog"]:visible, '
            '[aria-modal="true"]:visible, .advertisement-popup:visible, '
            '.ad-popup:visible, .announcement-popup:visible'
        )
        close_controls = (
            'button.btn-close, button.close, a.close, [data-bs-dismiss="modal"], '
            '[data-dismiss="modal"], [aria-label="close" i], '
            '[aria-label="close advertisement" i], [title="close" i]'
        )
        close_label = re.compile(r"^\s*(?:close(?: ad(?:vertisement)?)?|dismiss|skip ad|no thanks|[×✕✖])\s*$", re.I)
        dismissed = False
        for _ in range(3):
            closed = False
            for overlay in await overlays.all():
                if not await overlay.is_visible():
                    continue
                text = await overlay.inner_text(timeout=1000)
                if re.search(r"\b(consent|declaration|terms and conditions|payment|captcha)\b", text, re.I):
                    continue
                if await overlay.locator('input:not([type="hidden"]):visible, select:visible, textarea:visible').count():
                    continue
                controls = overlay.locator(close_controls).or_(
                    overlay.get_by_role("button", name=close_label)
                ).or_(overlay.get_by_role("link", name=close_label))
                for control in await controls.all():
                    try:
                        await control.click(timeout=1000)
                    except Exception:
                        continue
                    dismissed = closed = True
                    break
                if closed:
                    break
            if not closed:
                break
        return dismissed

    async def take_screenshot(self, workflow_id: str) -> bytes:
        """Capture screenshot of the current page."""
        async with self._lock:
            page = self._page(workflow_id)
            passwords = page.locator('input[type="password"], input[autocomplete$="-password"], input[name*="password" i]')
            return await page.screenshot(type="jpeg", quality=60, mask=[passwords])

    async def detect_page_actions(self, workflow_id: str) -> list[dict[str, Any]]:
        """Detect available authentication and navigation choices on the landing page."""
        async with self._lock:
            page = self._page(workflow_id)
            await self._dismiss_popups(page)
            actions = await page.evaluate(r"""() => {
                const elements = Array.from(document.querySelectorAll('a, button, [role="button"], input[type=submit]'));
                const found = [];
                for (const el of elements) {
                    const text = (el.innerText || el.textContent || el.value || '').trim();
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    if (/^(log ?in(?: \(existing user\))?|existing user|sign in|applicant login|citizen login)$/i.test(text)) {
                        if (!found.some(f => f.action === 'login')) found.push({ label: 'Log In (Existing User)', action: 'login', text });
                    } else if (/^(register(?: \(new user\))?|new user(?: registration)?|sign up|new registration|create account)$/i.test(text)) {
                        if (!found.some(f => f.action === 'register')) found.push({ label: 'Register (New User)', action: 'register', text });
                    } else if (/^(apply for passport|apply online|apply now|start application|new application)$/i.test(text)) {
                        if (!found.some(f => f.action === 'apply')) found.push({ label: text || 'Apply Online', action: 'apply', text });
                    }
                }
                return found;
            }""")
            return actions

    async def navigate_action(self, workflow_id: str, action: str) -> dict[str, Any]:
        """Navigate to the user-selected action on the portal."""
        async with self._lock:
            page = self._page(workflow_id)
            if not allowed_host(page.url, self._allowlist()):
                raise ValueError("Current page is outside the configured host allow-list.")
            await self._dismiss_popups(page)

            patterns = {
                "login": r"^\s*(log ?in(?: \(existing user\))?|existing user|sign in|applicant login|citizen login)\s*$",
                "register": r"^\s*(register(?: \(new user\))?|new user(?: registration)?|sign up|new registration|create account)\s*$",
                "apply": r"^\s*(apply for passport|apply online|apply now|start application|new application)\s*$"
            }
            pattern = patterns.get(action.lower(), action)
            navigated = False

            # Check links with href first (bypasses target=_blank tab creation)
            links = page.locator('a').filter(has_text=re.compile(pattern, re.I))
            count = await links.count()
            for i in range(count):
                el = links.nth(i)
                try:
                    if await el.is_visible():
                        href = await el.get_attribute("href")
                        if href and not href.startswith("javascript:") and not href.startswith("#"):
                            full_url = urljoin(page.url, href)
                            if not allowed_host(full_url, self._allowlist()):
                                continue
                            await page.goto(full_url, wait_until="domcontentloaded", timeout=45000)
                            if not allowed_host(page.url, self._allowlist()):
                                raise ValueError("The portal action redirected outside the configured host allow-list.")
                            await self._dismiss_popups(page)
                            navigated = True
                            break
                        await el.click(timeout=4000)
                        try: await page.wait_for_load_state("domcontentloaded", timeout=12000)
                        except Exception: pass
                        await self._dismiss_popups(page)
                        navigated = True
                        break
                except Exception:
                    continue

            if not navigated:
                buttons = page.get_by_role("button", name=re.compile(pattern, re.I))
                for button in await buttons.all():
                    if await button.is_visible() and await button.is_enabled():
                        await button.click(timeout=4000)
                        navigated = True
                        break

            if not allowed_host(page.url, self._allowlist()):
                raise ValueError("The portal action redirected outside the configured host allow-list.")
            if navigated:
                await self._dismiss_popups(page)
            return {
                "action": action,
                "url": page.url,
                "title": await page.title(),
                "next_step": "form",
                "navigated": navigated,
            }

    async def perform_login(self, workflow_id: str, username: str, password: str, action: str = "login") -> dict[str, Any]:
        """Automatically enter credentials into the portal in the background."""
        async with self._lock:
            page = self._page(workflow_id)
            if not allowed_host(page.url, self._allowlist()):
                raise ValueError("Current page is outside the configured host allow-list.")
            await self._dismiss_popups(page)

            # If action is login and password input is not on current page, click Login link/button
            if action == "login" and await page.locator('input[type="password"]').count() == 0:
                login_links = page.locator('a, button, [role="button"]')
                for i in range(min(await login_links.count(), 30)):
                    el = login_links.nth(i)
                    try:
                        txt = (await el.inner_text()).strip()
                        if re.search(r"^\s*(login|sign in|existing user|citizen login|applicant login)\s*$", txt, re.I):
                            if await el.is_visible():
                                href = await el.get_attribute("href")
                                if href and not href.startswith("javascript:") and not href.startswith("#"):
                                    full_url = href if href.startswith("http") else urlparse(page.url)._replace(path=href).geturl()
                                    if allowed_host(full_url, self._allowlist()):
                                        await page.goto(full_url, wait_until="domcontentloaded", timeout=45000)
                                        await self._dismiss_popups(page)
                                        break
                                await el.click(timeout=3000)
                                try: await page.wait_for_load_state("domcontentloaded", timeout=12000)
                                except Exception: pass
                                await self._dismiss_popups(page)
                                break
                    except Exception:
                        continue

            # If action is signup and password input is not on current page, click Register link/button
            if action == "signup" and await page.locator('input[type="password"]').count() == 0:
                reg_links = page.locator('a, button, [role="button"]')
                for i in range(min(await reg_links.count(), 30)):
                    el = reg_links.nth(i)
                    try:
                        txt = (await el.inner_text()).strip()
                        if re.search(r"^\s*(register|sign up|new user|new registration|create account)\s*$", txt, re.I):
                            if await el.is_visible():
                                href = await el.get_attribute("href")
                                if href and not href.startswith("javascript:") and not href.startswith("#"):
                                    full_url = href if href.startswith("http") else urlparse(page.url)._replace(path=href).geturl()
                                    if allowed_host(full_url, self._allowlist()):
                                        await page.goto(full_url, wait_until="domcontentloaded", timeout=45000)
                                        await self._dismiss_popups(page)
                                        break
                                await el.click(timeout=3000)
                                try: await page.wait_for_load_state("domcontentloaded", timeout=12000)
                                except Exception: pass
                                await self._dismiss_popups(page)
                                break
                    except Exception:
                        continue

            # Identify username or email input
            user_input = None
            selectors = [
                'input[type="email"]',
                'input[name*="user" i]', 'input[name*="login" i]', 'input[name*="email" i]', 'input[name*="id" i]',
                'input[id*="user" i]', 'input[id*="login" i]', 'input[id*="email" i]', 'input[id*="id" i]',
                'input[placeholder*="user" i]', 'input[placeholder*="email" i]', 'input[placeholder*="mobile" i]',
                'input[type="text"]:not([readonly]):not([disabled])', 'input[type="tel"]'
            ]
            for sel in selectors:
                candidates = page.locator(sel)
                cnt = await candidates.count()
                for i in range(cnt):
                    c = candidates.nth(i)
                    if await c.is_visible() and await c.is_enabled():
                        user_input = c
                        break
                if user_input:
                    break

            # Identify password input
            pwd_input = None
            pwd_cands = page.locator('input[type="password"]')
            for i in range(await pwd_cands.count()):
                c = pwd_cands.nth(i)
                if await c.is_visible() and await c.is_enabled():
                    pwd_input = c
                    break

            if not user_input or not pwd_input:
                return {"success": False, "reason": "Could not identify visible login username and password fields on the current portal page."}

            await user_input.fill(username)
            await pwd_input.fill(password)

            # Check for CAPTCHA challenge
            captcha = await page.evaluate("""() => {
              const body = (document.body?.innerText || '').slice(0, 10000);
              return !!document.querySelector('iframe[src*="recaptcha"], iframe[title*="challenge" i], .g-recaptcha, [data-sitekey]') ||
                     /enter the captcha|security code shown above/i.test(body);
            }""")
            if captcha:
                return {"success": False, "captcha_detected": True, "reason": "The portal requires a CAPTCHA. Please solve it in the browser window, then send ready."}

            # Locate and click submit / login button
            btn = None
            for pattern in [r"^\s*(sign in|log in|login|submit|continue|proceed|register|create account)\s*$", r"login", r"sign in"]:
                cands = page.get_by_role("button", name=re.compile(pattern, re.I))
                if await cands.count():
                    for i in range(await cands.count()):
                        c = cands.nth(i)
                        if await c.is_visible() and await c.is_enabled():
                            btn = c
                            break
                    if btn:
                        break

            if not btn:
                submits = page.locator('input[type="submit"], button[type="submit"]')
                if await submits.count():
                    for i in range(await submits.count()):
                        c = submits.nth(i)
                        if await c.is_visible() and await c.is_enabled():
                            btn = c
                            break

            if btn:
                try:
                    await btn.scroll_into_view_if_needed(timeout=2000)
                    await btn.click(timeout=5000)
                except Exception:
                    await btn.evaluate("el => el.click()")
            else:
                await pwd_input.press("Enter")

            try:
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                pass

            body_after = (await page.locator("body").inner_text())[:4000].lower()
            if re.search(r"invalid (username|password|credentials)|incorrect (username|password|credentials)|authentication failed|login failed", body_after):
                return {"success": False, "reason": "The portal reported invalid credentials. Please check your username and password."}

            return {"success": True, "url": page.url, "title": await page.title(), "message": "Credentials submitted to portal."}

    async def navigate_to_application(self, workflow_id: str, goal: str = "application") -> dict[str, Any]:
        """Try a conservative in-portal link discovery before asking the user to navigate."""
        async with self._lock:
            page = self._page(workflow_id)
            if not allowed_host(page.url, self._allowlist()):
                raise ValueError("Current page is outside the configured host allow-list.")
            await self._dismiss_popups(page)
            info = await page.locator("body").evaluate("""body => ({text:(body.innerText || '').slice(0,12000),
              passwordCount:Array.from(document.querySelectorAll('input[type=password]')).filter(e => e.offsetWidth || e.offsetHeight || e.getClientRects().length).length,
              visibleInputs:Array.from(document.querySelectorAll('input:not([type=hidden]),textarea,select')).filter(e => e.offsetWidth || e.offsetHeight || e.getClientRects().length).length})""")

            auth_info = await page.locator("body").evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a, button, [role="button"], input[type=submit]'));
                const hasLogin = links.some(el => {
                    const txt = (el.innerText || el.textContent || el.value || '').trim().toLowerCase();
                    return /^(login|sign in|existing user|applicant login|citizen login)$/.test(txt);
                });
                const hasRegister = links.some(el => {
                    const txt = (el.innerText || el.textContent || el.value || '').trim().toLowerCase();
                    return /^(register|sign up|new user|new registration|create account)$/.test(txt);
                });
                return { hasLogin, hasRegister };
            }""")

            if info["passwordCount"]:
                return {"found": False, "login_required": True, "has_form": info["passwordCount"] > 0, "has_login": auth_info.get("hasLogin", False), "has_register": auth_info.get("hasRegister", False), "url": page.url, "title": await page.title()}
            page_title = await page.title()
            if info["visibleInputs"] >= 2 and re.search(r"application|apply|admission|registration|scholarship|service", page_title + " " + info["text"], re.I):
                return {"found": True, "login_required": False, "has_form": True, "url": page.url, "title": page_title}
            links = await page.locator("a").evaluate_all("""els => els.filter(el => el.getClientRects().length && getComputedStyle(el).visibility === 'visible').map(el => ({text:(el.innerText || el.getAttribute('aria-label') || '').trim(),href:el.href || ''})).filter(x => x.text && x.href)""")
            goal_terms = [x for x in re.findall(r"[a-z]{4,}", goal.lower()) if x not in {"application", "apply", "portal", "official", "please", "complete", "submit", "online"}]
            scored = []
            for item in links:
                label = item["text"].lower()
                href = item["href"].lower()
                if re.search(r"logout|log out|help|contact|privacy|terms|track status|download", label):
                    continue
                score = 0
                if re.search(r"apply online|new application|start application|application form|apply now|start fresh", label):
                    score += 7
                elif re.search(r"existing user|user login|citizen login|applicant login|sign in|log in", label):
                    continue
                elif re.search(r"application|apply|admission|registration|register|enrol|enroll|start|renewal", label):
                    score += 4
                if any(term in label or term in href for term in goal_terms):
                    score += 2
                if urlparse(item["href"]).hostname == urlparse(page.url).hostname:
                    score += 2
                if score >= 7 and allowed_host(item["href"], self._allowlist()):
                    scored.append((score, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            ambiguous = len(scored) > 1 and scored[0][0] == scored[1][0]
            if scored and not ambiguous:
                target = scored[0][1]
                # Navigate directly to an allow-listed HTTPS href so target=_blank does not
                # silently create a second page that the runtime cannot observe.
                await page.goto(target["href"], wait_until="domcontentloaded", timeout=45000)
                if not allowed_host(page.url, self._allowlist()):
                    raise ValueError("The application link redirected outside the configured host allow-list.")
                await self._dismiss_popups(page)
                is_auth_page = await page.locator("input[type=password]:visible").count() > 0
                has_form = await page.locator(
                    'form input:not([type="hidden"]):not([type="submit"]):visible, form select:visible, form textarea:visible'
                ).count() > 0
                return {"found": True, "login_required": is_auth_page, "has_form": has_form, "url": page.url, "title": await page.title(), "link_text": target["text"]}
            return {"found": False, "login_required": False, "url": page.url, "title": await page.title(), "ambiguous": ambiguous, "reason": "No clear application entry link was found."}

    async def inspect(self, workflow_id: str) -> dict[str, Any]:
        async with self._lock:
            page = self._page(workflow_id)
            if not allowed_host(page.url, self._allowlist()):
                raise ValueError("Current page is outside the configured host allow-list.")
            await self._dismiss_popups(page)
            fields = await page.locator(FORM_CONTROLS).evaluate_all(f"els => els.map({FIELD_METADATA})")
            for item in fields:
                item["sensitive"] = self._protected_field(item)
            challenge = await page.evaluate(r"""() => {
              const captcha = Array.from(document.querySelectorAll(
                'iframe[src*="recaptcha"], iframe[title*="challenge" i], .g-recaptcha, [data-sitekey], img[alt*="captcha" i]'
              )).some(el => el.getClientRects().length);
              const body = (document.body?.innerText || '').slice(0, 12000);
              return {captcha: captcha || /enter (?:the )?(?:captcha|characters (?:shown )?in the image)/i.test(body),
                      hasBiometric: /biometric|fingerprint|face recognition/i.test(body),
                      registrationConfirmed: /\b(registration (?:(?:is|was) )?successful|registration (?:was )?completed successfully|you have successfully registered|user (?:has been )?registered successfully)\b/i.test(body)};
            }""")
            return {"url": page.url, "title": await page.title(), "fields": fields, "challenge": challenge,
                    "registration_confirmed": challenge["registrationConfirmed"],
                    "safe_field_count": sum(1 for f in fields if f["type"] in ALLOWED_INPUT_TYPES and not f["sensitive"] and not f["disabled"] and not f["readonly"])}

    @staticmethod
    def _protected_field(field: dict[str, Any]) -> bool:
        label = " ".join(str(field.get(key) or "") for key in ("label", "group_label", "name", "id", "placeholder"))
        return is_sensitive(label, field["type"])

    @staticmethod
    def _matches_mapping(page_url: str, field: dict[str, Any], mapping: dict[str, Any]) -> bool:
        expected = mapping.get("expected_label")
        if mapping.get("expected_url"):
            return (page_url == mapping["expected_url"] and field["type"] == mapping["expected_type"]
                    and field["id"] == mapping["field_id"] and field["name"] == mapping["field_name"]
                    and field_label(field) == expected)
        label = " ".join(str(field.get(key) or "") for key in ("label", "group_label", "name", "id", "placeholder"))
        return not expected or bool(label and (_clean(expected) in _clean(label) or _clean(label) in _clean(expected)))

    async def fill_password(self, workflow_id: str, mapping: dict[str, Any], password: str) -> bool:
        """Fill a password only on the page and field shown in the current prompt."""
        async with self._lock:
            page = self._page(workflow_id)
            origin = portal_origin(page.url)
            if not origin or not allowed_host(page.url, self._allowlist()) or page.url != mapping["expected_url"]:
                return False
            locator = page.locator(FORM_CONTROLS).nth(mapping["field_index"])
            try:
                meta = await locator.evaluate(FIELD_METADATA, mapping["field_index"], timeout=2500)
                if (meta["type"] != "password" or meta["disabled"] or meta["readonly"]
                        or not self._matches_mapping(page.url, meta, mapping)
                        or portal_origin(urljoin(page.url, meta["form_action"])) != origin):
                    return False
                await locator.fill(password, timeout=2500)
                return await locator.evaluate("el => el.validity.valid && !!el.value", timeout=2500)
            except Exception:
                return False

    async def fill(self, workflow_id: str, approved_mappings: list[dict[str, Any]]) -> dict[str, Any]:
        """Fill only user-approved mappings. Never triggers form submission."""
        async with self._lock:
            page = self._page(workflow_id)
            if not allowed_host(page.url, self._allowlist()):
                raise ValueError("Current page is outside the configured host allow-list.")
            elements = page.locator(FORM_CONTROLS)
            count = await elements.count()
            filled, skipped = [], []
            seen_indexes: set[int] = set()
            for mapping in approved_mappings:
                try:
                    index = int(mapping["field_index"])
                    if index < 0 or index >= count:
                        skipped.append({"field_index": index, "reason": "Field index is no longer present; inspect this page again."})
                        continue
                    if index in seen_indexes:
                        skipped.append({"field_index": index, "reason": "Duplicate field mapping was ignored."})
                        continue
                    seen_indexes.add(index)
                    locator = elements.nth(index)
                    meta = await locator.evaluate(FIELD_METADATA, index, timeout=2500)
                    label = field_label(meta)
                    if not self._matches_mapping(page.url, meta, mapping):
                        skipped.append({"field_index": index, "reason": "Field label changed since inspection; inspect this page again."})
                        continue
                    if meta["disabled"] or meta["readonly"] or self._protected_field(meta) or meta["type"] not in ALLOWED_INPUT_TYPES:
                        skipped.append({"field_index": index, "reason": "Field is protected or unsupported."})
                        continue
                    value = str(mapping.get("value", ""))
                    if meta["type"] == "select":
                        options = await locator.locator("option").evaluate_all("els => els.map(o => ({label:o.textContent.trim(), value:o.value}))")
                        match = next((x for x in options if _clean(x["label"]) == _clean(value) or _clean(x["value"]) == _clean(value)), None)
                        if match is None:
                            skipped.append({"field_index": index, "reason": "No matching dropdown option; choose it manually."})
                            continue
                        await locator.select_option(value=match["value"])
                    elif meta.get("combo"):
                        await locator.fill(value)
                        menu_id = await locator.get_attribute("aria-controls")
                        if not menu_id or not re.fullmatch(r"[\w:-]+", menu_id):
                            await locator.press("Escape")
                            continue
                        menu = page.locator(f'[id="{menu_id}"]')
                        options = menu.get_by_role("option", name=value, exact=True)
                        if await options.count() != 1:
                            await locator.press("Escape")
                            continue
                        await options.click(timeout=3000)
                    elif meta["type"] == "checkbox":
                        if value.strip().lower() in {"true", "yes", "1", "checked"}:
                            await locator.check()
                        elif value.strip().lower() in {"false", "no", "0", "unchecked"}:
                            await locator.uncheck()
                        else:
                            skipped.append({"field_index": index, "reason": "Checkbox requires an explicit true/false value."})
                            continue
                    elif meta["type"] == "radio":
                        if value.strip().lower() not in {"true", "yes", "1", "checked"}:
                            skipped.append({"field_index": index, "reason": "Radio option was not selected by the mapping."})
                            continue
                        await locator.check()
                    else:
                        await locator.fill(value)
                        if meta.get("birth_picker"):
                            await locator.press("Tab")
                    updated = await locator.evaluate(FIELD_METADATA, index, timeout=2500)
                    if (updated["has_value"] and updated["valid"]) or (
                        meta["type"] == "checkbox" and value.lower() in {"false", "no", "0", "unchecked"}
                        and updated["valid"] and not updated["has_value"]
                    ):
                        filled.append({"field_index": index, "field_label": label, "profile_key": mapping.get("profile_key")})
                    else:
                        skipped.append({"field_index": index, "reason": "The portal rejected this value."})
                except Exception:
                    skipped.append({"field_index": mapping.get("field_index"), "reason": "The field could not be updated."})
            return {"filled": filled, "skipped": skipped,
                    "message": "Approved fields populated only; the page was not submitted. Review every value in the open browser."}

    async def upload_file(self, workflow_id: str, field_index: int, file_path: str, *, expected: dict | None = None) -> dict[str, Any]:
        """Upload a user-provided document to a matching file input."""
        async with self._lock:
            page = self._page(workflow_id)
            if not allowed_host(page.url, self._allowlist()):
                raise ValueError("Current page is outside the configured host allow-list.")
            elements = page.locator(FORM_CONTROLS)
            count = await elements.count()
            if field_index < 0 or field_index >= count:
                raise ValueError("The file field is no longer present. Inspect the page again.")
            locator = elements.nth(field_index)
            meta = await locator.evaluate(FIELD_METADATA, field_index, timeout=2500)
            if meta.get("type") != "file" or meta.get("disabled"):
                raise ValueError("Selected control is not an enabled file upload field.")
            if expected and not self._matches_mapping(page.url, meta, expected):
                raise ValueError("The requested upload field changed.")
            if self._protected_field(meta):
                raise ValueError("This file field appears to be security-sensitive and was not auto-filled.")
            await locator.set_input_files(file_path, timeout=4000)
            return {"uploaded": True, "field_index": field_index, "field_label": field_label(meta)}

    async def submit_otp(self, workflow_id: str, otp: str) -> dict[str, Any]:
        """Enter an OTP only into a visibly labelled OTP field; do not persist the value."""
        if not otp.isdigit() or not 4 <= len(otp) <= 12:
            raise ValueError("Enter a numeric OTP containing 4 to 12 digits.")
        async with self._lock:
            page = self._page(workflow_id)
            if not allowed_host(page.url, self._allowlist()):
                raise ValueError("Current page is outside the configured host allow-list.")
            matches = await page.locator('input:not([type="hidden"])').evaluate_all("""els => els.map((el,index) => {
              const labels = el.labels ? Array.from(el.labels).map(x=>x.innerText).join(' ') : '';
              const text = [labels,el.getAttribute('aria-label'),el.getAttribute('placeholder'),el.name,el.id,
                el.closest('label')?.innerText,el.closest('fieldset')?.querySelector('legend')?.innerText].filter(Boolean).join(' ');
              return {index,text,disabled:!!el.disabled,visible:!!(el.offsetWidth||el.offsetHeight||el.getClientRects().length)};
            })""")
            otp_field = next((x for x in matches if re.search(r"\b(otp|one.?time password|verification code)\b", x["text"], re.I) and not x["disabled"] and x["visible"]), None)
            if not otp_field:
                raise ValueError("No visible OTP field was found. Inspect the current page and try again.")
            locator = page.locator('input:not([type="hidden"])').nth(otp_field["index"])
            await locator.fill(otp)
            candidates = page.get_by_role("button", name=re.compile(r"^(verify|validate|confirm otp|verify otp|continue)$", re.I))
            if await candidates.count():
                await candidates.first.click()
            else:
                submits = page.locator('input[type="submit"], button[type="submit"]')
                clicked = False
                for i in range(await submits.count()):
                    item = submits.nth(i)
                    try:
                        label = (await item.get_attribute("value")) or (await item.inner_text())
                    except Exception:
                        label = ""
                    if re.search(r"verify|validate|otp|continue", label, re.I):
                        await item.click()
                        clicked = True
                        break
                if not clicked:
                    raise ValueError("OTP was entered but no clearly labelled verification button was found. Please verify it in the browser.")
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=12000)
            except Exception:
                pass
            return {"accepted_for_submission": True, "url": page.url, "title": await page.title(),
                    "message": "OTP entered into the labelled field. The code was not saved in chat, memory or logs."}

    async def click_next(self, workflow_id: str, *, login: bool = False) -> dict[str, Any]:
        """Advance using only an unambiguous ordinary Next/Continue control with resilient click."""
        async with self._lock:
            page = self._page(workflow_id)
            if not allowed_host(page.url, self._allowlist()):
                raise ValueError("Current page is outside the configured host allow-list.")
            await self._dismiss_popups(page)
            names = r"log ?in|sign in" if login else r"next|continue|save and continue|proceed|save & next|next step"
            pattern = re.compile(rf"^\s*(?:{names})\s*$", re.I)
            candidates = page.get_by_role("button", name=pattern)
            actionable = [item for item in await candidates.all()
                          if await item.is_visible() and await item.is_enabled()]
            if len(actionable) != 1:
                return {"advanced": False, "reason": "No unambiguous Next or Continue button was found."}
            try:
                await actionable[0].click(timeout=6000)
            except Exception as exc:
                return {"advanced": False, "reason": f"Could not click Next button: {str(exc)[:120]}"}
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=12000)
            except Exception:
                pass
            return {"advanced": True, "url": page.url, "title": await page.title()}

    async def submit_application(self, workflow_id: str, authorized: bool, *, registration: bool = False) -> dict[str, Any]:
        """Submit only when authorized and no visible payment/declaration gate remains."""
        if not authorized:
            return {"submitted": False, "reason": "The original request did not clearly authorize final submission."}
        async with self._lock:
            page = self._page(workflow_id)
            if not allowed_host(page.url, self._allowlist()):
                raise ValueError("Current page is outside the configured host allow-list.")
            await self._dismiss_popups(page)
            body_text = (await page.locator("body").inner_text())[:16000].lower()
            if re.search(r"\b(payment due|pay now|make payment|payment gateway|transaction fee)\b", body_text):
                return {"submitted": False, "reason": "The page requires payment. The user must review and complete payment."}
            boxes = page.locator('input[type="checkbox"]')
            for i in range(await boxes.count()):
                item = boxes.nth(i)
                try:
                    label = await item.evaluate("el => (el.labels ? Array.from(el.labels).map(x=>x.innerText).join(' ') : '') + ' ' + (el.closest('label')?.innerText || '') + ' ' + (el.closest('fieldset')?.innerText || '')")
                    if re.search(r"declaration|consent|agree|terms|undertak|certify|accuracy of", label, re.I) and not await item.is_checked():
                        return {"submitted": False, "reason": "A declaration, consent or terms checkbox needs the user's review."}
                except Exception:
                    continue
            names = ["register", "create account", "sign up", "submit"] if registration else [
                "submit application", "submit form", "apply now", "submit",
            ]
            patterns = [rf"^\s*{name}\s*$" for name in names]
            chosen = None
            for pattern in patterns:
                candidates = page.get_by_role("button", name=re.compile(pattern, re.I))
                if await candidates.count():
                    for i in range(await candidates.count()):
                        c = candidates.nth(i)
                        if await c.is_visible() and await c.is_enabled():
                            chosen = c
                            break
                    if chosen:
                        break
            if chosen is None:
                candidates = page.locator('input[type="submit"]')
                for i in range(await candidates.count()):
                    item = candidates.nth(i)
                    if not await item.is_visible():
                        continue
                    label = (await item.get_attribute("value")) or ""
                    if label.strip().lower() in names:
                        chosen = item
                        break
            if chosen is None:
                return {"submitted": False, "reason": "No clear final application submission control was found."}
            try:
                await chosen.scroll_into_view_if_needed(timeout=3000)
                await chosen.click(timeout=6000)
            except Exception:
                try:
                    await chosen.evaluate("el => el.click()")
                except Exception as exc:
                    return {"submitted": False, "reason": f"Could not click Submit button: {str(exc)[:120]}"}
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                pass
            text = (await page.locator("body").inner_text())[:8000]
            return {"submitted": True, "url": page.url, "title": await page.title(), "confirmation_text": text[:1600],
                    "message": "The final submission control was activated. Verify the portal's confirmation and acknowledgement."}

    async def close(self, workflow_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(workflow_id, None)
            if session:
                for key in ("context", "browser"):
                    try: await session[key].close()
                    except Exception: pass
                try: await session["playwright"].stop()
                except Exception: pass

    async def close_all(self) -> None:
        for workflow_id in list(self._sessions):
            await self.close(workflow_id)
