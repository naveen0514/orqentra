"""Orqentra FastAPI server with user authentication, encrypted profile storage,
and intelligent document extraction for registration/onboarding."""
from pathlib import Path
from uuid import uuid4
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, HTTPException, Response, Depends, Header
from fastapi.middleware.cors import CORSMiddleware

from .models import (BrowserOpenRequest, BrowserInspectRequest, BrowserSuggestRequest, BrowserFillRequest,
                     ChatRequest, OTPRequest, PortalConfirmRequest, CredentialsRequest, ApprovalRequest,
                     ActionChoiceRequest, RegisterRequest, LoginRequest, OnboardingData, PasswordAnswerRequest)
from .store import Store
from .browser_agent import BrowserAutomationAgent, suggest_field_mappings
from .agent_runtime import AgentRuntime
from .auth import hash_password, verify_password, create_access_token, decode_token
from .document_extractor import classify_document_content, extract_profile_from_text
from .orchestrator import DocumentIntelligenceAgent

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT.parent / ".env")
except ImportError:
    pass

store = Store(ROOT / "orqentra.db")
browser_agent = BrowserAutomationAgent()
UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
runtime = AgentRuntime(store, browser_agent, UPLOAD_DIR)
doc_intelligence = DocumentIntelligenceAgent()

app = FastAPI(
    title="Orqentra API",
    description="Multi-agent autonomous application agent with encrypted user profiles, local RAG memory, and document extraction",
    version="3.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================== AUTH HELPERS =====================

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract and verify the JWT from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    user = store.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(401, "User not found")
    return user


def require_workflow(workflow_id: str, user: dict = Depends(get_current_user)) -> dict:
    workflow = store.get_workflow(workflow_id, user_id=user["id"])
    if workflow is None:
        raise HTTPException(404, "Workflow not found")
    return workflow


# ===================== PUBLIC ENDPOINTS =====================

@app.get("/health")
def health():
    return {"status": "ok", "project": "Orqentra", "mode": "multi-agent-encrypted", "version": "3.1.0"}


@app.post("/api/auth/register")
def register(payload: RegisterRequest):
    """Register a new user account."""
    existing = store.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(409, "An account with this email already exists. Please log in.")
    hashed = hash_password(payload.password)
    user = store.create_user(payload.email, hashed, payload.full_name)
    token = create_access_token(user["id"], payload.email)
    return {"token": token, "user": user}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    """Log in with email and password."""
    user = store.get_user_by_email(payload.email)
    if not user:
        raise HTTPException(401, "Invalid email or password")
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token(user["id"], payload.email)
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "onboarding_complete": bool(user["onboarding_complete"]),
        }
    }


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "onboarding_complete": bool(user["onboarding_complete"]),
    }


# ===================== ONBOARDING & PROFILE =====================

@app.post("/api/profile/onboarding")
def save_onboarding(payload: OnboardingData, user: dict = Depends(get_current_user)):
    """Save onboarding data (or any profile update). All values encrypted at rest."""
    store.save_user_fields_bulk(user["id"], payload.fields, payload.category, "onboarding")
    return {"saved": len(payload.fields), "category": payload.category}


@app.post("/api/profile/complete-onboarding")
def complete_onboarding(user: dict = Depends(get_current_user)):
    """Mark onboarding as complete."""
    store.set_onboarding_complete(user["id"])
    return {"onboarding_complete": True}


@app.get("/api/profile")
def get_profile(user: dict = Depends(get_current_user)):
    """Return all decrypted profile fields for the current user."""
    return store.get_user_profile(user["id"])


@app.get("/api/profile/keys")
def get_profile_keys(user: dict = Depends(get_current_user)):
    """Return the list of stored field keys (without values, for checking what's available)."""
    return store.get_user_field_keys(user["id"])


@app.post("/api/profile/fields")
def save_profile_fields(payload: OnboardingData, user: dict = Depends(get_current_user)):
    """Save or update profile fields (for adding missing data later)."""
    store.save_user_fields_bulk(user["id"], payload.fields, payload.category, "user-update")
    return {"saved": len(payload.fields)}


# ===================== USER DOCUMENTS (INTELLIGENT EXTRACTION) =====================

@app.get("/api/user/documents")
def list_user_documents(user: dict = Depends(get_current_user)):
    """List all documents for the current user (without file paths for security)."""
    docs = store.get_user_documents(user["id"])
    return [{k: v for k, v in d.items() if k != "file_path"} for d in docs]


