# Backend image — FastAPI RAG API.
#
# Heavy ML deps (torch, sentence-transformers, transformers). The processed data
# and search indexes are NOT baked into the image: they are built once with the
# ingestion/indexing scripts and mounted at runtime via the `./data` volume (see
# docker-compose.yml). Qdrant and Ollama are separate services.
FROM python:3.11-slim

WORKDIR /app

# Minimal build deps for any package that needs compilation; curl for healthchecks.
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first so the layer is cached across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Application code (data/, frontend/, venvs, etc. excluded via .dockerignore).
COPY . .

# Cache Hugging Face model downloads inside the image dir; mount a volume to persist.
ENV HF_HOME=/app/.hf-cache

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
