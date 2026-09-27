"""
Minimal account system: email/password signup+login backed by MongoDB, with opaque bearer
session tokens (no external auth/crypto dependencies) and an emailed-code password reset flow.

Users, sessions, and password reset codes each get their own collection in the same MongoDB
database as papers/paper_reviews (see db.py) - the JSON-file storage this module used originally
didn't survive concurrent writers or multiple backend instances, so account data now lives
alongside every other real document this app has.
"""
import time
import hashlib
import secrets
from typing import Dict, Optional

import db

SESSION_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
RESET_CODE_TTL_SECONDS = 15 * 60
PBKDF2_ITERATIONS = 200_000


class AuthError(Exception):
    """Raised for user-facing auth failures (bad credentials, duplicate email, etc.)."""
    pass


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

    users = db.get_db().users
    if users.find_one({"email": email}):
        raise AuthError("An account with this email already exists")

    hashed = _hash_password(password)
    user_id = secrets.token_hex(16)
    users.insert_one({
        "id": user_id,
        "email": email,
        "salt": hashed["salt"],
        "password_hash": hashed["hash"],
        "created_at": time.time(),
    })
    return {"id": user_id, "email": email}


def authenticate(email: str, password: str) -> Dict:
    """Verify credentials. Raises AuthError if they don't match."""
    email = _normalize_email(email)
    record = db.get_db().users.find_one({"email": email})
    if not record:
        raise AuthError("Invalid email or password")

    check = _hash_password(password, record["salt"])
    if not secrets.compare_digest(check["hash"], record["password_hash"]):
        raise AuthError("Invalid email or password")

    return {"id": record["id"], "email": record["email"]}


def get_user_by_id(user_id: str) -> Optional[Dict]:
    record = db.get_db().users.find_one({"id": user_id})
    if not record:
        return None
    return {"id": record["id"], "email": record["email"]}


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    db.get_db().sessions.insert_one({"_id": token, "user_id": user_id, "created_at": time.time()})
    return token


def get_user_id_for_token(token: str) -> Optional[str]:
    if not token:
        return None
    sessions = db.get_db().sessions
    session = sessions.find_one({"_id": token})
    if not session:
        return None

    if time.time() - session["created_at"] > SESSION_TTL_SECONDS:
        sessions.delete_one({"_id": token})
        return None

    return session["user_id"]


def delete_session(token: str) -> None:
    db.get_db().sessions.delete_one({"_id": token})


def create_password_reset_code(email: str) -> Optional[str]:
    """Generate and store a 6-digit reset code for this email, replacing any previous one.
    Returns None if there's no account with this email - the caller (api_server.py) still
    responds with the same generic "check your email" message either way, so this never leaks
    whether an address is registered."""
    email = _normalize_email(email)
    if not db.get_db().users.find_one({"email": email}):
        return None

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.get_db().password_resets.update_one(
        {"_id": email},
        {"$set": {"code": code, "created_at": time.time()}},
        upsert=True,
    )
    return code


def reset_password(email: str, code: str, new_password: str) -> None:
    """Consume a reset code and set a new password. Raises AuthError on a wrong/expired code or
    an invalid new password. Also invalidates every other active session for this account, since
    a password reset should log out anyone else who was signed in."""
    email = _normalize_email(email)
    if not new_password or len(new_password) < 8:
        raise AuthError("Password must be at least 8 characters")

    resets = db.get_db().password_resets
    entry = resets.find_one({"_id": email})
    if not entry or not code or not secrets.compare_digest(entry["code"], code):
        raise AuthError("Invalid or expired code")
    if time.time() - entry["created_at"] > RESET_CODE_TTL_SECONDS:
        resets.delete_one({"_id": email})
        raise AuthError("Invalid or expired code")

    users = db.get_db().users
    record = users.find_one({"email": email})
    if not record:
        raise AuthError("Invalid or expired code")

    hashed = _hash_password(new_password)
    users.update_one(
        {"email": email},
        {"$set": {"salt": hashed["salt"], "password_hash": hashed["hash"]}},
    )
    resets.delete_one({"_id": email})
    db.get_db().sessions.delete_many({"user_id": record["id"]})
