# CV Bullets — FinanceFlow AI

Pick the set that matches the role. Each bullet = action + technical detail +
product/business value. Swap in a live demo/repo link where noted.

## AI Product Intern

- Built **FinanceFlow AI**, a source-grounded RAG assistant for finance documents
  (FastAPI + React), where every answer ships with citations and the system
  **abstains** when evidence is missing — turning an untrustworthy chatbot pattern
  into a verifiable one.
- Designed a **golden-dataset evaluation** (citation coverage, correct-abstention,
  and unsupported-answer metrics) that treats a correct refusal as success;
  achieved **100% citation coverage and 0 unsupported answers** across the suite.
- Defined the product's anti-hallucination policy (two retrieval-based abstention
  gates + always-on citations) so non-technical finance users can trust and verify
  each answer in one glance.

## Product Operations Intern

- Shipped an end-to-end document-Q&A workflow (upload → parse → retrieve → answer →
  cite → evaluate) that replaces manual PDF lookups for invoice/contract questions,
  with a one-click demo mode that makes it testable in under 60 seconds.
- Instrumented the system with **logging and a measurable evaluation harness**
  (runnable from UI and CLI, gated in CI) to track answer quality and catch
  regressions — the operational backbone for running an AI feature responsibly.
- Authored the product case study, architecture docs, and demo script, translating
  a technical build into a clear story of user pain, scope, tradeoffs, and results.

## Backend / AI Engineering Intern

- Built a typed, validated **FastAPI** service (9 endpoints, Pydantic models,
  SQLAlchemy/SQLite, global exception handler, file-type/size validation) with
  auto-generated Swagger docs and **20 passing tests** (unit + API) in GitHub
  Actions CI.
- Implemented a dependency-free **TF-IDF retrieval** pipeline (tokenization,
  IDF weighting, length-normalized scoring, overlapping chunking) plus a focused
  extractive answerer that returns verbatim spans with page/chunk citations.
- Containerized the stack (**Dockerfiles + docker-compose**, nginx-proxied
  frontend) and added an optional OpenAI/Anthropic layer behind env vars with
  automatic fallback, so the app runs fully offline or LLM-augmented.

> Tip: lead each role's CV with **bullet #1**, then #2. Keep #3 as depth.
