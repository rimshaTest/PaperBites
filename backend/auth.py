"""
Minimal account system: email/password signup+login backed by JSON files,
with opaque bearer session tokens (no external auth/crypto dependencies).

This intentionally mirrors the JSON-file storage pattern already used by
bookmarks.py and the video metadata store rather than pulling in a database.
"""
import os
import json
import time
import hashlib
import secrets
from typing import Dict, Optional

USERS_FILE = os.environ.get("PAPERBITES_USERS_FILE", "users.json")
SESSIONS_FILE = os.environ.get("PAPERBITES_SESSIONS_FILE", "sessions.json")

SESSION_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
PBKDF2_ITERATIONS = 200_000


class AuthError(Exception):
    """Raised for user-facing auth failures (bad credentials, duplicate email, etc.)."""
    pass


def _load(path: str) -> Dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return {}


def _save(path: str, data: Dict) -> None:
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _hash_password(password: str, salt_hex: Optional[str] = None) -> Dict[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    return {"salt": salt.hex(), "hash": digest.hex()}


def create_user(email: str, password: str) -> Dict:
    """Create a new account. Raises AuthError on invalid input or duplicate email."""
    email = _normalize_email(email)
    if not email or "@" not in email:
        raise AuthError("A valid email is required")
    if not password or len(password) < 8:
        raise AuthError("Password must be at least 8 characters")

    users = _load(USERS_FILE)
    if email in users:
        raise AuthError("An account with this email already exists")

    hashed = _hash_password(password)
    user_id = secrets.token_hex(16)
    users[email] = {
        "id": user_id,
        "email": email,
        "salt": hashed["salt"],
        "password_hash": hashed["hash"],
        "created_at": time.time(),
    }
    _save(USERS_FILE, users)
    return {"id": user_id, "email": email}


def authenticate(email: str, password: str) -> Dict:
    """Verify credentials. Raises AuthError if they don't match."""
    email = _normalize_email(email)
    users = _load(USERS_FILE)
    record = users.get(email)
    if not record:
        raise AuthError("Invalid email or password")

    check = _hash_password(password, record["salt"])
    if not secrets.compare_digest(check["hash"], record["password_hash"]):
        raise AuthError("Invalid email or password")

    return {"id": record["id"], "email": record["email"]}


def get_user_by_id(user_id: str) -> Optional[Dict]:
    users = _load(USERS_FILE)
    for record in users.values():
        if record["id"] == user_id:
            return {"id": record["id"], "email": record["email"]}
    return None


def create_session(user_id: str) -> str:
    sessions = _load(SESSIONS_FILE)
    token = secrets.token_urlsafe(32)
    sessions[token] = {"user_id": user_id, "created_at": time.time()}
    _save(SESSIONS_FILE, sessions)
    return token


def get_user_id_for_token(token: str) -> Optional[str]:
    if not token:
        return None
    sessions = _load(SESSIONS_FILE)
    session = sessions.get(token)
    if not session:
        return None

    if time.time() - session["created_at"] > SESSION_TTL_SECONDS:
        del sessions[token]
        _save(SESSIONS_FILE, sessions)
        return None

    return session["user_id"]


def delete_session(token: str) -> None:
    sessions = _load(SESSIONS_FILE)
    if token in sessions:
        del sessions[token]
        _save(SESSIONS_FILE, sessions)
