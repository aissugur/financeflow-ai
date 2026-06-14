// Renders the evidence (retrieved chunks) behind an answer.
export default function Citations({ citations }) {
  if (!citations || citations.length === 0) return null;
  return (
    <div className="citations">
      <h4>Evidence ({citations.length})</h4>
      {citations.map((c, i) => (
        <div className="citation" key={i}>
          <div className="citation-head">
            <span className="badge">{c.document_name}</span>
            <span className="muted">
              {c.page != null ? `page ${c.page} · ` : ""}chunk #{c.chunk_index} ·
              score {c.score}
            </span>
          </div>
          <blockquote>{c.excerpt}</blockquote>
        </div>
      ))}
    </div>
  );
}
