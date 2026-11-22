import asyncio
import sqlite3

from fastapi.testclient import TestClient

from app import main
from app.agent_runtime import AgentRuntime
from app.auth import create_access_token
from app.store import Store


def account(store, email):
    user = store.create_user(email, "unused-hash")
    token = create_access_token(user["id"], email)
    return user["id"], {"Authorization": f"Bearer {token}"}


def test_workflow_api_requires_account_ownership(tmp_path, monkeypatch):
    store = Store(tmp_path / "isolated.db")
    monkeypatch.setattr(main, "store", store)
    owner, owner_headers = account(store, "owner@example.test")
    other, other_headers = account(store, "other@example.test")
    store.save_workflow({"id": "owner-task", "user_id": owner, "goal": "Owner goal",
                         "retrieved_memory": [{"content": "Old installation-wide result"}]})
    store.save_workflow({"id": "other-task", "user_id": other, "goal": "Other goal"})
    store.save_workflow({"id": "unowned-task", "goal": "Older goal"})
    store.add_message("owner-task", "user", "Owner message")
    store.event("owner-task", "created", "Owner activity")
    store.save_run_outcome("owner-task", "Owner goal", "test-service", "completed")
    store.save_run_outcome("other-task", "Other goal", "test-service", "error")

    calls = []

    async def take_screenshot(workflow_id):
        calls.append(workflow_id)
        return b"image"

    monkeypatch.setattr(main.browser_agent, "take_screenshot", take_screenshot)
    client = TestClient(main.app)
    base = "/api/workflows/owner-task"
    portal = {"url": "https://portal.example.test/"}
    workflow = {"workflow_id": "owner-task"}
    denied_requests = [
        *(("GET", f"{base}{suffix}", {}) for suffix in ("", "/messages", "/activity", "/audit", "/screenshot")),
        ("POST", "/api/chat", {"json": {**workflow, "message": "ready"}}),
        ("POST", f"{base}/portal", {"json": portal}),
        ("POST", f"{base}/otp", {"json": {"otp": "123456"}}),
        ("POST", f"{base}/credentials", {"json": {"username": "test", "password": "test"}}),
        ("POST", f"{base}/password", {"json": {"question_id": "test", "password": "test"}}),
        ("POST", f"{base}/approve", {"json": {"approved": True}}),
        ("POST", f"{base}/action", {"json": {"action": "apply"}}),
        ("POST", f"{base}/documents", {"files": {"file": ("upload.txt", b"test")}}),
        ("POST", "/api/browser/open", {"json": {**workflow, **portal}}),
        *(("POST", f"/api/browser/{action}", {"json": workflow}) for action in ("inspect", "suggest", "fill")),
        ("POST", "/api/browser/close/owner-task", {}),
    ]
    for method, path, kwargs in denied_requests:
        assert client.request(method, path, **kwargs).status_code == 401, path
        assert client.request(method, path, headers=other_headers, **kwargs).status_code == 404, path
    assert calls == []

    assert client.get(base, headers=owner_headers).json()["goal"] == "Owner goal"
    assert "retrieved_memory" not in client.get(base, headers=owner_headers).json()
    assert client.get(f"{base}/messages", headers=owner_headers).json()[0]["content"] == "Owner message"
    assert client.get(f"{base}/audit", headers=owner_headers).json()["events"][0]["message"] == "Owner activity"
    screenshot = client.get(f"{base}/screenshot", headers=owner_headers)
    assert screenshot.status_code == 200
    assert screenshot.headers["cache-control"] == "no-store"
    assert calls == ["owner-task"]
    assert client.get("/api/workflows/unowned-task", headers=owner_headers).status_code == 404
    assert [item["id"] for item in client.get("/api/workflows", headers=other_headers).json()] == ["other-task"]
    assert [item["goal"] for item in client.get("/api/optimizer/insights", headers=owner_headers).json()] == ["Owner goal"]
    assert [item["goal"] for item in store.get_run_insights("test-service", user_id=other)] == ["Other goal"]


