import { prettyDate, prettyDateTime } from "../format.js";

// Always honest, never silent. Reads ONLY meta flags from the unified payload —
// it has no idea which upstream API produced anything. It surfaces the mixed
// state too: the historical block may be cache-sourced while the live top-line
// comes from Finnhub.
export default function StatusBanner({ meta }) {
  if (!meta) return null;

  const { degraded, is_stale, fetched_at, live_quote_source, fetched_age_hours, source } = meta;
  const healthy = !degraded && !is_stale;

  let headline;
  if (degraded) {
    headline = `Live refresh failed — showing cached data as of ${prettyDate(fetched_at)}.`;
    if (live_quote_source === "finnhub") headline += " Live quote via Finnhub.";
  } else if (is_stale) {
    const age = fetched_age_hours != null ? ` (${Math.round(fetched_age_hours)}h old)` : "";
    headline = `Showing cached data as of ${prettyDate(fetched_at)}${age}.`;
  } else {
    headline = `Live data from yfinance · updated ${prettyDateTime(fetched_at)}.`;
  }

  return (
    <div className={`banner ${healthy ? "banner-ok" : "banner-warn"}`} role="status">
      <span className="banner-dot" aria-hidden="true" />
      <div className="banner-text">
        <strong>{headline}</strong>
        <div className="banner-chips">
          <span className="chip">
            History:&nbsp;<b>{degraded || is_stale ? "cache" : "yfinance"}</b>
          </span>
          <span className="chip">
            Live quote:&nbsp;<b>{live_quote_source || "—"}</b>
          </span>
          <span className="chip">
            Snapshot source:&nbsp;<b>{source || "—"}</b>
          </span>
        </div>
      </div>
    </div>
  );
}
