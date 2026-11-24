from app.store import Store

def test_portal_host_allowlist():
    from app.browser_agent import allowed_host
    assert allowed_host("https://www.passportindia.gov.in/", ["passportindia.gov.in"])
    assert not allowed_host("http://www.passportindia.gov.in/", ["passportindia.gov.in"])
    assert not allowed_host("https://passportindia.gov.in.attacker.example/", ["passportindia.gov.in"])
    assert not allowed_host("https://example.com/", ["passportindia.gov.in"])


def test_suggests_only_confident_safe_field_matches():
    from app.browser_agent import suggest_field_mappings
    fields = [
        {"index": 0, "label": "Full Name", "type": "text"},
        {"index": 1, "label": "Date of Birth", "type": "date"},
        {"index": 2, "label": "OTP", "type": "text"},
        {"index": 3, "label": "Password", "type": "password"},
    ]
    profile = {"full_name": "Asha Example", "date_of_birth": "1990-01-01", "otp": "123456", "password": "do-not-fill"}
    results = suggest_field_mappings(fields, profile)
    assert [r["profile_key"] for r in results] == ["full_name", "date_of_birth"]


def test_wildcard_allows_any_https_host_but_not_http():
    from app.browser_agent import allowed_host
    assert allowed_host("https://portal.example.org/apply", ["*"])
    assert allowed_host("https://login.another-site.com/", ["*"])
    assert not allowed_host("http://portal.example.org/", ["*"])


def test_generic_profile_matches_education_employment_and_address_fields():
    from app.browser_agent import suggest_field_mappings
    fields = [
        {"index": 0, "label": "College / University Name", "type": "text"},
        {"index": 1, "label": "Position / Job Title", "type": "text"},
        {"index": 2, "label": "Postal Code", "type": "text"},
        {"index": 3, "label": "Email Address", "type": "email"},
    ]
    profile = {"institution": "Example College", "occupation": "Analyst", "postal_code": "641001", "email": "person@example.test"}
    results = suggest_field_mappings(fields, profile)
    assert {r["profile_key"] for r in results} == {"institution", "occupation", "postal_code", "email"}


def test_radio_option_uses_profile_value():
    from app.browser_agent import suggest_field_mappings
    fields = [
        {"index": 0, "label": "Male", "option_label": "Male", "group_label": "Gender", "type": "radio"},
        {"index": 1, "label": "Female", "option_label": "Female", "group_label": "Gender", "type": "radio"},
    ]
    results = suggest_field_mappings(fields, {"gender": "Female"})
    assert len(results) == 1
    assert results[0]["field_index"] == 1
    assert results[0]["value"] == "true"


def test_nested_profile_is_flattened_for_matching():
    from app.browser_agent import suggest_field_mappings
    fields = [{"index": 0, "label": "City", "type": "text"}]
    results = suggest_field_mappings(fields, {"address": {"city": "Coimbatore"}})
    assert len(results) == 1
    assert results[0]["value"] == "Coimbatore"


def test_intent_agent_covers_multiple_application_categories():
    from app.orchestrator import IntentAgent
    agent = IntentAgent()
    assert agent.run("Apply for a university admission") ["service"] == "education"
    assert agent.run("Submit a job application") ["service"] == "employment"
    assert agent.run("Register a new business") ["service"] == "business"
    assert agent.run("Apply for a visa") ["service"] == "visa_and_travel"


def test_wildcard_rejects_local_and_private_addresses():
    from app.browser_agent import allowed_host
    assert not allowed_host("https://127.0.0.1/", ["*"])
    assert not allowed_host("https://192.168.1.20/", ["*"])
    assert not allowed_host("https://router.local/", ["*"])


def test_local_profile_and_document_memory_retrieval(tmp_path):
    store = Store(tmp_path / "memory.db")
    store.save_profile_value("full_name", "Asha Example", "user-chat")
    doc_path = tmp_path / "income.txt"
    doc_path.write_text("Income Certificate\nAnnual household income: 250000 INR")
    store.add_document("doc-1", "wf-1", "income_certificate.txt", str(doc_path), doc_path.read_text(), "income_certificate")
    profile_hits = store.search_memory("applicant full name")
    doc_hits = store.search_memory("income certificate annual household income")
    assert any("Asha Example" in hit["content"] for hit in profile_hits)
    assert any("Annual household income" in hit["content"] for hit in doc_hits)


