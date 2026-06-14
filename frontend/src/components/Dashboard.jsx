import { useRef, useState } from "react";
import { api } from "../api";

export default function Dashboard({ documents, reload, loading }) {
  const [uploading, setUploading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const fileRef = useRef(null);

  function notify(msg) {
    setError("");
    setMessage(msg);
  }

  async function onUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setMessage("");
    setUploading(true);
    try {
      const doc = await api.uploadDocument(file);
      await reload();
      if (doc.status === "processed") {
        notify(`Uploaded "${doc.filename}" — ${doc.num_chunks} chunks ready.`);
      } else {
        setError(`"${doc.filename}" could not be processed: ${doc.error || "unknown error"}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onSeedDemo() {
    setError("");
    setMessage("");
    setSeeding(true);
    try {
      const res = await api.seedDemo();
      await reload();
      notify(res.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setSeeding(false);
    }
  }

  async function onDelete(id, name) {
    if (!confirm("Delete this document and its history?")) return;
    setError("");
    setMessage("");
    try {
      await api.deleteDocument(id);
      await reload();
      notify(`Deleted "${name}".`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <div className="card">
        <h2>Quick start</h2>
        <p className="muted">
          New here? Load the bundled sample invoice, contract, and payment note,
          then head to the <strong>Ask</strong> tab — testable in under a minute.
        </p>
        <button onClick={onSeedDemo} disabled={seeding}>
          {seeding ? "Loading…" : "▶ Load sample documents"}
        </button>
      </div>

      <div className="card">
        <h2>Upload a document</h2>
        <p className="muted">Supported: PDF or TXT, up to 10 MB.</p>
        <label className="upload-btn">
          {uploading ? "Uploading…" : "Choose file"}
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.txt"
            onChange={onUpload}
            disabled={uploading}
            hidden
          />
        </label>
      </div>

      {message && <p className="success">✓ {message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="card">
        <h2>Documents</h2>
        {loading ? (
          <p className="muted">Loading…</p>
        ) : documents.length === 0 ? (
          <p className="muted">
            No documents yet. Click <strong>Load sample documents</strong> above or
            upload your own to get started.
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Chunks</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {documents.map((d) => (
                <tr key={d.id}>
                  <td>{d.filename}</td>
                  <td className="uppercase">{d.file_type}</td>
                  <td>
                    <span className={`status ${d.status}`}>{d.status}</span>
                    {d.error && <div className="error small">{d.error}</div>}
                  </td>
                  <td>{d.num_chunks}</td>
                  <td>
                    <button
                      className="link danger"
                      onClick={() => onDelete(d.id, d.filename)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
