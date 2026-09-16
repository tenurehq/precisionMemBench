FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285
WORKDIR /app
RUN pip install mem0ai==2.0.20 fastapi==0.136.3 uvicorn==0.47.0 qdrant-client==1.18.0 ollama==0.6.2
COPY mem0_service.py .
CMD ["python", "mem0_service.py"]