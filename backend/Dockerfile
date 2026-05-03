FROM python:3.12-slim

# Build tools needed by asyncpg / psycopg source wheels when binary wheels are unavailable
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
# Install backend deps first so Docker layer cache is reused on code-only changes.
COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

# Server-App (t212_miner_bot) extra deps — not in backend/requirements.txt
RUN pip install --no-cache-dir numpy pandas yfinance

# ── Source code ───────────────────────────────────────────────────────────────
COPY backend/ /app/backend/
COPY Server-App/ /app/Server-App/

RUN chmod +x /app/backend/docker-entrypoint.sh

# backend/ is the Python package root:  "from app.xxx import ..."
ENV PYTHONPATH=/app/backend

EXPOSE 8010

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
