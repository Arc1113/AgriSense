# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for ML libraries
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and increase timeout
RUN pip install --upgrade pip

# Install PyTorch CPU-only (required by sentence-transformers for RAG reranking)
RUN pip install --no-cache-dir --timeout=1000 \
    torch==2.6.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir --timeout=1000 -r requirements.txt

# Pre-download models to avoid cold-start during container boot
RUN python - <<'PY'
from sentence_transformers import SentenceTransformer
from sentence_transformers.cross_encoder import CrossEncoder

print('Downloading embedding model...')
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

print('Downloading cross-encoder reranker...')
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
PY

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=15s --timeout=10s --start-period=300s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
