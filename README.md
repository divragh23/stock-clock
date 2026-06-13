# Stock Clock

A stock performance dashboard. Two views for any ticker:

1. **Performance** — trailing returns over six windows (yesterday, 1w, 1m, 3m, 6m, 1y), each as a
   `%` change, plus a price line chart.
2. **Earnings Reactions** — for the last 5 years of quarterly earnings, how the stock moved around
   each release: reaction `%`, EPS actual vs. estimate, and surprise `%`, as a bar chart + table.

The frontend is **source-agnostic**: it reads one unified payload plus `meta` freshness flags and
never knows which upstream API produced a given number. A **status banner is always honest** — it
names exactly what failed and how stale the data is, including mixed states (cached history +
live Finnhub quote).

---

## Architecture & data-source roles

```
        ┌────────── React (Vite) SPA ──────────┐
        │  talks ONLY to our API (same origin)  │
        └───────────────────┬───────────────────┘
                            │  /api/*  (nginx proxy in prod, Vite proxy in dev)
        ┌───────────────────▼───────────────────┐
        │            FastAPI (uvicorn)           │
        │  normalize → cache → analytics → JSON  │
        └───┬───────────────┬───────────────┬────┘
            │               │               │
       ┌────▼────┐     ┌────▼─────┐    ┌─────▼─────┐
       │ yfinance│     │ Finnhub  │    │  SQLite   │
       │ PRIMARY │     │ SECONDARY│    │  cache    │
       └─────────┘     └──────────┘    └───────────┘
```

| Source       | Role | Notes |
|--------------|------|-------|
| **yfinance** | **Primary for everything** — 5y daily OHLCV *and* earnings dates (EPS actual/estimate). | No API key. Yahoo rate-limits cloud IPs, so calls retry with backoff and fall back to cache. |
| **Finnhub**  | **Narrow secondary, two jobs only:** (a) live/recent quote fallback for the top-line price when yfinance fails; (b) the BMO/AMC session flag from the earnings-calendar `hour` field. | Requires `FINNHUB_API_KEY`. **Free tier cannot serve historical prices**, so it is *never* a historical backup. Without a key, sessions default to `unknown` and there is no live-quote fallback. |
| **SQLite cache** | **The real backup for all historical data.** | If yfinance fails, the last good snapshot is served with a staleness warning instead of going blank. |

Everything is normalized into one internal schema *before* analytics or the API touch it:

```jsonc
{
  "ticker": "NVDA",
  "fetched_at": "2026-06-12T22:00:00+00:00",
  "source": "yfinance",
  "prices":   [{ "date": "2026-06-12", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1 }],
  "earnings": [{ "date": "2026-05-20", "eps_actual": 1.87, "eps_estimate": 1.77, "session": "amc" }]
}
```

### How the subtle bits are computed

- **Trailing returns** — latest close is "now". For each window, find the nearest *prior* trading
  day (previous trading day for "yesterday"; a calendar offset for the rest) and compute
  `latest_close / reference_close - 1`. Market holidays/weekends are handled by snapping to the
  nearest earlier trading day.
- **Earnings reaction** — the session that reflects a release depends on timing:
  - **BMO** (before open) on day `D` → reaction session is **`D`**.
  - **AMC** (after close) on day `D` → reaction session is **`D+1`** (next trading day).
  - **unknown** → defaults to AMC behaviour **and is flagged** (`session_assumed: true`).
  - `reaction_pct = close(reaction) / close(prior) - 1`; `gap_pct = open(reaction) / close(prior) - 1`.
  - The BMO/AMC flag comes from Finnhub's earnings calendar, merged onto the yfinance earnings
    dates by matching date; missing → `unknown`.

---

## Repo layout

```
backend/
  app/
    main.py            FastAPI app + endpoints (the only thing the SPA talks to)
    config.py          all env-var configuration
    db.py              SQLite cache (one JSON snapshot per ticker + meta kv)
    models.py          Pydantic response models (the unified payload shape)
    normalize.py       raw upstream → unified schema (source-agnostic)
    analytics.py       trailing returns + earnings reactions (pure Python)
    service.py         orchestration: cache policy + degraded fallbacks
    scheduler.py       APScheduler nightly batch refresh
    sources/
      yfinance_source.py   primary: prices + earnings (retry/backoff)
      finnhub_source.py    secondary: live quote + BMO/AMC session map
  tests/test_analytics.py  pure-Python unit tests (no network)
  requirements.txt
  .env.example
frontend/
  src/
    App.jsx, api.js, format.js, styles.css
    components/ StatusBanner, TickerInput, PerformanceDashboard,
                EarningsDashboard, ReturnCard, PriceChart,
                ReactionChart, EarningsTable
  package.json, vite.config.js, index.html, .env.example
deploy/
  stockclock-api.service   systemd unit for uvicorn
  nginx.conf               nginx static + reverse-proxy site
```

