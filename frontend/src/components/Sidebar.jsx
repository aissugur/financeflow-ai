import { IconAsk, IconEval, IconOverview, IconSpark } from "../lib/icons";

const NAV = [
  { id: "overview", label: "Overview", Icon: IconOverview },
  { id: "ask", label: "Ask", Icon: IconAsk },
  { id: "evaluation", label: "Evaluation", Icon: IconEval },
];

export default function Sidebar({ view, setView, online, llmAvailable }) {
  const status = online
    ? `API online · ${llmAvailable ? "Thinking ready" : "Fast mode"}`
    : "API offline";
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">
          <IconSpark size={17} />
        </span>
        <span className="brand-name brand-sub-hide">
          FinanceFlow <span>AI</span>
        </span>
      </div>

      <nav className="nav" aria-label="Primary">
        {NAV.map(({ id, label, Icon }) => (
          <button
            key={id}
            className={`nav-item ${view === id ? "active" : ""}`}
            onClick={() => setView(id)}
            aria-label={label}
            aria-current={view === id ? "page" : undefined}
          >
            <Icon />
            <span className="label">{label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-foot">
        <span
          className={`status-dot ${online ? "" : "off"}`}
          role="img"
          aria-label={online ? "API online" : "API offline"}
        />
        <span className="brand-sub-hide">{status}</span>
      </div>
    </aside>
  );
}
