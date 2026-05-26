#!/bin/sh
set -e

echo "[entrypoint] running alembic migrations..."
cd /app/packages/core
alembic upgrade head

echo "[entrypoint] starting uvicorn..."
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
