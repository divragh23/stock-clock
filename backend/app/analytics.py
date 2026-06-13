"""Analytics: trailing returns + earnings reactions.

Deliberately pure-Python (no pandas/numpy) and operating only on the normalized
snapshot dicts, so the subtle calendar/earnings logic is trivially unit-testable
without any network or heavy dependency.

--- Trailing returns -------------------------------------------------------
Latest close is the reference "now". For each window find the nearest prior
trading day (previous trading day for "yesterday"; a calendar offset for the
rest) and compute return = latest_close / reference_close - 1.

--- Earnings reactions -----------------------------------------------------
The trading session that reflects a release depends on when it was reported:
  * BMO reported on day D       -> reaction session is day D
  * AMC reported on day D       -> reaction session is day D+1 (next trading day)
  * unknown                     -> default to AMC behaviour, but flag it
  reaction_pct = close(reaction session) / close(prior trading day) - 1
  gap_pct      = open(reaction session)  / close(prior trading day) - 1
"""
from __future__ import annotations

import bisect
import calendar
from datetime import date, datetime
from typing import Optional


# --- date helpers ------------------------------------------------------------
def _to_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def _minus_months(d: date, months: int) -> date:
    total = (d.year * 12 + (d.month - 1)) - months
    year, month = divmod(total, 12)
    month += 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _idx_le(dates: list[date], target: date) -> Optional[int]:
    """Index of the latest date <= target (nearest prior trading day)."""
    i = bisect.bisect_right(dates, target) - 1
    return i if i >= 0 else None


def _idx_ge(dates: list[date], target: date) -> Optional[int]:
    """Index of the earliest date >= target."""
    i = bisect.bisect_left(dates, target)
    return i if i < len(dates) else None


def _idx_gt(dates: list[date], target: date) -> Optional[int]:
    """Index of the earliest date strictly > target."""
    i = bisect.bisect_right(dates, target)
    return i if i < len(dates) else None


def _quarter_label(d: date) -> str:
    q = (d.month - 1) // 3 + 1
    return f"Q{q} '{d.strftime('%y')}"


# --- trailing returns --------------------------------------------------------
_WINDOWS = [
    ("yesterday", "Yesterday"),
    ("1w", "1 Week"),
    ("1m", "1 Month"),
    ("3m", "3 Months"),
    ("6m", "6 Months"),
    ("1y", "1 Year"),
]


def _window_target(latest: date, window: str) -> Optional[date]:
    if window == "1w":
        from datetime import timedelta

        return latest - timedelta(weeks=1)
    if window == "1m":
        return _minus_months(latest, 1)
    if window == "3m":
        return _minus_months(latest, 3)
    if window == "6m":
        return _minus_months(latest, 6)
    if window == "1y":
        return _minus_months(latest, 12)
    return None  # "yesterday" handled separately


def trailing_returns(prices: list[dict]) -> dict:
    prices = sorted(prices, key=lambda p: p["date"])
    dates = [_to_date(p["date"]) for p in prices]
    closes = [p.get("close") for p in prices]

    result = {
        "as_of_date": None,
        "latest_close": None,
        "returns": [],
        "price_series": [{"date": p["date"][:10], "close": p.get("close")} for p in prices],
    }
    if len(prices) < 2:
        # Not enough history to compute any return.
        result["returns"] = [
            {"window": w, "label": lbl, "ref_date": None, "ref_close": None, "pct": None}
            for w, lbl in _WINDOWS
        ]
        if prices:
            result["as_of_date"] = prices[-1]["date"][:10]
            result["latest_close"] = closes[-1]
        return result

    latest_close = closes[-1]
    latest_date = dates[-1]
    result["as_of_date"] = latest_date.isoformat()
    result["latest_close"] = latest_close

    for window, label in _WINDOWS:
        if window == "yesterday":
            ref_idx: Optional[int] = len(prices) - 2  # previous trading day
        else:
            target = _window_target(latest_date, window)
            ref_idx = _idx_le(dates, target) if target else None

        entry = {"window": window, "label": label, "ref_date": None, "ref_close": None, "pct": None}
        if ref_idx is not None and 0 <= ref_idx < len(prices) - 0:
            ref_close = closes[ref_idx]
            if ref_close:
                entry["ref_date"] = dates[ref_idx].isoformat()
                entry["ref_close"] = ref_close
                entry["pct"] = latest_close / ref_close - 1
        result["returns"].append(entry)

    return result


# --- earnings reactions ------------------------------------------------------
def _surprise_pct(actual: Optional[float], estimate: Optional[float]) -> Optional[float]:
    if actual is None or estimate is None or estimate == 0:
        return None
    return (actual - estimate) / abs(estimate)


def earnings_reactions(prices: list[dict], earnings: list[dict], years: int = 5) -> list[dict]:
    prices = sorted(prices, key=lambda p: p["date"])
    if not prices:
        return []
    dates = [_to_date(p["date"]) for p in prices]
    closes = [p.get("close") for p in prices]
    opens = [p.get("open") for p in prices]

    latest = dates[-1]
    cutoff = _minus_months(latest, years * 12)

    out: list[dict] = []
    for ev in sorted(earnings, key=lambda e: e["date"]):
        ed = _to_date(ev["date"])
        if ed < cutoff:
            continue
        session = (ev.get("session") or "unknown").lower()
        if session not in ("bmo", "amc"):
            session = "unknown"
        assumed = session == "unknown"

        if session == "bmo":
            # Reaction is the announcement day itself (or the next trading day if
            # D somehow isn't a trading day).
            reaction_idx = _idx_ge(dates, ed)
        else:
            # AMC or unknown -> reaction is the NEXT trading day after D.
            reaction_idx = _idx_gt(dates, ed)

        if reaction_idx is None or reaction_idx == 0:
            # No reaction session in range, or no prior day to compare against
            # (e.g. a future earnings date has no price yet -> skipped here).
            continue
        prior_idx = reaction_idx - 1

        prior_close = closes[prior_idx]
        reaction_close = closes[reaction_idx]
        reaction_open = opens[reaction_idx]

        reaction_pct = None
        gap_pct = None
        if prior_close:
            if reaction_close is not None:
                reaction_pct = reaction_close / prior_close - 1
            if reaction_open is not None:
                gap_pct = reaction_open / prior_close - 1

        out.append(
            {
                "date": ed.isoformat(),
                "label": _quarter_label(ed),
                "session": session,
                "session_assumed": assumed,
                "reaction_session_date": dates[reaction_idx].isoformat(),
                "prior_session_date": dates[prior_idx].isoformat(),
                "reaction_pct": reaction_pct,
                "gap_pct": gap_pct,
                "eps_actual": ev.get("eps_actual"),
                "eps_estimate": ev.get("eps_estimate"),
                "surprise_pct": _surprise_pct(ev.get("eps_actual"), ev.get("eps_estimate")),
            }
        )

    return out
