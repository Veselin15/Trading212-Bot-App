# syntax=docker/dockerfile:1

# ── Builder: compile wheels when needed ───────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/backend-requirements.txt \
    && pip install --no-cache-dir --prefix=/install numpy pandas yfinance

# ── Runtime: minimal image for home-server / Watchtower pulls ─────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /install /usr/local
COPY backend/ /app/backend/
COPY Server-App/ /app/Server-App/

RUN chmod +x /app/backend/docker-entrypoint.sh

ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

EXPOSE 8010

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
