# Architecture — FinanceFlow AI

## System overview

A two-tier app: a React/Vite single-page frontend talks to a FastAPI backend over
a small REST/JSON API. The backend parses documents into chunks, ranks them with a
TF-IDF retriever, builds a grounded answer with citations, and persists everything
in SQLite. No external services are required to run it.

```mermaid
flowchart LR
    U[Browser - React/Vite] -->|/api JSON| API[FastAPI backend]
    API --> ING[Ingestion: parse -> chunk]
    API --> RET[Retrieval: TF-IDF rank]
    API --> ANS[Answering: abstain + extract + cite]
    ANS -. optional .-> LLM[(OpenAI / Anthropic)]
    ING --> DB[(SQLite)]
    RET --> DB
    API --> DB
```

In Docker, the frontend is served by nginx which proxies `/api` to the backend
container; in local dev, Vite proxies `/api` to `http://127.0.0.1:8000`.

## Backend modules (`backend/app/`)

| Module | Responsibility |
| ------ | -------------- |
| `main.py` | FastAPI app, all endpoints, CORS, logging setup, global exception handler |
| `config.py` | Env-driven settings with safe defaults (answer mode, thresholds, limits) |
| `database.py` | SQLAlchemy engine/session + SQLite `PRAGMA foreign_keys=ON` |
| `models.py` | ORM models: `Document`, `Chunk`, `QA` |
| `schemas.py` | Pydantic request/response models (typed I/O, Swagger) |
| `parsing.py` | Text extraction: TXT (whole file) and PDF (per page, via `pypdf`) |
| `chunking.py` | Overlapping word-window chunking |
| `retrieval.py` | Tokenizer + TF-IDF ranker (`rank_chunks`) — offline first stage |
| `reranking.py` | Optional cross-encoder reranking (FlashRank) of the TF-IDF candidates; graceful fallback to TF-IDF order when unavailable |
| `answering.py` | Abstention gates, focused extractive answer, citation builder |
| `llm.py` | Optional OpenAI/Anthropic synthesis with graceful fallback |
| `ingest.py` | Shared parse → chunk → persist pipeline |
| `evaluation.py` | Golden-dataset runner + metrics |
| `eval_cli.py` | `python -m app.eval_cli` |
| `reset_db.py` | `python -m app.reset_db` (drop + recreate) |
| `logging_config.py` | One-line logging setup |

## Frontend modules (`frontend/src/`)

| Area | Files |
| ---- | ----- |
| Shell | `App.jsx` (sidebar + view routing + demo orchestration) |
| Navigation | `components/Sidebar.jsx` |
| Views | `components/views/Overview.jsx`, `Ask.jsx`, `Evaluation.jsx` |
| Feature components | `DocumentCard.jsx`, `EvidencePanel.jsx`, `MetricCard.jsx`, `Upload.jsx` |
| UI primitives | `components/ui/Button.jsx`, `Card.jsx`, `Badge.jsx`, `Field.jsx`, `States.jsx` |
| Misc | `lib/icons.jsx`, `api.js`, `styles.css` |

## Database schema

```mermaid
erDiagram
    DOCUMENTS ||--o{ CHUNKS : has
    DOCUMENTS ||--o{ QA_HISTORY : has

    DOCUMENTS {
        int id PK
        string filename
        string file_type
        string status
        text error
        int num_chunks
        datetime created_at
    }
    CHUNKS {
        int id PK
        int document_id FK
        int chunk_index
        int page
        text text
    }
    QA_HISTORY {
        int id PK
        int document_id FK
        text question
        text answer
        int abstained
        text citations_json
        datetime created_at
    }
```

Deleting a `Document` cascades to its `Chunk` and `QA` rows (ORM cascade +
SQLite foreign-key pragma).

## Document processing flow

```mermaid
flowchart TD
    A[POST /documents/upload] --> B{Validate type + size}
    B -- invalid --> E[400 / 413 error]
    B -- ok --> C[Write to temp file]
    C --> D[parse: extract pages]
    D --> F[chunk: overlapping word windows]
    F --> G{Any chunks?}
    G -- no --> H[status = failed, error stored]
    G -- yes --> I[Store chunks, status = processed]
    C --> J[Delete temp file in finally]
```

The raw upload is parsed in a temp file and then discarded — only extracted
chunks are persisted.

## Retrieval flow

```mermaid
flowchart LR
    Q[Question] --> T[Tokenize - drop stopwords]
    C[Document chunks] --> IDF[Build IDF over chunks]
    T --> S[Score chunk = sum tf*idf]
    IDF --> S
    S --> N[Normalize by sqrt chunk length]
    N --> K[Take top-K above threshold]
```

## Ask → answer → citation flow

```mermaid
flowchart TD
    A[POST /ask] --> V{Document processed?}
    V -- no --> ERR[400/404]
    V -- yes --> R[rank_chunks top-K]
    R --> G1{score above threshold?}
    G1 -- no --> AB[Abstain message, no citations]
    G1 -- yes --> G2{at least 2 query terms matched?}
    G2 -- no --> AB
    G2 -- yes --> CIT[Build focused citations]
    CIT --> M{LLM mode + key?}
    M -- yes --> LLM[Synthesize from context, strict prompt]
    M -- no --> EX[Focused extractive span]
    LLM --> SAVE[Persist QA + return]
    EX --> SAVE
    AB --> SAVE
```

## Evaluation flow

```mermaid
flowchart LR
    GD[golden_dataset.json] --> SEED[Ensure sample docs ingested]
    SEED --> LOOP[For each question: answer_question]
    LOOP --> CLS{Expectation vs outcome}
    CLS --> MET[Metrics: coverage, abstentions, unsupported, evidence-match]
    MET --> OUT[UI cards + CLI report]
```

`unsupported_answer_count > 0` makes the CLI exit non-zero, so CI can gate on it.
