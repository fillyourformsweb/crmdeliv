@echo off
REM ========================================
REM CRM Delivery - Quick Start Script
REM Windows Batch Script
REM ========================================

setlocal enabledelayedexpansion

echo.
echo ============================================
echo CRM Delivery System - Starting...
echo ============================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo [INFO] Please run setup.bat first
    pause
    exit /b 1
)

REM Check if venv exists
if not exist venv (
    echo [ERROR] Virtual environment not found!
    echo [INFO] Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if Flask is installed
python -c "import flask" 2>nul
if errorlevel 1 (
    echo [ERROR] Flask not installed!
    echo [INFO] Please run setup.bat to install dependencies
    pause
    exit /b 1
)

echo [SUCCESS] All checks passed!
echo.
echo ============================================
echo Starting Flask Application...
echo ============================================
echo.
echo Server will start at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

REM Run Flask app with proper environment
set FLASK_APP=app.py
set FLASK_ENV=development

python app.py

pause
