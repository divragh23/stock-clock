import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  ReferenceLine,
} from "recharts";
import { pct, prettyDate } from "../format.js";

// Reaction % per quarter. Green bars for up moves, red for down.
export default function ReactionChart({ reactions }) {
  const data = (reactions || [])
    .filter((r) => r.reaction_pct != null)
    .map((r) => ({
      label: r.label,
      date: r.date,
      reaction: r.reaction_pct * 100,
      session: r.session,
    }));

  if (data.length === 0) {
    return <div className="chart-card empty">No earnings reactions to chart.</div>;
  }

  return (
    <div className="chart-card">
      <div className="chart-head">
        <h3>Earnings reaction by quarter</h3>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" stroke="var(--axis)" tick={{ fontSize: 11 }} minTickGap={4} />
          <YAxis
            tickFormatter={(v) => `${v.toFixed(0)}%`}
            stroke="var(--axis)"
            tick={{ fontSize: 11 }}
            width={46}
          />
          <ReferenceLine y={0} stroke="var(--axis)" />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            contentStyle={{
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              color: "var(--text)",
            }}
            labelFormatter={(_l, payload) =>
              payload && payload[0] ? prettyDate(payload[0].payload.date) : ""
            }
            formatter={(v, _n, p) => [
              pct(v / 100),
              `Reaction (${p.payload.session})`,
            ]}
          />
          <Bar dataKey="reaction" radius={[3, 3, 0, 0]} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.reaction >= 0 ? "var(--pos)" : "var(--neg)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
