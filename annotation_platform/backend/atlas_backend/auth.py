"""Password hashing, session tokens, and FastAPI auth dependencies."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session as SASession

from . import db
from .database import get_db

# scrypt parameters — tuned for interactive use (~50ms on a modern laptop).
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DK_LEN = 64
_SALT_LEN = 16

SESSION_TTL = timedelta(days=30)


def _scrypt(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_DK_LEN,
    )


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password must not be empty")
    salt = os.urandom(_SALT_LEN)
    dk = _scrypt(password, salt)
    return f"scrypt${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, dk_b64 = stored.split("$", 2)
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    try:
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
    except (ValueError, base64.binascii.Error):
        return False
    return hmac.compare_digest(_scrypt(password, salt), expected)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def expires_at_iso(ttl: timedelta = SESSION_TTL) -> str:
    return (datetime.now(timezone.utc) + ttl).isoformat(timespec="seconds")


# ---- FastAPI dependencies ------------------------------------------------

def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def get_current_user_optional(
    authorization: str | None = Header(None),
    session: SASession = Depends(get_db),
) -> dict | None:
    token = _extract_bearer(authorization)
    if not token:
        return None
    return db.get_user_by_token(session, token)


def require_user(
    authorization: str | None = Header(None),
    session: SASession = Depends(get_db),
) -> dict:
    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = db.get_user_by_token(session, token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def _normalize_username(username: str) -> str:
    username = username.strip()
    if not username:
        raise ValueError("username must not be empty")
    if len(username) > 64:
        raise ValueError("username too long")
    if any(c.isspace() for c in username):
        raise ValueError("username must not contain whitespace")
    return username


def register_user(session: SASession, username: str, password: str) -> dict:
    username = _normalize_username(username)
    if len(password) < 6:
        raise ValueError("password must be at least 6 characters")
    if db.get_user_by_username(session, username) is not None:
        raise ValueError("username already exists")
    return db.create_user(session, username, hash_password(password))


def login(session: SASession, username: str, password: str) -> tuple[dict, str, str]:
    """Return (user, token, expires_at) or raise ValueError on bad credentials."""
    username = _normalize_username(username)
    user = db.get_user_by_username(session, username)
    if user is None or not verify_password(password, user["password_hash"]):
        raise ValueError("invalid credentials")
    token = new_session_token()
    exp = expires_at_iso()
    db.create_session(session, user["id"], token, exp)
    return user, token, exp
