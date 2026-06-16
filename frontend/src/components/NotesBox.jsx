import { useEffect, useState } from "react";

// Per-user note for the current ticker. Saves on demand; "saved" state resets
// whenever the ticker or text changes.
export default function NotesBox({ ticker, value, onSave }) {
  const [text, setText] = useState(value || "");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setText(value || "");
    setSaved(false);
  }, [value, ticker]);

  async function save() {
    setBusy(true);
    try {
      await onSave(text);
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="notes-card">
      <div className="notes-head">
        <h3>
          My notes on <b>{ticker}</b>
        </h3>
        {saved && <span className="notes-saved">saved ✓</span>}
      </div>
      <textarea
        className="notes-area"
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setSaved(false);
        }}
        placeholder={`Private notes on ${ticker} — only you can see these (e.g. "bought at $180, watching earnings").`}
        rows={3}
      />
      <div className="notes-actions">
        <button className="btn" onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save note"}
        </button>
      </div>
    </div>
  );
}