def _process_uploaded_file(file_content: bytes, original_filename: str, user_id: str) -> dict:
    """Save file, extract text, classify, extract profile fields, and persist in encrypted vault & profile."""
    suffix = Path(original_filename or "upload.bin").suffix.lower()
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".docx"}
    if suffix not in allowed:
        raise HTTPException(400, f"Unsupported file type for {original_filename}. Supported: PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP")
    if len(file_content) > 20 * 1024 * 1024:
        raise HTTPException(413, f"File {original_filename} exceeds 20 MB limit")

    safe_name = Path(original_filename or "document").name
    user_dir = UPLOAD_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / f"{uuid4().hex}{suffix}"
    dest.write_bytes(file_content)

    # 1. Extract text
    text, method = doc_intelligence.extract_text(dest)

    # 2. Classify document
    classification = classify_document_content(safe_name, text)
    doc_type = classification["label"]
    category = classification["category"]

    # 3. Extract applicant profile attributes from text
    extracted_fields = extract_profile_from_text(text, safe_name)

    # 4. Save document in permanent user vault
    doc_id = store.add_user_document(
        user_id=user_id,
        doc_name=safe_name,
        doc_type=doc_type,
        file_path=str(dest),
        extracted_text=text,
        metadata={"method": method, "characters": len(text), "category": category, "fields_extracted": list(extracted_fields.keys())}
    )

    # 5. Automatically save extracted fields into encrypted profile memory!
    if extracted_fields:
        store.save_user_fields_bulk(user_id, extracted_fields, category=category, source=safe_name)

    return {
        "id": doc_id,
        "filename": safe_name,
        "doc_type": doc_type,
        "category": category,
        "characters_extracted": len(text),
        "extraction_method": method,
        "extracted_fields": extracted_fields,
        "fields_count": len(extracted_fields),
    }


