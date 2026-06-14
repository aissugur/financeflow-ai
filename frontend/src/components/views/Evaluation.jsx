import { useState } from "react";
import { api } from "../../api";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { ErrorState, LoadingState } from "../ui/States";
import MetricCard from "../MetricCard";

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

  const m = data?.metrics;
  const pct = (v) => `${Math.round(v * 100)}%`;

  return (
    <div className="stack">
      <Card glass>
        <div className="section-title mt-0">
          <h2>Why evaluation matters</h2>
        </div>
        <p className="muted" style={{ fontSize: 14.5, lineHeight: 1.6, maxWidth: "70ch" }}>
          In finance, a confidently wrong number is worse than no answer. This suite
          runs a fixed <strong>golden dataset</strong> — questions paired with the
          evidence they should cite and the ones they should refuse — and scores the
          system on whether it stays grounded. A correct <em>abstention</em> counts
          as a success; an answer without evidence counts as a failure.
        </p>
        <div style={{ marginTop: 16 }}>
          <Button variant="primary" onClick={run} loading={loading}>
            {loading ? "Running…" : data ? "Re-run evaluation" : "Run evaluation"}
          </Button>
        </div>
        <div style={{ marginTop: 14 }}>
          <ErrorState>{error}</ErrorState>
        </div>
      </Card>

      {loading && !data && (
        <Card>
          <LoadingState lines={4} label="Scoring golden dataset…" />
        </Card>
      )}

      {m && (
        <>
          <div className="metric-grid">
            <MetricCard
              value={`${m.passed}/${m.total_questions}`}
              label="Passed"
              tone={m.passed === m.total_questions ? "good" : "bad"}
            />
            <MetricCard value={m.answered_with_citation} label="Answered with citation" />
            <MetricCard value={m.correct_abstentions} label="Correct abstentions" />
            <MetricCard
              value={m.unsupported_answer_count}
              label="Unsupported answers"
              tone={m.unsupported_answer_count === 0 ? "good" : "bad"}
              hint="Answers with no evidence. Target: 0."
            />
            <MetricCard value={pct(m.citation_coverage)} label="Citation coverage" />
            <MetricCard value={pct(m.evidence_match_rate)} label="Evidence match" />
          </div>

          <div>
            <div className="section-title">
              <h2>Test questions</h2>
              <span className="muted">{data.cases.length} cases</span>
            </div>
            <div className="eval-table">
              {data.cases.map((c, i) => (
                <div className="eval-row" key={i}>
                  <Badge tone={c.passed ? "success" : "danger"} dot>
                    {c.passed ? "PASS" : "FAIL"}
                  </Badge>
                  <div>
                    <div className="eval-q">{c.question}</div>
                    <div className="eval-meta">
                      <span>{c.document}</span>
                      <span>·</span>
                      <span>expects {c.expectation.replace("_", " ")}</span>
                    </div>
                  </div>
                  <div className="eval-badges">
                    {c.abstained ? (
                      <Badge tone="warn">abstained</Badge>
                    ) : (
                      <Badge tone="accent">{c.citations.length} cited</Badge>
                    )}
                    {c.expectation === "answerable" && (
                      <Badge tone={c.evidence_found ? "success" : "danger"}>
                        {c.evidence_found ? "evidence ✓" : "evidence ✗"}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
