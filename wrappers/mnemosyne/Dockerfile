FROM python:3.13-slim
WORKDIR /app

RUN pip install "mnemosyne-memory" fastapi==0.136.3 uvicorn==0.47.0

COPY mnemosyne_service.py .

EXPOSE 8082
CMD ["python", "mnemosyne_service.py"]