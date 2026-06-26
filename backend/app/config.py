"""Central configuration loaded from environment variables.

Everything has a safe default so the app runs with zero setup.
"""
import logging
import os
import secrets
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

# Optional second-stage reranking (cross-encoder over the TF-IDF candidates).
# Pattern adapted from the hybrid-search RAG examples in awesome-llm-apps
# (Apache-2.0). It degrades gracefully to pure TF-IDF when flashrank or the model
# is unavailable, and the abstention DECISION always stays on the TF-IDF scores —
# reranking only reorders/selects the evidence that is cited and fed to the LLM.
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "1").strip().lower() not in {"0", "false", "no", ""}
RERANK_CANDIDATES = int(os.getenv("RERANK_CANDIDATES", "12"))  # TF-IDF pool to rerank
RERANK_MODEL = os.getenv("RERANK_MODEL", "ms-marco-TinyBERT-L-2-v2").strip()

# Optional dense (semantic) embeddings for HYBRID retrieval. We fuse the lexical
# TF-IDF ranking with a semantic vector ranking using Reciprocal Rank Fusion (RRF)
# so the candidate pool catches paraphrases that keyword search misses (e.g. a
# question worded differently from the document). Lightweight CPU/ONNX via
# fastembed — no torch. Degrades gracefully to pure TF-IDF when fastembed or the
# model is unavailable, so the app still runs with zero ML setup. The abstention
# DECISION still runs on the lexical TF-IDF gate, so grounding stays conservative.
EMBED_ENABLED = os.getenv("EMBED_ENABLED", "1").strip().lower() not in {"0", "false", "no", ""}
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5").strip()
HYBRID_RRF_K = int(os.getenv("HYBRID_RRF_K", "60"))  # RRF damping constant

# Upload limits / validation.
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

ABSTAIN_MESSAGE = "Not enough information in the uploaded document."

# --------------------------------------------------------------------------- #
# Authentication (JWT access tokens + bcrypt password hashing)
# --------------------------------------------------------------------------- #
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

# AUTH_SECRET_KEY signs the JWTs. It MUST come from the env for any real deploy.
# When unset we NEVER fall back to a shared constant (that would let anyone forge
# tokens): in production we hard-fail, and in dev we mint a random EPHEMERAL key
# (tokens just reset on restart). So a default deploy can't run on a public secret.
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "").strip()
if not AUTH_SECRET_KEY:
    if ENVIRONMENT == "production":
        raise RuntimeError(
            "AUTH_SECRET_KEY must be set when ENVIRONMENT=production "
            "(generate one with: python -c \"import secrets;print(secrets.token_urlsafe(64))\")."
        )
    AUTH_SECRET_KEY = secrets.token_urlsafe(64)  # random per-process; NOT a constant
    logging.getLogger(__name__).warning(
        "AUTH_SECRET_KEY is unset — using a random ephemeral key (sessions reset on "
        "restart). Set AUTH_SECRET_KEY for stable, secure sessions."
    )

AUTH_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 12)))
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
PASSWORD_MAX_LENGTH = int(os.getenv("PASSWORD_MAX_LENGTH", "72"))  # bcrypt's input cap

# Optional "Continue with Google" sign-in. Set GOOGLE_CLIENT_ID to the public
# OAuth Web client id; unset = the Google button is hidden and /auth/google 503s.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_ENABLED = bool(GOOGLE_CLIENT_ID)
