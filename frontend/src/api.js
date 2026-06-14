// Thin API client. All requests go through the Vite proxy at /api -> backend.
const BASE = "/api";

async function handle(res) {
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

export const api = {
  health: () => fetch(`${BASE}/health`).then(handle),

  listDocuments: () => fetch(`${BASE}/documents`).then(handle),

  uploadDocument: (file) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${BASE}/documents/upload`, {
      method: "POST",
      body: form,
    }).then(handle);
  },

  deleteDocument: (id) =>
    fetch(`${BASE}/documents/${id}`, { method: "DELETE" }).then(handle),

  ask: (document_id, question) =>
    fetch(`${BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id, question }),
    }).then(handle),

  history: (document_id) => {
    const q = document_id ? `?document_id=${document_id}` : "";
    return fetch(`${BASE}/history${q}`).then(handle);
  },

  evaluate: () => fetch(`${BASE}/evaluate`, { method: "POST" }).then(handle),

  seedDemo: () => fetch(`${BASE}/demo/seed`, { method: "POST" }).then(handle),
};
