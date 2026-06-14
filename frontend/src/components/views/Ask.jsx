import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { Select, Textarea } from "../ui/Field";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import EvidencePanel from "../EvidencePanel";

const DEMO = [
  { q: "What is the total amount due?", doc: "sample_invoice.txt", hint: "Strong cited answer" },
  { q: "What are the payment terms and late fees?", doc: "sample_invoice.txt", hint: "Multiple evidence chunks" },
  { q: "What is the customer's social security number?", doc: "sample_invoice.txt", hint: "Correctly abstains" },
];

export default function Ask({ documents, demoSignal, onDemoConsumed }) {
  const processed = documents.filter((d) => d.status === "processed");
  const [docId, setDocId] = useState("");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const lastDemo = useRef(0);

  // Default to the sample invoice for a deterministic demo, else the first doc.
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

  async function runDemo(item) {
    const doc = processed.find((d) => d.filename === item.doc) || processed[0];
    if (!doc) return;
    setDocId(String(doc.id));
    setQuestion(item.q);
    await submit(doc.id, item.q);
  }

  // When "Try Demo" navigates here, auto-run the first showcase question once.
  useEffect(() => {
    if (demoSignal && demoSignal !== lastDemo.current && processed.length > 0) {
      lastDemo.current = demoSignal;
      runDemo(DEMO[0]);
      onDemoConsumed?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demoSignal, processed.length]);

  if (processed.length === 0) {
    return (
      <EmptyState title="No documents to query">
        Head to <strong>Overview</strong> and click <strong>Try Demo</strong> (or
        upload a file), then come back to ask questions.
      </EmptyState>
    );
  }

  return (
    <div className="ask-grid">
      <div>
        <Card>
          <Select
            label="Document"
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
          >
            {processed.map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename}
              </option>
            ))}
          </Select>

          <span className="field-label">Try a demo question</span>
          <div className="chips" style={{ marginBottom: 18 }}>
            {DEMO.map((item) => (
              <button
                key={item.q}
                className="chip"
                disabled={loading}
                onClick={() => runDemo(item)}
                title={item.doc}
              >
                <span>{item.q}</span>
                <small>{item.hint}</small>
              </button>
            ))}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(docId, question);
            }}
          >
            <Textarea
              label="Your question"
              rows={3}
              placeholder="e.g. What is the total amount due?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <Button variant="primary" type="submit" loading={loading} disabled={!question.trim()}>
              {loading ? "Retrieving…" : "Ask"}
            </Button>
          </form>

          <div style={{ marginTop: 16 }}>
            <ErrorState>{error}</ErrorState>
          </div>

          {loading && (
            <div className="answer-card">
              <div className="answer-head">
                <h3>Answer</h3>
              </div>
              <LoadingState lines={3} />
            </div>
          )}

          {!loading && result && (
            <div
              className={`answer-card ${result.abstained ? "abstain" : "grounded"}`}
            >
              <div className="answer-head">
                <h3>Answer</h3>
                <Badge tone="accent">{result.mode}</Badge>
                {result.abstained && <Badge tone="warn">abstained</Badge>}
                {!result.abstained && (
                  <Badge tone="success" dot>
                    {result.citations.length} cited
                  </Badge>
                )}
              </div>
              <p className={`answer-body ${result.abstained ? "dim" : ""}`}>
                {result.answer}
              </p>
            </div>
          )}
        </Card>

        <Card style={{ marginTop: 18 }}>
          <div className="section-title mt-0">
            <h2>History</h2>
          </div>
          {history.length === 0 ? (
            <p className="muted" style={{ fontSize: 13.5 }}>
              No questions yet for this document.
            </p>
          ) : (
            history.map((h) => (
              <div className="history-item" key={h.id}>
                <div className="history-q">{h.question}</div>
                <div className="history-a">
                  {h.answer}{" "}
                  {h.abstained && <Badge tone="warn">abstained</Badge>}
                </div>
              </div>
            ))
          )}
        </Card>
      </div>

      <EvidencePanel citations={result?.citations} loading={loading} />
    </div>
  );
}
