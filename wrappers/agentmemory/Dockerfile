FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285

WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.12 httpx==0.28.1 uvicorn==0.34.2
COPY agentmemory_service.py /app/agentmemory_service.py

EXPOSE 8084
CMD ["uvicorn", "agentmemory_service:app", "--host", "0.0.0.0", "--port", "8084"]