def test_portal_discovery_has_common_india_service_hint():
    import asyncio
    from app.agent_runtime import PortalDiscovery
    results = asyncio.run(PortalDiscovery().discover("Apply for a scholarship", "scholarship"))
    assert results
    assert results[0]["url"] == "https://scholarships.gov.in/"
    assert results[0]["confidence"] >= 0.9


def test_otp_chat_message_is_not_persisted(tmp_path):
    import asyncio
    from app.agent_runtime import AgentRuntime

    class FakeBrowser:
        async def submit_otp(self, wid, otp):
            assert otp == "123456"
            return {"accepted_for_submission": True}

    store = Store(tmp_path / "otp.db")
    wf = {
        "id": "wf-otp", "goal": "Apply for a service", "service": "general", "task": "application",
        "status": "waiting_user", "plan": [], "pending_input": {"kind": "otp"},
        "portal_candidates": [], "portal_url": None, "documents": [], "submit_authorized": True,
    }
    store.save_workflow(wf)
    runtime = AgentRuntime(store, FakeBrowser(), tmp_path / "uploads")
    runtime._schedule = lambda wid, coro: coro.close()  # prevent a browser continuation in this isolated unit test
    asyncio.run(runtime.chat("wf-otp", "123456"))
    contents = [m["content"] for m in store.get_messages("wf-otp")]
    assert "123456" not in " ".join(contents)
    events = store.get_events("wf-otp")
    assert "123456" not in str(events)


def test_prompt_extracts_explicit_profile_facts_without_guessing():
    from app.agent_runtime import AgentRuntime
    facts = AgentRuntime._parse_prompt_facts(
        "Apply for a service. My name is Naveen Kumar, my email is naveen@example.test.\nGender: Male\nState: Tamil Nadu"
    )
    assert facts["full_name"] == "Naveen Kumar"
    assert facts["email"] == "naveen@example.test"
    assert facts["gender"] == "Male"
    assert facts["state"] == "Tamil Nadu"
    assert "password" not in facts and "otp" not in facts


def test_label_parser_prefers_specific_family_name_aliases():
    from app.agent_runtime import AgentRuntime
    assert AgentRuntime._key_from_label("Father Name") == "father_name"
    assert AgentRuntime._key_from_label("Mother's Name") == "mother_name"
    assert AgentRuntime._key_from_label("Applicant Full Name") == "full_name"


def test_credentials_are_not_persisted_in_chat_or_events(tmp_path):
    import asyncio
    from app.agent_runtime import AgentRuntime

    class FakeBrowser:
        async def perform_login(self, wid, username, password, action="login"):
            assert username == "applicant@example.com"
            assert password == "SecretPass123!"
            return {"success": True, "message": "logged in"}

    store = Store(tmp_path / "cred.db")
    wf = {
        "id": "wf-cred", "goal": "Apply for a service", "service": "general", "task": "application",
        "status": "waiting_user", "plan": [], "pending_input": {"kind": "credentials"},
        "portal_candidates": [], "portal_url": None, "documents": [], "submit_authorized": True,
    }
    store.save_workflow(wf)
    runtime = AgentRuntime(store, FakeBrowser(), tmp_path / "uploads")
    runtime._schedule = lambda wid, coro: coro.close()
    res = asyncio.run(runtime.submit_credentials("wf-cred", "applicant@example.com", "SecretPass123!"))
    assert res["result"]["success"] is True

    # Ensure password is NOT in messages or events
    contents = [m["content"] for m in store.get_messages("wf-cred")]
    assert "SecretPass123!" not in " ".join(contents)
    events = store.get_events("wf-cred")
    assert "SecretPass123!" not in str(events)



def test_phone_and_address_use_portal_format_and_saved_components():
    from app.agent_runtime import AgentRuntime

    field = {"type": "text", "digits": 10}
    assert AgentRuntime._form_value(field, "+91 98765 43210") == "9876543210"
    assert AgentRuntime._form_value(field, "+91 98765432") == ""
    assert AgentRuntime._form_value({"type": "tel"}, "+91 98765 43210") == "+91 98765 43210"

    profile = {"address_line_1": "42 Test Street", "postal_code": "625001"}
    _, missing = AgentRuntime._address_details(profile)
    assert missing == ["post_office", "district"]
    profile.update(post_office="Test Post", district="Test District")
    address, missing = AgentRuntime._address_details(profile)
    assert not missing
    assert address == "42 Test Street, Test Post, Test District, 625001"
