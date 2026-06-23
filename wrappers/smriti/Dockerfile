# syntax=docker/dockerfile:1
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Smriti PrecisionMemBench Wrapper"
LABEL org.opencontainers.image.description="Temporal memory layer — Chronos OS"
LABEL org.opencontainers.image.source="https://github.com/RemanenetSpy/chronos-os"
LABEL org.opencontainers.image.authors="Spy9191"

WORKDIR /app

# ── Install dependencies with pinned versions ─────────────────────────────────
RUN pip install --no-cache-dir \
    fastapi==0.111.0 \
    uvicorn==0.30.1 \
    pydantic==2.7.1 \
    chromadb==0.5.0 \
    sentence-transformers==3.0.1

# ── Pre-download the embedding model into the image layer ─────────────────────
# This eliminates all network calls at runtime (HF_HUB_OFFLINE=1 is set in the app).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Copy wrapper ──────────────────────────────────────────────────────────────
COPY smriti_service.py .

EXPOSE 8080

CMD ["python", "smriti_service.py"]
