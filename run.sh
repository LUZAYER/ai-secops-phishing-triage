#!/bin/bash
set -e

echo "=========================================="
echo " AI SecOps Phishing Triage — Web Dashboard"
echo "=========================================="

# Virtual environment
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[*] Virtual environment already exists."
fi

source venv/bin/activate

echo "[*] Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "[*] Starting FastAPI dashboard on http://localhost:8000"
echo "[*] Press Ctrl+C to stop."
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
