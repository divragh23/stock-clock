// The ONLY network layer. Talks exclusively to our FastAPI backend (same origin
// via the Vite proxy in dev / nginx in prod). A session token (from login) is
// stored in localStorage and sent as a Bearer header on every request.
const BASE = import.meta.env.VITE_API_BASE || "";
const TOKEN_KEY = "sc_token";

let unauthorizedHandler = null;
export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn;
}
export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}
function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function getJSON(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  const tok = getToken();
  if (tok) headers["Authorization"] = `Bearer ${tok}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (res.status === 401) {
    setToken("");
    if (unauthorizedHandler) unauthorizedHandler();
    const e = new Error("Session expired — please log in again.");
    e.status = 401;
    throw e;
  }
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON */
  }
  if (!res.ok) {
    const detail = (body && (body.detail || body.message)) || res.statusText;
    const e = new Error(detail || `Request failed (${res.status})`);
    e.status = res.status;
    throw e;
  }
  return body;
}

const jsonBody = (obj) => ({
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(obj),
});

// --- auth ---
export async function login(username, password) {
  const r = await getJSON(`/api/auth/login`, { method: "POST", ...jsonBody({ username, password }) });
  setToken(r.token);
  return r;
}
export async function logout() {
  try {
    await getJSON(`/api/auth/logout`, { method: "POST" });
  } catch {
    /* ignore */
  }
  setToken("");
}
export function getMe() {
  return getJSON(`/api/auth/me`);
}

// --- stock data ---
export function getStock(ticker, { refresh = false } = {}) {
  const q = refresh ? "?refresh=true" : "";
  return getJSON(`/api/stock/${encodeURIComponent(ticker)}${q}`);
}
export function searchSymbols(q) {
  return getJSON(`/api/search?q=${encodeURIComponent(q)}`);
}
export function refreshTicker(ticker) {
  return getJSON(`/api/refresh`, { method: "POST", ...jsonBody(ticker ? { ticker } : {}) });
}

// --- per-user data ---
export function getWatchlist() {
  return getJSON(`/api/me/watchlist`);
}
export function addWatchlist(ticker) {
  return getJSON(`/api/me/watchlist`, { method: "POST", ...jsonBody({ ticker }) });
}
export function removeWatchlist(ticker) {
  return getJSON(`/api/me/watchlist/${encodeURIComponent(ticker)}`, { method: "DELETE" });
}
export function getPreferences() {
  return getJSON(`/api/me/preferences`);
}
export function setPreferences(p) {
  return getJSON(`/api/me/preferences`, { method: "PUT", ...jsonBody(p) });
}
export function getNote(ticker) {
  return getJSON(`/api/me/notes/${encodeURIComponent(ticker)}`);
}
export function setNote(ticker, body) {
  return getJSON(`/api/me/notes/${encodeURIComponent(ticker)}`, { method: "PUT", ...jsonBody({ body }) });
}
export function getRecent() {
  return getJSON(`/api/me/recent`);
}

// --- admin ---
export function adminListUsers() {
  return getJSON(`/api/admin/users`);
}
export function adminCreateUser(username, password, is_admin = false) {
  return getJSON(`/api/admin/users`, { method: "POST", ...jsonBody({ username, password, is_admin }) });
}
export function adminDeleteUser(username) {
  return getJSON(`/api/admin/users/${encodeURIComponent(username)}`, { method: "DELETE" });
}
