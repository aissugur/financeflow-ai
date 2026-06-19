import { useEffect, useState } from "react";
import { api } from "../../api";
import {
  IconAsk,
  IconCheck,
  IconDoc,
  IconEval,
  IconQuote,
  IconShield,
  IconSpark,
  IconUpload,
} from "../../lib/icons";
import { useScrollReveal } from "../../lib/useScrollReveal";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { EmptyState, ErrorState, LoadingState, SuccessNote } from "../ui/States";
import DocumentCard from "../DocumentCard";
import Upload from "../Upload";
import HeroPreview from "./HeroPreview";

const STEPS = [
  { Icon: IconUpload, t: "Upload", d: "Drop a PDF or TXT. We extract the text and split it into overlapping, page-tagged chunks." },
  { Icon: IconAsk, t: "Retrieve", d: "Your question ranks the most relevant passages with a transparent TF-IDF retriever." },
  { Icon: IconQuote, t: "Cite", d: "The answer is built only from those passages — and every claim shows its source." },
];

// Lightweight count-up for the stats band (rAF, ease-out cubic).
function CountUp({ end, suffix = "", duration = 1200 }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!end) return;
    let raf, start;
    const tick = (t) => {
      if (!start) start = t;
      const p = Math.min((t - start) / duration, 1);
      setV(Math.round((1 - Math.pow(1 - p, 3)) * end));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [end, duration]);
  return (
    <>
      {v}
      {suffix}
    </>
  );
}

