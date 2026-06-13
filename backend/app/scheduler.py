"""APScheduler nightly refresh (Option A, always-on).

Refreshes the fixed TICKERS watch-list PLUS any ticker that has been requested
on demand (those live in the cache after their first request). Runs at
REFRESH_HOUR:REFRESH_MINUTE server-local time (or SCHEDULER_TIMEZONE). Between
tickers it pauses BATCH_SLEEP_SECONDS so we don't hammer Yahoo from a cloud IP.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from . import config, db, service

log = logging.getLogger("stockclock.scheduler")

_scheduler: Optional[BackgroundScheduler] = None
_lock = threading.Lock()


def refresh_all() -> dict:
    """Refresh TICKERS ∪ everything already cached. Used by the nightly job and
    by POST /api/refresh (no ticker)."""
    targets = sorted(set(config.TICKERS) | set(db.all_tickers()))
    refreshed: list[str] = []
    failed: list[dict] = []
    log.info("batch refresh starting for %d tickers: %s", len(targets), targets)
    for i, ticker in enumerate(targets):
        try:
            service.refresh_ticker(ticker)
            refreshed.append(ticker)
        except Exception as exc:  # noqa: BLE001
            log.warning("batch refresh failed for %s: %s", ticker, exc)
            failed.append({"ticker": ticker, "error": str(exc)})
        if i < len(targets) - 1:
            time.sleep(config.BATCH_SLEEP_SECONDS)
    db.set_meta("last_refresh", db.now_iso())
    log.info("batch refresh done: %d ok, %d failed", len(refreshed), len(failed))
    return {"requested": targets, "refreshed": refreshed, "failed": failed}


def _nightly_job() -> None:
    refresh_all()


def start_scheduler() -> None:
    global _scheduler
    with _lock:
        if _scheduler is not None:
            return
        kwargs = {}
        if config.SCHEDULER_TIMEZONE:
            kwargs["timezone"] = config.SCHEDULER_TIMEZONE
        sched = BackgroundScheduler(**kwargs)
        sched.add_job(
            _nightly_job,
            trigger="cron",
            hour=config.REFRESH_HOUR,
            minute=config.REFRESH_MINUTE,
            id="nightly_refresh",
            replace_existing=True,
            misfire_grace_time=3600,
            coalesce=True,
        )
        sched.start()
        _scheduler = sched
        log.info("scheduler started; nightly refresh at %02d:%02d %s",
                 config.REFRESH_HOUR, config.REFRESH_MINUTE,
                 config.SCHEDULER_TIMEZONE or "server-local")


def shutdown_scheduler() -> None:
    global _scheduler
    with _lock:
        if _scheduler is not None:
            _scheduler.shutdown(wait=False)
            _scheduler = None


def warm_cache_async() -> None:
    """Fire a one-off batch refresh in a daemon thread (never blocks startup)."""

    def _run() -> None:
        try:
            refresh_all()
        except Exception as exc:  # noqa: BLE001
            log.warning("startup warm-up failed: %s", exc)

    threading.Thread(target=_run, name="warm-cache", daemon=True).start()
