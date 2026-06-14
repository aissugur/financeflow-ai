# FinanceFlow AI

![CI](https://github.com/your-username/financeflow-ai/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> Upload business finance documents (invoices, contracts, payment notes), ask
> questions in plain English, and get **source-backed answers with citations** —
> or a clear "Not enough information" when the document doesn't support an answer.

> **30-second tour:** start the app → **Dashboard → Load sample documents** →
> **Ask → click a sample question**. You'll see a grounded answer with a
> highlighted citation, and an unanswerable question correctly refused.

FinanceFlow AI is a compact, production-shaped **RAG (Retrieval-Augmented
Generation)** MVP built for fintech / AI-workflow / B2B-SaaS portfolios. It runs
**fully offline with no paid API key** using an extractive answer engine, and can
optionally call OpenAI or Anthropic for nicer phrasing.

---

## Problem statement

Finance and operations teams drown in documents: invoices, vendor contracts,
dunning notes, payment terms. Answering a simple question ("What's the total due?
When is it overdue? What's the contract's payment term?") means hunting through
PDFs by hand. Generic chatbots *hallucinate* numbers and dates — unacceptable in
finance, where a wrong figure has real consequences.

## Target users

- **Finance / AP / AR analysts** who answer recurring questions from invoices,
  contracts, and dunning notes.
- **Operations & RevOps teams** triaging vendor terms, due dates, and late fees.
- **Product / AI teams** that need a grounded, auditable Q&A pattern they can
  trust in front of customers.

## Why this project matters

- **Document automation** is one of the highest-value, most concrete uses of AI
  in fintech and B2B SaaS.
- It demonstrates **trustworthy AI**: every answer is grounded in retrieved
  evidence, and the system **abstains** instead of guessing.
- It mirrors real **AI product-operations** concerns: retrieval quality,
  citations, evaluation metrics, and graceful degradation without a paid model.

## Documentation

- [CASE_STUDY.md](CASE_STUDY.md) — product case study (problem → results)
- [ARCHITECTURE.md](ARCHITECTURE.md) — system design + diagrams
- [INTERVIEW_NOTES.md](INTERVIEW_NOTES.md) — direct answers to common questions
- [DEMO_SCRIPT.md](DEMO_SCRIPT.md) — 60-second demo walkthrough

---

## Features

- 📤 **Upload** PDF or TXT documents (validated, size-limited).
- 🧩 **Automatic parsing + chunking** with page numbers preserved for PDFs.
- 🔎 **Retrieval** via a TF-IDF-style keyword/semantic-like ranker (no model
  required).
- 💬 **Ask questions** and get an answer built **only** from retrieved context.
- 📎 **Citations** on every answer: document name, page/chunk, source excerpt,
  and relevance score.
- 🛑 **Anti-hallucination**: abstains ("Not enough information in the uploaded
  document.") when evidence is weak; never invents numbers/dates/names.
- 📊 **Dashboard**: document list, processed/failed status, chunk counts,
  Q&A history, delete, and a one-click **"Load sample documents"** demo mode.
- ✅ **Evaluation**: a **golden dataset** scored in the UI *and* from the CLI,
  reporting citation coverage, correct abstentions, and evidence-match rate.
- 🪵 **Logging** across ingestion, retrieval, ask, abstention, and evaluation,
  plus a global exception handler so a bad request never crashes the server.
- 🧪 **Tested**: 20 backend tests (pytest + FastAPI TestClient) and **CI** via
  GitHub Actions.
- 🐳 **Dockerized**: `docker compose up --build` runs backend + frontend.
- 🤖 **Optional LLM mode** (OpenAI/Anthropic) behind env vars, with automatic
  fallback to extractive mode.

---

## Tech stack

| Layer        | Choice                                  |
| ------------ | --------------------------------------- |
| Backend      | Python, FastAPI, Uvicorn                |
| Database     | SQLite via SQLAlchemy                   |
| Parsing      | `pypdf` (PDF), built-in reader (TXT)    |
| Retrieval    | Custom TF-IDF keyword ranker (no ML dep)|
| Frontend     | React + Vite                            |
| Styling      | Plain modern CSS                        |
| LLM (opt-in) | OpenAI or Anthropic via env vars        |

---

## Architecture overview

```
                 ┌──────────────────────────┐
  Browser  ───►  │  React + Vite frontend    │
                 │  Dashboard / Ask / Eval   │
                 └─────────────┬─────────────┘
                  /api proxy   │  REST/JSON
                 ┌─────────────▼─────────────┐
                 │      FastAPI backend       │
                 │  upload  ask  history ...  │
                 └───┬───────────┬────────────┘
        parse+chunk  │           │  retrieve + answer
                 ┌───▼───┐   ┌───▼──────────────┐
                 │ pypdf │   │ TF-IDF ranker +   │
                 │ /txt  │   │ extractive/LLM    │
                 └───┬───┘   └───┬──────────────┘
                     │           │
                 ┌───▼───────────▼───┐
                 │   SQLite (SQLAlchemy)
                 │ documents / chunks / qa_history
                 └────────────────────┘
```

**Backend modules** (`backend/app/`):

- `config.py` — env-driven settings, with safe defaults.
- `database.py` / `models.py` — SQLite + SQLAlchemy models
  (`Document`, `Chunk`, `QA`).
- `parsing.py` — extract text per page (PDF) or whole file (TXT).
- `chunking.py` — overlapping word-window chunking.
- `retrieval.py` — TF-IDF keyword ranking with stopwords + length normalization.
- `answering.py` — abstention logic + extractive answer + citation builder.
- `llm.py` — optional OpenAI/Anthropic synthesis (graceful fallback).
- `ingest.py` — shared parse→chunk→store pipeline.
- `evaluation.py` — the 5-question evaluation harness.
- `main.py` — FastAPI app and all endpoints.

---

## How RAG / retrieval works

1. **Ingest**: extracted text is normalized and split into overlapping
   ~120-word chunks (25-word overlap) so a fact on a boundary stays intact.
   Each chunk stores `document_id`, `chunk_index`, `page`, and `text`.
2. **Index at query time**: for the selected document, we compute an **IDF**
   weight per term across its chunks (rarer words matter more).
3. **Score**: each chunk is scored as `Σ tf(term)·idf(term)` over the question's
   terms, normalized by `√(chunk length)` so long chunks don't dominate.
4. **Select**: the top-K chunks become the context; below-threshold scores are
   dropped.
5. **Answer**: in extractive mode we return the densest verbatim word-window
   from the best chunk (re-centered on the matched terms so the value next to a
   label like "Total Amount Due  $2,413.98" is kept); in LLM mode we pass the
   same context to the model with a strict, grounding-only prompt.

## How hallucination is reduced

- **Two abstention gates** that return *"Not enough information in the uploaded
  document."* and show no answer:
  1. **Score floor** — the best chunk must clear `SCORE_THRESHOLD`.
  2. **Term coverage** — the evidence must share at least two distinct content
     words with the question, so a single incidental overlap (e.g. asking for a
     "social security number" and matching only the word "number") can't produce
     a confident answer.
- **Extractive by default**: answers are copied verbatim from the document — the
  engine literally cannot invent a number that isn't there.
- **Grounded LLM prompt** (when enabled): system prompt forbids inventing facts
  and requires the exact abstain string when context is insufficient;
  temperature is 0.
- **Evidence always shown**: every answer displays its citations so a human can
  verify instantly.
- **Evaluation metrics** track `unsupported_answer_count` to catch regressions.

> **Privacy note:** raw uploads are parsed into chunks and then discarded — the
> app stores extracted text, never the original file. There are no orphaned
> documents on disk to manage or leak.

---

## Project structure

```
financeflow-ai/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            # FastAPI app + endpoints (tagged Swagger docs)
│  │  ├─ config.py          # env-driven settings, safe defaults
│  │  ├─ database.py        # SQLAlchemy engine + SQLite FK pragma
│  │  ├─ models.py          # Document, Chunk, QA tables
│  │  ├─ schemas.py         # Pydantic request/response models
│  │  ├─ parsing.py         # PDF (pypdf) + TXT extraction
│  │  ├─ chunking.py        # overlapping word-window chunking
│  │  ├─ retrieval.py       # TF-IDF keyword ranker (no ML dep)
│  │  ├─ answering.py       # abstention gates + focused extractive answer
│  │  ├─ llm.py             # optional OpenAI/Anthropic synthesis
│  │  ├─ ingest.py          # shared parse→chunk→store pipeline
│  │  ├─ evaluation.py      # golden-dataset eval + metrics
│  │  ├─ eval_cli.py        # `python -m app.eval_cli`
│  │  ├─ golden_dataset.json# questions + expected evidence/abstentions
│  │  └─ logging_config.py  # one-line logging setup
│  ├─ tests/                # pytest unit + API tests (20 cases)
│  ├─ Dockerfile
│  ├─ requirements.txt / requirements-dev.txt
│  └─ .env.example
├─ frontend/                # React + Vite (Dashboard / Ask / Evaluation)
│  ├─ src/components/        # Dashboard, AskPanel, Evaluation, Citations
│  ├─ Dockerfile + nginx.conf
│  └─ vite.config.js
├─ sample_docs/             # fictional invoice, contract, payment note
├─ docker-compose.yml
├─ Makefile
└─ .github/workflows/ci.yml
```

---

## Local setup

### Prerequisites
- Python 3.10+ (3.12 recommended)
- Node.js 18+

### Option A — Docker (one command)
```bash
docker compose up --build
```
Open **http://localhost:5173**. The frontend (nginx) proxies `/api` to the
backend container. Stop with `docker compose down`.

### Option B — Run locally

**1) Backend**
```bash
cd backend
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS/Linux:           source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend runs at **http://127.0.0.1:8000** (interactive Swagger docs at `/docs`).

> Optional: copy `.env.example` to `.env` and set `ANSWER_MODE=llm` plus a key
> to enable LLM answers. Leave it as-is to run fully offline.

**2) Frontend** (second terminal)
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at **http://localhost:5173** and proxies `/api` to the backend.

Then: **Dashboard → Load sample documents → Ask → click a sample question.**

### Make shortcuts
```bash
make install      # install backend (dev) + frontend deps
make backend      # run the API
make frontend     # run the UI
make test         # run the backend tests
make eval         # run the anti-hallucination evaluation (CLI)
make reset-db     # drop + recreate the local database (clean slate)
make docker-up    # build + run everything in Docker
```

> No `make`? Run the underlying command directly, e.g. reset the DB with
> `cd backend && python -m app.reset_db`.

---

## API documentation summary

| Method | Path                      | Description                              |
| ------ | ------------------------- | ---------------------------------------- |
| GET    | `/health`                 | Health + current answer mode             |
| POST   | `/documents/upload`       | Upload PDF/TXT (multipart `file`)        |
| GET    | `/documents`              | List all documents                       |
| GET    | `/documents/{id}`         | Get one document's metadata              |
| DELETE | `/documents/{id}`         | Delete a document (+ chunks & history)   |
| POST   | `/ask`                    | `{document_id, question}` → answer+cites |
| GET    | `/history?document_id=`   | Past Q&A (optionally filtered)           |
| POST   | `/evaluate`               | Run the golden-dataset evaluation        |
| POST   | `/demo/seed`              | Load the bundled sample documents        |

Full interactive docs (with request/response schemas) are auto-generated by
FastAPI at **`/docs`**.

Example:
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"document_id":1,"question":"What is the total amount due?"}'
```

---

## Testing & evaluation

**Unit + API tests** (pytest + FastAPI TestClient, no running server needed):
```bash
cd backend
pip install -r requirements-dev.txt
pytest                      # 20 tests: chunking, retrieval, abstention, API, eval
```
Coverage includes bad file types, empty files, missing documents, weak context,
unsupported questions, the full upload→ask→delete flow, and the evaluation suite.
CI runs these on every push (`.github/workflows/ci.yml`).

**Anti-hallucination evaluation** against the golden dataset
(`backend/app/golden_dataset.json` — questions paired with expected evidence and
expected abstentions). Run it from the UI (**Evaluation → Run evaluation**) or the
CLI:
```bash
cd backend
python -m app.eval_cli
```
Reported metrics:

| Metric | Meaning |
| ------ | ------- |
| `total_questions` | size of the golden set |
| `answered_with_citation` | answerable questions answered *with* a citation |
| `correct_abstentions` | unanswerable questions correctly refused |
| `unsupported_answer_count` | answers without evidence (should be **0**) |
| `citation_coverage` | cited answers / answerable questions |
| `evidence_match_rate` | expected evidence actually surfaced in the citation |

Current result: **7/7 passed, citation_coverage 1.0, evidence_match_rate 1.0,
0 unsupported answers.**

> A dependency-free `backend/e2e_test.py` also exercises the live HTTP API end to
> end if you prefer a black-box smoke test.

---

## Screenshots

> Premium dark-first UI. Create a `docs/` folder and drop in real screenshots
> before sharing, then the links below will render.

- `docs/screenshot-overview.png` — landing/overview: hero pitch, trust badges, documents
- `docs/screenshot-ask.png` — Ask workspace: answer card + right-hand evidence panel
- `docs/screenshot-evaluation.png` — evaluation metric cards + pass/fail table

---

## Demo script (1-minute Loom)

1. **(0:00–0:10)** "This is FinanceFlow AI — it answers questions about finance
   documents with citations, and refuses to guess." Show the dashboard.
2. **(0:10–0:20)** Click **Load sample documents** — three docs appear as
   *processed* with chunk counts.
3. **(0:20–0:40)** Go to **Ask**, click the *"What is the total amount due?"*
   chip — show the answer **and the highlighted citation** underneath.
4. **(0:40–0:50)** Ask *"What is the customer's social security number?"* — show
   it **abstains** with "Not enough information…". This is the anti-hallucination
   story.
5. **(0:50–1:00)** Open **Evaluation**, click **Run evaluation**, show
   citation_coverage 100%, correct abstentions, and 0 unsupported answers. Done.

---

## What this project demonstrates (for reviewers)

| Skill area | Where to look |
| ---------- | ------------- |
| **Backend / API design** | FastAPI with validation, tagged Swagger docs, typed Pydantic I/O, SQLAlchemy models, a global exception handler — `backend/app/main.py` |
| **AI / RAG engineering** | Chunking, TF-IDF retrieval, focused extractive answers, optional LLM layer — `retrieval.py`, `answering.py` |
| **Trustworthy AI / AI product ops** | Two abstention gates, citation-backed answers, and a **golden-dataset evaluation** with coverage/abstention/evidence metrics — `answering.py`, `evaluation.py` |
| **Testing & CI** | 20 pytest cases (unit + API) + GitHub Actions — `backend/tests/`, `.github/workflows/ci.yml` |
| **DevOps / DX** | Dockerfiles, `docker-compose.yml`, `Makefile`, `.env.example`, logging |
| **Product / UX** | Clean B2B dashboard, demo mode, sample-question chips, empty/loading/error/success states — `frontend/src/` |

**Role relevance:** the evaluation harness and abstention behaviour map directly
to **AI Product / Product Operations** work (defining quality, measuring grounded
vs. refused answers); the retrieval + API + tests map to **Backend/ML**; the
upload→retrieve→answer→cite loop is the core of **AI workflow / document
automation**.

---

## Future improvements

- Swap the keyword ranker for vector embeddings (e.g. `sentence-transformers`)
  with a FAISS/SQLite-vec index for semantic recall.
- Cross-document Q&A and multi-document collections.
- Highlight the exact answer span inside the cited excerpt.
- User accounts + per-tenant isolation for real B2B SaaS.
- Background processing queue for large PDFs; OCR for scanned documents.
- Confidence calibration and a human-in-the-loop review queue.

---

## License

MIT — sample documents are fictional and safe to publish.
