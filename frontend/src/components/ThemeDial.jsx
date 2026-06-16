import { useState, useRef, useEffect } from "react";
import { THEMES, currentTheme, applyTheme } from "../theme.js";

export default function ThemeDial({ onThemeChange }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(currentTheme);
  const ref = useRef(null);

  useEffect(() => {
    function onDoc(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function pick(name) {
    applyTheme(name);
    setActive(name);
    onThemeChange?.(name);
    setOpen(false);
  }

  return (
    <div className="theme-dial" ref={ref}>
      <button
        className="theme-dial-btn"
        onClick={() => setOpen((o) => !o)}
        title="Change theme"
        aria-label="Change theme"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z"
            stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
          />
          <path
            d="M16.18 12.5a1.36 1.36 0 00.27 1.5l.05.05a1.65 1.65 0 11-2.33 2.33l-.05-.05a1.36 1.36 0 00-1.5-.27 1.36 1.36 0 00-.83 1.25v.14a1.65 1.65 0 01-3.3 0v-.07a1.36 1.36 0 00-.89-1.25 1.36 1.36 0 00-1.5.27l-.05.05a1.65 1.65 0 11-2.33-2.33l.05-.05a1.36 1.36 0 00.27-1.5 1.36 1.36 0 00-1.25-.83h-.14a1.65 1.65 0 010-3.3h.07a1.36 1.36 0 001.25-.89 1.36 1.36 0 00-.27-1.5l-.05-.05a1.65 1.65 0 112.33-2.33l.05.05a1.36 1.36 0 001.5.27h.07a1.36 1.36 0 00.82-1.25v-.14a1.65 1.65 0 013.3 0v.07a1.36 1.36 0 00.83 1.25 1.36 1.36 0 001.5-.27l.05-.05a1.65 1.65 0 112.33 2.33l-.05.05a1.36 1.36 0 00-.27 1.5v.07a1.36 1.36 0 001.25.82h.14a1.65 1.65 0 010 3.3h-.07a1.36 1.36 0 00-1.25.83z"
            stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
          />
        </svg>
      </button>
      {open && (
        <div className="theme-pop">
          <div className="theme-pop-title">Theme</div>
          {Object.entries(THEMES).map(([key, t]) => (
            <button
              key={key}
              className={`theme-opt ${active === key ? "active" : ""}`}
              onClick={() => pick(key)}
            >
              <span className="theme-swatch" style={{ background: t.vars["--accent"] }} />
              <span className="theme-opt-label">{t.label}</span>
              {active === key && <span className="theme-check">&#10003;</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
