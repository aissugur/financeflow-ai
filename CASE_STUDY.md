# Case Study — FinanceFlow AI

A concise product case study of why this exists, what was built, and what the
results were.

## Problem

Finance and operations teams answer the same small questions hundreds of times a
week — *"What's the total due? When is it overdue? What's the payment term? What's
the late-fee clause?"* — by opening a PDF and scanning for the number. It's slow,
repetitive, and error-prone. Dropping a general chatbot on top makes it worse: an
LLM will confidently produce a due date or dollar amount that isn't in the
document. In finance, a confidently wrong number is more dangerous than no answer.

## User pain

- **Time:** minutes per lookup, multiplied across invoices/contracts/notes.
- **Trust:** no way to see *where* an answer came from, so every AI answer has to
  be re-verified by hand — which defeats the point.
- **Risk:** hallucinated figures can flow into payments, reconciliations, or
  customer comms.

## Product hypothesis

If every answer is (a) built only from retrieved passages, (b) shown with the
exact source excerpt, and (c) **refused** when the evidence is weak, then a
finance user will trust the tool enough to use it for real lookups — because they
can verify each answer in one glance and know the system won't invent facts.

## MVP scope

Deliberately small and demoable:

- Upload PDF/TXT → parse → chunk → store.
- Ask a question against one document → retrieve top chunks → answer **only** from
  them → return citations (document, page/chunk, excerpt, score).
- Abstain with a fixed message when evidence is weak.
- Dashboard (status, chunk counts, history, delete) + one-click demo mode.
- A golden-dataset **evaluation** that scores grounding, not just accuracy.

Out of scope (on purpose): auth, multi-tenant storage, vector DB, OCR,
cross-document Q&A.

## Technical approach

- **Backend:** FastAPI + SQLite (SQLAlchemy). A single ingestion pipeline
  (parse → chunk → store) shared by uploads and the eval harness.
- **Chunking:** overlapping ~120-word windows (25-word overlap), page numbers
  preserved for PDFs.
- **Retrieval:** a custom TF-IDF keyword ranker (no ML dependency, fully offline)
  — rarer shared terms weigh more, normalized by chunk length.
- **Answering:** extractive by default — return the densest verbatim span,
  re-centered on the matched terms so a value next to its label
  (`Total Amount Due  $2,413.98`) is preserved. Optional LLM layer (OpenAI/
  Anthropic) behind env vars, with automatic fallback.
- **Anti-hallucination:** two abstention gates (score floor + term coverage),
  citations always shown, and `unsupported_answer_count` tracked in evaluation.

## Tradeoffs

| Decision | Why | Cost |
| -------- | --- | ---- |
| Keyword TF-IDF over embeddings | Zero deps, offline, transparent, fast to demo | Misses pure paraphrases |
| Extractive over generative default | Cannot invent a number not in the source | Phrasing is less fluent than an LLM |
| Discard raw files after parsing | Privacy + no orphaned-file cleanup | Can't re-process without re-upload |
| SQLite | One-file, zero setup for a reviewer | Not for concurrent production load |
| Abstain aggressively | Trust > coverage in finance | Occasionally refuses a borderline-answerable question |

## Evaluation method

A **golden dataset** (`backend/app/golden_dataset.json`) pairs each question with
its target document, expected behaviour (`answerable` / `should_abstain`), and the
evidence string that should be cited. The harness runs every question through the
real answer pipeline and reports: `answered_with_citation`, `correct_abstentions`,
`unsupported_answer_count`, `citation_coverage`, and `evidence_match_rate`.
Runnable from the UI **and** the CLI (`python -m app.eval_cli`); CI fails on any
unsupported answer.

## Results

- **7/7 golden questions pass**, `citation_coverage = 1.0`, `evidence_match_rate
  = 1.0`, **`unsupported_answer_count = 0`**, 2 correct abstentions.
- **20 backend tests** pass (unit + API via TestClient), green in CI.
- Runs fully offline with no API key; one-click demo seeds three sample documents.

## What I would build next

1. Swap the keyword ranker for sentence-embedding retrieval (FAISS / sqlite-vec)
   to handle paraphrased questions, and A/B it against the current ranker using
   the same golden dataset.
2. Exact answer-span highlighting inside the cited excerpt.
3. Cross-document Q&A and document collections.
4. Auth + per-tenant isolation; background processing + OCR for scanned PDFs.
5. Expand the golden set and add precision/recall on citations.

## Why this matters for AI workflow automation

This is the core loop behind most useful document AI: **ingest → retrieve →
answer → cite → evaluate**, with guardrails that make it safe to put in front of
a real team. The interesting work isn't calling a model — it's the retrieval
quality, the abstention policy, and the evaluation that proves the system stays
grounded. That's exactly the work of shipping trustworthy AI features in fintech
and operations.
