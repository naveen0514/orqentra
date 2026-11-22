import asyncio
import time

from fastapi.testclient import TestClient

from app import main
from app.agent_runtime import AgentRuntime
from app.auth import create_access_token
from app.browser_agent import BrowserAutomationAgent
from app.store import Store


class RegistrationPortal:
    origin = "https://portal.example.test"
    url = f"{origin}/forms/registration"

    def __init__(self):
        self.values = {}
        self.opened = False
        self.verified_in_portal = False
        self.submit_calls = 0

    async def open_portal(self, wid, url):
        return {"url": self.origin, "title": "Portal"}

    async def navigate_to_application(self, wid, goal):
        return {}

    async def detect_page_actions(self, wid):
        return [{"label": "Register (New User)", "action": "register"}]

    async def navigate_action(self, wid, action):
        assert action == "register"
        self.opened = True
        return {"url": self.url, "title": "Registration", "next_step": "form"}

    async def inspect(self, wid):
        assert self.opened
        fields = []

        def add(name, label, typ="text", **metadata):
            selected = self.values.get(name)
            has_value = selected == label if typ == "radio" else bool(selected)
            fields.append({"index": len(fields), "type": typ, "name": name, "label": label, "required": True,
                           "has_value": has_value, "valid": has_value, **metadata})

        for option in ("CPV Delhi", "Passport Office"):
            add("officeType", option, "radio", group_label="Register to apply at", option_label=option)
        if self.values.get("officeType") == "Passport Office":
            add("office", "Passport Office Location", "select",
                options=[{"label": "Chennai", "value": "CHE"}, {"label": "Madurai", "value": "MDU"}])
        add("fullName", "Full Name (Initials and honorifics are not allowed)")
        add("email", "Email ID", "email")
        for option in ("Yes", "No"):
            add("emailAsLogin", option, "radio", option_label=option,
                group_label="Do you want your Login Id to be same as E-mail Id?")
        add("loginId", "Login ID")
        add("password", "Password", "password", sensitive=True)
        add("confirmPassword", "Confirm Password", "password", sensitive=True)
        if not self.verified_in_portal:
            add("captcha", "Enter the characters shown in the image", sensitive=True)
        return {"url": self.url, "title": "Registration", "fields": fields,
                "challenge": {"captcha": not self.verified_in_portal}, "registration_confirmed": bool(self.submit_calls)}

    async def fill(self, wid, mappings):
        filled = []
        for mapping in mappings:
            fields = (await self.inspect(wid))["fields"]
            field = fields[mapping["field_index"]]
            if field["label"] != mapping["expected_label"]:
                continue
            assert not field.get("sensitive")
            value = field["label"] if field["type"] == "radio" else mapping["value"]
            self.values[mapping["field_name"]] = value
            filled.append(mapping)
        return {"filled": filled}

    async def fill_password(self, wid, field, value):
        assert field["expected_url"] == self.url
        assert field["expected_type"] == "password"
        self.values[field["field_name"]] = value
        return True

    async def click_next(self, wid):
        return {"advanced": False}

    async def submit_application(self, wid, authorized, *, registration=False):
        assert self.verified_in_portal and authorized and registration
        self.submit_calls += 1
        return {"submitted": True, "confirmation_text": "Registration successful", "url": self.url}

    async def close_all(self):
        pass


