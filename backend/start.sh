#!/bin/sh
set -e
echo "Running alembic upgrade head..."
alembic upgrade head
echo "Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
