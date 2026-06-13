import ReturnCard from "./ReturnCard.jsx";
import PriceChart from "./PriceChart.jsx";
import { money, pct, signClass, prettyDate } from "../format.js";

export default function PerformanceDashboard({ ticker, performance, liveQuote }) {
  const returns = performance?.returns || [];
  const series = performance?.price_series || [];

  return (
    <section className="dashboard">
      <div className="topline">
        <div>
          <div className="topline-ticker">{ticker}</div>
          <div className="topline-price">
            {money(liveQuote?.price)}
            <span className={`topline-change ${signClass(liveQuote?.change_pct)}`}>
              {pct(liveQuote?.change_pct)}
            </span>
          </div>
          <div className="muted small">
            {liveQuote?.as_of ? `as of ${prettyDate(liveQuote.as_of)}` : ""}
            {liveQuote?.source ? ` · via ${liveQuote.source}` : ""}
          </div>
        </div>
      </div>

      <h2 className="section-title">Trailing returns</h2>
      <div className="returns-grid">
        {returns.map((r) => (
          <ReturnCard key={r.window} entry={r} />
        ))}
      </div>

      <PriceChart series={series} />
    </section>
  );
}
