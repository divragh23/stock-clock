import { pct, money, prettyDate, signClass } from "../format.js";

export default function ReturnCard({ entry }) {
  const cls = signClass(entry.pct);
  return (
    <div className={`return-card ${cls}`}>
      <div className="return-label">{entry.label}</div>
      <div className={`return-pct ${cls}`}>{pct(entry.pct)}</div>
      <div className="return-sub">
        {entry.ref_close != null ? (
          <>
            from {money(entry.ref_close)}
            <span className="return-date">{prettyDate(entry.ref_date)}</span>
          </>
        ) : (
          <span className="muted">not enough history</span>
        )}
      </div>
    </div>
  );
}