---

## Environment variables

Set these for the backend (a `.env` for local dev, or the systemd `EnvironmentFile` in prod).

| Var | Default | Purpose |
|-----|---------|---------|
| `FINNHUB_API_KEY` | *(empty)* | Finnhub key. Empty = sessions `unknown`, no live-quote fallback. |
| `CACHE_PATH` | `./cache.db` | SQLite file path. Use a stable path in prod, e.g. `/var/lib/stockclock/cache.db`. |
| `TICKERS` | `NVDA,AAPL,MSFT` | Watch-list refreshed nightly (plus any on-demand ticker). |
| `STALE_AFTER_HOURS` | `30` | Snapshot older than this is flagged stale to the UI. |
| `REFRESH_HOUR` / `REFRESH_MINUTE` | `22` / `0` | Nightly refresh time. |
| `SCHEDULER_TIMEZONE` | *(server local)* | IANA tz for the job, e.g. `America/New_York`. |
| `REFRESH_ON_START` | `true` | Warm the cache for `TICKERS` on boot (background thread; never blocks). |
| `HISTORY_PERIOD` | `5y` | yfinance history window. |
| `YF_RETRY_ATTEMPTS` / `YF_RETRY_BASE_SECONDS` | `3` / `1.5` | Backoff for Yahoo rate-limits. |
| `BATCH_SLEEP_SECONDS` | `2.0` | Pause between tickers in the nightly batch. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Dev only; prod is same-origin behind nginx. |

Frontend (optional, `frontend/.env`):

| Var | Default | Purpose |
|-----|---------|---------|
| `VITE_API_BASE` | *(empty)* | Leave empty so the app calls `/api` on its own origin. Only set to call an absolute API base. |
| `VITE_PROXY_TARGET` | `http://localhost:8000` | Dev-only: where `vite dev` proxies `/api`. |

**Secrets never reach the frontend bundle** — the Finnhub key is read only by the Python backend.

---

## Local development

Requires **Python 3.11 or 3.12** (recommended) and **Node 18+**.

> Note: some compiled deps (`pydantic-core`, `lxml`) may not yet ship wheels for very new Python
> like 3.14 — stick to 3.11/3.12 for a clean `pip install`.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then paste your FINNHUB_API_KEY (optional)
uvicorn app.main:app --reload --port 8000
```

API is now at `http://localhost:8000`. Quick checks:

```bash
curl localhost:8000/api/health
curl localhost:8000/api/stock/NVDA | head -c 400
```

Run the analytics unit tests (pure Python, no network):

```bash
python tests/test_analytics.py        # or: python -m pytest tests/
```

### Frontend

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

`vite dev` proxies `/api` to `http://localhost:8000`, so the browser only ever talks to the Vite
origin — no CORS in dev. Start the backend first.

---

## API reference

- `GET /api/health` →
  `{ status, last_refresh, active_sources, stale_tickers, cached_tickers, watchlist }`
- `GET /api/stock/{ticker}` (optional `?refresh=true`) → the unified payload:
  `{ ticker, meta, live_quote, performance, earnings }` where
  `meta = { source, fetched_at, fetched_age_hours, is_stale, degraded, live_quote_source, stale_after_hours, note }`.
- `POST /api/refresh` with body `{ "ticker": "NVDA" }` (one) or `{}` (whole watch-list ∪ cached
  tickers) → `{ requested, refreshed, failed }`.

`degraded: true` means a live refresh was attempted this request and failed, so cached data is being
served (the banner says so). `is_stale: true` means the snapshot is older than `STALE_AFTER_HOURS`.

---

## Deploy to a DigitalOcean droplet

Single droplet: **uvicorn (systemd) behind nginx**, with the React app built to static files and
served by nginx. Tested against Ubuntu 22.04/24.04.

### 1. Provision

Create a Basic droplet (1 GB RAM is plenty). SSH in as root (or a sudo user).

```bash
apt update && apt -y upgrade
apt -y install python3-venv python3-pip nginx git curl
# Node 20 for building the frontend:
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt -y install nodejs
```

### 2. Get the code & create the service user

