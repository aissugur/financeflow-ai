// MetricCard — big value + label + optional hint. tone: good | bad.
export default function MetricCard({ value, label, hint, tone }) {
  return (
    <div className="metric-card">
      <div className={`metric-value ${tone || ""}`}>{value}</div>
      <div className="metric-label">{label}</div>
      {hint && <div className="metric-hint">{hint}</div>}
    </div>
  );
}