export default function Overview({ documents, loading, reload, onTryDemo, seeding, onOpenEval }) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useScrollReveal([loading, documents.length]);

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
    document
      .getElementById("upload-zone")
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <div className="landing">
      {/* ---- Hero ---- */}
      <section className="hero-stage">
        <div>
          <span className="hero-eyebrow">
            <IconSpark size={14} /> Source-grounded answers
          </span>
          <h1 className="hero-h1">
            Answers you can <span className="clip">prove.</span>
          </h1>
          <p className="hero-sub">
            FinanceFlow reads your invoices, contracts, and payment notes and answers
            questions <strong>only</strong> from what's in the document — with citations
            you can verify. When the evidence isn't there, it says so instead of guessing.
          </p>
          <div className="hero-cta">
            <Button variant="primary" size="lg" loading={seeding} onClick={onTryDemo}>
              {seeding ? "Loading demo…" : "Try the live demo"}
            </Button>
            <Button variant="ghost" size="lg" onClick={scrollToUpload}>
              Upload a document
            </Button>
          </div>
          <div className="hero-trust-strip">
            <span>Grounded only</span>
            <span>Cites every line</span>
            <span>Abstains when unsure</span>
          </div>
        </div>
        <HeroPreview />
      </section>

      {/* ---- Works-with strip ---- */}
      <div className="logo-strip">
        <span className="ls-label">Reads your</span>
        <span className="ls-item"><IconDoc size={16} /> Invoices</span>
        <span className="ls-item"><IconDoc size={16} /> Contracts</span>
        <span className="ls-item"><IconDoc size={16} /> Statements</span>
        <span className="ls-item"><IconDoc size={16} /> Payment notes</span>
        <span className="ls-item"><IconDoc size={16} /> PDF &amp; TXT</span>
      </div>

      {/* ---- How it works ---- */}
      <section className="reveal" style={{ marginTop: 24 }}>
        <p className="eyebrow-mono">01 / <b>How it works</b></p>
        <div className="flow">
          {STEPS.map(({ Icon, t, d }, i) => (
            <Card key={t}>
              <div className="flow-num">{i + 1}</div>
              <Icon size={20} />
              <h3>{t}</h3>
              <p>{d}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* ---- Stats band ---- */}
      <section className="reveal" style={{ marginTop: 40 }}>
        <div className="stats-band">
          <div className="stat">
            <div className="stat-num"><CountUp end={100} suffix="%" /></div>
            <div className="stat-label">of answers carry a citation</div>
          </div>
          <div className="stat">
            <div className="stat-num">0</div>
            <div className="stat-label">unsupported / hallucinated answers</div>
          </div>
          <div className="stat">
            <div className="stat-num"><CountUp end={25} />/25</div>
            <div className="stat-label">automated tests passing in CI</div>
          </div>
        </div>
      </section>

      {/* ---- Why it's trustworthy (bento) ---- */}
      <section className="reveal" style={{ marginTop: 48 }}>
        <p className="eyebrow-mono">02 / <b>Why it's trustworthy</b></p>
        <div className="bento">
          <div className="bento-tile bento-cite">
            <IconQuote size={20} />
            <h3>Citation-first retrieval</h3>
            <p>Every answer shows the exact source excerpt, page, and relevance score — so you verify in one glance.</p>
            <div className="bento-rankviz">
              <div className="bento-rankbar" style={{ width: "100%" }} />
              <div className="bento-rankbar" style={{ width: "72%" }} />
              <div className="bento-rankbar" style={{ width: "48%" }} />
            </div>
          </div>
          <div className="bento-tile bento-abst">
            <IconShield size={20} />
            <h3>Abstains when unsure</h3>
            <p>Two retrieval gates. If the evidence is weak, it replies “Not enough information” instead of guessing.</p>
          </div>
          <div className="bento-tile bento-src">
            <IconSpark size={20} />
            <h3>Source-only answers</h3>
            <p>Extractive by default — it can't invent a number that isn't in your file.</p>
          </div>
          <div className="bento-tile bento-eval">
            <IconEval size={20} />
            <h3>Evaluation suite included</h3>
            <p>A golden dataset grades grounding on every run: 100% citation coverage, 0 unsupported answers.</p>
          </div>
        </div>
      </section>

      {/* ---- Evaluation teaser ---- */}
      <section className="reveal" style={{ marginTop: 48 }}>
        <div className="eval-teaser">
          <div>
            <h2>We grade ourselves.</h2>
            <p>
              Most AI demos ask you to trust them. FinanceFlow ships a golden-dataset
              evaluation that scores whether it stayed grounded — and counts a correct
              refusal as a success.
            </p>
            <Button variant="ghost" onClick={onOpenEval}>
              Open the evaluation
            </Button>
          </div>
          <div className="metric-grid" style={{ margin: 0, minWidth: 240 }}>
            <div className="metric-card">
              <div className="metric-value good">100%</div>
              <div className="metric-label">Citation coverage</div>
            </div>
            <div className="metric-card">
              <div className="metric-value good">0</div>
              <div className="metric-label">Unsupported answers</div>
            </div>
          </div>
        </div>
      </section>

      {/* ---- Proof band (dark) ---- */}
      <section className="proof-band">
        <div className="pb-head">
          <p className="eyebrow-mono" style={{ color: "rgba(234,241,251,0.6)" }}>
            <b style={{ color: "#fff" }}>Proof, not promises</b>
          </p>
          <h2>Trust you can check.</h2>
          <p className="pb-sub">
            FinanceFlow doesn’t ask you to trust it — it shows its work. Every answer
            links back to the exact source line, it abstains when the document doesn’t
            say, and a bundled evaluation grades that grounding on every run.
          </p>
        </div>

        <div className="pb-proof">
          <div className="pb-proof-item">
            <IconCheck size={20} />
            <div>
              <b>100%</b>
              <span className="pb-proof-label">of answers carry a citation</span>
            </div>
          </div>
          <div className="pb-proof-item">
            <IconCheck size={20} />
            <div>
              <b>0</b>
              <span className="pb-proof-label">unsupported / hallucinated answers</span>
            </div>
          </div>
          <div className="pb-proof-item">
            <IconCheck size={20} />
            <div>
              <b>25/25</b>
              <span className="pb-proof-label">automated tests passing</span>
            </div>
          </div>
        </div>
      </section>

      {/* ---- Upload + documents (functional) ---- */}
      <section id="upload-zone" className="reveal" style={{ marginTop: 56 }}>
        <p className="eyebrow-mono">03 / <b>Try it with your own files</b></p>
        <div className="section-title">
          <h2>Add a document</h2>
          <span className="muted">PDF or TXT · 10 MB max</span>
        </div>
        <Upload onFile={onFile} uploading={uploading} />

        {message && <div style={{ marginTop: 16 }}><SuccessNote>{message}</SuccessNote></div>}
        <div style={{ marginTop: 12 }}><ErrorState>{error}</ErrorState></div>

        <div style={{ marginTop: 28 }}>
          <div className="section-title">
            <h2>Your documents</h2>
            {documents.length > 0 && <span className="muted">{documents.length} total</span>}
          </div>
          {loading ? (
            <Card>
              <LoadingState lines={3} label="Loading documents…" />
            </Card>
          ) : documents.length === 0 ? (
            <EmptyState title="No documents yet">
              Click <strong>Try the live demo</strong> to load sample finance documents,
              or drop your own file above.
            </EmptyState>
          ) : (
            <div className="doc-grid">
              {documents.map((d) => (
                <DocumentCard key={d.id} doc={d} onDelete={onDelete} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ---- Final CTA ---- */}
      <section className="reveal final-cta">
        <h2>
          Stop trusting. <span className="clip">Start verifying.</span>
        </h2>
        <Button variant="primary" size="lg" loading={seeding} onClick={onTryDemo}>
          {seeding ? "Loading demo…" : "Try the live demo"}
        </Button>
      </section>

      {/* ---- Footer ---- */}
      <footer className="site-footer">
        <span className="foot-brand">
          <span
            style={{
              width: 22, height: 22, borderRadius: 7,
              background: "var(--accent-grad)", display: "inline-grid", placeItems: "center",
            }}
          >
            <IconSpark size={13} />
          </span>
          FinanceFlow AI
        </span>
        <span>Source-backed document intelligence.</span>
        <a href="https://github.com/aissugur/financeflow-ai" target="_blank" rel="noreferrer">
          GitHub ↗
        </a>
      </footer>
    </div>
  );
}