@app.post("/api/user/documents")
async def upload_user_document(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Upload a single document, extract details, and auto-populate user profile."""
    content = await file.read()
    res = _process_uploaded_file(content, file.filename, user["id"])
    res["updated_profile"] = store.get_user_profile(user["id"])
    return res


@app.post("/api/user/documents/batch")
async def upload_user_documents_batch(files: List[UploadFile] = File(...), user: dict = Depends(get_current_user)):
    """Upload multiple documents at once (N documents), extract all details, and auto-populate profile."""
    results = []
    all_extracted_fields = {}
    for f in files:
        content = await f.read()
        res = _process_uploaded_file(content, f.filename, user["id"])
        all_extracted_fields.update(res["extracted_fields"])
        results.append(res)

    return {
        "uploaded_count": len(results),
        "documents": results,
        "total_fields_extracted": len(all_extracted_fields),
        "extracted_fields": all_extracted_fields,
        "updated_profile": store.get_user_profile(user["id"])
    }


# ===================== WORKFLOW CHAT =====================

@app.get("/api/browser/config")
def browser_config():
    return browser_agent.config()


@app.post("/api/chat")
async def chat(payload: ChatRequest, user: dict = Depends(get_current_user)):
    if payload.workflow_id:
        require_workflow(payload.workflow_id, user)
    try:
        if payload.workflow_id:
            result = await runtime.chat(payload.workflow_id, payload.message, reply_to=payload.reply_to)
            return {"workflow": result.get("workflow"), "messages": store.get_messages(payload.workflow_id)}
        wf = await runtime.start_chat(payload.message, user_id=user["id"])
        return {"workflow": wf, "messages": store.get_messages(wf["id"])}
    except KeyError:
        raise HTTPException(404, "Conversation not found")
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Could not process chat message: {str(exc)[:300]}")


@app.get("/api/workflows")
def list_workflows(user: dict = Depends(get_current_user)):
    return store.list_workflows(user_id=user["id"])


@app.get("/api/workflows/{workflow_id}")
def get_workflow(workflow: dict = Depends(require_workflow)):
    return workflow


@app.get("/api/workflows/{workflow_id}/messages", dependencies=[Depends(require_workflow)])
def messages(workflow_id: str):
    return store.get_messages(workflow_id)


@app.get("/api/workflows/{workflow_id}/activity", dependencies=[Depends(require_workflow)])
def activity(workflow_id: str):
    return store.get_events(workflow_id)


@app.post("/api/workflows/{workflow_id}/portal", dependencies=[Depends(require_workflow)])
async def select_portal(workflow_id: str, payload: PortalConfirmRequest):
    try:
        wf = await runtime.confirm_portal(workflow_id, str(payload.url))
        return wf
    except KeyError:
        raise HTTPException(404, "Workflow not found")


@app.post("/api/workflows/{workflow_id}/otp", dependencies=[Depends(require_workflow)])
async def submit_otp(workflow_id: str, payload: OTPRequest):
    try:
        return await runtime.submit_otp(workflow_id, payload.otp)
    except KeyError:
        raise HTTPException(404, "Workflow not found")
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.post("/api/workflows/{workflow_id}/credentials", dependencies=[Depends(require_workflow)])
async def submit_credentials(workflow_id: str, payload: CredentialsRequest):
    try:
        return await runtime.submit_credentials(workflow_id, payload.username, payload.password, payload.action_type)
    except KeyError:
        raise HTTPException(404, "Workflow not found")
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    except Exception:
        raise HTTPException(500, "The portal could not process the credentials.")


@app.post("/api/workflows/{workflow_id}/password", dependencies=[Depends(require_workflow)])
async def answer_password(workflow_id: str, payload: PasswordAnswerRequest):
    try:
        return await runtime.answer_password(workflow_id, payload.question_id, payload.password.get_secret_value(), payload.remember)
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.post("/api/workflows/{workflow_id}/approve", dependencies=[Depends(require_workflow)])
async def submit_approval(workflow_id: str, payload: ApprovalRequest):
    try:
        return await runtime.submit_approval(workflow_id, payload.approved, payload.overrides)
    except KeyError:
        raise HTTPException(404, "Workflow not found")


@app.post("/api/workflows/{workflow_id}/action", dependencies=[Depends(require_workflow)])
async def submit_action(workflow_id: str, payload: ActionChoiceRequest):
    try:
        return await runtime.submit_action_choice(workflow_id, payload.action)
    except KeyError:
        raise HTTPException(404, "Workflow not found")
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.get("/api/workflows/{workflow_id}/screenshot", dependencies=[Depends(require_workflow)])
async def workflow_screenshot(workflow_id: str):
    try:
        img_bytes = await browser_agent.take_screenshot(workflow_id)
        return Response(content=img_bytes, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
    except Exception as exc:
        raise HTTPException(404, f"Screenshot unavailable: {str(exc)[:200]}")


@app.post("/api/workflows/{workflow_id}/documents")
async def upload_document(workflow_id: str, file: UploadFile = File(...), wf: dict = Depends(require_workflow)):
    suffix = Path(file.filename or "upload.bin").suffix.lower()
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".docx"}
    if suffix not in allowed:
        raise HTTPException(400, "Supported: PDF, DOCX, TXT, PNG, JPG, JPEG, WEBP")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "File exceeds 20 MB limit")
    safe_name = Path(file.filename or "document").name
    user_dir = UPLOAD_DIR / wf["user_id"]
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / f"{uuid4().hex}{suffix}"
    try:
        dest.write_bytes(content)
    except OSError:
        dest.unlink(missing_ok=True)
        raise HTTPException(500, "Could not store document")
    try:
        return await runtime.handle_upload(workflow_id, dest, safe_name)
    except Exception as exc:
        raise HTTPException(422, f"Could not process document: {str(exc)[:250]}")


@app.get("/api/workflows/{workflow_id}/audit", dependencies=[Depends(require_workflow)])
def audit(workflow_id: str):
    return {"workflow_id": workflow_id, "events": store.get_events(workflow_id)}


# ===================== OPTIMIZER =====================

@app.get("/api/optimizer/insights")
def optimizer_insights(user: dict = Depends(get_current_user)):
    return store.get_all_run_insights(limit=50, user_id=user["id"])


# ===================== LEGACY BROWSER ENDPOINTS =====================

@app.post("/api/browser/open")
async def browser_open(payload: BrowserOpenRequest, user: dict = Depends(get_current_user)):
    require_workflow(payload.workflow_id, user)
    try:
        result = await browser_agent.open_portal(payload.workflow_id, str(payload.url))
        store.event(payload.workflow_id, "portal_opened", "Browser agent opened the selected portal", {"url": result["url"]})
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Could not open portal: {str(exc)[:300]}")


@app.post("/api/browser/inspect")
async def browser_inspect(payload: BrowserInspectRequest, user: dict = Depends(get_current_user)):
    require_workflow(payload.workflow_id, user)
    try:
        return await browser_agent.inspect(payload.workflow_id)
    except KeyError as exc:
        raise HTTPException(409, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Could not inspect page: {str(exc)[:300]}")


@app.post("/api/browser/suggest")
async def browser_suggest(payload: BrowserSuggestRequest, user: dict = Depends(get_current_user)):
    require_workflow(payload.workflow_id, user)
    try:
        inspected = await browser_agent.inspect(payload.workflow_id)
        return {"url": inspected["url"], "suggestions": suggest_field_mappings(inspected["fields"], payload.profile)}
    except KeyError as exc:
        raise HTTPException(409, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Could not map fields: {str(exc)[:300]}")


@app.post("/api/browser/fill")
async def browser_fill(payload: BrowserFillRequest, user: dict = Depends(get_current_user)):
    require_workflow(payload.workflow_id, user)
    try:
        result = await browser_agent.fill(payload.workflow_id, [m.model_dump() for m in payload.approved_mappings])
        store.event(payload.workflow_id, "form_fields_filled", "Browser agent populated approved form fields", {"filled_count": len(result["filled"])})
        return result
    except KeyError as exc:
        raise HTTPException(409, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Could not fill form: {str(exc)[:300]}")


@app.post("/api/browser/close/{workflow_id}", dependencies=[Depends(require_workflow)])
async def browser_close(workflow_id: str):
    await browser_agent.close(workflow_id)
    return {"closed": True}


@app.on_event("shutdown")
async def shutdown_browser_sessions():
    await browser_agent.close_all()
