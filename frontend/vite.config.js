import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, the React app calls the backend through this proxy, so the browser
// only ever talks to the Vite origin (no CORS). In production nginx plays the
// same role: it serves the built static files and proxies /api to uvicorn.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
