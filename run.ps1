# Root startup script for AM (I Have No Mouth and I Must Scream)
# Starts both the FastAPI Backend and the Vite React Frontend in separate windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting AM AI Assistant...          " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$backendDir = Join-Path $PSScriptRoot "DR-doom-Day-2-Backend"
$frontendDir = Join-Path $PSScriptRoot "jarvis-frontend"

# 1. Start Backend in a new PowerShell window
Write-Host "Starting Backend on http://127.0.0.1:8765..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; if (Test-Path '.\.venv\Scripts\Activate.ps1') { .\.venv\Scripts\Activate.ps1 }; python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload"

# 2. Start Frontend in a new PowerShell window
Write-Host "Starting Frontend on http://localhost:1420..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm run dev"

Write-Host "`nBoth services are launching!" -ForegroundColor Cyan
Write-Host "Open your browser at: http://localhost:1420/" -ForegroundColor Yellow
