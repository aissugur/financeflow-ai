// Dependency-free results visualization: SVG donut (pass/fail) + labeled
// progress bars (citation coverage / evidence match). Color is never the sole
// signal — every value has a visible text label, and the chart is screen-reader
// described. Honors prefers-reduced-motion via styles.css.
export default function EvalChart({ metrics }) {
  const m = metrics;
  if (!m) return null;

  const total = m.total_questions || 0;
  const passed = m.passed || 0;
  const failed = Math.max(total - passed, 0);
  const passPct = total ? Math.round((passed / total) * 100) : 0;

  // Donut geometry
  const r = 54;
  const C = 2 * Math.PI * r;
  const passLen = total ? C * (passed / total) : 0;

  const bars = [
    {
      key: "coverage",
      label: "Citation coverage",
      value: m.citation_coverage,
      hint: "Cited answers / answerable questions",
    },
    {
      key: "evidence",
      label: "Evidence match",
      value: m.evidence_match_rate,
      hint: "Expected evidence found / answerable questions",
    },
  ];

  return (
    <div className="eval-viz">
      {/* Donut: pass / fail ratio */}
      <div className="eval-donut-block">
        <svg
          className="eval-donut"
          viewBox="0 0 140 140"
          role="img"
          aria-label={`${passed} of ${total} test questions passed (${passPct}%), ${failed} failed.`}
        >
          <circle
            cx="70" cy="70" r={r}
            fill="none" stroke="var(--danger)" strokeOpacity="0.32" strokeWidth="14"
          />
          <circle
            className="eval-donut-arc"
            cx="70" cy="70" r={r}
            fill="none" stroke="var(--success)" strokeWidth="14" strokeLinecap="round"
            strokeDasharray={`${passLen} ${C - passLen}`}
            strokeDashoffset={C * 0.25}
            transform="rotate(-90 70 70)"
            style={{ "--arc-c": C }}
          />
          <text x="70" y="66" className="eval-donut-num" textAnchor="middle">
            {passed}/{total}
          </text>
          <text x="70" y="86" className="eval-donut-cap" textAnchor="middle">
            passed
          </text>
        </svg>
        <ul className="eval-legend">
          <li>
            <span className="eval-swatch pass" aria-hidden="true" /> Passed{" "}
            <strong>{passed}</strong>
          </li>
          <li>
            <span className="eval-swatch fail" aria-hidden="true" /> Failed{" "}
            <strong>{failed}</strong>
          </li>
        </ul>
      </div>

      {/* Progress bars: coverage / evidence match */}
      <div className="eval-bars">
        {bars.map((b) => {
          const pct = Math.round((b.value || 0) * 100);
          return (
            <div className="eval-bar" key={b.key}>
              <div className="eval-bar-top">
                <span className="eval-bar-label">{b.label}</span>
                <span className="eval-bar-val">{pct}%</span>
              </div>
              <div
                className="eval-bar-track"
                role="progressbar"
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${b.label}: ${pct} percent`}
              >
                <div className="eval-bar-fill" style={{ width: `${pct}%` }} />
              </div>
              <div className="eval-bar-hint">{b.hint}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
