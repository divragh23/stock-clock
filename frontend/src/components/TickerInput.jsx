import { useEffect, useRef, useState } from "react";
import { searchSymbols } from "../api.js";

// Typeahead: accepts a ticker OR a company name. As you type it queries
// /api/search (Yahoo primary, Finnhub fallback) and shows matches; picking one
// (or pressing Enter) resolves to the real symbol. Exact tickers still work even
// if search is unavailable.
export default function TickerInput({ current, loading, onSubmit, onRefresh }) {
  const [value, setValue] = useState(current || "");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const boxRef = useRef(null);
  const skipNextSearch = useRef(false);

  // Debounced search as the user types.
  useEffect(() => {
    const q = value.trim();
    if (skipNextSearch.current) {
      skipNextSearch.current = false;
      return;
    }
    if (q.length < 1) {
      setResults([]);
      setOpen(false);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const r = (await searchSymbols(q)) || [];
        setResults(r);
        setOpen(r.length > 0);
        setActive(-1);
      } catch {
        setResults([]);
        setOpen(false);
      }
    }, 220);
    return () => clearTimeout(t);
  }, [value]);

  // Close the dropdown on an outside click.
  useEffect(() => {
    function onDoc(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function choose(symbol) {
    skipNextSearch.current = true;
    setValue(symbol);
    setResults([]);
    setOpen(false);
    setActive(-1);
    onSubmit(symbol);
  }

  async function submit(e) {
    e.preventDefault();
    if (active >= 0 && results[active]) return choose(results[active].symbol);
    if (results.length > 0) return choose(results[0].symbol); // "Apple" -> top match
    const q = value.trim();
    if (!q) return;
    // Enter pressed before suggestions loaded: try a quick resolve, else use raw.
    try {
      const r = await searchSymbols(q);
      if (r && r.length) return choose(r[0].symbol);
    } catch {
      /* fall through to raw */
    }
    choose(q.toUpperCase());
  }

  function onKeyDown(e) {
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <form className="ticker-form" onSubmit={submit} ref={boxRef} autoComplete="off">
      <div className="ticker-box">
        <input
          className="ticker-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          onFocus={() => results.length && setOpen(true)}
          placeholder="Ticker or company — e.g. AAPL or Apple"
          aria-label="Stock ticker or company name"
          spellCheck={false}
        />
        {open && results.length > 0 && (
          <ul className="suggest" role="listbox">
            {results.map((r, i) => (
              <li
                key={r.symbol}
                role="option"
                aria-selected={i === active}
                className={`suggest-item ${i === active ? "active" : ""}`}
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  choose(r.symbol);
                }}
              >
                <span className="suggest-sym">{r.symbol}</span>
                <span className="suggest-name">{r.name}</span>
                {r.exchange && <span className="suggest-exch">{r.exchange}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
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
