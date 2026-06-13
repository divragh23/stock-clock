import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { money, shortDate, prettyDate } from "../format.js";

const RANGES = [
  { key: "1m", label: "1M", days: 31 },
  { key: "3m", label: "3M", days: 92 },
  { key: "6m", label: "6M", days: 183 },
  { key: "1y", label: "1Y", days: 366 },
  { key: "5y", label: "5Y", days: 100000 },
];

export default function PriceChart({ series }) {
  const [range, setRange] = useState("3m");

  const data = useMemo(() => {
    if (!series || series.length === 0) return [];
    const r = RANGES.find((x) => x.key === range) || RANGES[1];
    const cutoffMs = Date.now() - r.days * 24 * 3600 * 1000;
    return series
      .filter((p) => p.close != null)
      .filter((p) => new Date(`${p.date}T00:00:00`).getTime() >= cutoffMs || r.days > 99999)
      .map((p) => ({ date: p.date, close: p.close }));
  }, [series, range]);

  const up =
    data.length >= 2 ? data[data.length - 1].close >= data[0].close : true;
  const stroke = up ? "var(--pos)" : "var(--neg)";

  return (
    <div className="chart-card">
      <div className="chart-head">
        <h3>Price</h3>
        <div className="range-toggle">
          {RANGES.map((r) => (
            <button
              key={r.key}
              className={`range-btn ${range === r.key ? "active" : ""}`}
              onClick={() => setRange(r.key)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      {data.length === 0 ? (
        <div className="empty">No price data.</div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={shortDate}
              minTickGap={40}
              stroke="var(--axis)"
              tick={{ fontSize: 11 }}
            />
            <YAxis
              domain={["auto", "auto"]}
              tickFormatter={(v) => `$${Math.round(v)}`}
              stroke="var(--axis)"
              tick={{ fontSize: 11 }}
              width={52}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--text)",
              }}
              labelFormatter={(l) => prettyDate(l)}
              formatter={(v) => [money(v), "Close"]}
            />
            <Line
              type="monotone"
              dataKey="close"
              stroke={stroke}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
