FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code — any code change invalidates layers below this
COPY role3_backend/ ./role3_backend/
COPY role1/data/ ./role1/data/
COPY frontend/ ./frontend/

# Pre-download the ONNX embedding model into the image at build time
# This runs AFTER code is copied so a code change triggers a fresh model download too
RUN HF_HUB_DISABLE_SYMLINKS=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV FAISS_INDEX_DIR=role1/data/index_minilm
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV HF_HUB_DISABLE_SYMLINKS=1
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --app-dir role3_backend"]
