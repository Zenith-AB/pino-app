# Dockerfile para Pino ML Infrastructure & PISA Analytics Engine
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download es_core_news_md

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "pino_ml.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
