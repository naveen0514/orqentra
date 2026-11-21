# Orqentra 2.0

**Prompt-driven autonomous application assistant with a chat interface, background agent execution, local RAG memory, document requests, and Playwright browser automation.**

Orqentra is designed around the experience you described: the user gives one natural-language request; the agent understands the task, searches saved applicant information and documents first, finds a likely official portal, and works in the background. The user primarily interacts through the chat window. A separate live activity panel reports agent steps, progress, and interruptions.

> This is a local research prototype, not a guarantee that every website or application can be completed end-to-end. Portal-specific adapters are needed for custom widgets, unusual page flows, and sites that block browser automation.

## What this version does

### Chat-first interaction

- Start by describing the desired application in ordinary language.
- The backend creates a workflow and runs agent steps asynchronously.
- The main UI contains a conversation and a separate live activity timeline.
- The user can upload requested documents from the chat composer.
- The agent asks for one missing required detail at a time and resumes after the answer.
- The activity panel shows queued, running, waiting, and completed steps.

### Prompt and portal discovery

- A lightweight intent agent categorizes common application requests.
- A small India service registry covers common destinations such as Passport Seva, National Scholarship Portal, National Career Service, GST, MCA, PAN/e-Filing, and Sarathi.
- For other requests, the optional `ddgs` search integration searches for possible portals. Search candidates are presented for user selection instead of being treated as verified official sites.
- Only HTTPS portal addresses are allowed by the browser agent. The host allow-list is configurable.

### RAG-first applicant memory

- Applicant profile values are stored locally in SQLite and reused across workflows.
- Previously uploaded documents are retained in a local document vault and can be reused in later tasks.
- A local lexical retrieval layer searches saved profile fields and document text before the agent asks the user for missing items.
- PDF, DOCX, TXT, PNG, JPG, JPEG, and WEBP uploads are accepted. PDF/DOCX/TXT extraction is supported; image OCR requires Tesseract.
- The optional local Llama 3 / Ollama fallback is disabled by default. It is only considered after deterministic extraction and local retrieval do not yield useful profile facts.

### Browser execution

- Playwright opens the selected portal in Chromium.
- For normal HTML forms, the agent inspects the current page and automatically fills high-confidence fields from saved applicant data.
- It can attach a previously uploaded document to a matching required file field.
- If a required value or document is missing, the agent asks in chat and resumes after the response or upload.
- Clearly labelled Next/Continue controls can be followed automatically.
- An OTP request appears in the chat as a dedicated one-time input. The value is sent directly to the browser and is not saved in chat history, profile memory, or audit events.
- The initial prompt must clearly authorize applying/submitting before the final submit control can be activated.

## Human-control boundaries

Some portal actions cannot safely or reliably be automated in a generic way:

- Users must sign in directly on the official website; passwords should not be sent in chat.
- CAPTCHA, biometric checks, e-signatures, legal declarations/consents, and payments require direct user handling.
- The agent pauses on protected fields or payment/declaration gates.
- The agent never invents missing applicant facts. It asks the user instead.
- The system can only guarantee form support for common HTML controls. Portals using custom JavaScript widgets, nested frames, complex upload widgets, or anti-automation controls may need an adapter or manual step.

For final submission, Orqentra checks for a clearly labelled final control, payment prompts, and unchecked declaration/consent/terms checkboxes. If a payment or declaration is present, it pauses. A portal-specific review is still required; the application owner is responsible for correctness and legal accuracy.

## Project structure

```text
orqentra/
  backend/
    app/
      main.py             FastAPI routes
      agent_runtime.py    Background chat/workflow runtime
      browser_agent.py    Playwright browser controls
      orchestrator.py     Intent/planning and document text extraction
      store.py            SQLite chat, events, applicant memory and document vault
      llm.py               Optional local Ollama/Llama adapter
      models.py            API request models
    tests/
    requirements.txt
    uploads/               Created automatically; local user documents
    orqentra.db             Created automatically; local application data
  frontend/
    src/App.jsx            Chat + live activity UI
    src/style.css
    package.json
  docs/
  sample_data/
  .env.example
```

## Run on macOS

**Requirements:** Python 3.10 or newer and Node.js 18 or newer. Install them first if they are not already available.

Unzip the project. Open Terminal in the extracted `orqentra` folder. Two convenience launchers are included: `start_backend_macos.command` creates the backend virtual environment, installs Python dependencies and Chromium, then starts FastAPI; `start_frontend_macos.command` installs Node dependencies once and starts Vite. You can double-click them in Finder or run them from Terminal.

