@echo off
REM ========================================
REM CRM Delivery - Environment Setup Script
REM Windows Batch Script
REM ========================================

echo.
echo ============================================
echo CRM Delivery System - Setup Script
echo ============================================
echo.

REM Check if .env exists
if exist .env (
    echo [INFO] .env file already exists
    echo.
) else (
    echo [INFO] Creating .env from .env.example...
    if exist .env.example (
        copy .env.example .env
        echo [SUCCESS] .env file created
        echo [IMPORTANT] Please open .env and update the values:
        echo   1. SECRET_KEY - generate a strong key
        echo   2. MAIL_* settings - configure email
        echo   3. GEMINI_API_KEY - if using AI features
        echo   4. DATABASE_URL - change if not using SQLite
    ) else (
        echo [ERROR] .env.example not found!
        exit /b 1
    )
)

echo.
echo [INFO] Checking Python installation...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    exit /b 1
)

echo.
echo [INFO] Checking virtual environment...
if exist venv (
    echo [INFO] Virtual environment exists
) else (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    echo [SUCCESS] Virtual environment created
)

echo.
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [INFO] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)

echo.
echo [INFO] Creating instance directory...
if not exist instance mkdir instance

echo.
echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo Next steps:
echo 1. Edit .env file with your configuration
echo 2. Run: python app.py
echo 3. Visit: http://localhost:5000
echo.
echo For detailed setup instructions, see ENV_SETUP_GUIDE.md
echo.

pause
