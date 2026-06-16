import { useState, useMemo } from "react";
import * as api from "../api.js";
import PrismaticBurst from "./PrismaticBurst.jsx";
import { burstColors } from "../theme.js";

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const colors = useMemo(() => burstColors(), []);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await api.login(username.trim(), password);
      onLogin({ username: user.username, is_admin: user.is_admin });
    } catch (err) {
      setError(err.message || "Login failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-burst">
        <PrismaticBurst
          animationType="rotate3d"
          intensity={1.4}
          speed={0.3}
          distort={0.8}
          paused={false}
          offset={{ x: 0, y: 0 }}
          hoverDampness={0.25}
          rayCount={20}
          mixBlendMode="lighten"
          colors={colors}
        />
      </div>
      <form className="login-card" onSubmit={submit}>
        <div className="login-brand">
          <span className="brand-mark">&#9716;</span> Stock Clock
        </div>
        <p className="login-sub">Sign in to your account</p>

        {error && <div className="login-error">{error}</div>}

        <label className="login-label">
          Email
          <input
            className="login-input"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            spellCheck={false}
          />
        </label>
        <label className="login-label">
          Password
          <input
            className="login-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>

        <button className="btn login-btn" type="submit" disabled={busy || !username || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="login-foot">Accounts are created by the administrator.</p>
      </form>
    </div>
  );
}
