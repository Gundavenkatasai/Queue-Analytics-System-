@echo off
REM ============================================================================
REM Real-Time Surveillance System - AUTO STARTUP SCRIPT
REM ============================================================================
REM This script starts all three components in separate windows
REM Usage: Run this file from the project root directory
REM ============================================================================

echo.
echo ========================================
echo 🚀 REAL-TIME SURVEILLANCE SYSTEM
echo ========================================
echo.
echo Starting all components...
echo.

REM Get project root directory
cd /d "%~dp0"

REM Check if required directories exist
if not exist "backend" (
    echo ❌ ERROR: backend directory not found!
    exit /b 1
)
if not exist "frontend" (
    echo ❌ ERROR: frontend directory not found!
    exit /b 1
)
if not exist "ml-service" (
    echo ❌ ERROR: ml-service directory not found!
    exit /b 1
)

echo ✓ Project structure verified
echo.

REM Terminal 1: Backend API
echo Starting Backend API on port 8000...
start "Backend API" cmd /k "cd backend && php artisan serve --port=8000"
timeout /t 2 /nobreak

REM Terminal 2: Frontend React
echo Starting Frontend on port 3000...
start "Frontend" cmd /k "cd frontend && npm start"
timeout /t 3 /nobreak

REM Terminal 3: ML Service
echo Starting ML Service (requires camera)...
start "ML Service" cmd /k "cd ml-service && python main.py"

echo.
echo ========================================
echo ✅ ALL COMPONENTS STARTED
echo ========================================
echo.
echo 📍 Dashboard:   http://localhost:3000
echo 🔌 Backend API: http://localhost:8000
echo 📹 Camera:      Real-time detection active
echo.
echo Check the 3 terminal windows for logs
echo Press Ctrl+C in each window to stop
echo.
pause
