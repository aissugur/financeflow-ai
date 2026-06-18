import { IconSpark } from "../../lib/icons";

// Self-contained, pure-CSS/SVG "Verified Answer" product mock. No props, no
// network — the animation (typewriter, highlight sweep, citation connector)
// is CSS-driven and self-runs on mount. Honors prefers-reduced-motion.
export default function HeroPreview() {
  return (
    <div className="preview-wrap">
      <div className="preview-card">
        <div className="preview-head">
          <span
            style={{
              width: 22,
              height: 22,
              borderRadius: 7,
              background: "var(--accent-grad)",
              display: "grid",
              placeItems: "center",
              flex: "none",
            }}
          >
            <IconSpark size={13} />
          </span>
          <span>FinanceFlow</span>
          <span className="status-dot" />
          <span className="on">online</span>
        </div>

        <div className="preview-q">
          What’s the total due and the payment deadline?
        </div>

        <div className="answer-card grounded" style={{ marginTop: 0 }}>
          <p className="preview-answer">
            The total due is{" "}
            <span className="type">
              <mark>$48,250.00</mark>, payable by Net 30 — Oct 14, 2025
            </span>
            <sup className="cite-chip">1</sup>
          </p>
        </div>

        <div className="preview-evidence">
          <div className="preview-evidence-head">
            <span className="evidence-rank">1</span>
            <span className="preview-evidence-doc">INVOICE-2207.pdf · p.1</span>
          </div>
          <div className="preview-evidence-line">
            Total Due: <mark>$48,250.00</mark> — Terms: Net 30 (due Oct 14, 2025)
          </div>
        </div>

        <svg
          className="connector"
          viewBox="0 0 60 200"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path d="M52 46 C 8 78, 8 132, 52 158" />
        </svg>
      </div>

      <div className="preview-card preview-peek" aria-hidden="true">
        <span className="badge badge--warn">abstained</span>
        <span style={{ fontSize: 13, color: "var(--text-dim)" }}>
          Not stated in this document.
        </span>
      </div>
    </div>
  );
}
