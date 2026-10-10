# Synapse RiskOps - PowerShell Master Startup Script
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "    STARTING SYNAPSE RISKOPS - COMPLETE SYSTEM PLATFORM" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Docker infrastructure
Write-Host "[1/4] Checking Docker Infrastructure (Postgres, Redis, Prometheus)..." -ForegroundColor Yellow
try {
    docker compose up -d postgres redis prometheus jaeger 2>$null
} catch {
    Write-Host "Docker compose check skipped or failed." -ForegroundColor DarkGray
}

# 2. ML Engine
Write-Host "[2/4] Starting ML Engine on port 8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir\ml-engine'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# 3. Backend Core API
Write-Host "[3/4] Starting Backend Core API on port 8080..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir\backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload"

# 4. Frontend Dashboard
Write-Host "[4/5] Starting Frontend Dashboard on port 5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir\frontend'; npm run dev"

# 5. Live 10 Microservices + Storefront
Write-Host "[5/5] Starting 10 Microservices & Hardware Hub on ports 9100-9110..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptDir\live-microservices-demo'; python run_demo.py"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "    ALL SERVICES LAUNCHED SUCCESSFULLY!" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Synapse Dashboard:      http://localhost:5173" -ForegroundColor White
Write-Host "Backend API Docs:       http://localhost:8080/docs" -ForegroundColor White
Write-Host "ML Engine Docs:         http://localhost:8000/docs" -ForegroundColor White
Write-Host "Hardware Hub Store:     http://localhost:9100" -ForegroundColor White
Write-Host "Hardware API Gateway:   http://localhost:9101" -ForegroundColor White
Write-Host "Prometheus (Docker):    http://localhost:9090" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan
