"""SQLite persistence for Orqentra with user-scoped encrypted storage.

All user profile data is encrypted at rest using per-user Fernet keys.
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .encryption import encrypt_data, decrypt_data, encrypt_dict, decrypt_dict


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        self.path = str(path)
        with self.connect() as con:
            # ---- Users ----
            con.execute("""CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL DEFAULT '',
                onboarding_complete INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email COLLATE NOCASE)")

            # ---- Encrypted user profile (key-value, all values encrypted) ----
            con.execute("""CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                field_key TEXT NOT NULL,
                encrypted_value TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                source TEXT NOT NULL DEFAULT 'onboarding',
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, field_key)
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_profile_user ON user_profile(user_id)")

            # ---- Encrypted user documents ----
            con.execute("""CREATE TABLE IF NOT EXISTS user_documents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                doc_name TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                encrypted_text TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_userdocs_user ON user_documents(user_id)")

            # ---- Workflows (now user-scoped) ----
            con.execute("""CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT '',
                goal TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_workflows_user ON workflows(user_id)")
            # Add user_id column if missing (migration from old schema)
            try:
                con.execute("ALTER TABLE workflows ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # column already exists

            # ---- Events ----
            con.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT NOT NULL
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_events_wf ON events(workflow_id, id)")

            # ---- Messages ----
            con.execute("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'text'
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_messages_wf ON messages(workflow_id, id)")

            # ---- Legacy tables (kept for compatibility) ----
            con.execute("CREATE TABLE IF NOT EXISTS profile_memory (key TEXT PRIMARY KEY, value TEXT NOT NULL, source TEXT NOT NULL, updated_at TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, workflow_id TEXT, filename TEXT NOT NULL, path TEXT NOT NULL, extracted_text TEXT NOT NULL, doc_type TEXT NOT NULL, created_at TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS knowledge_chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT NOT NULL, created_at TEXT NOT NULL)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_documents_wf ON documents(workflow_id, created_at)")

            # ---- Optimizer run history ----
            con.execute("""CREATE TABLE IF NOT EXISTS run_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                goal TEXT NOT NULL,
                service TEXT NOT NULL,
                status TEXT NOT NULL,
                fields_filled INTEGER NOT NULL DEFAULT 0,
                pages_visited INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                insights TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_run_history_svc ON run_history(service, status)")

    def connect(self):
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        return con

    # ===================== USER MANAGEMENT =====================

    def create_user(self, email: str, password_hash: str, full_name: str = "") -> dict:
        uid = str(uuid.uuid4())
        stamp = now()
        with self.connect() as con:
            con.execute("INSERT INTO users(id,email,password_hash,full_name,onboarding_complete,created_at,updated_at) VALUES (?,?,?,?,0,?,?)",
                        (uid, email, password_hash, full_name, stamp, stamp))
        return {"id": uid, "email": email, "full_name": full_name, "onboarding_complete": False}

    def get_user_by_email(self, email: str) -> dict | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone()
        if not row:
            return None
        return dict(row)

    def get_user_by_id(self, user_id: str) -> dict | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return None
        return dict(row)

    def set_onboarding_complete(self, user_id: str):
        with self.connect() as con:
            con.execute("UPDATE users SET onboarding_complete=1, updated_at=? WHERE id=?", (now(), user_id))

    # ===================== ENCRYPTED PROFILE =====================

    def save_user_field(self, user_id: str, key: str, value: str, category: str = "general", source: str = "onboarding"):
        """Save a single profile field, encrypted at rest."""
        if not value or not str(value).strip():
            return
        encrypted = encrypt_data(user_id, str(value).strip())
        stamp = now()
        with self.connect() as con:
            con.execute("""INSERT INTO user_profile(user_id, field_key, encrypted_value, category, source, updated_at)
                          VALUES (?,?,?,?,?,?)
                          ON CONFLICT(user_id, field_key) DO UPDATE SET
                            encrypted_value=excluded.encrypted_value,
                            source=excluded.source,
                            updated_at=excluded.updated_at""",
                        (user_id, key, encrypted, category, source, stamp))

    def save_user_fields_bulk(self, user_id: str, fields: dict[str, str], category: str = "general", source: str = "onboarding"):
        """Save multiple profile fields at once."""
        for key, value in fields.items():
            if value and str(value).strip():
                self.save_user_field(user_id, key, str(value).strip(), category, source)

    def get_user_profile(self, user_id: str) -> dict[str, str]:
        """Retrieve and decrypt all profile fields for a user."""
        with self.connect() as con:
            rows = con.execute("SELECT field_key, encrypted_value FROM user_profile WHERE user_id=? ORDER BY field_key", (user_id,)).fetchall()
        profile = {}
        for row in rows:
            try:
                profile[row["field_key"]] = decrypt_data(user_id, row["encrypted_value"])
            except Exception:
                profile[row["field_key"]] = "[decryption error]"
        return profile

    def get_user_profile_by_category(self, user_id: str, category: str) -> dict[str, str]:
        """Retrieve profile fields for a specific category."""
        with self.connect() as con:
            rows = con.execute("SELECT field_key, encrypted_value FROM user_profile WHERE user_id=? AND category=?", (user_id, category)).fetchall()
        profile = {}
        for row in rows:
            try:
                profile[row["field_key"]] = decrypt_data(user_id, row["encrypted_value"])
            except Exception:
                profile[row["field_key"]] = "[decryption error]"
        return profile

    def has_user_field(self, user_id: str, key: str) -> bool:
        """Check if a user has a specific profile field stored."""
        with self.connect() as con:
            row = con.execute("SELECT 1 FROM user_profile WHERE user_id=? AND field_key=?", (user_id, key)).fetchone()
        return row is not None

    def get_user_field_keys(self, user_id: str) -> list[str]:
        """Return a list of all stored field keys (not values) for a user."""
        with self.connect() as con:
            rows = con.execute("SELECT field_key FROM user_profile WHERE user_id=? ORDER BY field_key", (user_id,)).fetchall()
        return [r["field_key"] for r in rows]

    # ===================== USER DOCUMENTS =====================

    def add_user_document(self, user_id: str, doc_name: str, doc_type: str, file_path: str, extracted_text: str = "", metadata: dict = None) -> str:
        """Store an uploaded document for a user. Extracted text is encrypted."""
        doc_id = str(uuid.uuid4())
        enc_text = encrypt_data(user_id, extracted_text) if extracted_text else ""
        with self.connect() as con:
            con.execute("INSERT INTO user_documents(id,user_id,doc_name,doc_type,file_path,encrypted_text,metadata,created_at) VALUES (?,?,?,?,?,?,?,?)",
                        (doc_id, user_id, doc_name, doc_type, file_path, enc_text,
                         json.dumps(metadata or {}, ensure_ascii=False), now()))
        return doc_id

    def get_user_documents(self, user_id: str) -> list[dict]:
        with self.connect() as con:
            rows = con.execute("SELECT id,doc_name,doc_type,file_path,metadata,created_at FROM user_documents WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_user_document_text(self, user_id: str, doc_id: str) -> str:
        """Decrypt and return the extracted text of a document."""
        with self.connect() as con:
            row = con.execute("SELECT encrypted_text FROM user_documents WHERE id=? AND user_id=?", (doc_id, user_id)).fetchone()
        if not row or not row["encrypted_text"]:
            return ""
        try:
            return decrypt_data(user_id, row["encrypted_text"])
        except Exception:
            return ""

    # ===================== WORKFLOWS (user-scoped) =====================

    def save_workflow(self, item: dict[str, Any]):
        stamp = now()
        with self.connect() as con:
            old = con.execute("SELECT id FROM workflows WHERE id=?", (item["id"],)).fetchone()
            user_id = item.get("user_id", "")
            if old:
                con.execute("UPDATE workflows SET data=?, updated_at=? WHERE id=?", (json.dumps(item), stamp, item["id"]))
            else:
                con.execute("INSERT INTO workflows VALUES (?,?,?,?,?,?)", (item["id"], user_id, item["goal"], json.dumps(item), stamp, stamp))

    def get_workflow(self, wid: str):
        with self.connect() as con:
            row = con.execute("SELECT data FROM workflows WHERE id=?", (wid,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_workflows(self, user_id: str = ""):
        with self.connect() as con:
            if user_id:
                rows = con.execute("SELECT data FROM workflows WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (user_id,)).fetchall()
            else:
                rows = con.execute("SELECT data FROM workflows ORDER BY created_at DESC LIMIT 50").fetchall()
        return [json.loads(r["data"]) for r in rows]

    # ===================== EVENTS & MESSAGES =====================

    def event(self, wid: str, kind: str, message: str, details=None):
        with self.connect() as con:
            con.execute("INSERT INTO events(workflow_id,created_at,kind,message,details) VALUES (?,?,?,?,?)",
                        (wid, now(), kind, message, json.dumps(details or {}, ensure_ascii=False)))

    def get_events(self, wid: str):
        with self.connect() as con:
            rows = con.execute("SELECT created_at,kind,message,details FROM events WHERE workflow_id=? ORDER BY id", (wid,)).fetchall()
        return [{"created_at": r["created_at"], "kind": r["kind"], "message": r["message"], "details": json.loads(r["details"])} for r in rows]

    def add_message(self, wid: str, role: str, content: str, kind: str = "text"):
        with self.connect() as con:
            con.execute("INSERT INTO messages(workflow_id,created_at,role,content,kind) VALUES (?,?,?,?,?)",
                        (wid, now(), role, content, kind))

    def get_messages(self, wid: str):
        with self.connect() as con:
            rows = con.execute("SELECT created_at,role,content,kind FROM messages WHERE workflow_id=? ORDER BY id", (wid,)).fetchall()
        return [dict(r) for r in rows]

    # ===================== LEGACY PROFILE (backward compat) =====================

    def save_profile_value(self, key: str, value: Any, source: str = "user"):
        if value is None or str(value).strip() == "":
            return
        encoded = json.dumps(value, ensure_ascii=False)
        with self.connect() as con:
            con.execute("INSERT INTO profile_memory(key,value,source,updated_at) VALUES (?,?,?,?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, source=excluded.source, updated_at=excluded.updated_at",
                        (key, encoded, source, now()))

    def get_profile(self) -> dict[str, Any]:
        with self.connect() as con:
            rows = con.execute("SELECT key,value FROM profile_memory ORDER BY key").fetchall()
        profile: dict[str, Any] = {}
        for row in rows:
            try:
                profile[row["key"]] = json.loads(row["value"])
            except Exception:
                profile[row["key"]] = row["value"]
        return profile

    def add_document(self, doc_id: str, workflow_id: str | None, filename: str, path: str, extracted_text: str, doc_type: str):
        with self.connect() as con:
            con.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?)",
                        (doc_id, workflow_id, filename, path, extracted_text, doc_type, now()))
        if extracted_text.strip():
            words = extracted_text.split()
            for start in range(0, len(words), 220):
                chunk = " ".join(words[start:start + 220])
                with self.connect() as con:
                    con.execute("INSERT INTO knowledge_chunks(source,content,metadata,created_at) VALUES (?,?,?,?)",
                                (filename, chunk, json.dumps({"doc_id": doc_id, "workflow_id": workflow_id, "doc_type": doc_type}), now()))

    def list_documents(self):
        with self.connect() as con:
            rows = con.execute("SELECT id,workflow_id,filename,path,doc_type,created_at FROM documents ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def get_documents(self):
        with self.connect() as con:
            rows = con.execute("SELECT id,workflow_id,filename,path,extracted_text,doc_type,created_at FROM documents ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    # ===================== RAG MEMORY SEARCH =====================

    def search_memory(self, query: str, limit: int = 8, user_id: str = ""):
        """Enhanced local lexical & synonym retriever, now also searches encrypted user profile."""
        import re
        base_terms = {t.lower() for t in re.findall(r"[a-zA-Z0-9]{3,}", query)}
        synonyms_map = {
            "dob": ["date", "birth", "birthday"], "birth": ["dob", "born"],
            "income": ["salary", "annual", "earnings", "ctc"], "salary": ["income", "earnings", "ctc"],
            "job": ["career", "employment", "position", "work", "occupation"],
            "work": ["job", "employment", "career", "experience"],
            "college": ["university", "institution", "school", "degree"],
            "degree": ["qualification", "education", "graduation", "course"],
            "phone": ["mobile", "contact", "cell", "telephone"], "mobile": ["phone", "contact", "cell"],
            "address": ["residence", "residential", "street", "city", "state", "pincode"],
            "passport": ["travel", "citizenship", "identity"], "id": ["identity", "identification", "aadhaar", "national"],
        }
        expanded_terms = set(base_terms)
        for term in base_terms:
            if term in synonyms_map:
                expanded_terms.update(synonyms_map[term])
        terms = expanded_terms
        hits: list[tuple[float, dict[str, Any]]] = []

        # Search encrypted user profile if user_id provided
        if user_id:
            try:
                user_profile = self.get_user_profile(user_id)
                for key, value in user_profile.items():
                    content = f"{key.replace('_', ' ')}: {value}"
                    tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]{3,}", content)}
                    overlap = len(terms & tokens)
                    if overlap > 0:
                        score = (overlap / max(1, len(terms))) + 0.15  # Boost user-scoped data
                        hits.append((score, {"source": "user profile", "content": content, "kind": "profile", "key": key}))
            except Exception:
                pass

        # Legacy profile
        profile = self.get_profile()
        for key, value in profile.items():
            content = f"{key.replace('_', ' ')}: {value}"
            tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]{3,}", content)}
            overlap = len(terms & tokens)
            if overlap > 0:
                score = (overlap / max(1, len(terms))) + 0.1
                hits.append((score, {"source": "saved profile", "content": content, "kind": "profile", "key": key}))

        for doc in self.get_documents():
            content = doc["extracted_text"]
            tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]{3,}", content[:12000])}
            overlap = len(terms & tokens)
            if overlap > 0:
                score = overlap / max(1, len(terms))
                lowered = content.lower()
                pos = next((lowered.find(term) for term in terms if lowered.find(term) >= 0), 0)
                snippet = content[max(0, pos - 220):pos + 700]
                hits.append((score, {"source": doc["filename"], "content": snippet, "kind": "document", "doc_id": doc["id"]}))

        for row in self._get_chunks():
            tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]{3,}", row["content"])}
            overlap = len(terms & tokens)
            if overlap > 0:
                score = overlap / max(1, len(terms))
                hits.append((score, {"source": row["source"], "content": row["content"][:1000], "kind": "chunk"}))

        hits.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in hits[:limit]]

    def _get_chunks(self):
        with self.connect() as con:
            return [dict(r) for r in con.execute("SELECT source,content,metadata FROM knowledge_chunks ORDER BY id DESC LIMIT 200").fetchall()]

    # ===================== OPTIMIZER =====================

    def save_run_outcome(self, workflow_id: str, goal: str, service: str, status: str,
                         fields_filled: int = 0, pages_visited: int = 0, error_count: int = 0, insights: dict = None):
        with self.connect() as con:
            con.execute("INSERT INTO run_history(workflow_id,goal,service,status,fields_filled,pages_visited,error_count,insights,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                        (workflow_id, goal, service, status, fields_filled, pages_visited, error_count, json.dumps(insights or {}), now()))

    def get_run_insights(self, service: str, limit: int = 10) -> list[dict]:
        with self.connect() as con:
            rows = con.execute("SELECT goal,status,fields_filled,pages_visited,error_count,insights,created_at FROM run_history WHERE service=? ORDER BY id DESC LIMIT ?", (service, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_all_run_insights(self, limit: int = 20) -> list[dict]:
        with self.connect() as con:
            rows = con.execute("SELECT workflow_id,goal,service,status,fields_filled,pages_visited,error_count,created_at FROM run_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
