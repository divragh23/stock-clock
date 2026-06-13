// Small presentation helpers. Purely cosmetic — they read the unified payload
// and never care which source produced a number.

export function pct(x, digits = 2) {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  const v = x * 100;
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}%`;
}

export function money(x, digits = 2) {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return `$${Number(x).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

export function eps(x) {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return Number(x).toFixed(2);
}

export function signClass(x) {
  if (x === null || x === undefined || Number.isNaN(x)) return "neutral";
  if (x > 0) return "pos";
  if (x < 0) return "neg";
  return "neutral";
}

// "2026-06-10" -> "Jun 10, 2026"
export function prettyDate(iso) {
  if (!iso) return "—";
  const d = new Date(`${String(iso).slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

// "2026-06-10T22:00:00+00:00" -> "Jun 10, 22:00"
export function prettyDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function shortDate(iso) {
  if (!iso) return "";
  const d = new Date(`${String(iso).slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
