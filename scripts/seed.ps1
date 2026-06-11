# Mahakosh — migrate and seed database
# Requires: Docker Desktop running, postgres service up

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "Starting PostgreSQL..." -ForegroundColor Cyan
Set-Location $Root
docker compose up -d postgres
docker compose exec postgres sh -c "until pg_isready -U mahakosh; do sleep 1; done"

Write-Host "Running migrations..." -ForegroundColor Cyan
Set-Location "$Root\backend"
alembic upgrade head

Write-Host "Seeding database..." -ForegroundColor Cyan
Set-Location $Root
python -m backend.scripts.seed_db @args

Write-Host "Done." -ForegroundColor Green
