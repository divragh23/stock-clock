"""yfinance — PRIMARY source for *everything*.

  * 5y daily OHLCV price history
  * quarterly earnings dates with EPS actual / estimate

No API key. Yahoo rate-limits/429s requests from cloud IPs, so every call is
wrapped in retry-with-backoff and failures are raised cleanly so the caller can
fall back to the cached snapshot. yfinance sometimes returns an *empty* frame
instead of raising on a soft rate-limit — we treat an empty price frame as a
failure for that reason.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Callable, Optional, TypeVar

import pandas as pd
import yfinance as yf

from .. import config

log = logging.getLogger("stockclock.yfinance")

T = TypeVar("T")


class YFinanceError(RuntimeError):
    """Raised when yfinance cannot produce usable data."""


def _with_retry(fn: Callable[[], T], what: str) -> T:
    last_exc: Optional[Exception] = None
    for attempt in range(config.YF_RETRY_ATTEMPTS):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - we genuinely want to retry anything
            last_exc = exc
            if attempt < config.YF_RETRY_ATTEMPTS - 1:
                delay = config.YF_RETRY_BASE_SECONDS * (2 ** attempt) + random.random()
                log.warning("yfinance %s failed (attempt %d): %s; retrying in %.1fs",
                            what, attempt + 1, exc, delay)
                time.sleep(delay)
    raise YFinanceError(f"yfinance {what} failed after {config.YF_RETRY_ATTEMPTS} attempts: {last_exc}")


def fetch_prices(ticker: str) -> pd.DataFrame:
    """Return a daily OHLCV DataFrame for ~5y. Raises YFinanceError on failure."""

    def _do() -> pd.DataFrame:
        tk = yf.Ticker(ticker)
        df = tk.history(period=config.HISTORY_PERIOD, interval="1d", auto_adjust=True)
        if df is None or df.empty:
            # Empty frame is how a soft rate-limit usually surfaces.
            raise YFinanceError(f"empty price history for {ticker}")
        return df

    return _with_retry(_do, f"history({ticker})")


def search_symbols(query: str, limit: int = 10) -> list[dict]:
    """Yahoo symbol search — resolve a company name / partial query to tickers.

    Uses the same browser-impersonated client as the price/earnings calls, so it
    works from datacenter IPs. Single attempt (no backoff) to stay snappy for an
    interactive typeahead; raises on failure so the caller can fall back.
    """
    query = (query or "").strip()
    if not query:
        return []
    search = yf.Search(query, max_results=limit)
    out: list[dict] = []
    for q in (getattr(search, "quotes", None) or []):
        symbol = q.get("symbol")
        if not symbol:
            continue
        out.append(
            {
                "symbol": symbol,
                "name": (q.get("shortname") or q.get("longname") or "").strip(),
                "exchange": q.get("exchange") or "",
                "type": (q.get("quoteType") or "").upper(),
            }
        )
    return out


def fetch_earnings(ticker: str) -> Optional[pd.DataFrame]:
    """Return an earnings-dates DataFrame, or None.

    Unlike prices, an empty/absent earnings frame is *not* fatal — some tickers
    simply have no earnings history. Network failures are retried but ultimately
    swallowed (returns None) so a price pull can still succeed on its own.
    """

    def _do() -> Optional[pd.DataFrame]:
        tk = yf.Ticker(ticker)
        # ~6 years of quarters; we filter to 5y downstream.
        df = tk.get_earnings_dates(limit=24)
        return df

    try:
        df = _with_retry(_do, f"earnings({ticker})")
    except YFinanceError as exc:
        log.warning("earnings dates unavailable for %s: %s", ticker, exc)
        return None
    if df is None or df.empty:
        return None
    return df
