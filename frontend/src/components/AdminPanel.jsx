import { useEffect, useState } from "react";
import * as api from "../api.js";

// Admin-only modal: list, create, and remove accounts.
export default function AdminPanel({ me, onClose }) {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState(null);
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [busy, setBusy] = useState(false);

  async function reload() {
    try {
      setUsers(await api.adminListUsers());
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => {
    reload();
  }, []);

  async function create(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.adminCreateUser(u.trim(), p, isAdmin);
      setU("");
      setP("");
      setIsAdmin(false);
      await reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(username) {
    if (!window.confirm(`Remove account ${username}? Their saved data will be deleted.`)) return;
    setError(null);
    try {
      await api.adminDeleteUser(username);
      await reload();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>Manage accounts</h2>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        {error && <div className="login-error">{error}</div>}

        <table className="admin-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((usr) => (
              <tr key={usr.username}>
                <td>{usr.username}</td>
                <td>{usr.is_admin ? <span className="usermenu-admin">admin</span> : "user"}</td>
                <td className="num">
                  {usr.username === me.username ? (
                    <span className="muted small">you</span>
                  ) : (
                    <button className="link-danger" onClick={() => remove(usr.username)}>
                      remove
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <form className="admin-create" onSubmit={create}>
          <h3>Add account</h3>
          <input
            className="login-input"
            placeholder="email"
            value={u}
            onChange={(e) => setU(e.target.value)}
            spellCheck={false}
          />
          <input
            className="login-input"
            type="password"
            placeholder="password"
            value={p}
            onChange={(e) => setP(e.target.value)}
          />
          <label className="admin-check">
            <input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} />
            make admin
          </label>
          <button className="btn" type="submit" disabled={busy || !u || !p}>
            {busy ? "Adding…" : "Add account"}
          </button>
        </form>
      </div>
    </div>
  );
}
