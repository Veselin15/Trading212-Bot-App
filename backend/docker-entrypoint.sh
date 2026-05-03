#!/bin/sh
set -e

echo "[entrypoint] Working directory: $(pwd)"
echo "[entrypoint] Running database migrations..."

# alembic.ini script_location is relative to cwd (/app), which resolves to /app/backend/migrations
python -m alembic -c backend/alembic.ini upgrade head

echo "[entrypoint] Starting backend server on 0.0.0.0:8010..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8010
