FROM python:3.11-slim

WORKDIR /app

RUN pip install \
    fastapi==0.136.3 \
    uvicorn==0.47.0 \
    graphiti-core=0.29.1 \
    neo4j==6.2.0

COPY zep_service.py .
COPY patch.py .

CMD ["python", "zep_service.py"]