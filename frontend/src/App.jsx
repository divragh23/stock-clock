import { useCallback, useEffect, useState } from "react";
import { getStock } from "./api.js";
import StatusBanner from "./components/StatusBanner.jsx";
import TickerInput from "./components/TickerInput.jsx";
import PerformanceDashboard from "./components/PerformanceDashboard.jsx";
import EarningsDashboard from "./components/EarningsDashboard.jsx";

const DEFAULT_TICKER = "NVDA";

export default function App() {
  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("performance");

  const load = useCallback(async (t, { forceRefresh = false } = {}) => {
    setLoading(true);
    setError(null);
    try {
      // refresh=true forces a server-side live refresh and returns the result in
      // one call. On failure the server still returns cached data + an honest
      // banner (degraded), so we don't special-case errors here.
      const payload = await getStock(t, { refresh: forceRefresh });
      setData(payload);
      setTicker(payload.ticker);
    } catch (e) {
      setError(e.message || "Failed to load data.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(DEFAULT_TICKER);
  }, [load]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">◴</span> Stock Clock
        </div>
        <TickerInput
          current={data?.ticker}
          loading={loading}
          onSubmit={(t) => load(t)}
          onRefresh={() => load(ticker, { forceRefresh: true })}
        />
      </header>

      {data?.meta && <StatusBanner meta={data.meta} />}

      {error && (
        <div className="banner banner-error" role="alert">
          <span className="banner-dot" aria-hidden="true" />
          <div className="banner-text">
            <strong>Couldn’t load {ticker}.</strong>
            <div className="small">{error}</div>
          </div>
        </div>
      )}

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
            <PerformanceDashboard
              ticker={data.ticker}
              performance={data.performance}
              liveQuote={data.live_quote}
            />
          ) : (
            <EarningsDashboard reactions={data.earnings} />
          )}
        </>
      )}

      {!data && loading && <div className="loading">Loading {ticker}…</div>}

      <footer className="app-footer">
        <span>
          Primary: yfinance · Secondary: Finnhub (live-quote fallback + BMO/AMC) · Backup: local
          cache
        </span>
      </footer>
    </div>
  );
}
