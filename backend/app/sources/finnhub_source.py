"""Finnhub — NARROW SECONDARY source. Exactly two jobs:

  (a) live/recent quote fallback for the top-line current/"yesterday" price when
      yfinance fails;
  (b) the earnings-session timing flag (BMO / AMC) from the earnings-calendar
      endpoint's `hour` field.

Finnhub's free tier CANNOT serve historical prices, so it is NEVER used as a
historical backup — the cache is the real backup for historical data. All calls
fail soft (return None / {}), and everything is skipped entirely when no API key
is configured.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import requests

from .. import config

log = logging.getLogger("stockclock.finnhub")

_BASE = "https://finnhub.io/api/v1"
_TIMEOUT = 10


def _get(path: str, params: dict) -> Optional[dict]:
    if not config.finnhub_enabled():
        return None
    params = {**params, "token": config.FINNHUB_API_KEY}
    try:
        resp = requests.get(f"{_BASE}{path}", params=params, timeout=_TIMEOUT)
        if resp.status_code != 200:
            log.warning("finnhub %s -> HTTP %s", path, resp.status_code)
            return None
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("finnhub %s failed: %s", path, exc)
        return None


def fetch_quote(ticker: str) -> Optional[dict]:
    """Live quote. Returns {price, prev_close, change_pct, as_of} or None.

    Finnhub /quote returns: c=current, pc=previous close, t=unix ts.
    """
    data = _get("/quote", {"symbol": ticker.upper()})
    if not data:
        return None
    current = data.get("c")
    prev_close = data.get("pc")
    # Finnhub returns 0/None for unknown symbols.
    if not current:
        return None
    change_pct = None
    if prev_close:
        change_pct = current / prev_close - 1
    as_of = None
    ts = data.get("t")
    if ts:
        from datetime import datetime, timezone

        as_of = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return {
        "price": current,
        "prev_close": prev_close,
        "change_pct": change_pct,
        "as_of": as_of,
    }


def search_symbols(query: str) -> list[dict]:
    """Finnhub symbol search (/search) — fallback for the Yahoo search.

    Returns [] when Finnhub is disabled or on any failure.
    """
    data = _get("/search", {"q": query})
    if not data:
        return []
    out: list[dict] = []
    for x in data.get("result", []) or []:
        symbol = x.get("symbol")
        if not symbol:
            continue
        out.append(
            {
                "symbol": symbol,
                "name": x.get("description", "") or "",
                "exchange": "",
                "type": (x.get("type", "") or "").upper(),
            }
        )
    return out


def _normalize_hour(hour: Optional[str]) -> str:
    """Map Finnhub's `hour` field to our session vocabulary."""
    h = (hour or "").strip().lower()
    if h == "bmo":
        return "bmo"
    if h == "amc":
        return "amc"
    # "dmh" (during market hours) or blank -> we can't reliably classify.
    return "unknown"


def fetch_session_map(ticker: str, years: int = 6) -> dict[str, str]:
    """Return {YYYY-MM-DD: 'bmo'|'amc'|'unknown'} from the earnings calendar.

    Used only to stamp the session timing onto yfinance earnings dates. Returns
    {} on any failure / when Finnhub is disabled — callers default to "unknown".
    """
    if not config.finnhub_enabled():
        return {}
    today = date.today()
    start = today - timedelta(days=int(years * 365.25))
    end = today + timedelta(days=120)  # include the next scheduled report
    data = _get(
        "/calendar/earnings",
        {"symbol": ticker.upper(), "from": start.isoformat(), "to": end.isoformat()},
    )
    if not data:
        return {}
    out: dict[str, str] = {}
    for row in data.get("earningsCalendar", []) or []:
        d = row.get("date")
        if not d:
            continue
        out[str(d)[:10]] = _normalize_hour(row.get("hour"))
    return out
