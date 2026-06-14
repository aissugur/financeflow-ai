# Interview Notes — FinanceFlow AI

Direct, honest answers I can give in an interview. No hype.

### Why did you build this?
I wanted a portfolio project that proves I can ship **trustworthy AI for a real
business workflow**, not another chatbot wrapper. Finance is a good forcing
function: numbers and dates have to be exactly right, so the system has to ground
every answer and refuse to guess. It also runs with no paid API key, which forced
me to build the actual RAG machinery instead of leaning on a model.

### What problem does it solve?
Finance/ops teams repeatedly look up the same facts in invoices, contracts, and
payment notes (totals, due dates, payment terms, late fees). It's slow by hand and
unsafe with a generic chatbot that hallucinates figures. FinanceFlow answers from
the document, shows the source, and abstains when the evidence isn't there.

### Why FastAPI?
Typed request/response models via Pydantic, automatic OpenAPI/Swagger docs,
first-class async, and dependency injection for the DB session. It let me build a
small, well-validated API quickly and get interactive docs at `/docs` for free —
which is also how I test endpoints manually.

### Why React?
The UI needed real interactive state (upload status, async retrieval, a
collapsible evidence panel, an evaluation table). React + Vite gives fast HMR, a
clean component model, and a tiny build. I kept it dependency-light (no UI kit) and
wrote a small reusable component system instead.

### How does document chunking work?
Text is extracted per page for PDFs (so I can cite a page number) and as one block
for TXT. Each page is normalized and split into **overlapping ~120-word windows
with a 25-word overlap**. The overlap means a fact sitting on a chunk boundary
still appears intact in at least one chunk. Each chunk stores `document_id`,
`chunk_index`, `page`, and `text`.

### How does retrieval work?
A **TF-IDF keyword ranker** — no external model. At query time I compute an IDF
weight per term across the document's chunks (rare words count more). Each chunk is
scored as `Σ tf(term)·idf(term)` over the question's terms, divided by
`√(chunk length)` so long chunks don't automatically win. I take the top-K chunks
above a threshold as the context.

### How do citations work?
The chunks that survive the threshold become citations, each carrying the document
name, page/chunk index, a **query-focused excerpt** (the relevant span, not the
chunk's opening), and the relevance score. They're shown under every answer and
stored with the Q&A history, so past answers stay auditable.

### How do you reduce hallucinations?
Five things working together:
1. **Two abstention gates** — a score floor, plus a term-coverage check (the
   evidence must share ≥2 distinct content words with the question, so a single
   incidental overlap can't trigger a confident answer).
2. **Extractive by default** — answers are copied verbatim from the document, so
   the engine literally cannot invent a number.
3. **Grounded LLM prompt** (when LLM mode is on) — forbids inventing facts,
   requires the exact abstain string, temperature 0, with fallback to extractive.
4. **Evidence always shown** — the user can verify instantly.
5. **Evaluation** — `unsupported_answer_count` is tracked and gated in CI.

### What happens when the answer is not in the document?
It returns exactly: **"Not enough information in the uploaded document."** with no
citations, and the UI shows an "abstained" state. In evaluation, a correct
abstention counts as a *pass*; answering anyway counts as an unsupported answer
(a failure).

### How would you improve it with more time?
Swap the keyword ranker for sentence embeddings + a vector index to handle
paraphrases (and A/B it against the current ranker on the same golden dataset),
add exact answer-span highlighting, cross-document Q&A, auth/multi-tenancy, and OCR
for scanned PDFs.

### What technical tradeoffs did you make?
Keyword TF-IDF over embeddings (zero deps + transparency, at the cost of paraphrase
recall); extractive over generative by default (no hallucinations, less fluent
phrasing); discarding raw files after parsing (privacy + no cleanup, can't
re-process); SQLite (zero-setup for a reviewer, not for production concurrency);
and abstaining aggressively (trust over coverage).

### How is this relevant to AI Product / Product Ops / FinTech / Backend roles?
- **AI Product / Product Ops:** the evaluation harness *is* the product-ops work —
  defining expected behaviour, measuring grounded-vs-refused vs unsupported, and
  treating a correct refusal as success. That's how you operate an AI feature
  responsibly.
- **FinTech / document automation:** invoices, contracts, and dunning notes are
  core finance artifacts; reliable extraction with an audit trail is real back-
  office automation.
- **Backend / ML:** a validated, typed, tested FastAPI service with a retrieval
  pipeline, logging, CI, and Docker — the end-to-end engineering, not just a model
  call.
