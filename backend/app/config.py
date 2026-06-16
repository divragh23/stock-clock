"""Central configuration, all sourced from environment variables.

Nothing secret lives in code. The frontend never imports this module — it only
talks to the FastAPI backend, so the Finnhub key stays server-side.
"""
from __future__ import annotations

import os

# Load backend/.env for local-dev convenience. In production the systemd
# EnvironmentFile sets these vars directly; python-dotenv does NOT override
# variables that are already set, so the two never conflict. No-op if
# python-dotenv isn't installed.
try:
    from dotenv import load_dotenv

    _ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(_ENV_FILE)
except ImportError:
    pass


def _split_tickers(raw: str) -> list[str]:
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


# --- Secrets / sources -------------------------------------------------------
FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "").strip()

# --- Accounts / sessions -----------------------------------------------------
# Bootstrap admin: if set and the users table is empty, this account is created
# (is_admin) on startup. Admin can then create/remove other accounts via the API.
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "").strip().lower()
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
# How long a login session stays valid.
SESSION_TTL_DAYS: int = int(os.getenv("SESSION_TTL_DAYS", "30"))

# --- Cache -------------------------------------------------------------------
# Persist the SQLite file at a stable path on the droplet (e.g.
# /var/lib/stockclock/cache.db). Defaults to a file next to the backend for
# local dev.
CACHE_PATH: str = os.getenv(
    "CACHE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache.db"),
)

# --- Refresh / staleness -----------------------------------------------------
# Fixed watch-list refreshed by the nightly job (in addition to any ticker that
# has been requested on demand and is therefore already in the cache).
TICKERS: list[str] = _split_tickers(os.getenv("TICKERS", "NVDA,AAPL,MSFT"))

# A snapshot older than this many hours is flagged "stale" to the UI.
STALE_AFTER_HOURS: float = float(os.getenv("STALE_AFTER_HOURS", "30"))

# Nightly refresh time (server local time, 24h clock) unless TZ overridden.
REFRESH_HOUR: int = int(os.getenv("REFRESH_HOUR", "22"))
REFRESH_MINUTE: int = int(os.getenv("REFRESH_MINUTE", "0"))
# IANA name e.g. "America/New_York"; empty => server local time.
SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "").strip()

# Warm the cache for the TICKERS list on startup (in a background thread, never
# blocks boot). Set to "false" on flaky networks.
REFRESH_ON_START: bool = os.getenv("REFRESH_ON_START", "true").lower() in ("1", "true", "yes")

# --- yfinance fetch behaviour ------------------------------------------------
HISTORY_PERIOD: str = os.getenv("HISTORY_PERIOD", "5y")
YF_RETRY_ATTEMPTS: int = int(os.getenv("YF_RETRY_ATTEMPTS", "3"))
YF_RETRY_BASE_SECONDS: float = float(os.getenv("YF_RETRY_BASE_SECONDS", "1.5"))
# Seconds to pause between tickers in the nightly batch (be gentle with Yahoo).
BATCH_SLEEP_SECONDS: float = float(os.getenv("BATCH_SLEEP_SECONDS", "2.0"))

# --- HTTP --------------------------------------------------------------------
# Dev-only CORS. In production the React app is served same-origin behind nginx,
# so this is not needed; it only helps `vite dev` if you bypass the proxy.
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]


def finnhub_enabled() -> bool:
    return bool(FINNHUB_API_KEY)
