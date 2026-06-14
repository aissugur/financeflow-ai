import { useEffect, useState } from "react";
import { api } from "../api";
import Citations from "./Citations";

// Curated demo questions that each showcase a distinct behaviour against the
// bundled sample invoice. Clicking one selects the right document and asks it,
// so a reviewer can see the product working in a couple of clicks.
const DEMO_QUESTIONS = [
  {
    q: "What is the total amount due?",
    doc: "sample_invoice.txt",
    hint: "Strong cited answer",
  },
  {
    q: "What are the payment terms and late fees?",
    doc: "sample_invoice.txt",
    hint: "Multiple evidence chunks",
  },
  {
    q: "What is the customer's social security number?",
    doc: "sample_invoice.txt",
    hint: "Correctly abstains",
  },
];

export default function AskPanel({ documents }) {
  const processed = documents.filter((d) => d.status === "processed");
  const [docId, setDocId] = useState("");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Default to the sample invoice when present (deterministic demo), else the
  // first processed document.
  useEffect(() => {
    if (docId || processed.length === 0) return;
    const invoice = processed.find((d) => d.filename === "sample_invoice.txt");
    setDocId(String((invoice || processed[0]).id));
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

  async function submit(id, q) {
    if (!id || !q.trim()) return;
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await api.ask(Number(id), q.trim());
      setResult(res);
      await loadHistory(id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function onAsk(e) {
    e.preventDefault();
    submit(docId, question);
  }

  async function runDemo(item) {
    const doc =
      processed.find((d) => d.filename === item.doc) || processed[0];
    if (!doc) return;
    setDocId(String(doc.id));
    setQuestion(item.q);
    await submit(doc.id, item.q);
  }

  if (processed.length === 0) {
    return (
      <section className="card">
        <h2>Ask a question</h2>
        <p className="muted">
          No documents yet. Go to the <strong>Dashboard</strong> and click{" "}
          <strong>Load sample documents</strong> (or upload your own), then come
          back to ask questions.
        </p>
      </section>
    );
  }

  return (
    <section>
      <div className="card">
        <h2>Ask a question</h2>

        <p className="muted">Try a demo question:</p>
        <div className="suggestions">
          {DEMO_QUESTIONS.map((item) => (
            <button
              type="button"
              key={item.q}
              className="chip demo"
              onClick={() => runDemo(item)}
              disabled={loading}
              title={item.doc}
            >
              <span>{item.q}</span>
              <small>{item.hint}</small>
            </button>
          ))}
        </div>

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
