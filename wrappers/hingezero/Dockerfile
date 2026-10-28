# Python base is an immutable digest used by the benchmark's own reference wrapper.
FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    HZ_MODEL_CACHE=/opt/hz-models \
    HZ_DATABASE=/data/hingezero.sqlite3 \
    HZ_EMBED_MODEL=BAAI/bge-small-en-v1.5
RUN pip install --no-cache-dir numpy==2.3.4 fastapi==0.136.3 uvicorn==0.47.0 fastembed==0.9.1
COPY HingeZero_Core.py HingeZero_Core.py
COPY hingezero_runtime.py hingezero_runtime.py
COPY hingezero_memory.py hingezero_memory.py
COPY hingezero_service.py hingezero_service.py
# Materialize model in build so inference needs no live internet connection.
RUN python -c "import HingeZero_Core; from hingezero_runtime import HingeZeroWitness, HingeZeroRetainingLoop; from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='/opt/hz-models')"
RUN mkdir -p /data
EXPOSE 8080
CMD ["uvicorn", "hingezero_service:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
