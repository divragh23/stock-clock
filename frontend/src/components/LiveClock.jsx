import { useEffect, useRef, useState } from "react";

export default function LiveClock() {
  const [now, setNow] = useState(() => new Date());
  const rafRef = useRef(0);

  useEffect(() => {
    let prev = 0;
    const tick = (ts) => {
      if (ts - prev >= 200) {
        setNow(new Date());
        prev = ts;
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  const s = now.getSeconds() + now.getMilliseconds() / 1000;
  const m = now.getMinutes() + s / 60;
  const h = (now.getHours() % 12) + m / 60;

  const secAngle = s * 6;
  const minAngle = m * 6;
  const hrAngle = h * 30;

  const pad = (n) => String(n).padStart(2, "0");
  const digital = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

  return (
    <div className="live-clock">
      <svg
        className="live-clock-face"
        viewBox="0 0 100 100"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          cx="50" cy="50" r="46"
          fill="none"
          stroke="var(--border)"
          strokeWidth="2"
        />
        <circle
          cx="50" cy="50" r="46"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
          strokeDasharray="8 12.88"
          opacity="0.5"
        />
        {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map((a) => {
          const major = a % 90 === 0;
          const rad = (a - 90) * (Math.PI / 180);
          const r1 = major ? 36 : 39;
          const r2 = 44;
          return (
            <line
              key={a}
              x1={50 + r1 * Math.cos(rad)}
              y1={50 + r1 * Math.sin(rad)}
              x2={50 + r2 * Math.cos(rad)}
              y2={50 + r2 * Math.sin(rad)}
              stroke={major ? "var(--accent)" : "var(--muted)"}
              strokeWidth={major ? 2.5 : 1.2}
              strokeLinecap="round"
              opacity={major ? 1 : 0.5}
            />
          );
        })}
        <line
          x1="50" y1="50"
          x2="50" y2="22"
          stroke="var(--text)"
          strokeWidth="3"
          strokeLinecap="round"
          transform={`rotate(${hrAngle} 50 50)`}
        />
        <line
          x1="50" y1="50"
          x2="50" y2="16"
          stroke="var(--text)"
          strokeWidth="2"
          strokeLinecap="round"
          transform={`rotate(${minAngle} 50 50)`}
        />
        <line
          x1="50" y1="56"
          x2="50" y2="14"
          stroke="var(--accent)"
          strokeWidth="1"
          strokeLinecap="round"
          transform={`rotate(${secAngle} 50 50)`}
        />
        <circle cx="50" cy="50" r="3" fill="var(--accent)" />
        <circle cx="50" cy="50" r="1.5" fill="var(--bg)" />
      </svg>
      <span className="live-clock-digital">{digital}</span>
    </div>
  );
}
