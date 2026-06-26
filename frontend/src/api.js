// Thin API client. All requests go through the Vite proxy at /api -> backend.
// A JWT access token (from login/register/google) is kept in localStorage and
// sent as `Authorization: Bearer <token>`. A 401 on an AUTHENTICATED request
// (one that carried a token) clears it and notifies the app with a reason; a 401
// on a login attempt (no token) just throws so the form shows the error inline.
const BASE = "/api";
const TOKEN_KEY = "ff_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

let onUnauthorized = null;
export function setOnUnauthorized(fn) {
  onUnauthorized = fn;
}

async function handle(res, hadToken) {
  if (res.status === 401 && hadToken) {
    tokenStore.clear();
    onUnauthorized?.("Your session expired — please sign in again.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }
  return res.json();
}

function request(path, { method = "GET", body, json } = {}) {
  const headers = {};
  const token = tokenStore.get();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  let payload = body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(json);
  }
  return fetch(`${BASE}${path}`, { method, headers, body: payload }).then((res) =>
    handle(res, !!token)
  );
}

const storeToken = (r) => {
  tokenStore.set(r.access_token);
  return r;
};

export const api = {
  // ---- Auth ----
  register: (creds) => request("/auth/register", { method: "POST", json: creds }).then(storeToken),
  login: (creds) => request("/auth/login", { method: "POST", json: creds }).then(storeToken),
  googleLogin: (credential) =>
    request("/auth/google", { method: "POST", json: { credential } }).then(storeToken),
  me: () => request("/auth/me"),
  logout: () => tokenStore.clear(),

  // ---- App ----
  health: () => request("/health"),
  listDocuments: () => request("/documents"),
  uploadDocument: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/documents/upload", { method: "POST", body: form });
  },
  deleteDocument: (id) => request(`/documents/${id}`, { method: "DELETE" }),
  ask: (document_id, question, mode = "fast") =>
    request("/ask", { method: "POST", json: { document_id, question, mode } }),
  audit: (document_id, audit_type = "general") =>
    request("/audit", { method: "POST", json: { document_id, audit_type } }),
  history: (document_id) =>
    request(`/history${document_id ? `?document_id=${document_id}` : ""}`),
  evaluate: () => request("/evaluate", { method: "POST" }),
  seedDemo: () => request("/demo/seed", { method: "POST" }),
};
