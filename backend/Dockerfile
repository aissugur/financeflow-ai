# Backend image. Build from the REPO ROOT so sample_docs is in context:
#   docker build -f backend/Dockerfile -t financeflow-backend .
FROM python:3.12-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App code and the bundled sample documents (used by /evaluate and /demo/seed).
COPY backend/app ./app
COPY sample_docs /sample_docs

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
