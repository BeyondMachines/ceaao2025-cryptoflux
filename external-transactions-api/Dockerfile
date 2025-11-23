
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*


RUN useradd -m appuser

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data && chown -R appuser:appuser /data

USER appuser

EXPOSE 8000

CMD ["gunicorn", "app:app", "--workers", "2", "--bind", "0.0.0.0:8000", "--timeout", "60"]
