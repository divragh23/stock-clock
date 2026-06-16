"""Per-user data: watchlist, preferences, notes, and recently-viewed.

All keyed by user_id. The stock data itself (prices/earnings) stays a single
shared cache — only these personalization tables are per account.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .db import _connect


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- watchlist ---------------------------------------------------------------
def get_watchlist(user_id: int) -> list[str]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at", (user_id,)
        ).fetchall()
    finally:
        conn.close()
    return [r["ticker"] for r in rows]


def add_watchlist(user_id: int, ticker: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, ticker, added_at) VALUES (?,?,?)",
            (user_id, ticker.strip().upper(), _now()),
        )
        conn.commit()
    finally:
        conn.close()


def remove_watchlist(user_id: int, ticker: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker.strip().upper())
        )
        conn.commit()
    finally:
        conn.close()


# --- preferences -------------------------------------------------------------
def get_preferences(user_id: int) -> dict:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT default_ticker, default_range FROM preferences WHERE user_id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {"default_ticker": None, "default_range": None}
    return {"default_ticker": row["default_ticker"], "default_range": row["default_range"]}


def set_preferences(user_id: int, default_ticker=None, default_range=None) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO preferences (user_id, default_ticker, default_range) VALUES (?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                default_ticker = excluded.default_ticker,
                default_range  = excluded.default_range
            """,
            (user_id, (default_ticker or None), (default_range or None)),
        )
        conn.commit()
    finally:
        conn.close()


# --- notes (one editable note per ticker per user) ---------------------------
def get_note(user_id: int, ticker: str) -> str:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT body FROM notes WHERE user_id = ? AND ticker = ?", (user_id, ticker.strip().upper())
        ).fetchone()
    finally:
        conn.close()
    return row["body"] if row else ""


def set_note(user_id: int, ticker: str, body: str) -> None:
    ticker = ticker.strip().upper()
    conn = _connect()
    try:
        if body and body.strip():
            conn.execute(
                """
                INSERT INTO notes (user_id, ticker, body, updated_at) VALUES (?,?,?,?)
                ON CONFLICT(user_id, ticker) DO UPDATE SET body = excluded.body, updated_at = excluded.updated_at
                """,
                (user_id, ticker, body.strip(), _now()),
            )
        else:
            conn.execute("DELETE FROM notes WHERE user_id = ? AND ticker = ?", (user_id, ticker))
        conn.commit()
    finally:
        conn.close()


# --- recently viewed ---------------------------------------------------------
def record_view(user_id: int, ticker: str, keep: int = 12) -> None:
    ticker = ticker.strip().upper()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO recently_viewed (user_id, ticker, viewed_at) VALUES (?,?,?)
            ON CONFLICT(user_id, ticker) DO UPDATE SET viewed_at = excluded.viewed_at
            """,
            (user_id, ticker, _now()),
        )
        # Keep only the most recent `keep` per user.
        conn.execute(
            """
            DELETE FROM recently_viewed WHERE user_id = ? AND ticker NOT IN (
                SELECT ticker FROM recently_viewed WHERE user_id = ? ORDER BY viewed_at DESC LIMIT ?
            )
            """,
            (user_id, user_id, keep),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent(user_id: int, limit: int = 12) -> list[str]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT ticker FROM recently_viewed WHERE user_id = ? ORDER BY viewed_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [r["ticker"] for r in rows]