def test_registration_uses_saved_data_and_applies_one_chat_reply_at_a_time(tmp_path, monkeypatch):
    monkeypatch.setenv("ORQENTRA_MASTER_KEY", "test-only-master-key-for-chat-registration")
    store = Store(tmp_path / "test.db")
    user = store.create_user("asha@example.test", "unused-hash", "Asha Example")
    uid = user["id"]
    assert store.get_user_profile(uid) == {}
    portal = RegistrationPortal()
    runtime = AgentRuntime(store, portal, tmp_path / "uploads")
    monkeypatch.setattr(main, "runtime", runtime)
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(main, "browser_agent", portal)
    headers = {"Authorization": f"Bearer {create_access_token(uid, user['email'])}"}
    password = "  ExamplePortalPassword!  "

    with TestClient(main.app, headers=headers) as client:
        created = client.post("/api/chat", json={"message": f"Help with this portal: {portal.origin}/"})
        assert created.status_code == 200
        wid = created.json()["workflow"]["id"]
        endpoint = f"/api/workflows/{wid}"

        def wait_for_question(kind):
            for _ in range(100):
                workflow = client.get(endpoint).json()
                pending = workflow.get("pending_input") or {}
                if workflow["status"] == "waiting_user" and pending.get("kind") == kind:
                    return pending
                if workflow["status"] == "error":
                    raise AssertionError(workflow["last_error"])
                time.sleep(0.01)
            raise AssertionError(f"Expected {kind}. Workflow: {workflow}")

        def reply(message, question=None):
            response = client.post("/api/chat", json={"workflow_id": wid, "message": message,
                                                      "reply_to": question.get("id") if question else None})
            assert response.status_code == 200

        wait_for_question("portal_action_choice")
        selected = client.post(f"{endpoint}/action", json={"action": "register"})
        assert selected.status_code == 200
        question = wait_for_question("detail")
        assert question["label"] == "Register to apply at"
        assert question["options"] == ["CPV Delhi", "Passport Office"]
        assert portal.values == {"fullName": "Asha Example", "email": "asha@example.test"}

        reply("Passport Office", question)
        location = wait_for_question("detail")
        assert location["label"] == "Passport Office Location"
        stale = client.post("/api/chat", json={"workflow_id": wid, "message": "CPV Delhi", "reply_to": question["id"]})
        assert stale.status_code == 409
        reply("Chennai", location)
        preference = wait_for_question("detail")
        assert preference["options"] == ["Yes", "No"]
        reply("Yes", preference)

        password_question = wait_for_question("password")
        assert portal.values["loginId"] == "asha@example.test"
        assert password_question["remember"] is True
        reply("text-that-should-never-enter-chat-or-the-portal", password_question)
        response = client.post(f"{endpoint}/password", json={"question_id": password_question["id"],
                                                              "password": password, "remember": True})
        assert response.status_code == 200
        wait_for_question("manual_verification")
        assert portal.values["password"] == portal.values["confirmPassword"] == password
        assert "captcha" not in portal.values
        assert portal.submit_calls == 0
        assert store.get_portal_values(uid, portal.origin, password=True) == {"password": password}
        assert store.get_portal_values(uid, "https://other.example.test", password=True) == {}
        assert "password" not in store.get_portal_values(uid, portal.origin)
        assert "password" not in client.get("/api/profile").json()
        for path in ("", "/messages", "/activity", "/audit"):
            payload = client.get(f"{endpoint}{path}").text
            assert password.strip() not in payload
            assert "text-that-should-never-enter-chat-or-the-portal" not in payload

        portal.verified_in_portal = True
        reply("ready")
        wait_for_question("submit_registration")
        reply("submit registration")
        for _ in range(100):
            if client.get(endpoint).json()["status"] == "completed":
                break
            time.sleep(0.01)
        assert client.get(endpoint).json()["status"] == "completed"
        assert portal.submit_calls == 1

        portal.values.clear()
        portal.submit_calls = 0
        portal.verified_in_portal = False
        repeated = client.post("/api/chat", json={"message": f"Register an account at {portal.origin}/"}).json()
        endpoint = f"/api/workflows/{repeated['workflow']['id']}"
        wait_for_question("manual_verification")
        assert portal.values["office"] == "Chennai"
        assert portal.values["emailAsLogin"] == "Yes"
        assert portal.values["loginId"] == "asha@example.test"
        assert portal.values["password"] == portal.values["confirmPassword"] == password


