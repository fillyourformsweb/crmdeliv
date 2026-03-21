#!/bin/bash

# ========================================
# CRM Delivery - Quick Start Script
# Linux/Mac Shell Script
# ========================================

echo ""
echo "============================================"
echo "CRM Delivery System - Starting..."
echo "============================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "[ERROR] .env file not found!"
    echo "[INFO] Please run ./setup.sh first"
    exit 1
fi

# Check if venv exists
if [ ! -d venv ]; then
    echo "[ERROR] Virtual environment not found!"
    echo "[INFO] Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Check if Flask is installed
python -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] Flask not installed!"
    echo "[INFO] Please run ./setup.sh to install dependencies"
    exit 1
fi

echo "[SUCCESS] All checks passed!"
echo ""
echo "============================================"
echo "Starting Flask Application..."
echo "============================================"
echo ""
echo "Server will start at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

# Run Flask app with proper environment
export FLASK_APP=app.py
export FLASK_ENV=development

python app.py
