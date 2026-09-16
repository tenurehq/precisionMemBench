FROM python:3.11-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285

WORKDIR /app

RUN pip install \
    fastapi==0.136.3 \
    uvicorn==0.47.0 \
    graphiti-core \
    neo4j==6.2.0 \
    httpx==0.28.1

COPY zep_service.py .

CMD ["python", "zep_service.py"]