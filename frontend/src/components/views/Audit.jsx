import { useEffect, useState } from "react";
import { api } from "../../api";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { Select } from "../ui/Field";
import { EmptyState, ErrorState, LoadingState } from "../ui/States";
import MetricCard from "../MetricCard";
import { highlightMatch } from "../../lib/highlight";
import { IconAlert, IconCheck } from "../../lib/icons";

const AUDIT_TYPES = [
  { id: "invoice", label: "Invoice" },
  { id: "contract", label: "Contract" },
  { id: "payment_note", label: "Payment note" },
  { id: "general", label: "General" },
];

const RISK_TONE = { low: "success", medium: "warn", high: "danger" };
const SEV_TONE = { low: "neutral", medium: "warn", high: "danger" };

const titleize = (s) =>
  s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

// Evidence-backed audit dashboard. Picks a processed document + an audit type,
// runs the backend checklist, and renders the result as a B2B audit report:
// a risk badge, coverage metrics, and a finding per check (verified value with
// its citation, or a flagged missing field). Nothing here is generated — every
// supported claim carries the document excerpt it came from.
export default function Audit({ documents }) {
  const processed = documents.filter((d) => d.status === "processed");
  const [docId, setDocId] = useState("");
  const [auditType, setAuditType] = useState("invoice");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Default to the sample invoice when present, else the first processed doc.
  useEffect(() => {
    if (docId || processed.length === 0) return;
    const invoice = processed.find((d) => d.filename === "sample_invoice.txt");
    setDocId(String((invoice || processed[0]).id));
  }, [processed, docId]);

  // Clear a stale result whenever the selection changes, so the report on screen
  // always corresponds to the currently selected document + audit type (an audit
  // tool must never attribute citations to the wrong document).
  useEffect(() => {
    setData(null);
    setError("");
  }, [docId, auditType]);

  async function run() {
    if (!docId) return;
    setError("");
    setLoading(true);
    setData(null);
    try {
      setData(await api.audit(Number(docId), auditType));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (processed.length === 0) {
    return (
      <EmptyState title="No documents to audit">
        Head to <strong>Overview</strong> and click <strong>Try Demo</strong> (or
        upload a file), then come back to run an audit.
      </EmptyState>
    );
  }

  const m = data?.metrics;
  const pct = (v) => `${Math.round(v * 100)}%`;

  return (
    <div className="stack">
      <Card>
        <div className="audit-controls">
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
          <div>
            <span className="field-label">Audit type</span>
            <div className="audit-types" role="group" aria-label="Audit type">
              {AUDIT_TYPES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  aria-pressed={auditType === t.id}
                  className={`audit-type-btn ${auditType === t.id ? "active" : ""}`}
                  onClick={() => setAuditType(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="muted audit-tagline">
          FinanceFlow audits invoices, contracts, and payment notes for totals,
          due dates, payment terms, late fees, and unsupported claims — with
          citations you can verify.
        </p>

        <div style={{ marginTop: 16 }}>
          <Button variant="primary" onClick={run} loading={loading}>
            {loading ? "Auditing…" : data ? "Re-run audit" : "Run audit"}
          </Button>
        </div>
        <div style={{ marginTop: 12 }}>
          <ErrorState>{error}</ErrorState>
        </div>
      </Card>

      {loading && !data && (
        <Card>
          <LoadingState lines={4} label="Auditing document…" />
        </Card>
      )}

      {data && m && (
        <>
          <Card>
            <div className="audit-summary-head">
              <h2 style={{ margin: 0, fontSize: "var(--text-lg)" }}>Audit result</h2>
              <Badge tone={RISK_TONE[data.risk_level]} dot>
                {data.risk_level} risk
              </Badge>
            </div>
            <p className="audit-summary">{data.summary}</p>
            <div className="metric-grid">
              <MetricCard value={m.findings_count} label="Checks run" />
              <MetricCard value={m.supported_findings} label="Supported" tone="good" />
              <MetricCard
                value={m.unsupported_findings}
                label="Unsupported"
                tone={m.unsupported_findings === 0 ? "good" : "bad"}
                hint="Expected fields with no evidence."
              />
              <MetricCard value={pct(m.citation_coverage)} label="Citation coverage" />
            </div>
          </Card>

          <div>
            <div className="section-title">
              <h2>Findings</h2>
              <span className="muted">{data.findings.length} checks</span>
            </div>
            <div className="audit-findings">
              {data.findings.map((f, i) => {
                const supported = f.citation != null;
                return (
                  <div key={i} className={`finding ${supported ? "ok" : "miss"}`}>
                    <div className="finding-top">
                      <span className="finding-icon" aria-hidden>
                        {supported ? <IconCheck size={14} /> : <IconAlert size={14} />}
                      </span>
                      <span className="finding-type">{titleize(f.type)}</span>
                      {supported ? (
                        <Badge tone="success" dot>verified</Badge>
                      ) : (
                        <Badge tone={SEV_TONE[f.severity]} dot>
                          {f.severity}
                        </Badge>
                      )}
                    </div>
                    <div className="finding-claim">{f.claim}</div>
                    {supported && (
                      <div className="finding-evidence">
                        <div className="finding-evidence-label">
                          Evidence · {f.citation.document_name}
                          {f.citation.page != null ? ` · page ${f.citation.page}` : ""}
                        </div>
                        <div className="finding-excerpt">
                          {highlightMatch(f.evidence, f.citation.match_text)}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
