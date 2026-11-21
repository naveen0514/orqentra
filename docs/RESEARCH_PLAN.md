# Orqentra 2.0 Development Roadmap

The included project is an executable local MVP of the conversational background-agent design.

## Completed in this package

- Chat-first task initiation and conversation persistence.
- Separate live activity panel backed by workflow events.
- Deterministic intent classification and portal discovery (known services + optional search).
- Local SQLite applicant profile and document vault with RAG-style lexical retrieval.
- PDF, DOCX, TXT and image upload/extraction support (image OCR needs Tesseract).
- Optional local Llama 3/Ollama fallback for non-secret document facts.
- Playwright portal launch, conservative application-link discovery, form inspection, high-confidence form filling, prior-document attachment, OTP routing, and guarded submission attempts.
- Pause/resume behavior for missing details, missing documents, login, and unsupported controls.

## Next engineering iterations

1. Add vector embeddings and provenance-aware conflict resolution for RAG.
2. Add a browser session manager with durable persistence and optional embedded browser streaming.
3. Add portal-specific adapters and an integration test harness with mock application portals.
4. Add a document-to-requirement classifier and support for more file types and scanned PDF OCR.
5. Add per-user authentication, encryption at rest, data retention/deletion and tenant isolation.
6. Add a durable worker queue, retries, idempotency, and workflow recovery after server restarts.
7. Add a portal verification registry and domain ownership checks before automatic navigation.
8. Improve submit-result verification and acknowledgement-number extraction.
