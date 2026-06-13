import { pct, eps, prettyDate, signClass } from "../format.js";

const SESSION_LABEL = { bmo: "BMO", amc: "AMC", unknown: "?" };

export default function EarningsTable({ reactions }) {
  const rows = reactions || [];
  if (rows.length === 0) {
    return <div className="empty">No earnings data in the last 5 years.</div>;
  }

  return (
    <div className="table-wrap">
      <table className="earn-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Session</th>
            <th className="num">EPS est.</th>
            <th className="num">EPS actual</th>
            <th className="num">Surprise</th>
            <th className="num">Reaction</th>
            <th className="num">Gap</th>
          </tr>
        </thead>
        <tbody>
          {[...rows].reverse().map((r) => (
            <tr key={r.date}>
              <td>{prettyDate(r.date)}</td>
              <td>
                <span className={`pill pill-${r.session}`}>
                  {SESSION_LABEL[r.session] || "?"}
                </span>
                {r.session_assumed && (
                  <span className="assumed" title="Session timing unknown — assumed after-market">
                    assumed
                  </span>
                )}
              </td>
              <td className="num">{eps(r.eps_estimate)}</td>
              <td className="num">{eps(r.eps_actual)}</td>
              <td className={`num ${signClass(r.surprise_pct)}`}>{pct(r.surprise_pct, 1)}</td>
              <td className={`num ${signClass(r.reaction_pct)}`}>{pct(r.reaction_pct)}</td>
              <td className={`num ${signClass(r.gap_pct)}`}>{pct(r.gap_pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
