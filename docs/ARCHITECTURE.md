# Orqentra 2.0 Architecture

## User-facing model

The React client presents two primary regions: (1) chat for the task, questions, document upload, and secure OTP entry; (2) live activity for background agent execution. The user does not configure a sequence of manual workflow steps.

## Runtime sequence

1. `POST /api/chat` creates a workflow and schedules the background runtime.
2. IntentAgent classifies the request and action type.
3. Store search retrieves applicant profile values and extracted text from previously uploaded documents (RAG-first).
4. PortalDiscovery uses a small known-service registry, then optional DDGS search for other requests.
5. Known registry matches can open automatically; general search candidates are surfaced for selection before browser navigation.
6. Playwright opens the chosen HTTPS site. Users sign in directly on the site if necessary.
7. The user sends `ready` after reaching an application page.
8. BrowserAutomationAgent inspects common HTML controls, field matching maps them to local memory, and high-confidence fields are filled.
9. Existing documents are matched to required file inputs; missing files/details are requested through chat.
10. The runtime pauses and resumes as user messages or uploads arrive. OTP uses a separate transient path and is excluded from persistence.
11. A clear Next/Continue action may be followed automatically. Final submit is conditional on an explicit original prompt and no detected payment/declaration/consent gate.
12. Events are persisted to SQLite and polled by the activity UI.

## Components

- **IntentAgent:** deterministic categorization baseline.
- **PortalDiscovery:** local service registry + optional DDGS search provider.
- **RAG memory:** SQLite profile key/value storage and local lexical search over document chunks.
- **Document intelligence:** text extraction from PDF/DOCX/TXT; optional Tesseract OCR for images.
- **OptionalLlama:** local Ollama fallback for extracting explicitly labelled facts from documents when deterministic extraction yields none.
- **BrowserAutomationAgent:** Playwright navigation, DOM inspection, safe field filling, file attachment, OTP routing, safe Next/Continue, guarded final submit.
- **AgentRuntime:** async task scheduling, chat handling, workflow checkpoints, pause/resume, and activity events.
- **Store:** SQLite workflows, events, messages, profile, documents and knowledge chunks.

## Security rules

- HTTPS only; wildcard host allow-list is for local prototype use. Restrict exact hosts in deployments.
- Never place OTP values in chat history, memory, model prompts, or audit details.
- Passwords and recovery codes are not collected in chat.
- Protected fields, payments, legal declarations, consent boxes, signatures, CAPTCHA and biometrics are human-controlled.
- Final submit requires clear authorization in the user's initial request, and payment/declaration checks can stop it.
- Extracted document facts are provenance-tagged and not invented when absent.

## Known gaps

The workflow task registry and browser session currently live in the FastAPI process. Durable job queues, multi-user authentication, database encryption, tenant isolation, browser session persistence, OCR service isolation, embedding-based RAG, portal-specific adapters, and full E2E testing are production hardening tasks.
