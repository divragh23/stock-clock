"""Normalization layer.

Converts raw upstream payloads (pandas frames from yfinance, a date->session map
from Finnhub) into the single internal schema everything else consumes:

    {
      ticker, fetched_at, source,
      prices:   [{date, open, high, low, close, volume}],   # daily, 5y
      earnings: [{date, eps_actual, eps_estimate, session}] # bmo|amc|unknown
    }

After this point nothing downstream (analytics, cache, API, frontend) knows or
cares which API produced a number — that is the whole point of this layer.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from . import db


def _f(value: Any) -> Optional[float]:
    """Coerce to float, turning NaN/None into None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _i(value: Any) -> Optional[int]:
    f = _f(value)
    return int(f) if f is not None else None


def _iso_date(index_value: Any) -> str:
    if hasattr(index_value, "date"):
        return index_value.date().isoformat()
    return str(index_value)[:10]


def _col(row: pd.Series, *names: str) -> Any:
    """First matching column value (yfinance column names drift over versions)."""
    for n in names:
        if n in row.index:
            return row[n]
    return None


def normalize_prices(price_df: pd.DataFrame) -> list[dict]:
    prices: list[dict] = []
    for idx, row in price_df.iterrows():
        prices.append(
            {
                "date": _iso_date(idx),
                "open": _f(_col(row, "Open")),
                "high": _f(_col(row, "High")),
                "low": _f(_col(row, "Low")),
                "close": _f(_col(row, "Close")),
                "volume": _i(_col(row, "Volume")),
            }
        )
    prices.sort(key=lambda p: p["date"])
    return prices


def normalize_earnings(
    earnings_df: Optional[pd.DataFrame], session_map: dict[str, str]
) -> list[dict]:
    if earnings_df is None or earnings_df.empty:
        return []
    earnings: list[dict] = []
    seen: set[str] = set()
    for idx, row in earnings_df.iterrows():
        date_iso = _iso_date(idx)
        if date_iso in seen:
            continue
        seen.add(date_iso)
        earnings.append(
            {
                "date": date_iso,
                "eps_actual": _f(_col(row, "Reported EPS", "epsActual")),
                "eps_estimate": _f(_col(row, "EPS Estimate", "epsEstimate")),
                "session": session_map.get(date_iso, "unknown"),
            }
        )
    earnings.sort(key=lambda e: e["date"])
    return earnings


def build_snapshot(
    ticker: str,
    price_df: pd.DataFrame,
    earnings_df: Optional[pd.DataFrame],
    session_map: dict[str, str],
) -> dict:
    """Assemble the normalized, source-agnostic snapshot (source=yfinance)."""
    return {
        "ticker": ticker.upper(),
        "fetched_at": db.now_iso(),
        "source": "yfinance",
        "prices": normalize_prices(price_df),
        "earnings": normalize_earnings(earnings_df, session_map),
    }
