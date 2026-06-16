import { useEffect, useRef, useState } from "react";

export default function UserMenu({ user, onManageAccounts, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onDoc(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const initial = (user?.username || "?").slice(0, 1).toUpperCase();

  return (
    <div className="usermenu" ref={ref}>
      <button className="usermenu-trigger" onClick={() => setOpen((o) => !o)} title={user?.username}>
        <span className="usermenu-avatar">{initial}</span>
      </button>
      {open && (
        <div className="usermenu-pop">
          <div className="usermenu-head">
            {user?.username}
            {user?.is_admin && <span className="usermenu-admin">admin</span>}
          </div>
          {user?.is_admin && (
            <button
              className="usermenu-item"
              onClick={() => {
                setOpen(false);
                onManageAccounts();
              }}
            >
              Manage accounts
            </button>
          )}
          <button className="usermenu-item danger" onClick={onLogout}>
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
