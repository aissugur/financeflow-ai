import { useState } from "react";
import { api } from "../../api";
import { IconQuote, IconShield, IconSpark, IconEval } from "../../lib/icons";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { EmptyState, ErrorState, LoadingState, SuccessNote } from "../ui/States";
import DocumentCard from "../DocumentCard";
import Upload from "../Upload";

const TRUST = [
  {
    Icon: IconQuote,
    title: "Source-backed answers",
    text: "Every answer is built only from retrieved passages.",
  },
  {
    Icon: IconSpark,
    title: "Citation-first retrieval",
    text: "See the exact excerpts behind each response.",
  },
  {
    Icon: IconShield,
    title: "Abstains when unsure",
    text: "Refuses to guess when evidence is missing.",
  },
  {
    Icon: IconEval,
    title: "Evaluation included",
    text: "A golden-dataset suite measures answer quality.",
  },
];

export default function Overview({ documents, loading, reload, onTryDemo, seeding }) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function onFile(file) {
    setError("");
    setMessage("");
    setUploading(true);
    try {
      const doc = await api.uploadDocument(file);
      await reload();
      if (doc.status === "processed") {
        setMessage(`Uploaded "${doc.filename}" — ${doc.num_chunks} chunks ready.`);
      } else {
        setError(`"${doc.filename}" couldn't be processed: ${doc.error || "unknown error"}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function onDelete(doc) {
    if (!confirm(`Delete "${doc.filename}" and its history?`)) return;
    setError("");
    setMessage("");
    try {
      await api.deleteDocument(doc.id);
      await reload();
      setMessage(`Deleted "${doc.filename}".`);
    } catch (err) {
      setError(err.message);
    }
  }

  function scrollToUpload() {
    document.getElementById("upload-zone")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <div className="stack">
      <section className="hero">
        <span className="hero-eyebrow">
          <IconSpark size={14} /> Document intelligence
        </span>
        <h1 className="hero-title">Source-backed AI assistant for business documents.</h1>
        <p className="hero-sub">
          Upload an invoice, contract, or finance note, ask a question in plain
          English, and get an answer grounded in the document — with citations you
          can verify. If the evidence isn’t there, it says so instead of guessing.
        </p>
        <div className="hero-cta">
          <Button variant="primary" size="lg" loading={seeding} onClick={onTryDemo}>
            {seeding ? "Loading demo…" : "Try Demo"}
          </Button>
          <Button variant="ghost" size="lg" onClick={scrollToUpload}>
            Upload Document
          </Button>
        </div>
      </section>

      <div className="trust">
        {TRUST.map(({ Icon, title, text }) => (
          <div className="trust-item" key={title}>
            <Icon size={18} />
            <div>
              <h4>{title}</h4>
              <p>{text}</p>
            </div>
          </div>
        ))}
      </div>

      <div id="upload-zone">
        <div className="section-title">
          <h2>Add a document</h2>
          <span className="muted">PDF or TXT · 10 MB max</span>
        </div>
        <Upload onFile={onFile} uploading={uploading} />
      </div>

      {message && <SuccessNote>{message}</SuccessNote>}
      <ErrorState>{error}</ErrorState>

      <div>
        <div className="section-title">
          <h2>Your documents</h2>
          {documents.length > 0 && (
            <span className="muted">{documents.length} total</span>
          )}
        </div>
        {loading ? (
          <Card>
            <LoadingState lines={3} label="Loading documents…" />
          </Card>
        ) : documents.length === 0 ? (
          <EmptyState title="No documents yet">
            Click <strong>Try Demo</strong> to load sample finance documents, or
            drop your own file above.
          </EmptyState>
        ) : (
          <div className="doc-grid">
            {documents.map((d) => (
              <DocumentCard key={d.id} doc={d} onDelete={onDelete} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
