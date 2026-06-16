// The ONLY network layer. The app talks exclusively to our FastAPI backend
// (same origin via the Vite proxy in dev / nginx in prod). It never calls
// yfinance or Finnhub directly — those aren't browser-callable and the keys
// live server-side.
const BASE = import.meta.env.VITE_API_BASE || "";

async function getJSON(path, opts) {
  const res = await fetch(`${BASE}${path}`, opts);
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON error body */
  }
  if (!res.ok) {
    const detail = (body && (body.detail || body.message)) || res.statusText;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return body;
}

export function getStock(ticker, { refresh = false } = {}) {
  const q = refresh ? "?refresh=true" : "";
  return getJSON(`/api/stock/${encodeURIComponent(ticker)}${q}`);
}

export function getHealth() {
  return getJSON(`/api/health`);
}

export function searchSymbols(q) {
  return getJSON(`/api/search?q=${encodeURIComponent(q)}`);
}

export function refreshTicker(ticker) {
  return getJSON(`/api/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ticker ? { ticker } : {}),
  });
}
