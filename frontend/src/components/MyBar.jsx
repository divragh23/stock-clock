// Personal bar: the user's saved watchlist (removable) and recently-viewed
// tickers. Clicking any chip loads that stock.
export default function MyBar({ watchlist, recent, current, onPick, onRemove }) {
  const recentOnly = (recent || []).filter((t) => !(watchlist || []).includes(t));

  if ((watchlist || []).length === 0 && recentOnly.length === 0) return null;

  return (
    <div className="mybar">
      {(watchlist || []).length > 0 && (
        <div className="mybar-row">
          <span className="mybar-label">★ Watchlist</span>
          <div className="chips">
            {watchlist.map((t) => (
              <span key={t} className={`chip-tick ${t === current ? "active" : ""}`}>
                <button className="chip-tick-main" onClick={() => onPick(t)}>
                  {t}
                </button>
                <button className="chip-tick-x" title="Remove" onClick={() => onRemove(t)}>
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
      {recentOnly.length > 0 && (
        <div className="mybar-row">
          <span className="mybar-label">Recent</span>
          <div className="chips">
            {recentOnly.map((t) => (
              <button
                key={t}
                className={`chip-tick chip-tick-plain ${t === current ? "active" : ""}`}
                onClick={() => onPick(t)}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
