FROM python:3.13-slim

WORKDIR /app

RUN pip install fastapi==0.136.3 uvicorn==0.47.0 openai==1.93.2

COPY okf_service.py .

CMD ["python", "okf_service.py", "/data/okf-bundle"]