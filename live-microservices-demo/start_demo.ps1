# Launch 10 Microservices + Storefront + Traffic Generator
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   STARTING 10 MICROSERVICES LIVE E-COMMERCE PLATFORM" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
python run_demo.py
