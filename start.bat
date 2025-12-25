@echo off
REM ============================================================
REM MRD Agent - Quick Start Script
REM ============================================================

echo.
echo ========================================
echo   MRD Agent v2.0 - Quick Start
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Please create a .env file with your API keys.
    echo.
    pause
)

REM Install dependencies if needed
echo Checking dependencies...
pip install -r requirements.txt --quiet

echo.
echo Starting MRD Agent...
echo.
echo Options:
echo   1. Run CLI (interactive)
echo   2. Run API Server
echo   3. Run Both (API + Frontend)
echo.

set /p choice="Enter choice (1-3): "

if "%choice%"=="1" (
    echo.
    echo Starting CLI mode...
    python -m src.agents.orchestrator
) else if "%choice%"=="2" (
    echo.
    echo Starting API server on http://localhost:8000
    echo API docs: http://localhost:8000/docs
    python -m uvicorn api.main:app --reload --port 8000
) else if "%choice%"=="3" (
    echo.
    echo Starting API server...
    start cmd /k python -m uvicorn api.main:app --reload --port 8000
    
    timeout /t 2 >nul
    
    echo Starting frontend server...
    start cmd /k python -m http.server 3000 --directory frontend
    
    timeout /t 2 >nul
    
    echo.
    echo ========================================
    echo   Servers are running!
    echo   API: http://localhost:8000
    echo   Frontend: http://localhost:3000
    echo ========================================
    
    start http://localhost:3000
) else (
    echo Invalid choice.
)

pause
