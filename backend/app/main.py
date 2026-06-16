"""FastAPI application: the ONLY thing the React frontend talks to.

All upstream data fetching (yfinance, Finnhub) happens here, server-side — none
of those APIs are browser-callable, and the Finnhub key never leaves the server.

Access is gated by app-level accounts (admin-created). Everything except
/api/health and /api/auth/login requires a valid session (Bearer token).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from . import accounts, config, db, scheduler, service, userdata
from .models import (
    AdminUser,
    CreateUserRequest,
    HealthResponse,
    LoginRequest,
    LoginResponse,
    PreferencesModel,
    RefreshResult,
    StockResponse,
    SymbolMatch,
    UserOut,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("stockclock")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    accounts.init_accounts()
    scheduler.start_scheduler()
    if config.REFRESH_ON_START:
        scheduler.warm_cache_async()
    log.info("startup complete (finnhub %s)",
             "enabled" if config.finnhub_enabled() else "disabled — sessions will be 'unknown'")
    yield
    scheduler.shutdown_scheduler()


app = FastAPI(title="Stock Clock API", version="1.1.0", lifespan=lifespan)

# Dev convenience only; production serves the SPA same-origin behind nginx.
if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )


# --- auth dependencies -------------------------------------------------------
def _bearer_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def current_user(request: Request) -> dict:
    user = accounts.user_for_token(_bearer_token(request))
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def admin_user(user: dict = Depends(current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# --- auth --------------------------------------------------------------------
@app.post("/api/auth/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    user = accounts.authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = accounts.create_session(user["id"])
    return LoginResponse(token=token, username=user["username"], is_admin=bool(user["is_admin"]))


@app.post("/api/auth/logout")
def logout(request: Request) -> dict:
    accounts.delete_session(_bearer_token(request))
    return {"ok": True}


@app.get("/api/auth/me", response_model=UserOut)
def me(user: dict = Depends(current_user)) -> UserOut:
    return UserOut(username=user["username"], is_admin=bool(user["is_admin"]))


# --- admin: account management ----------------------------------------------
@app.get("/api/admin/users", response_model=list[AdminUser])
def admin_list_users(_: dict = Depends(admin_user)) -> list[AdminUser]:
    return [AdminUser(username=u["username"], is_admin=bool(u["is_admin"]), created_at=u["created_at"])
            for u in accounts.list_users()]


@app.post("/api/admin/users", response_model=UserOut)
def admin_create_user(body: CreateUserRequest, _: dict = Depends(admin_user)) -> UserOut:
    if not body.username.strip() or not body.password:
        raise HTTPException(status_code=400, detail="username and password are required")
    if accounts.get_user(body.username):
        raise HTTPException(status_code=409, detail="That account already exists")
    u = accounts.create_user(body.username, body.password, is_admin=body.is_admin)
    return UserOut(username=u["username"], is_admin=bool(u["is_admin"]))


@app.delete("/api/admin/users/{username}")
def admin_delete_user(username: str, admin: dict = Depends(admin_user)) -> dict:
    if username.strip().lower() == admin["username"]:
        raise HTTPException(status_code=400, detail="You can't delete your own admin account")
    if not accounts.delete_user(username):
        raise HTTPException(status_code=404, detail="Account not found")
    return {"ok": True}


# --- per-user data -----------------------------------------------------------
@app.get("/api/me/watchlist")
def get_watchlist(user: dict = Depends(current_user)) -> list[str]:
    return userdata.get_watchlist(user["id"])


@app.post("/api/me/watchlist")
def add_watchlist(body: dict = Body(...), user: dict = Depends(current_user)) -> list[str]:
    ticker = (body.get("ticker") or "").strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")
    userdata.add_watchlist(user["id"], ticker)
    return userdata.get_watchlist(user["id"])


@app.delete("/api/me/watchlist/{ticker}")
def remove_watchlist(ticker: str, user: dict = Depends(current_user)) -> list[str]:
    userdata.remove_watchlist(user["id"], ticker)
    return userdata.get_watchlist(user["id"])


@app.get("/api/me/preferences", response_model=PreferencesModel)
def get_preferences(user: dict = Depends(current_user)) -> PreferencesModel:
    return PreferencesModel(**userdata.get_preferences(user["id"]))


@app.put("/api/me/preferences", response_model=PreferencesModel)
def set_preferences(body: PreferencesModel, user: dict = Depends(current_user)) -> PreferencesModel:
    userdata.set_preferences(user["id"], body.default_ticker, body.default_range)
    return PreferencesModel(**userdata.get_preferences(user["id"]))


@app.get("/api/me/notes/{ticker}")
def get_note(ticker: str, user: dict = Depends(current_user)) -> dict:
    return {"ticker": ticker.strip().upper(), "body": userdata.get_note(user["id"], ticker)}


@app.put("/api/me/notes/{ticker}")
def set_note(ticker: str, body: dict = Body(...), user: dict = Depends(current_user)) -> dict:
    userdata.set_note(user["id"], ticker, body.get("body", ""))
    return {"ticker": ticker.strip().upper(), "body": userdata.get_note(user["id"], ticker)}


@app.get("/api/me/recent")
def get_recent(user: dict = Depends(current_user)) -> list[str]:
    return userdata.get_recent(user["id"])


# --- health (public) ---------------------------------------------------------
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


# --- stock data (auth required) ---------------------------------------------
@app.get("/api/search", response_model=list[SymbolMatch])
def symbol_search(q: str = "", user: dict = Depends(current_user)) -> list[SymbolMatch]:
    """Resolve a company name or partial ticker to matching symbols (typeahead)."""
    q = (q or "").strip()
    if not q:
        return []
    return [SymbolMatch(**m) for m in service.search_symbols(q)]


@app.get("/api/stock/{ticker}", response_model=StockResponse)
def stock(ticker: str, refresh: bool = False, user: dict = Depends(current_user)) -> StockResponse:
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
    userdata.record_view(user["id"], ticker)
    return StockResponse(**payload)


@app.post("/api/refresh", response_model=RefreshResult)
def refresh(payload: Optional[dict] = Body(default=None), user: dict = Depends(current_user)) -> RefreshResult:
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
