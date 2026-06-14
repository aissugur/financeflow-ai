# Recruiter Checklist

A self-audit of whether this repo passes a recruiter / technical screen.

| Check | Status | Notes |
| ----- | ------ | ----- |
| Can a recruiter run it? | ✅ | `docker compose up --build` (one command) **or** local backend + frontend; both documented in the README. |
| Is the README clear in 30s? | ✅ | Badges, one-line pitch, 30-second tour, target users, and a docs index up top. |
| Is demo mode working? | ✅ | "Try Demo" seeds 3 sample docs and auto-runs a cited answer; verified end to end. |
| Are screenshots included? | ⚠️ | Placeholders + capture instructions in README. **You must add 3 real PNGs to `docs/`.** |
| Are tests passing? | ✅ | 20 backend tests (unit + API) pass; CI workflow runs them on push. |
| Is the value obvious? | ✅ | Source-backed answers + abstention + evaluation are front-and-center, not buried. |
| Relevant to target roles? | ✅ | Maps to AI Product, Product Ops, AI Workflow, Backend, and ML/LLM (see `CV_BULLETS.md`). |
| Secrets / junk removed? | ✅ | No keys; `.env.example` only; debug/scratch files removed; unrelated files gitignored. |
| Docs match real behavior? | ✅ | All metrics in docs come from the actual eval run (7/7, coverage 1.0, 0 unsupported). |

## What could still look weak (be honest about it)

- **Retrieval is keyword/TF-IDF, not embeddings** — strong on these docs, but a
  heavily paraphrased question can miss. (Named as the #1 next step.)
- **No real screenshots yet** — the single most important gap; add them before
  sharing the link anywhere.
- **No auth / multi-tenancy** — fine for a portfolio MVP, not production SaaS.
- **Small golden dataset (7 questions)** — credible but not large; expanding it
  (with precision/recall on citations) would strengthen the eval story.
- **SQLite + single-process** — intentionally simple; mention the production path
  if asked.

## Before you share the link
1. Add `docs/screenshot-overview.png`, `screenshot-ask.png`, `screenshot-evaluation.png`.
2. Push to GitHub; update the CI badge URL and `your-username` placeholders in the README.
3. Record the 60-second Loom (see `DEMO_SCRIPT.md`) and paste the link at the top of the README.
