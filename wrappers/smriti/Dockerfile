# syntax=docker/dockerfile:1
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Smriti PrecisionMemBench Wrapper"
LABEL org.opencontainers.image.description="Adapter for Smriti Temporal Memory API"
LABEL org.opencontainers.image.source="https://github.com/RemanenetSpy/smriti"

WORKDIR /app

RUN pip install --no-cache-dir fastapi==0.111.0 uvicorn==0.30.1 pydantic==2.7.1 httpx==0.27.0

COPY smriti_service.py .

EXPOSE 8080
CMD ["python", "smriti_service.py"]
