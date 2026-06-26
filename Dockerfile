# Single-container image: FastAPI serves BOTH the built React app and the /api
# backend on one port. Suited to Hugging Face Spaces and any one-port host.
#   docker build -t financeflow .
#   docker run -p 7860:7860 financeflow   ->   http://localhost:7860

# 1) Build the React/Vite frontend into static files.
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2) Python backend that also serves those static files.
FROM python:3.12-slim
WORKDIR /app

# System packages: tesseract-ocr powers the optional OCR fallback for scanned /
# image-only PDFs (parsing.py). Without it the app still runs — OCR just no-ops —
# but installing it lets scanned uploads be read. PyMuPDF/pytesseract come via pip.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
# requirements.txt already pins flashrank (the reranker) and fastembed (the dense
# embeddings for hybrid retrieval). Add the optional LLM SDKs too so "Thinking"
# mode works when a key is provided.
RUN pip install --no-cache-dir -r requirements.txt openai anthropic

COPY backend/app ./app
COPY sample_docs /sample_docs
COPY --from=frontend /fe/dist ./static

# Hugging Face Spaces runs the container as UID 1000; create that user and give
# it ownership of the writable paths (the SQLite dir + sample docs).
RUN useradd -m -u 1000 user \
    && mkdir -p /app/data \
    && chown -R user:user /app /sample_docs
USER user

ENV FRONTEND_DIR=/app/static
EXPOSE 7860
CMD ["uvicorn", "app.server:root", "--host", "0.0.0.0", "--port", "7860"]
