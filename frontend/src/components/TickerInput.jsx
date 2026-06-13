import { useState } from "react";

export default function TickerInput({ current, loading, onSubmit, onRefresh }) {
  const [value, setValue] = useState(current || "");

  function submit(e) {
    e.preventDefault();
    const t = value.trim().toUpperCase();
    if (t) onSubmit(t);
  }

  return (
    <form className="ticker-form" onSubmit={submit}>
      <input
        className="ticker-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ticker (e.g. NVDA)"
        aria-label="Stock ticker"
        autoCapitalize="characters"
        spellCheck={false}
      />
      <button className="btn" type="submit" disabled={loading}>
        {loading ? "Loading…" : "Load"}
      </button>
      <button
        className="btn btn-ghost"
        type="button"
        disabled={loading || !current}
        onClick={onRefresh}
        title="Force a live refresh from yfinance"
      >
        ↻ Refresh
      </button>
    </form>
  );
}
