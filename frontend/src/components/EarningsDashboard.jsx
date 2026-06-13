import ReactionChart from "./ReactionChart.jsx";
import EarningsTable from "./EarningsTable.jsx";

export default function EarningsDashboard({ reactions }) {
  return (
    <section className="dashboard">
      <h2 className="section-title">Earnings reactions — last 5 years</h2>
      <p className="muted small explainer">
        Reaction = close of the session that reflects the release vs. the prior close. BMO reports
        move the same day; AMC (and unknown, shown “assumed”) move the next session. Gap = the
        overnight open vs. prior close.
      </p>
      <ReactionChart reactions={reactions} />
      <EarningsTable reactions={reactions} />
    </section>
  );
}
