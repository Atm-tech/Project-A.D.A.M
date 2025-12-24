// Resolves API base for both local dev and deployed static hosting.
(function resolveApiBase() {
  const QUERY_KEYS = ["apiBase", "api_base", "api"];
  const STORAGE_KEY = "API_BASE";

  const params = new URLSearchParams(window.location.search);
  const queryOverride = QUERY_KEYS.map((k) => params.get(k)).find(Boolean);
  const stored = localStorage.getItem(STORAGE_KEY);
  const hostname = window.location.hostname;

  const defaultBase =
    hostname === "localhost" || hostname === "127.0.0.1"
      ? "http://localhost:8000/api/v1"
      : `${window.location.origin}/api/v1`;

  const resolved =
    (queryOverride && queryOverride.trim()) ||
    (stored && stored.trim()) ||
    (window.API_BASE && String(window.API_BASE).trim()) ||
    defaultBase;

  const normalized = resolved.replace(/\/$/, "");
  if (queryOverride) {
    localStorage.setItem(STORAGE_KEY, normalized);
  }

  window.API_BASE = normalized;
})();
