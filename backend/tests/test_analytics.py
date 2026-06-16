"""Unit tests for the subtle analytics — pure Python, no network, no deps.

Run with:  python -m pytest backend/tests/        (or)  python backend/tests/test_analytics.py
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import analytics  # noqa: E402


def _series(start: date, closes, opens=None):
    """Build a daily price list over consecutive *weekdays* (skips weekends)."""
    opens = opens or closes
    prices = []
    d = start
    i = 0
    while i < len(closes):
        if d.weekday() < 5:  # Mon-Fri only -> mimics trading days
            prices.append(
                {"date": d.isoformat(), "open": opens[i], "high": max(opens[i], closes[i]),
                 "low": min(opens[i], closes[i]), "close": closes[i], "volume": 1000}
            )
            i += 1
        d += timedelta(days=1)
    return prices


def test_trailing_returns_yesterday_and_windows():
    # 400 weekdays of prices ending today-ish; close grows by 1 each day from 100.
    closes = [100 + i for i in range(400)]
    prices = _series(date(2023, 1, 2), closes)
    res = analytics.trailing_returns(prices)

    latest = prices[-1]["close"]
    by_window = {r["window"]: r for r in res["returns"]}

    # yesterday = previous trading day
    prev = prices[-2]["close"]
    assert abs(by_window["yesterday"]["pct"] - (latest / prev - 1)) < 1e-12
    assert by_window["yesterday"]["ref_date"] == prices[-2]["date"]

    # every window resolves to a real prior trading day and a positive return
    for w in ("1w", "1m", "3m", "6m", "1y"):
        assert by_window[w]["ref_close"] is not None, w
        assert by_window[w]["pct"] > 0, w

    # 1y reference must be the nearest trading day on/before (today - 12 months)
    target = analytics._minus_months(date.fromisoformat(latest_date := prices[-1]["date"]), 12)
    ref = date.fromisoformat(by_window["1y"]["ref_date"])
    assert ref <= target
    # nothing between ref and target is a weekday we skipped
    assert (target - ref).days <= 4


def test_amc_reaction_uses_next_trading_day():
    # closes: ... D-1=100, D=110 (announce day close), D+1=121 (reaction)
    closes = [90, 100, 110, 121, 130]
    opens = [90, 100, 110, 115, 130]
    prices = _series(date(2024, 3, 4), closes, opens)  # Mon..Fri
    announce = prices[2]["date"]  # the "D" with close 110

    earnings = [{"date": announce, "eps_actual": 2.0, "eps_estimate": 1.0, "session": "amc"}]
    r = analytics.earnings_reactions(prices, earnings, years=10)
    assert len(r) == 1
    e = r[0]
    # AMC -> reaction is D+1; prior is D
    assert e["reaction_session_date"] == prices[3]["date"]
    assert e["prior_session_date"] == prices[2]["date"]
    assert abs(e["reaction_pct"] - (121 / 110 - 1)) < 1e-12
    assert abs(e["gap_pct"] - (115 / 110 - 1)) < 1e-12
    assert abs(e["surprise_pct"] - (2.0 - 1.0) / 1.0) < 1e-12
    assert e["session_assumed"] is False


def test_bmo_reaction_uses_announcement_day():
    closes = [90, 100, 110, 121, 130]
    prices = _series(date(2024, 3, 4), closes)
    announce = prices[2]["date"]  # D with close 110, prior close 100

    earnings = [{"date": announce, "eps_actual": 1.5, "eps_estimate": 2.0, "session": "bmo"}]
    r = analytics.earnings_reactions(prices, earnings, years=10)
    e = r[0]
    # BMO -> reaction is D itself; prior is D-1
    assert e["reaction_session_date"] == prices[2]["date"]
    assert e["prior_session_date"] == prices[1]["date"]
    assert abs(e["reaction_pct"] - (110 / 100 - 1)) < 1e-12
    # negative surprise
    assert e["surprise_pct"] < 0


def test_unknown_defaults_to_amc_but_flags():
    closes = [90, 100, 110, 121, 130]
    prices = _series(date(2024, 3, 4), closes)
    announce = prices[2]["date"]
    earnings = [{"date": announce, "eps_actual": 1.0, "eps_estimate": 1.0, "session": "unknown"}]
    r = analytics.earnings_reactions(prices, earnings, years=10)
    e = r[0]
    # behaves like AMC (reaction = next day) ...
    assert e["reaction_session_date"] == prices[3]["date"]
    # ... but is flagged
    assert e["session_assumed"] is True
    assert e["session"] == "unknown"
    # estimate==actual -> 0 surprise; estimate 0 would be None
    assert abs(e["surprise_pct"]) < 1e-12


def test_future_earnings_without_price_is_skipped():
    closes = [100, 101, 102]
    prices = _series(date(2024, 3, 4), closes)
    future = (date(2024, 3, 4) + timedelta(days=400)).isoformat()
    earnings = [{"date": future, "eps_actual": None, "eps_estimate": 1.0, "session": "amc"}]
    r = analytics.earnings_reactions(prices, earnings, years=10)
    assert r == []


def test_surprise_pct_guards_zero_estimate():
    assert analytics._surprise_pct(1.0, 0) is None
    assert analytics._surprise_pct(None, 1.0) is None
    assert analytics._surprise_pct(2.0, 1.0) == 1.0
    assert analytics._surprise_pct(0.5, 1.0) == -0.5


def test_trailing_returns_tolerates_null_latest_close():
    # A junk trailing bar with no close (an in-progress session) must not crash
    # the return math — guards should yield None pct rather than dividing by None.
    closes = [100 + i for i in range(30)]
    prices = _series(date(2024, 1, 1), closes)
    prices.append({"date": "2099-01-01", "open": None, "high": None, "low": None,
                   "close": None, "volume": 0})
    res = analytics.trailing_returns(prices)  # must not raise
    assert isinstance(res["returns"], list) and len(res["returns"]) == 6


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} analytics tests passed")
