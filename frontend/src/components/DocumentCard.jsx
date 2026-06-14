import { IconDoc } from "../lib/icons";
import Badge from "./ui/Badge";
import Button from "./ui/Button";

export default function DocumentCard({ doc, onDelete }) {
  const processed = doc.status === "processed";
  return (
    <div className="doc-card">
      <div className="doc-card-head">
        <span className="doc-icon">
          <IconDoc />
        </span>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="doc-name">{doc.filename}</div>
          <div className="doc-sub">{doc.file_type.toUpperCase()}</div>
          {doc.error && <div className="doc-err">{doc.error}</div>}
        </div>
      </div>
      <div className="doc-foot">
        <div className="row" style={{ gap: 8 }}>
          <Badge tone={processed ? "success" : "danger"} dot>
            {doc.status}
          </Badge>
          {processed && (
            <span className="doc-sub">{doc.num_chunks} chunks</span>
          )}
        </div>
        <Button variant="danger" size="sm" onClick={() => onDelete(doc)}>
          Delete
        </Button>
      </div>
    </div>
  );
}
