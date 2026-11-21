# Production hardening

Before using Orqentra with real personal or legally consequential applications:

1. Add authentication and per-user data isolation. Current SQLite storage is single-user local mode.
2. Encrypt sensitive fields and document storage at rest; add retention/deletion controls and backups.
3. Replace in-process task scheduling with durable workers/checkpoints and recover browser sessions safely after restart.
4. Restrict portal hosts; validate search sources and portal ownership. Avoid unrestricted production wildcard mode.
5. Add portal-specific adapters and a supported-site test matrix. Generic DOM matching is not universal.
6. Improve RAG with embeddings and provenance, confidence calibration, conflict detection, and explicit user correction.
7. Add robust document classification, scanned-PDF OCR, file malware scanning, and upload size/page limits.
8. Add secure remote OTP/browser-session channels; never log OTP, password, token, or session cookie data.
9. Add separate gates for fees, signatures, sworn declarations, consents, and statutory attestations.
10. Verify acknowledgements with portal state, not only browser text. Provide user-visible audit/export.
11. Add browser isolation, network egress controls, DNS rebinding protection, CSRF protection and API authentication.
12. Conduct threat modeling, privacy review, and human-factors testing before real-world use.
