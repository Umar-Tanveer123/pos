#!/bin/bash
echo "=========================================="
echo "  POS SYSTEM AUTOMATIC INSTALLER & RUNNER"
echo "=========================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed! Please install Python 3.10+ or Python 3.11+ first."
    exit 1
fi

# 1. Create Virtual Environment if not present
if [ ! -d "venv" ]; then
    echo "Creating virtual environment (venv)..."
    python3 -m venv venv
fi

# 2. Activate environment and install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Setup Database
echo "Setting up local database..."
alembic upgrade head
python3 scripts/seed_admin.py

# 4. Launch Backend API and Frontend GUI
echo "Starting Backend API Server..."
# Run uvicorn in the background
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "Starting Desktop Application..."
python3 desktop_app.py

# When PySide6 closes, kill the background backend process
kill $BACKEND_PID
echo "Done."
