"""Single-process entrypoint: serve the built React app AND the JSON API.

Used for one-container hosts (e.g. Hugging Face Spaces) where only one port is
exposed. The existing API app is mounted under /api — so the frontend's relative
"/api" base keeps working and there is no cross-origin/CORS step — and the built
frontend (Vite `dist`, copied to ./static in the image) is served at /.

Local dev still uses the Vite dev server + `app.main:app`; this module is only
the production single-container shell. Tests are unaffected (they import
`app.main:app` and call the routes at root).
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import BACKEND_DIR
from .main import app as api_app

# Where the built frontend lives. The Docker image copies Vite's dist here.
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", BACKEND_DIR / "static"))

root = FastAPI(title="FinanceFlow AI", docs_url=None, redoc_url=None)

# /api/* -> the full JSON API. Routes are defined at the app root in main.py, so
# GET /api/health hits api_app's /health. Mounted FIRST so it always wins.
root.mount("/api", api_app)

# Everything else -> the static single-page frontend (index.html + hashed assets).
if FRONTEND_DIR.is_dir():
    root.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