### 1. Configure the local environment

```bash
cp .env.example .env
```

By default the example is configured for India and any public HTTPS portal. For a more restrictive setup, edit `ORQENTRA_ALLOWED_PORTAL_HOSTS` in `.env` to an explicit comma-separated list of trusted hostnames.

### 2. Install and start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m uvicorn app.main:app --reload
```

Keep this terminal open. The browser must run on the same computer as the backend. `ORQENTRA_HEADLESS=false` opens a Chromium window so you can handle login or any portal action that needs your direct attention. The agent itself runs its workflow in the backend while you use the chat interface.

### 3. Install and start the frontend

Open a **second Terminal window**:

```bash
cd /path/to/orqentra/frontend
npm install
npm run dev
```

Replace `/path/to/orqentra` with the path where you extracted the ZIP. Vite prints a local address, usually `http://localhost:5173`. Open that address in your browser.

The backend API runs at `http://127.0.0.1:8000`; API documentation is at `http://127.0.0.1:8000/docs`.

## Optional Llama 3 via Ollama

Orqentra does not require an LLM for the baseline workflow. It uses deterministic intent classification, local retrieval, labelled field matching and validation first.

To enable the optional fallback:

1. Install and run Ollama locally.
2. Pull a Llama 3 model, for example `ollama pull llama3`.
3. Change `.env`:

```env
ORQENTRA_OLLAMA_ENABLED=true
ORQENTRA_OLLAMA_MODEL=llama3
ORQENTRA_OLLAMA_HOST=http://127.0.0.1:11434
```

Restart the backend. The adapter is only used as a fallback for explicitly labelled non-secret profile information extracted from uploaded documents. OTPs and other authentication secrets are never passed to the LLM.

## How to use

1. Open Orqentra and type a request such as “Apply for a government scholarship using my saved documents and profile.”
2. Watch the Activity panel while the agent classifies the task, searches memory, and discovers a portal.
3. For a known India portal, Orqentra opens it. For web-search candidates, select the portal from the chat.
4. If the portal requires sign-in, complete it on the official website; navigate to the application page and type `ready` in chat.
5. The agent inspects fields, fills confident matches, and attaches matching saved documents.
6. If a required detail is missing, answer the chat question. If a document is missing, upload it in the chat composer. The workflow resumes automatically.
7. If the portal requests an OTP, enter it in the one-time OTP box shown in chat.
8. When the portal is ready to submit, Orqentra activates a clearly labelled final submit control only if the original request explicitly authorized submission and no payment/declaration/consent gate remains. Review the official portal confirmation.

## Data and privacy

- This prototype is intended for a **single local user**. It has no account system or multi-user isolation.
- Applicant profile data, chat messages, workflow events, extracted document text, and uploaded files are stored under `backend/` on the computer running FastAPI.
- Uploaded files are stored in `backend/uploads/`; SQLite data is stored in `backend/orqentra.db`.
- OTP input is not stored in the chat, profile, or event log. Do not send passwords, recovery codes, payment-card data, or other secrets through chat.
- Back up or remove the local database and upload folder deliberately. There is no cloud sync in this prototype.

## Tests

```bash
cd backend
python -m pytest -q
```

## API highlights

- `POST /api/chat` — start a task or send a message to an existing workflow.
- `GET /api/workflows/{id}` — workflow state and dynamic plan.
- `GET /api/workflows/{id}/messages` — chat history (OTP values are excluded).
- `GET /api/workflows/{id}/activity` — live activity events.
- `POST /api/workflows/{id}/documents` — upload a document and resume a document wait.
- `POST /api/workflows/{id}/otp` — send a one-time code directly to the browser without persistence.
- `POST /api/workflows/{id}/portal` — select a discovered HTTPS portal.
- `GET /api/memory/profile` and `GET /api/memory/documents` — inspect locally saved applicant memory metadata.

## Current prototype limitations

- The portal registry is deliberately small; web search helps discover other portals but candidates need confirmation.
- RAG retrieval is local lexical retrieval from saved profile values and document chunks. It is not yet a vector-embedding database.
- The first version uses deterministic field-label matching. Ambiguous or custom fields pause for user input instead of guessing.
- The browser session is held in memory. A backend restart closes it; restart/reopen the portal and send `retry` or `ready` to continue.
- A universal browser agent cannot guarantee completion of every portal. Site adapters are needed for non-standard components, dynamic grids, nested frames, and unusual workflows.
- Automatic submission can click a matching control but cannot prove that the portal accepted the application; verify the acknowledgement on the official portal.
