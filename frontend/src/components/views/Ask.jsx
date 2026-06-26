import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { Select, Textarea } from "../ui/Field";
import { EmptyState, LoadingState } from "../ui/States";
import EvidencePanel from "../EvidencePanel";
import EvidenceReport from "../EvidenceReport";

// Map a 0..1 confidence to a tone bucket. Green when we're confident, amber in
// the murky middle, danger when the evidence barely cleared the gate.
function confidenceTone(c) {
  if (typeof c !== "number") return "neutral";
  if (c > 0.7) return "success";
  if (c >= 0.4) return "warn";
  return "danger";
}

// Small confidence bar + numeric % next to the answer. Reads metadata.confidence
// (0..1) and metadata.evidence_status from the CONTRACT. Degrades to nothing
// when metadata is absent (older responses).
function ConfidenceMeter({ metadata, abstained }) {
  if (!metadata || typeof metadata.confidence !== "number") return null;
  const c = Math.max(0, Math.min(1, metadata.confidence));
  const tone = confidenceTone(c);
  const grounded = metadata.evidence_status === "supported" && !abstained;
  const pct = Math.round(c * 100);

  return (
    <div className="confidence" aria-label={`Confidence ${pct} percent`}>
      <div className="confidence-row">
        <span className={`conf-status conf-status--${grounded ? "ok" : "weak"}`}>
          <span className="dot" aria-hidden />
          {grounded ? "grounded" : "not enough info"}
        </span>
        <span className="conf-pct">{pct}%</span>
      </div>
      <div
        className="conf-track"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Answer confidence"
      >
        <span className={`conf-fill conf-fill--${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const DEMO = [
  { q: "What is the total amount due?", doc: "sample_invoice.txt", hint: "Strong cited answer" },
  { q: "What are the payment terms and late fees?", doc: "sample_invoice.txt", hint: "Multiple evidence chunks" },
  { q: "What is the customer's social security number?", doc: "sample_invoice.txt", hint: "Correctly abstains" },
];

export default function Ask({ documents, demoSignal, llmAvailable, onDemoConsumed }) {
  const processed = documents.filter((d) => d.status === "processed");
  const [docId, setDocId] = useState("");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("fast"); // "fast" (extractive) | "thinking" (LLM)
  const [report, setReport] = useState(null); // { result, question } while printing
  const lastDemo = useRef(0);

  // Thinking needs a provider API key. If the backend reports none, don't let the
  // UI sit on a mode that would silently fall back to Fast — switch back to Fast.
  useEffect(() => {
    if (llmAvailable === false && mode === "thinking") setMode("fast");
  }, [llmAvailable, mode]);

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
      const res = await api.ask(Number(id), q.trim(), mode);
      setResult({ ...res, requestedMode: mode, askedQuestion: q.trim() });
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

          <span className="field-label">Answer mode</span>
          <div className="segmented" role="tablist" aria-label="Answer mode">
            <button
              type="button"
              className={mode === "fast" ? "seg active" : "seg"}
              aria-pressed={mode === "fast"}
              onClick={() => setMode("fast")}
            >
              ⚡ Fast
              <small>Instant · grounded snippet</small>
            </button>
            <button
              type="button"
              className={mode === "thinking" ? "seg active" : "seg"}
              aria-pressed={mode === "thinking"}
              disabled={llmAvailable === false}
              onClick={() => setMode("thinking")}
              title={
                llmAvailable === false
                  ? "Add a provider API key to enable Thinking mode"
                  : undefined
              }
            >
              🧠 Thinking
              <small>
                {llmAvailable === false ? "Needs API key" : "LLM reasons · grounded"}
              </small>
            </button>
          </div>
          {llmAvailable === false && (
            <p className="seg-note">
              Thinking mode needs a provider API key — running in Fast mode.
            </p>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(docId, question);
            }}
          >
            <Textarea
              label="Your question"
              id="ask-question"
              rows={3}
              placeholder="e.g. What is the total amount due?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              error={error || undefined}
            />
            <Button variant="primary" type="submit" loading={loading} disabled={!question.trim()}>
              {loading ? (mode === "thinking" ? "Thinking…" : "Retrieving…") : "Ask"}
            </Button>
          </form>

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
                <button
                  type="button"
                  className="report-btn"
                  onClick={() =>
                    setReport((prev) => ({
                      result,
                      question: result.askedQuestion || question,
                      key: (prev?.key || 0) + 1,
                    }))
                  }
                  title="Export a printable evidence report"
                >
                  ⤓ Export report
                </button>
              </div>
              <ConfidenceMeter
                metadata={result.metadata}
                abstained={result.abstained}
              />
              <p className={`answer-body ${result.abstained ? "dim" : ""}`}>
                {result.answer}
              </p>
              {result.metadata && (
                <dl className="ask-meta">
                  <div className="ask-meta-row">
                    <dt className="ask-meta-k">Question type</dt>
                    <dd className="ask-meta-v">
                      {typeof result.metadata.question_type === "string"
                        ? result.metadata.question_type.replace(/_/g, " ")
                        : "—"}
                    </dd>
                  </div>
                  <div className="ask-meta-row">
                    <dt className="ask-meta-k">Evidence</dt>
                    <dd className="ask-meta-v">
                      {result.metadata.evidence_status ?? "—"}
                    </dd>
                  </div>
                  <div className="ask-meta-row">
                    <dt className="ask-meta-k">Confidence</dt>
                    <dd className="ask-meta-v">
                      {typeof result.metadata.confidence === "number"
                        ? `${Math.round(result.metadata.confidence * 100)}%`
                        : "—"}
                    </dd>
                  </div>
                  <div className="ask-meta-row">
                    <dt className="ask-meta-k">Retrieved / cited</dt>
                    <dd className="ask-meta-v">
                      {result.metadata.retrieved_chunks ?? "—"} /{" "}
                      {result.metadata.cited_chunks ?? "—"}
                    </dd>
                  </div>
                  <div className="ask-meta-row">
                    <dt className="ask-meta-k">Latency</dt>
                    <dd className="ask-meta-v">
                      {typeof result.metadata.latency_ms === "number"
                        ? `${result.metadata.latency_ms} ms`
                        : "—"}
                    </dd>
                  </div>
                </dl>
              )}
              {result.requestedMode === "thinking" && result.mode === "fast" && (
                <p className="seg-note" style={{ margin: "10px 0 0" }}>
                  Thinking was unavailable for this request — answered with Fast.
                </p>
              )}
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

      {report && (
        <EvidenceReport
          key={report.key}
          result={report.result}
          question={report.question}
          onClose={() => setReport(null)}
        />
      )}
    </div>
  );
}
