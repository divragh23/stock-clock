import { useCallback, useEffect, useState } from "react";
import * as api from "./api.js";
import StatusBanner from "./components/StatusBanner.jsx";
import TickerInput from "./components/TickerInput.jsx";
import PerformanceDashboard from "./components/PerformanceDashboard.jsx";
import EarningsDashboard from "./components/EarningsDashboard.jsx";
import LoginPage from "./components/LoginPage.jsx";
import UserMenu from "./components/UserMenu.jsx";
import MyBar from "./components/MyBar.jsx";
import NotesBox from "./components/NotesBox.jsx";
import AdminPanel from "./components/AdminPanel.jsx";
import ThemeDial from "./components/ThemeDial.jsx";

const FALLBACK_TICKER = "NVDA";

export default function App() {
  const [user, setUser] = useState(undefined);
  const [entering, setEntering] = useState(false);

  const [ticker, setTicker] = useState(FALLBACK_TICKER);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("performance");
  const [chartRange, setChartRange] = useState("3m");

  const [watchlist, setWatchlist] = useState([]);
  const [recent, setRecent] = useState([]);
  const [prefs, setPrefs] = useState({ default_ticker: null, default_range: null });
  const [note, setNote] = useState("");
  const [showAdmin, setShowAdmin] = useState(false);

  const load = useCallback(async (t, { forceRefresh = false } = {}) => {
    setLoading(true);
    setError(null);
    try {
      const payload = await api.getStock(t, { refresh: forceRefresh });
      setData(payload);
      setTicker(payload.ticker);
      api.getRecent().then(setRecent).catch(() => {});
      api.getNote(payload.ticker).then((n) => setNote(n.body || "")).catch(() => setNote(""));
    } catch (e) {
      if (e.status !== 401) {
        setError(e.message || "Failed to load data.");
        setData(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api.setUnauthorizedHandler(() => {
      setUser(null);
      setData(null);
    });
    api.getMe().then(setUser).catch(() => setUser(null));
  }, []);

  useEffect(() => {
    if (!user) return;
    Promise.all([api.getWatchlist(), api.getRecent(), api.getPreferences()])
      .then(([wl, rc, pr]) => {
        setWatchlist(wl || []);
        setRecent(rc || []);
        setPrefs(pr || {});
        if (pr?.default_range) setChartRange(pr.default_range);
        load(pr?.default_ticker || FALLBACK_TICKER);
      })
      .catch(() => load(FALLBACK_TICKER));
  }, [user, load]);

  function handleLogin(u) {
    setEntering(true);
    setUser(u);
    setTimeout(() => setEntering(false), 600);
  }

  async function toggleWatch() {
    const t = data?.ticker;
    if (!t) return;
    try {
      const next = watchlist.includes(t) ? await api.removeWatchlist(t) : await api.addWatchlist(t);
      setWatchlist(next);
    } catch (e) {
      if (e.status !== 401) setError(e.message);
    }
  }

  async function saveNote(text) {
    await api.setNote(ticker, text);
    setNote(text);
  }

  async function setDefault() {
    try {
      const p = await api.setPreferences({ default_ticker: ticker, default_range: chartRange });
      setPrefs(p);
    } catch (e) {
      if (e.status !== 401) setError(e.message);
    }
  }

  async function handleLogout() {
    await api.logout();
    setUser(null);
    setData(null);
    setWatchlist([]);
    setRecent([]);
  }

  if (user === undefined) return <div className="loading">Loading…</div>;
  if (user === null) return <LoginPage onLogin={handleLogin} />;

  const inWatchlist = !!data && watchlist.includes(data.ticker);
  const isDefault = prefs?.default_ticker === ticker && prefs?.default_range === chartRange;

  return (
    <div className={`app ${entering ? "app-enter" : ""}`}>
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">&#9716;</span> Stock Clock
        </div>
        <div className="header-center">
          <TickerInput
            current={data?.ticker}
            loading={loading}
            onSubmit={(t) => load(t)}
            onRefresh={() => load(ticker, { forceRefresh: true })}
          />
        </div>
        <div className="header-right">
          <UserMenu user={user} onManageAccounts={() => setShowAdmin(true)} onLogout={handleLogout} />
        </div>
      </header>

      {data?.meta && <StatusBanner meta={data.meta} />}

      {error && (
        <div className="banner banner-error" role="alert">
          <span className="banner-dot" aria-hidden="true" />
          <div className="banner-text">
            <strong>Couldn't load {ticker}.</strong>
            <div className="small">{error}</div>
          </div>
        </div>
      )}

      <MyBar
        watchlist={watchlist}
        recent={recent}
        current={data?.ticker}
        onPick={(t) => load(t)}
        onRemove={async (t) => setWatchlist(await api.removeWatchlist(t))}
      />

      {data && (
        <>
          <nav className="tabs">
            <button
              className={`tab ${tab === "performance" ? "active" : ""}`}
              onClick={() => setTab("performance")}
            >
              Performance
            </button>
            <button
              className={`tab ${tab === "earnings" ? "active" : ""}`}
              onClick={() => setTab("earnings")}
            >
              Earnings Reactions
            </button>
          </nav>

          {tab === "performance" ? (
            <>
              <PerformanceDashboard
                ticker={data.ticker}
                performance={data.performance}
                liveQuote={data.live_quote}
                inWatchlist={inWatchlist}
                onToggleWatch={toggleWatch}
                onSetDefault={setDefault}
                isDefault={isDefault}
                chartRange={chartRange}
                onChartRange={setChartRange}
              />
              <NotesBox ticker={data.ticker} value={note} onSave={saveNote} />
            </>
          ) : (
            <EarningsDashboard reactions={data.earnings} />
          )}
        </>
      )}

      {!data && loading && <div className="loading">Loading {ticker}…</div>}

      {showAdmin && <AdminPanel me={user} onClose={() => setShowAdmin(false)} />}

      <ThemeDial />

      <footer className="app-footer">
        <span>
          Primary: yfinance · Secondary: Finnhub · Backup: local cache
        </span>
      </footer>
    </div>
  );
}
