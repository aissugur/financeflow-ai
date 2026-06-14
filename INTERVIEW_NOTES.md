# Interview Notes — FinanceFlow AI

A plain-English walkthrough I can use to explain this project in interviews and
job applications.

## Why I built this

I wanted a portfolio project that proves I can ship **trustworthy AI for real
business workflows**, not just a chatbot demo. Finance is the perfect stress
test: numbers and dates have to be exactly right, so the system has to *ground*
every answer in a source and *refuse* to guess. It targets the skills fintech,
AI-workflow-automation, product-ops, and B2B-SaaS teams actually hire for:
retrieval, citations, evaluation, and graceful degradation.

It also runs **without any paid API key**, which shows I can build the core RAG
machinery myself instead of just calling someone else's model.

## How the backend works

- **FastAPI** exposes a small REST API (`/documents/upload`, `/ask`,
  `/evaluate`, etc.).
- **SQLite + SQLAlchemy** store three tables: `documents`, `chunks`, and
  `qa_history`.
- A single **ingestion pipeline** (`ingest.py`) handles parse → chunk → store,
  so uploads and the evaluation suite share one tested code path.
- Errors are handled defensively: a document that fails to parse is saved with
  `status="failed"` and an error message rather than crashing, so the dashboard
  can show it.

## How document chunking works

- Text is extracted **per page** for PDFs (so I can cite a page number) and as a
  single block for TXT files.
- Each page's text is normalized (whitespace collapsed) and split into
  **overlapping ~120-word windows with a 25-word overlap**. The overlap means a
  fact sitting on a chunk boundary still appears intact in at least one chunk.
- Every chunk is stored with `document_id`, `chunk_index`, `page`, and `text`.

## How retrieval works

- It's a **TF-IDF-style keyword ranker** — no external ML model, fully offline.
- At query time I compute an **IDF** weight for each term across the document's
  chunks (rare words count more, common words less).
- Each chunk gets a score = `Σ tf(term)·idf(term)` over the question's terms,
  divided by `√(chunk length)` so long chunks don't automatically win.
- The top-K chunks become the answer context. I call this "semantic-like"
  because IDF weighting approximates which words actually carry meaning.

## How citations work

- The chunks that survive the score threshold are returned as **citations**.
- Each citation carries the **document name, page/chunk index, a source excerpt,
  and the relevance score**, so a human can verify the answer in one glance.
- Citations are stored with the Q&A history too, so past answers stay auditable.

## How the app avoids hallucination

1. **Abstention gate** — if the best chunk score is below a threshold, it returns
   exactly *"Not enough information in the uploaded document."* and shows no
   answer.
2. **Extractive by default** — answers are assembled from the document's own
   sentences, so the engine can't fabricate a number that isn't present.
3. **Grounded LLM prompt (optional)** — if LLM mode is on, the prompt forbids
   inventing facts, requires the exact abstain phrase when unsupported, and runs
   at temperature 0. Any failure falls back to extractive mode.
4. **Evidence on screen** — every answer shows its sources.
5. **Evaluation** — a built-in suite tracks `unsupported_answer_count`,
   `answered_with_citation`, and `abstained_when_missing` so I can prove the
   behaviour and catch regressions.

## What I would improve next

- Replace keyword retrieval with **vector embeddings** for true semantic search.
- **Span highlighting** of the exact answer text inside the cited excerpt.
- **Multi-document** and cross-document questions.
- **Auth + multi-tenancy** to make it a real B2B SaaS.
- **OCR** for scanned PDFs and a **background queue** for large files.
- A larger, labeled **evaluation dataset** with precision/recall on citations.

## How this relates to AI product operations, fintech & document automation

- **AI product operations**: the evaluation page is the heart of it — defining
  expectations, measuring answered-with-citation vs. abstained-vs-unsupported,
  and treating "the model refused correctly" as a *success*. That's exactly how
  you operate an AI feature responsibly in production.
- **Fintech workflows**: invoices, contracts, and dunning notes are core finance
  artifacts. Extracting totals, due dates, and payment terms reliably — with an
  audit trail — is real back-office automation.
- **Document automation / B2B SaaS**: the upload → parse → retrieve → answer →
  cite loop is the same pattern behind contract analysis, support deflection,
  and knowledge assistants. I built it end to end with the guardrails that make
  it safe to ship.

## One-line pitch for applications

> "I built FinanceFlow AI, a full-stack RAG app (FastAPI + React) that answers
> questions about finance documents with citations and **refuses to hallucinate**
> — it runs offline with a custom TF-IDF retriever and ships with an evaluation
> harness that measures grounded-answer and abstention rates."
