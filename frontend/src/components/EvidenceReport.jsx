// EvidenceReport — a clean, printable one-page summary of an answer and the
// evidence behind it. Rendered off-screen until the user triggers a print; we
// flip a class on <html> so a print-only stylesheet shows just the report.
// No new deps — window.print() does the work.
import { useEffect } from "react";
import { highlightMatch } from "../lib/highlight";

function fmtConfidence(c) {
  if (typeof c !== "number") return "—";
  return `${Math.round(c * 100)}%`;
}

// One printable evidence row. Mirrors EvidencePanel's metadata line + excerpt,
// but always expanded (a report shows everything) and ink-on-paper styled.
function ReportEvidence({ citation, rank }) {
  const meta = [
    citation.page != null ? `page ${citation.page}` : null,
    `chunk #${citation.chunk_index}`,
    citation.score != null ? `relevance ${citation.score}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="report-evidence">
      <div className="report-evidence-head">
        <span className="report-rank">{rank}</span>
        <span className="report-doc">{citation.document_name}</span>
        <span className="report-meta">{meta}</span>
      </div>
      <div className="report-excerpt">
        {highlightMatch(citation.excerpt, citation.match_text)}
      </div>
    </div>
  );
}

export default function EvidenceReport({ result, question, onClose }) {
  // Trigger the browser print dialog once mounted, then notify the parent so it
  // can drop the report from the tree. afterprint covers both "Print" and
  // "Cancel" so we never get stuck in the print-only view.
  useEffect(() => {
    if (!result) return;
    const root = document.documentElement;
    root.classList.add("printing-report");
    let finished = false;
    let fallback;
    // Runs exactly once: drop the print-only class and notify the parent so it
    // can unmount the report. Must ALWAYS fire (even if printing fails), or the
    // parent is left with a stuck report and a later re-export can't reopen.
    const done = () => {
      if (finished) return;
      finished = true;
      clearTimeout(fallback);
      window.removeEventListener("afterprint", done);
      root.classList.remove("printing-report");
      onClose?.();
    };
    window.addEventListener("afterprint", done);
    // Let the report paint before opening the dialog.
    const t = setTimeout(() => {
      try {
        window.print();
      } catch {
        done(); // print blocked/threw — don't leave the report stuck
        return;
      }
      // Safety net for environments where `afterprint` never fires (sandboxed
      // iframes / print-blocking browsers): clean up anyway.
      fallback = setTimeout(done, 3000);
    }, 60);
    return () => {
      clearTimeout(t);
      clearTimeout(fallback);
      window.removeEventListener("afterprint", done);
      root.classList.remove("printing-report");
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!result) return null;
  const citations = result.citations || [];
  const meta = result.metadata || {};
  const supported = meta.evidence_status === "supported" && !result.abstained;

  return (
    <div className="evidence-report" role="document" aria-label="Evidence report">
      <header className="report-header">
        <div>
          <div className="report-brand">FinanceFlow AI · Evidence Report</div>
          <div className="report-date">{new Date().toLocaleString()}</div>
        </div>
        <div className={`report-status ${supported ? "ok" : "weak"}`}>
          {supported ? "Grounded" : "Not enough info"}
        </div>
      </header>

      <section className="report-block">
        <h2 className="report-label">Question</h2>
        <p className="report-question">{question}</p>
      </section>

      <section className="report-block">
        <div className="report-answer-head">
          <h2 className="report-label">Answer</h2>
          <div className="report-conf">
            <span className="report-conf-num">{fmtConfidence(meta.confidence)}</span>
            <span className="report-conf-lbl">confidence</span>
          </div>
        </div>
        <p className="report-answer">{result.answer}</p>
        <div className="report-facts">
          <span>Mode: {result.mode || "—"}</span>
          <span>Sources cited: {citations.length}</span>
          {meta.question_type && <span>Type: {meta.question_type}</span>}
          {typeof meta.top_score === "number" && (
            <span>Top match: {meta.top_score}</span>
          )}
        </div>
      </section>

      <section className="report-block">
        <h2 className="report-label">
          Evidence{citations.length > 0 ? ` (${citations.length})` : ""}
        </h2>
        {citations.length > 0 ? (
          citations.map((c, i) => (
            <ReportEvidence key={i} citation={c} rank={i + 1} />
          ))
        ) : (
          <p className="report-noevidence">
            No supporting passages — the assistant abstained rather than guess.
          </p>
        )}
      </section>

      <footer className="report-footer">
        Generated by FinanceFlow AI — answers are grounded in the cited source
        passages above.
      </footer>
    </div>
  );
}
