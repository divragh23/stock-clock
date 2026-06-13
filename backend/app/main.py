"""FastAPI application: the ONLY thing the React frontend talks to.

All upstream data fetching (yfinance, Finnhub) happens here, server-side — none
of those APIs are browser-callable, and the Finnhub key never leaves the server.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, db, scheduler, service
from .models import HealthResponse, RefreshResult, StockResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("stockclock")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    scheduler.start_scheduler()
    if config.REFRESH_ON_START:
        scheduler.warm_cache_async()
    log.info("startup complete (finnhub %s)",
             "enabled" if config.finnhub_enabled() else "disabled — sessions will be 'unknown'")
    yield
    scheduler.shutdown_scheduler()


app = FastAPI(title="Stock Clock API", version="1.0.0", lifespan=lifespan)

# Dev convenience only; production serves the SPA same-origin behind nginx.
if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        last_refresh=db.get_meta("last_refresh"),
        active_sources=service.active_sources(),
        stale_tickers=service.stale_tickers(),
        cached_tickers=db.all_tickers(),
        watchlist=config.TICKERS,
    )


@app.get("/api/stock/{ticker}", response_model=StockResponse)
def stock(ticker: str, refresh: bool = False) -> StockResponse:
    ticker = ticker.strip().upper()
    if not ticker or len(ticker) > 12 or not ticker.replace(".", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker!r}")
    payload = service.get_stock(ticker, force_refresh=refresh)
    # Only hard-fail when there is genuinely nothing to show (no cache, no live).
    if payload["meta"]["source"] == "none" and payload["live_quote"]["price"] is None:
        raise HTTPException(
            status_code=502,
            detail=f"No data available for {ticker}: live fetch failed and nothing is cached.",
        )
    return StockResponse(**payload)


@app.post("/api/refresh", response_model=RefreshResult)
def refresh(payload: Optional[dict] = Body(default=None)) -> RefreshResult:
    """Trigger a manual refresh. Body {"ticker": "X"} for one, or {} for the
    full watch-list ∪ cached tickers."""
    ticker = (payload or {}).get("ticker")
    if ticker:
        ticker = str(ticker).strip().upper()
        try:
            service.refresh_ticker(ticker)
            db.set_meta("last_refresh", db.now_iso())
            return RefreshResult(requested=[ticker], refreshed=[ticker], failed=[])
        except Exception as exc:  # noqa: BLE001
            return RefreshResult(requested=[ticker], refreshed=[], failed=[{"ticker": ticker, "error": str(exc)}])
    result = scheduler.refresh_all()
    return RefreshResult(**result)