def test_workflow_profile_and_vault_follow_the_signed_in_account(tmp_path, monkeypatch):
    class Portal:
        def __init__(self):
            self.filled = []
            self.attached = []

        async def inspect(self, wid):
            return {"url": "https://portal.example.test/", "title": "Demo application", "fields": [
                {"index": 0, "label": "Full Name", "type": "text"},
                {"index": 1, "label": "Income Certificate", "type": "file", "required": True},
            ]}

        async def fill(self, wid, mappings):
            self.filled.extend(mapping["value"] for mapping in mappings)
            return {"filled": mappings}

        async def upload_file(self, wid, index, path):
            self.attached.append(path)

        async def click_next(self, wid):
            return {"advanced": False}

        async def submit_application(self, wid, authorized):
            return {"submitted": False}

    monkeypatch.setenv("ORQENTRA_MASTER_KEY", "test-only-master-key-for-account-isolation")
    upload_dir = tmp_path / "uploads"
    store = Store(tmp_path / "isolated.db")
    portal = Portal()
    runtime = AgentRuntime(store, portal, upload_dir)
    monkeypatch.setattr(runtime, "_schedule", lambda wid, coro: coro.close())
    monkeypatch.setattr(main, "runtime", runtime)
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(main, "UPLOAD_DIR", upload_dir)
    owner, owner_headers = account(store, "owner@example.test")
    other, other_headers = account(store, "other@example.test")
    store.save_profile_value("full_name", "Legacy Applicant")
    client = TestClient(main.app)

    start = client.post("/api/chat", json={"message": "Apply for a service. My name is Asha Example."}, headers=owner_headers)
    assert start.status_code == 200
    owner_task = start.json()["workflow"]
    owner_wid = owner_task["id"]
    owner_task["pending_input"] = {"kind": "detail", "key": "email", "label": "Email"}
    store.save_workflow(owner_task)
    response = client.post("/api/chat", json={"workflow_id": owner_wid, "message": "asha@example.test"}, headers=owner_headers)
    assert response.status_code == 200
    assert store.get_user_profile(owner) == {"full_name": "Asha Example", "email": "asha@example.test"}
    assert store.get_user_profile(other) == {}
    assert store.get_profile() == {"full_name": "Legacy Applicant"}

    response = client.post(f"/api/workflows/{owner_wid}/documents", headers=owner_headers,
                           files={"file": ("income_certificate.txt", b"Income Certificate\nAnnual household income: 250000 INR")})
    assert response.status_code == 200
    document_id = response.json()["id"]
    assert [doc["id"] for doc in client.get("/api/user/documents", headers=owner_headers).json()] == [document_id]
    assert client.get("/api/user/documents", headers=other_headers).json() == []
    assert "250000" in store.get_user_document_text(owner, document_id)
    assert "250000" in str(store.search_memory("income certificate", user_id=owner))
    assert store.search_memory("income certificate applicant full name", user_id=other) == []

    store.add_document("legacy-owned", owner_wid, "old_resume.txt", "old_resume.txt", "Resume for Asha Example", "resume")
    assert "legacy-owned" in {doc["id"] for doc in store.get_documents(owner)}
    assert store.get_documents(other) == []

    other_task = client.post("/api/chat", json={"message": "Apply for a service"}, headers=other_headers).json()["workflow"]
    asyncio.run(runtime._continue_form(other_task["id"]))
    assert portal.filled == []
    assert portal.attached == []
    assert store.get_workflow(other_task["id"])["pending_input"]["kind"] == "document"
    asyncio.run(runtime._continue_form(owner_wid))
    assert portal.filled == ["Asha Example"]
    assert portal.attached == [next(doc["path"] for doc in store.get_documents(owner) if doc["id"] == document_id)]


def test_pre_account_database_can_store_new_workflows(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE workflows (id TEXT PRIMARY KEY, goal TEXT, data TEXT, created_at TEXT, updated_at TEXT)")
        connection.execute("INSERT INTO workflows VALUES (?, ?, ?, ?, ?)",
                           ("old", "Old goal", '{"id":"old","goal":"Old goal"}', "", ""))

    store = Store(path)
    store.save_workflow({"id": "new", "user_id": "owner", "goal": "New goal"})
    assert store.get_workflow("old")["user_id"] == ""
    assert store.get_workflow("old", user_id="owner") is None
    assert [item["id"] for item in store.list_workflows(user_id="owner")] == ["new"]
