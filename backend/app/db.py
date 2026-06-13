"""SQLite cache layer.

One row per ticker holding the full normalized snapshot as JSON, plus a small
key/value meta table (used for `last_refresh`). Short-lived connections + WAL
keep the FastAPI request thread and the APScheduler background thread from
stepping on each other.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from . import config

_init_lock = threading.Lock()
_initialized = False


def _connect() -> sqlite3.Connection:
    # check_same_thread=False is safe here because every call opens and closes
    # its own connection; we never share a connection across threads.
    conn = sqlite3.connect(config.CACHE_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    global _initialized
    with _init_lock:
        if _initialized:
            return
        directory = os.path.dirname(os.path.abspath(config.CACHE_PATH))
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = _connect()
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    ticker     TEXT PRIMARY KEY,
                    fetched_at TEXT NOT NULL,
                    source     TEXT NOT NULL,
                    data       TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        _initialized = True


def save_snapshot(snapshot: dict) -> None:
    """Overwrite the cached snapshot for a ticker."""
    init_db()
    ticker = snapshot["ticker"].upper()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO snapshots (ticker, fetched_at, source, data)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                fetched_at = excluded.fetched_at,
                source     = excluded.source,
                data       = excluded.data
            """,
            (
                ticker,
                snapshot["fetched_at"],
                snapshot["source"],
                json.dumps(snapshot, separators=(",", ":")),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_snapshot(ticker: str) -> Optional[dict]:
    init_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT data FROM snapshots WHERE ticker = ?", (ticker.upper(),)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return json.loads(row["data"])


def all_tickers() -> list[str]:
    init_db()
    conn = _connect()
    try:
        rows = conn.execute("SELECT ticker FROM snapshots ORDER BY ticker").fetchall()
    finally:
        conn.close()
    return [r["ticker"] for r in rows]


def all_snapshots_meta() -> list[dict]:
    """Lightweight listing (ticker, fetched_at, source) without the JSON blob."""
    init_db()
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT ticker, fetched_at, source FROM snapshots ORDER BY ticker"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def set_meta(key: str, value: str) -> None:
    init_db()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO meta (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def get_meta(key: str) -> Optional[str]:
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    finally:
        conn.close()
    return row["value"] if row else None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