```bash
useradd --system --create-home --shell /usr/sbin/nologin stockclock
mkdir -p /opt/stockclock
git clone <your-repo-url> /opt/stockclock      # or rsync/scp the project here
chown -R stockclock:stockclock /opt/stockclock
```

### 3. Backend: virtualenv + deps

```bash
cd /opt/stockclock/backend
sudo -u stockclock python3 -m venv .venv
sudo -u stockclock .venv/bin/pip install --upgrade pip
sudo -u stockclock .venv/bin/pip install -r requirements.txt
```

### 4. Environment file (secrets + config)

```bash
mkdir -p /etc/stockclock
cat > /etc/stockclock/stockclock.env <<'EOF'
FINNHUB_API_KEY=your_finnhub_key_here
CACHE_PATH=/var/lib/stockclock/cache.db
TICKERS=NVDA,AAPL,MSFT
STALE_AFTER_HOURS=30
REFRESH_HOUR=22
SCHEDULER_TIMEZONE=America/New_York
REFRESH_ON_START=true
EOF
chmod 600 /etc/stockclock/stockclock.env
chown root:stockclock /etc/stockclock/stockclock.env
```

This is the **only** place the Finnhub key lives. `CACHE_PATH` points at `/var/lib/stockclock`,
which the systemd unit creates and owns via `StateDirectory`.

### 5. systemd unit for uvicorn

```bash
cp /opt/stockclock/deploy/stockclock-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now stockclock-api
systemctl status stockclock-api          # should be active (running)
curl localhost:8000/api/health
```

The unit runs **`--workers 1`** on purpose: APScheduler is in-process, so a single worker means the
nightly refresh fires exactly once. (The app is read-mostly and fully cached — one worker is ample.
If you ever need more, move the scheduler to a separate one-shot systemd timer instead.)

### 6. Build & place the frontend

```bash
cd /opt/stockclock/frontend
sudo -u stockclock npm ci          # or: npm install
sudo -u stockclock npm run build   # outputs to frontend/dist
```

nginx serves `frontend/dist` directly. Because the SPA calls `/api` on the same origin, there is no
CORS and no secret in the bundle.

### 7. nginx reverse proxy

```bash
cp /opt/stockclock/deploy/nginx.conf /etc/nginx/sites-available/stockclock
# edit server_name to your droplet IP or domain
ln -s /etc/nginx/sites-available/stockclock /etc/nginx/sites-enabled/stockclock
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

Visit `http://<droplet-ip>/`. The SPA loads, calls `/api/stock/NVDA` through nginx → uvicorn.

### 8. Firewall (optional but recommended)

```bash
ufw allow OpenSSH
ufw allow 'Nginx HTTP'
ufw --force enable
```

### 9. HTTPS (optional)

Point a domain at the droplet, then:

```bash
apt -y install certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
```

### Updating later

```bash
cd /opt/stockclock && git pull
# backend deps if changed:
sudo -u stockclock backend/.venv/bin/pip install -r backend/requirements.txt
sudo -u stockclock bash -c 'cd frontend && npm ci && npm run build'
systemctl restart stockclock-api
systemctl reload nginx
```

---

## Operational notes & gotchas

- **Yahoo rate-limits/blocks cloud IPs — and it's a TLS-fingerprint block, not just an IP one.**
  From a DigitalOcean/AWS/etc. droplet, the default HTTP client gets `HTTP 429 Too Many Requests`
  even with a browser `User-Agent`. The fix (already baked in) is **yfinance ≥ 1.4 + `curl_cffi`**,
  which gives requests a genuine Chrome TLS fingerprint and sails through. Both are pinned in
  `requirements.txt`. If you ever see empty price history / "possibly delisted" on the server, check
  `pip show yfinance curl_cffi` first — an old yfinance (0.2.x) will be silently 429'd.
  The design still leans on the nightly batch + cache (on-demand fetches happen only when a ticker
  is missing or stale, with retry/backoff), and any failure cleanly degrades to cached data.
- **No Finnhub key?** Everything still works from yfinance + cache; earnings sessions are reported
  as `unknown` (assumed AMC, flagged in the table) and there is no live-quote fallback.
- **CORS:** none of these upstream APIs are browser-callable, so *all* data fetching is server-side.
  In prod the SPA and API share one origin (nginx), so no CORS is needed at all.
- **Cache location:** keep `CACHE_PATH` on a stable, writable path (`/var/lib/stockclock`) so the
  cache — the real historical backup — survives restarts and redeploys.
- **Single worker:** required so the in-process scheduler doesn't multiply.

---

## License

MIT (or your choice).
