import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The SPA never talks to AWS directly — it only calls our API (CLAUDE.md §2 Frontend).
// In dev, proxy /api to the backend so there are no CORS surprises. The target is
// localhost:8000 when running bare, or the `backend` service inside docker compose.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Allow the Vite dev server to be reached through a public tunnel (Cloudflare/ngrok) for
    // demos — Vite otherwise blocks requests with an unknown Host header.
    allowedHosts: true,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
