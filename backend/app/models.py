"""Pydantic response models.

These describe the *unified* payload the frontend consumes. The frontend is
source-agnostic: it reads these fields plus the meta flags and never learns
which upstream API produced a given number.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

Session = Literal["bmo", "amc", "unknown"]


# --- Normalized snapshot (also the SQLite JSON shape) ------------------------
class PricePoint(BaseModel):
    date: str  # YYYY-MM-DD
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None


class EarningsPoint(BaseModel):
    date: str  # YYYY-MM-DD
    eps_actual: Optional[float] = None
    eps_estimate: Optional[float] = None
    session: Session = "unknown"


class Snapshot(BaseModel):
    ticker: str
    fetched_at: str  # ISO-8601 UTC
    source: str  # "yfinance"
    prices: list[PricePoint] = []
    earnings: list[EarningsPoint] = []


# --- Computed analytics ------------------------------------------------------
class TrailingReturn(BaseModel):
    window: str  # "yesterday" | "1w" | "1m" | "3m" | "6m" | "1y"
    label: str
    ref_date: Optional[str] = None
    ref_close: Optional[float] = None
    pct: Optional[float] = None  # latest_close / ref_close - 1


class Performance(BaseModel):
    as_of_date: Optional[str] = None
    latest_close: Optional[float] = None
    returns: list[TrailingReturn] = []
    price_series: list[dict] = []  # [{date, close}], daily, full history


class EarningsReaction(BaseModel):
    date: str
    label: str  # short, e.g. "Q2 '25"
    session: Session
    session_assumed: bool  # True when session timing was defaulted (unknown)
    reaction_session_date: Optional[str] = None
    prior_session_date: Optional[str] = None
    reaction_pct: Optional[float] = None  # close(reaction)/close(prior) - 1
    gap_pct: Optional[float] = None  # open(reaction)/close(prior) - 1
    eps_actual: Optional[float] = None
    eps_estimate: Optional[float] = None
    surprise_pct: Optional[float] = None  # (actual - estimate)/|estimate|


class LiveQuote(BaseModel):
    price: Optional[float] = None
    prev_close: Optional[float] = None
    change_pct: Optional[float] = None
    source: Optional[str] = None  # "yfinance" | "finnhub"
    as_of: Optional[str] = None


class Meta(BaseModel):
    source: str  # origin of the historical numbers, e.g. "yfinance"
    fetched_at: Optional[str] = None
    fetched_age_hours: Optional[float] = None
    is_stale: bool = False
    degraded: bool = False  # a live refresh was attempted this request and failed
    live_quote_source: Optional[str] = None
    stale_after_hours: float = 0
    note: Optional[str] = None  # human-readable explanation of any problem


class StockResponse(BaseModel):
    ticker: str
    meta: Meta
    live_quote: LiveQuote
    performance: Performance
    earnings: list[EarningsReaction] = []


class HealthResponse(BaseModel):
    status: str
    last_refresh: Optional[str] = None
    active_sources: list[str] = []
    stale_tickers: list[str] = []
    cached_tickers: list[str] = []
    watchlist: list[str] = []


class RefreshResult(BaseModel):
    requested: list[str]
    refreshed: list[str]
    failed: list[dict]  # [{ticker, error}]
