import { useEffect, useState } from "react";
import { api } from "../api";
import Citations from "./Citations";

// One-click examples that work against the bundled sample documents — makes the
// demo flow obvious and avoids fumbling for a question on camera.
const SAMPLE_QUESTIONS = [
  "What is the total amount due?",
  "What is the invoice due date?",
  "What is the payment term in days?",
  "How many days overdue is the payment?",
];

export default function AskPanel({ documents }) {
  const processed = documents.filter((d) => d.status === "processed");
  const [docId, setDocId] = useState("");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Default to the first processed document.
  useEffect(() => {
    if (!docId && processed.length > 0) setDocId(String(processed[0].id));
  }, [processed, docId]);

  async function loadHistory(id) {
    if (!id) return;
    try {
      setHistory(await api.history(id));
    } catch (_) {
      /* non-critical */
    }
  }

  useEffect(() => {
    loadHistory(docId);
  }, [docId]);

  async function onAsk(e) {
    e.preventDefault();
    if (!docId || !question.trim()) return;
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await api.ask(Number(docId), question.trim());
      setResult(res);
      await loadHistory(docId);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (processed.length === 0) {
    return (
      <section className="card">
        <h2>Ask a question</h2>
        <p className="muted">
          Upload and process a document first, then come back to ask questions.
        </p>
      </section>
    );
  }

  return (
    <section>
      <div className="card">
        <h2>Ask a question</h2>
        <form onSubmit={onAsk}>
          <label>Document</label>
          <select value={docId} onChange={(e) => setDocId(e.target.value)}>
            {processed.map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename}
              </option>
            ))}
          </select>

          <label>Question</label>
          <textarea
            rows={3}
            placeholder="e.g. What is the total amount due?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />

          <div className="suggestions">
            {SAMPLE_QUESTIONS.map((q) => (
              <button
                type="button"
                key={q}
                className="chip"
                onClick={() => setQuestion(q)}
              >
                {q}
              </button>
            ))}
          </div>

          <button type="submit" disabled={loading || !question.trim()}>
            {loading ? "Thinking…" : "Ask"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}

        {result && (
          <div className={`answer ${result.abstained ? "abstained" : ""}`}>
            <div className="answer-head">
              <h3>Answer</h3>
              <span className="badge mode">{result.mode}</span>
              {result.abstained && <span className="badge warn">abstained</span>}
            </div>
            <p>{result.answer}</p>
            <Citations citations={result.citations} />
          </div>
        )}
      </div>

      <div className="card">
        <h2>Previous questions</h2>
        {history.length === 0 ? (
          <p className="muted">No questions yet for this document.</p>
        ) : (
          history.map((h) => (
            <div className="history-item" key={h.id}>
              <p className="q">Q: {h.question}</p>
              <p className="a">
                A: {h.answer}{" "}
                {h.abstained && <span className="badge warn">abstained</span>}
              </p>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
