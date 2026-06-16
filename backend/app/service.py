"""Orchestration: the place that implements the always-on caching policy.

Refresh policy (Option A):
  * On a successful yfinance pull, overwrite the cached snapshot (source=yfinance).
  * On yfinance failure, KEEP the last cached snapshot and mark the response
    `degraded`; still try Finnhub for the live top-line quote.
  * A snapshot older than STALE_AFTER_HOURS is flagged `is_stale` to the UI.
  * The cache — never Finnhub — is the backup for historical data.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from . import analytics, config, db, normalize
from .sources import finnhub_source, yfinance_source

log = logging.getLogger("stockclock.service")


# --- freshness helpers -------------------------------------------------------
def _age_hours(fetched_at: Optional[str]) -> Optional[float]:
    if not fetched_at:
        return None
    try:
        dt = datetime.fromisoformat(fetched_at)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    return delta.total_seconds() / 3600.0


def is_stale(snapshot: Optional[dict]) -> bool:
    if not snapshot:
        return True
    age = _age_hours(snapshot.get("fetched_at"))
    return age is None or age > config.STALE_AFTER_HOURS


# --- the actual fetch + cache write ------------------------------------------
def refresh_ticker(ticker: str) -> dict:
    """Pull fresh data from yfinance (+ Finnhub session flags) and cache it.

    Raises on yfinance failure so callers can decide whether to fall back to the
    cache. Finnhub failures are non-fatal (sessions default to "unknown").
    """
    ticker = ticker.upper()
    price_df = yfinance_source.fetch_prices(ticker)  # raises YFinanceError on failure
    earnings_df = yfinance_source.fetch_earnings(ticker)  # None on failure (non-fatal)
    session_map = finnhub_source.fetch_session_map(ticker)  # {} when disabled/failed
    snapshot = normalize.build_snapshot(ticker, price_df, earnings_df, session_map)
    db.save_snapshot(snapshot)
    log.info("refreshed %s: %d prices, %d earnings (sessions from %d finnhub rows)",
             ticker, len(snapshot["prices"]), len(snapshot["earnings"]), len(session_map))
    return snapshot


# --- the read path used by the API -------------------------------------------
def _live_quote_from_snapshot(snapshot: dict) -> dict:
    """Top-line derived purely from the (yfinance-sourced) cached snapshot."""
    prices = snapshot.get("prices") or []
    if not prices:
        return {"price": None, "prev_close": None, "change_pct": None,
                "source": snapshot.get("source"), "as_of": None}
    last = prices[-1]
    prev = prices[-2] if len(prices) >= 2 else None
    change = None
    if prev and prev.get("close"):
        change = last["close"] / prev["close"] - 1
    return {
        "price": last.get("close"),
        "prev_close": prev.get("close") if prev else None,
        "change_pct": change,
        "source": snapshot.get("source", "yfinance"),
        "as_of": last.get("date"),
    }


def _build_payload(ticker: str, snapshot: Optional[dict], degraded: bool) -> dict:
    """Assemble the unified, source-agnostic API response from a snapshot."""
    live_quote_source: Optional[str] = None
    note: Optional[str] = None

    # Live top-line. When degraded (yfinance failed this request) try Finnhub for
    # a recent quote; otherwise the snapshot's latest close is the top-line.
    if snapshot:
        live_quote = _live_quote_from_snapshot(snapshot)
        live_quote_source = live_quote["source"]
    else:
        live_quote = {"price": None, "prev_close": None, "change_pct": None,
                      "source": None, "as_of": None}

    if degraded:
        fh = finnhub_source.fetch_quote(ticker)
        if fh:
            live_quote = {**fh, "source": "finnhub"}
            live_quote_source = "finnhub"

    # Historical analytics come exclusively from the cached/normalized snapshot.
    if snapshot and snapshot.get("prices"):
        perf = analytics.trailing_returns(snapshot["prices"])
        reactions = analytics.earnings_reactions(snapshot["prices"], snapshot.get("earnings", []))
    else:
        perf = {"as_of_date": None, "latest_close": None, "returns": [], "price_series": []}
        reactions = []
        if not snapshot:
            note = "No historical data available (yfinance failed and nothing was cached)."

    fetched_at = snapshot.get("fetched_at") if snapshot else None
    age = _age_hours(fetched_at)
    stale = is_stale(snapshot)

    if degraded and snapshot:
        as_of = (fetched_at or "")[:10]
        note = f"Live refresh failed — showing cached data as of {as_of}."
        if live_quote_source == "finnhub":
            note += " Live quote via Finnhub."
    elif stale and snapshot:
        as_of = (fetched_at or "")[:10]
        hrs = f"{age:.0f}h" if age is not None else "unknown age"
        note = f"Showing cached data as of {as_of} ({hrs} old)."

    meta = {
        "source": snapshot.get("source", "yfinance") if snapshot else "none",
        "fetched_at": fetched_at,
        "fetched_age_hours": round(age, 2) if age is not None else None,
        "is_stale": stale,
        "degraded": degraded,
        "live_quote_source": live_quote_source,
        "stale_after_hours": config.STALE_AFTER_HOURS,
        "note": note,
    }

    return {
        "ticker": ticker,
        "meta": meta,
        "live_quote": live_quote,
        "performance": perf,
        "earnings": reactions,
    }


def get_stock(ticker: str, force_refresh: bool = False) -> dict:
    """Return the full unified payload for a ticker, honouring the cache policy.

    On-demand: if the ticker isn't cached or is stale (or force_refresh), fetch
    it live and cache it. If that live fetch fails, serve the last good cached
    snapshot and mark the response degraded.
    """
    ticker = ticker.upper()
    cached = db.get_snapshot(ticker)
    need_fetch = force_refresh or cached is None or is_stale(cached)

    snapshot = cached
    degraded = False

    if need_fetch:
        try:
            snapshot = refresh_ticker(ticker)
        except Exception as exc:  # noqa: BLE001 - any failure -> serve cache
            log.warning("live refresh failed for %s: %s", ticker, exc)
            snapshot = cached  # keep last good (may be None if never cached)
            degraded = True

    return _build_payload(ticker, snapshot, degraded)


# --- symbol search -----------------------------------------------------------
# Drop things that aren't tradable equities/funds for this dashboard.
_SEARCH_DROP_TYPES = {"CRYPTOCURRENCY", "CURRENCY", "FUTURE"}


def search_symbols(query: str, limit: int = 7) -> list[dict]:
    """Resolve a company name / partial query to ticker symbols.

    Yahoo (yfinance, browser-impersonated) is primary; Finnhub /search is the
    fallback. Output is source-agnostic: [{symbol, name, exchange, type}].
    """
    query = (query or "").strip()
    if not query:
        return []

    results: list[dict] = []
    try:
        results = yfinance_source.search_symbols(query, limit=limit * 2)
    except Exception as exc:  # noqa: BLE001
        log.warning("yahoo symbol search failed for %r: %s", query, exc)
    if not results:
        try:
            results = finnhub_source.search_symbols(query)
        except Exception as exc:  # noqa: BLE001
            log.warning("finnhub symbol search failed for %r: %s", query, exc)

    seen: set[str] = set()
    cleaned: list[dict] = []
    for r in results:
        symbol = (r.get("symbol") or "").upper()
        if not symbol or symbol in seen or r.get("type") in _SEARCH_DROP_TYPES:
            continue
        seen.add(symbol)
        cleaned.append({**r, "symbol": symbol})
    return cleaned[:limit]


# --- health ------------------------------------------------------------------
def stale_tickers() -> list[str]:
    out = []
    for row in db.all_snapshots_meta():
        if _age_hours(row.get("fetched_at")) is None or \
           _age_hours(row.get("fetched_at")) > config.STALE_AFTER_HOURS:
            out.append(row["ticker"])
    return out


def active_sources() -> list[str]:
    sources = ["yfinance", "cache"]
    if config.finnhub_enabled():
        sources.insert(1, "finnhub")
    return sources
