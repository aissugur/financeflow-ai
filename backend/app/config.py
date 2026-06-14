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
ANSWER_MODE = os.getenv("ANSWER_MODE", "extractive").strip().lower()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001").strip()

# Retrieval tuning.
TOP_K = int(os.getenv("TOP_K", "4"))
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.12"))

# Upload limits / validation.
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

ABSTAIN_MESSAGE = "Not enough information in the uploaded document."
