/**
 * Centralized frontend configuration. Backed by Vite env vars so the API
 * origin and upload limits can be changed per-deployment without touching
 * code (see .env.example).
 *
 * When VITE_API_BASE_URL isn't set, the API host is derived from
 * `window.location.hostname` — i.e. whatever host the browser used to load
 * this page — rather than a hardcoded IP. This matters for a LAN setup
 * where the backend and frontend run together on one "server" laptop: a
 * hardcoded fallback (or a stale .env value) only works for clients on
 * that exact address, and silently breaks — or worse, points a client back
 * at *itself* — the moment someone connects over a different interface
 * (Ethernet vs. Wi-Fi hotspot) or from a different machine. Deriving from
 * the page's own host means opening http://<server-ip>:5173 from any
 * client, on any reachable interface, automatically talks to the backend
 * at http://<that-same-server-ip>:8000 — no per-client config needed.
 * Only set VITE_API_BASE_URL when the backend genuinely lives on a
 * different host than the frontend.
 */
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? `http://${window.location.hostname}:8000`,
  maxUploadMb: Number(import.meta.env.VITE_MAX_UPLOAD_MB ?? 25),
} as const;

export const ACCEPTED_FILE_EXTENSIONS = [
  ".pdf",
  ".docx",
  ".xlsx",
  ".csv",
  ".pptx",
  ".png",
  ".jpg",
  ".jpeg",
  ".txt",
  ".py",
  ".cpp",
  ".c",
  ".js",
  ".ts",
];
