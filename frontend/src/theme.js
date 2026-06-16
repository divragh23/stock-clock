// Theme palettes. Every color in the app is a CSS variable, so switching themes
// is just overriding these custom properties on :root — charts included.
export const THEMES = {
  midnight: {
    label: "Midnight",
    vars: {
      "--bg": "#0b0e14", "--surface": "#121723", "--surface-2": "#1a2130", "--border": "#263042",
      "--text": "#e6edf6", "--muted": "#8b9ab2", "--accent": "#4c8dff",
      "--pos": "#2ecc71", "--neg": "#ff5d5d", "--grid": "#1e2636", "--axis": "#5a6678",
    },
    burst: ["#4c8dff", "#1a2130", "#2ecc71"],
  },
  graphite: {
    label: "Graphite",
    vars: {
      "--bg": "#0e0e10", "--surface": "#17181b", "--surface-2": "#202227", "--border": "#2b2d33",
      "--text": "#ececec", "--muted": "#9a9ca3", "--accent": "#7c8cff",
      "--pos": "#3ecf8e", "--neg": "#ff6b6b", "--grid": "#222328", "--axis": "#5c5e66",
    },
    burst: ["#7c8cff", "#202227", "#3ecf8e"],
  },
  emerald: {
    label: "Emerald",
    vars: {
      "--bg": "#08120e", "--surface": "#0f1c17", "--surface-2": "#16271f", "--border": "#22382e",
      "--text": "#e7f5ee", "--muted": "#85a89a", "--accent": "#16c784",
      "--pos": "#16c784", "--neg": "#ff5d5d", "--grid": "#16271f", "--axis": "#4e7565",
    },
    burst: ["#16c784", "#16271f", "#85a89a"],
  },
  violet: {
    label: "Violet",
    vars: {
      "--bg": "#0e0b18", "--surface": "#171327", "--surface-2": "#1f1a35", "--border": "#2c2546",
      "--text": "#ece8fb", "--muted": "#9b91c0", "--accent": "#8b5cf6",
      "--pos": "#2ecc71", "--neg": "#ff5d6c", "--grid": "#1f1a35", "--axis": "#5e5685",
    },
    burst: ["#8b5cf6", "#1f1a35", "#ff5d6c"],
  },
  daylight: {
    label: "Daylight",
    vars: {
      "--bg": "#f5f7fb", "--surface": "#ffffff", "--surface-2": "#eef1f7", "--border": "#d8dee9",
      "--text": "#1a2230", "--muted": "#5c6b82", "--accent": "#2f6df0",
      "--pos": "#0a9d57", "--neg": "#e23b41", "--grid": "#e6eaf2", "--axis": "#9aa6ba",
    },
    burst: ["#2f6df0", "#eef1f7", "#0a9d57"],
  },
};

const KEY = "sc_theme";

export function currentTheme() {
  const t = localStorage.getItem(KEY);
  return t && THEMES[t] ? t : "midnight";
}

export function applyTheme(name) {
  const theme = THEMES[name] || THEMES.midnight;
  const root = document.documentElement;
  Object.entries(theme.vars).forEach(([k, v]) => root.style.setProperty(k, v));
  localStorage.setItem(KEY, THEMES[name] ? name : "midnight");
}

export function burstColors() {
  const t = currentTheme();
  return (THEMES[t] || THEMES.midnight).burst;
}

export function loadTheme() {
  applyTheme(currentTheme());
}
