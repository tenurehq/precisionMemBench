FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN pip install fastapi==0.136.3 uvicorn==0.47.0 httpx==0.28.1 \
    sentence-transformers===5.5.1 \
    git+https://github.com/agiresearch/A-mem.git@ceffb860f0712bbae97b184d440df62bc910ca8d
COPY amem_service.py .
COPY patch.py .
CMD ["python", "amem_service.py"]