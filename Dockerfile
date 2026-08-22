FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Cache-bust: update this value to force a full rebuild when code changes don't invalidate Docker cache
ARG CACHE_BUST=2
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    HF_HUB_DISABLE_SYMLINKS=1 HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# Copy application code, frontend assets, and indexed FAISS knowledge vectors
COPY role3_backend/ ./role3_backend/
COPY role1/data/ ./role1/data/
COPY frontend/ ./frontend/

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV FAISS_INDEX_DIR=role1/data/index_minilm
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --app-dir role3_backend"]
