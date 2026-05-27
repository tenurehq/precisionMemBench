FROM python:3.13-slim
WORKDIR /app
RUN pip install mem0ai==2.0.2 fastapi==0.136.3 uvicorn==0.47.0 qdrant-client==1.18.0 ollama==0.6.2
COPY mem0_service.py .
CMD ["python", "mem0_service.py"]