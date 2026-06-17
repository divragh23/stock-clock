import { useEffect, useRef, useState } from "react";
import Grainient from "./Grainient.jsx";
import LiveClock from "./LiveClock.jsx";

export default function WelcomeScreen({ user, gradient, loaded, onComplete }) {
  const [phase, setPhase] = useState("clock-in");
  const [progress, setProgress] = useState(0);
  const nameRef = useRef("");

  const raw = user?.username || "";
  nameRef.current = raw.includes("@") ? raw.split("@")[0] : raw;

  useEffect(() => {
    const timers = [];
    const t = (fn, ms) => timers.push(setTimeout(fn, ms));

    const typeLen = nameRef.current.length * 80;
    t(() => setPhase("typing"), 800);
    t(() => setPhase("hold"), 800 + typeLen + 1000);
    t(() => setPhase("flicker"), 800 + typeLen + 2200);
    t(() => setPhase("fade-out"), 800 + typeLen + 3400);
    t(() => onComplete(), 800 + typeLen + 3800);

    return () => timers.forEach(clearTimeout);
  }, [onComplete]);

  useEffect(() => {
    const id = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) return 100;
        if (loaded) return Math.min(100, p + 6);
        return Math.min(82, p + (Math.random() * 2.5 + 0.5));
      });
    }, 120);
    return () => clearInterval(id);
  }, [loaded]);

  const showText = phase !== "clock-in";
  const flickering = phase === "flicker";
  const fading = phase === "fade-out";
  const pct = Math.round(progress);

  return (
    <div className={`welcome-screen ${fading ? "welcome-fade-out" : ""}`}>
      <div className="welcome-bg">
        <Grainient
          color1={gradient.color1}
          color2={gradient.color2}
          color3={gradient.color3}
          timeSpeed={0.2}
          warpStrength={0.8}
          warpFrequency={4.0}
          warpSpeed={1.5}
          warpAmplitude={60.0}
          blendSoftness={0.1}
          rotationAmount={400.0}
          noiseScale={1.8}
          grainAmount={0.04}
          contrast={1.3}
          saturation={0.9}
        />
      </div>
      <div className="welcome-content">
        <div className={`welcome-clock ${flickering ? "welcome-flicker" : ""} ${fading ? "welcome-el-fade" : ""}`}>
          <LiveClock size="large" />
        </div>
        {showText && (
          <div className={`welcome-text ${fading ? "welcome-el-fade" : ""}`}>
            <span className="welcome-label">Welcome </span>
            <span className="welcome-name">
              <Typewriter text={nameRef.current} speed={80} />
            </span>
          </div>
        )}
        <div className={`welcome-loader ${fading ? "welcome-el-fade" : ""}`}>
          <span className="welcome-loader-text">Loading assets</span>
          <span className="welcome-loader-dots" />
          <span className="welcome-loader-pct">{pct}%</span>
          <div className="welcome-loader-bar">
            <div className="welcome-loader-fill" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}

function Typewriter({ text, speed }) {
  const [len, setLen] = useState(0);

  useEffect(() => {
    if (len >= text.length) return;
    const id = setTimeout(() => setLen((l) => l + 1), speed);
    return () => clearTimeout(id);
  }, [len, text, speed]);

  return (
    <>
      {text.slice(0, len)}
      <span className="typewriter-cursor">|</span>
    </>
  );
}
