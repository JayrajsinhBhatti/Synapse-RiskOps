@echo off
title Synapse RiskOps - Master Startup
echo =================================================================
echo     STARTING SYNAPSE RISKOPS - COMPLETE SYSTEM PLATFORM
echo =================================================================

echo [1/4] Checking Docker Infrastructure (Postgres, Redis, Prometheus)...
docker compose up -d postgres redis prometheus jaeger 2>nul || echo (Note: Docker Desktop not running or already started)

echo [2/4] Starting ML Engine on port 8000...
start "Synapse ML Engine (8000)" cmd /k "cd /d %~dp0ml-engine && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [3/4] Starting Backend Core API on port 8080...
start "Synapse Backend (8080)" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload"

echo [4/5] Starting Frontend Dashboard on port 5173...
start "Synapse Frontend (5173)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo [5/5] Starting 10 Microservices & Hardware Hub on ports 9100-9110...
start "Hardware Hub (9100-9110)" cmd /k "cd /d %~dp0live-microservices-demo && python run_demo.py"

echo =================================================================
echo     ALL SERVICES LAUNCHED SUCCESSFULLY!
echo =================================================================
echo Synapse Dashboard:      http://localhost:5173
echo Backend API Docs:       http://localhost:8080/docs
echo ML Engine Docs:         http://localhost:8000/docs
echo Hardware Hub Store:     http://localhost:9100
echo Hardware API Gateway:   http://localhost:9101
echo Prometheus (Docker):    http://localhost:9090
echo =================================================================
echo You can keep this window open or press any key to close this launcher.
pause
