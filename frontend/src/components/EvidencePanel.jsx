import { useState } from "react";
import { IconChevron, IconQuote } from "../lib/icons";
import { EmptyState, LoadingState } from "./ui/States";

function EvidenceItem({ citation, rank, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen);
  const meta = [
    citation.page != null ? `page ${citation.page}` : null,
    `chunk #${citation.chunk_index}`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="evidence-item">
      <button className="evidence-item-head" onClick={() => setOpen((o) => !o)}>
        <span className="evidence-rank">{rank}</span>
        <span style={{ flex: 1, minWidth: 0 }}>
          <span className="evidence-doc">{citation.document_name}</span>
          <div className="evidence-meta">{meta}</div>
        </span>
        <span className={`chevron ${open ? "open" : ""}`}>
          <IconChevron />
        </span>
      </button>
      {open && (
        <div className="evidence-body">
          {citation.excerpt}
          <span className="evidence-score">relevance {citation.score}</span>
        </div>
      )}
    </div>
  );
}

export default function EvidencePanel({ citations, loading }) {
  return (
    <div className="evidence-panel">
      <div className="evidence-top">
        <h3>Evidence</h3>
        {citations?.length > 0 && (
          <span className="evidence-meta">{citations.length} sources</span>
        )}
      </div>
      <div className="evidence-list">
        {loading ? (
          <div style={{ padding: 8 }}>
            <LoadingState lines={4} />
          </div>
        ) : citations && citations.length > 0 ? (
          citations.map((c, i) => (
            <EvidenceItem
              key={i}
              citation={c}
              rank={i + 1}
              defaultOpen={i === 0}
            />
          ))
        ) : (
          <EmptyState title="No evidence yet" icon={<IconQuote />}>
            Ask a question — the source passages behind each answer appear here.
          </EmptyState>
        )}
      </div>
    </div>
  );
}
