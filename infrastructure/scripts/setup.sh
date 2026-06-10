#!/usr/bin/env bash
set -euo pipefail

echo "=== Mahakosh Setup ==="

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example — update secrets before production."
fi

echo "Starting infrastructure services..."
docker compose up -d postgres redis qdrant minio temporal ollama

echo "Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U mahakosh -d mahakosh > /dev/null 2>&1; do
    sleep 2
done

echo "Running database migrations..."
docker compose run --rm backend alembic upgrade head

echo "Starting application services..."
docker compose up -d backend frontend nginx

echo ""
echo "=== Mahakosh is ready ==="
echo "Frontend:  http://localhost:3000"
echo "API:       http://localhost:8000/api/v1"
echo "API Docs:  http://localhost:8000/docs"
echo "Temporal:  http://localhost:8080"
