"""User accounts + sessions (app-level auth).

Admin-created accounts only (no open signup). Passwords are PBKDF2-HMAC-SHA256
hashed with a per-user salt (stdlib — no extra deps). Sessions are opaque random
tokens stored server-side (so they're individually revocable) and presented by
the client as a `Bearer` token.

This module also creates all the per-user data tables (watchlist, preferences,
notes, recently_viewed) so account state lives alongside the existing cache in
the same SQLite file.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import config
from .db import _connect, init_db

log = logging.getLogger("stockclock.accounts")

_PBKDF2_ROUNDS = 200_000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def init_accounts() -> None:
    """Create account + per-user tables, then bootstrap the admin from env."""
    init_db()
    conn = _connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt          TEXT NOT NULL,
                is_admin      INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS watchlist (
                user_id  INTEGER NOT NULL,
                ticker   TEXT NOT NULL,
                added_at TEXT NOT NULL,
                PRIMARY KEY (user_id, ticker)
            );
            CREATE TABLE IF NOT EXISTS preferences (
                user_id        INTEGER PRIMARY KEY,
                default_ticker TEXT,
                default_range  TEXT
            );
            CREATE TABLE IF NOT EXISTS notes (
                user_id    INTEGER NOT NULL,
                ticker     TEXT NOT NULL,
                body       TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, ticker)
            );
            CREATE TABLE IF NOT EXISTS recently_viewed (
                user_id   INTEGER NOT NULL,
                ticker    TEXT NOT NULL,
                viewed_at TEXT NOT NULL,
                PRIMARY KEY (user_id, ticker)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    if config.ADMIN_USERNAME and config.ADMIN_PASSWORD and not get_user(config.ADMIN_USERNAME):
        create_user(config.ADMIN_USERNAME, config.ADMIN_PASSWORD, is_admin=True)
        log.info("bootstrapped admin account %s", config.ADMIN_USERNAME)


# --- password hashing --------------------------------------------------------
def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ROUNDS)
    return dk.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    test, _ = hash_password(password, salt)
    return secrets.compare_digest(test, password_hash)


# --- users -------------------------------------------------------------------
def create_user(username: str, password: str, is_admin: bool = False) -> dict:
    username = (username or "").strip().lower()
    if not username or not password:
        raise ValueError("username and password are required")
    password_hash, salt = hash_password(password)
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, is_admin, created_at) VALUES (?,?,?,?,?)",
            (username, password_hash, salt, 1 if is_admin else 0, _now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    return get_user(username)


def get_user(username: str) -> Optional[dict]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", ((username or "").strip().lower(),)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def list_users() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, username, is_admin, created_at FROM users ORDER BY username"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def delete_user(username: str) -> bool:
    user = get_user(username)
    if not user:
        return False
    uid = user["id"]
    conn = _connect()
    try:
        for table in ("sessions", "watchlist", "preferences", "notes", "recently_viewed"):
            conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()
    finally:
        conn.close()
    return True


def set_password(username: str, password: str) -> bool:
    user = get_user(username)
    if not user:
        return False
    password_hash, salt = hash_password(password)
    conn = _connect()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (password_hash, salt, user["id"])
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))  # force re-login
        conn.commit()
    finally:
        conn.close()
    return True


def authenticate(username: str, password: str) -> Optional[dict]:
    user = get_user(username)
    if not user or not verify_password(password, user["password_hash"], user["salt"]):
        return None
    return user


# --- sessions ----------------------------------------------------------------
def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
            (token, user_id, now.isoformat(), (now + timedelta(days=config.SESSION_TTL_DAYS)).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def user_for_token(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < _now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        urow = conn.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)).fetchone()
    finally:
        conn.close()
    return dict(urow) if urow else None


def delete_session(token: Optional[str]) -> None:
    if not token:
        return
    conn = _connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()