def test_password_cannot_be_filled_after_redirect_or_into_a_cross_origin_form(monkeypatch):
    class PasswordField:
        def __init__(self):
            self.form_action = "https://other.example.test/receive"
            self.value = ""

        def nth(self, index):
            assert index == 0
            return self

        async def evaluate(self, expression, *args, **kwargs):
            return {"type": "password", "disabled": False, "readonly": False, "label": "Password",
                    "name": "password", "id": "pw", "form_action": self.form_action}

        async def fill(self, value, **kwargs):
            self.value = value

    class Page:
        url = "https://portal.example.test/registration"
        field = PasswordField()

        def locator(self, selector):
            return self.field

    browser = BrowserAutomationAgent()
    page = Page()
    monkeypatch.setattr(browser, "_page", lambda wid: page)
    monkeypatch.setattr(browser, "_allowlist", lambda: ["*"])
    mapping = {"field_index": 0, "expected_url": page.url, "expected_label": "Password",
               "expected_type": "password", "field_name": "password", "field_id": "pw"}
    assert not asyncio.run(browser.fill_password("workflow", mapping, "test-password"))
    page.field.form_action = "/registration"
    page.url = "https://other.example.test/registration"
    assert not asyncio.run(browser.fill_password("workflow", mapping, "test-password"))
    assert page.field.value == ""


def test_login_reuses_portal_id_and_resumes_application_after_transient_password(tmp_path, monkeypatch):
    class LoginPortal(RegistrationPortal):
        url = f"{RegistrationPortal.origin}/login"

        def __init__(self):
            super().__init__()
            self.signed_in = False

        async def navigate_action(self, wid, action):
            assert action == "login"
            return {"url": self.url, "title": "Sign In", "next_step": "form"}

        async def inspect(self, wid):
            if self.signed_in:
                return {"url": f"{self.origin}/application", "title": "Application", "fields": [
                    {"index": 0, "name": "phone", "label": "Mobile Number", "type": "tel", "required": True},
                ]}
            return {"url": self.url, "title": "Sign In", "fields": [
                {"index": 0, "name": "loginId", "label": "Login ID", "type": "text", "required": True,
                 "has_value": "loginId" in self.values},
                {"index": 1, "name": "password", "label": "Password", "type": "password", "required": True,
                 "sensitive": True, "has_value": "password" in self.values},
            ]}

        async def click_next(self, wid, *, login=False):
            assert login
            assert self.values == {"loginId": "asha-portal", "password": "example-only"}
            self.signed_in = True
            return {"advanced": True}

    monkeypatch.setenv("ORQENTRA_MASTER_KEY", "test-only-master-key-for-portal-login")
    store = Store(tmp_path / "test.db")
    uid = store.create_user("asha@example.test", "unused-hash")["id"]
    portal = LoginPortal()
    store.save_portal_value(uid, portal.origin, "login_id", "asha-portal")
    runtime = AgentRuntime(store, portal, tmp_path / "uploads")
    wid = "login-workflow"
    store.save_workflow({"id": wid, "goal": "Apply online", "user_id": uid, "status": "waiting_user",
                         "pending_input": {"kind": "portal_action_choice", "choices": [{"action": "login"}]}})

    async def run_workflow():
        await runtime.submit_action_choice(wid, "login")
        await runtime._tasks[wid]
        question = store.get_workflow(wid)["pending_input"]
        assert question["kind"] == "password"
        assert portal.values["loginId"] == "asha-portal"
        await runtime.answer_password(wid, question["id"], "example-only", remember=False)
        login_task = runtime._tasks[wid]
        await login_task
        await runtime._tasks[wid]
        assert store.get_workflow(wid)["pending_input"]["label"] == "Mobile Number"

    asyncio.run(run_workflow())
    assert store.get_portal_values(uid, portal.origin, password=True) == {}
    assert "example-only" not in str(store.get_messages(wid))
