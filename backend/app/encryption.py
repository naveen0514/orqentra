"""AES-Fernet encryption for user profile data at rest.

Every user gets their own Fernet key derived from a master key stored in .env.
If no ORQENTRA_MASTER_KEY is set, one is generated and written to .env automatically.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet


def _get_master_key() -> bytes:
    """Return the 32-byte master key, creating one if it doesn't exist."""
    key = os.getenv("ORQENTRA_MASTER_KEY", "")
    if key and len(key) >= 32:
        return key[:32].encode()
    # Auto-generate a secure master key.
    generated = secrets.token_urlsafe(32)[:32]
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    try:
        existing = env_path.read_text() if env_path.exists() else ""
        if "ORQENTRA_MASTER_KEY" not in existing:
            with open(env_path, "a") as f:
                f.write(f"\n# Auto-generated encryption master key — do NOT share or delete.\nORQENTRA_MASTER_KEY={generated}\n")
        os.environ["ORQENTRA_MASTER_KEY"] = generated
    except OSError:
        os.environ["ORQENTRA_MASTER_KEY"] = generated
    return generated.encode()


def _derive_user_key(user_id: str) -> bytes:
    """Derive a per-user Fernet key from the master key + user_id."""
    master = _get_master_key()
    derived = hashlib.pbkdf2_hmac("sha256", master, user_id.encode(), iterations=100_000)
    return base64.urlsafe_b64encode(derived)


def encrypt_data(user_id: str, plaintext: str) -> str:
    """Encrypt a plaintext string; returns a URL-safe base64 token."""
    f = Fernet(_derive_user_key(user_id))
    return f.encrypt(plaintext.encode()).decode()


def decrypt_data(user_id: str, token: str) -> str:
    """Decrypt a Fernet token back to plaintext."""
    f = Fernet(_derive_user_key(user_id))
    return f.decrypt(token.encode()).decode()


def encrypt_dict(user_id: str, data: dict) -> str:
    """Encrypt a Python dict as JSON."""
    return encrypt_data(user_id, json.dumps(data, ensure_ascii=False))


def decrypt_dict(user_id: str, token: str) -> dict:
    """Decrypt a Fernet token back to a Python dict."""
    return json.loads(decrypt_data(user_id, token))
