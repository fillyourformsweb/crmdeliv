#!/bin/bash

# ========================================
# CRM Delivery - Environment Setup Script
# Linux/Mac Shell Script
# ========================================

echo ""
echo "============================================"
echo "CRM Delivery System - Setup Script"
echo "============================================"
echo ""

# Check if .env exists
if [ -f .env ]; then
    echo "[INFO] .env file already exists"
    echo ""
else
    echo "[INFO] Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[SUCCESS] .env file created"
        echo "[IMPORTANT] Please open .env and update the values:"
        echo "  1. SECRET_KEY - generate a strong key"
        echo "  2. MAIL_* settings - configure email"
        echo "  3. GEMINI_API_KEY - if using AI features"
        echo "  4. DATABASE_URL - change if not using SQLite"
    else
        echo "[ERROR] .env.example not found!"
        exit 1
    fi
fi

echo ""
echo "[INFO] Checking Python installation..."
python3 --version
if [ $? -ne 0 ]; then
    echo "[ERROR] Python3 not found! Please install Python 3.8+"
    exit 1
fi

echo ""
echo "[INFO] Checking virtual environment..."
if [ -d venv ]; then
    echo "[INFO] Virtual environment exists"
else
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
    echo "[SUCCESS] Virtual environment created"
fi

echo ""
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

echo ""
echo "[INFO] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi

echo ""
echo "[INFO] Creating instance directory..."
mkdir -p instance

echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Run: python app.py"
echo "3. Visit: http://localhost:5000"
echo ""
echo "For detailed setup instructions, see ENV_SETUP_GUIDE.md"
echo ""
