import { useState } from "react";
import { api } from "../api";
import Citations from "./Citations";

export default function Evaluation() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setError("");
    setLoading(true);
    try {
      setData(await api.evaluate());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <div className="card">
        <h2>Evaluation</h2>
        <p className="muted">
          Runs 5 predefined questions against the bundled sample documents to
          check that the app answers with citations, abstains when information is
          missing, and never produces unsupported answers.
        </p>
        <button onClick={run} disabled={loading}>
          {loading ? "Running…" : "Run evaluation"}
        </button>
        {error && <p className="error">{error}</p>}
      </div>

      {data && (
        <>
          <div className="card metrics">
            <h3>Metrics</h3>
            <div className="metric-grid">
              <Metric
                label="Passed"
                value={`${data.metrics.passed}/${data.metrics.total_questions}`}
              />
              <Metric
                label="Answered w/ citation"
                value={data.metrics.answered_with_citation}
              />
              <Metric
                label="Correct abstentions"
                value={data.metrics.correct_abstentions}
              />
              <Metric
                label="Unsupported answers"
                value={data.metrics.unsupported_answer_count}
              />
              <Metric
                label="Citation coverage"
                value={`${Math.round(data.metrics.citation_coverage * 100)}%`}
              />
              <Metric
                label="Evidence match"
                value={`${Math.round(data.metrics.evidence_match_rate * 100)}%`}
              />
            </div>
          </div>

          <div className="card">
            <h3>Cases</h3>
            {data.cases.map((c, i) => (
              <div className="eval-case" key={i}>
                <div className="answer-head">
                  <span className={`status ${c.passed ? "processed" : "failed"}`}>
                    {c.passed ? "PASS" : "FAIL"}
                  </span>
                  <span className="badge">{c.document}</span>
                  <span className="muted">expects: {c.expectation}</span>
                  {c.expectation === "answerable" && (
                    <span className={`badge ${c.evidence_found ? "mode" : "warn"}`}>
                      {c.evidence_found ? "evidence ✓" : "evidence ✗"}
                    </span>
                  )}
                </div>
                <p className="q">Q: {c.question}</p>
                <p className="a">
                  A: {c.answer}{" "}
                  {c.abstained && <span className="badge warn">abstained</span>}
                </p>
                <Citations citations={c.citations} />
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
