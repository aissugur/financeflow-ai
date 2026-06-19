"""Central configuration loaded from environment variables.

Everything has a safe default so the app runs with zero setup.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env if present (optional).
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

# Where the SQLite DB lives. We deliberately do NOT keep raw uploaded files:
# uploads are parsed into chunks and then discarded, so there are no orphaned
# files to clean up and no raw documents sitting on disk.
DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "financeflow.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Path to the bundled sample documents (used by /evaluate).
SAMPLE_DOCS_DIR = BACKEND_DIR.parent / "sample_docs"

# Answer behaviour.
# Two request-time answer modes (chosen per /ask call, not globally):
#   "fast"     -> extractive engine: instant, offline, free (no API key needed).
#   "thinking" -> LLM reasons on the fly with adaptive thinking (needs an API
#                 key); automatically falls back to "fast" if no key is set.
DEFAULT_ANSWER_MODE = "fast"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

# Model used by "thinking" mode (reasons with adaptive thinking on Anthropic).
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o").strip()

# Optional OpenAI-compatible base URL. Set this to point the OpenAI client at any
# OpenAI-API-compatible provider (e.g. a free tier like Mistral, Cohere, LLM7) so
# "thinking" mode works without an OpenAI account. Empty = real OpenAI.
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()

# True if any provider key is configured (so "thinking" mode is actually usable).
LLM_AVAILABLE = bool(
    (LLM_PROVIDER == "anthropic" and ANTHROPIC_API_KEY)
    or (LLM_PROVIDER == "openai" and OPENAI_API_KEY)
)

# Retrieval tuning.
TOP_K = int(os.getenv("TOP_K", "4"))
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.12"))

# Upload limits / validation.
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

ABSTAIN_MESSAGE = "Not enough information in the uploaded document."
