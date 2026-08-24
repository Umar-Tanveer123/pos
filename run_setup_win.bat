@echo off
echo ==========================================
echo   POS SYSTEM AUTOMATIC INSTALLER & RUNNER
echo ==========================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH! Please install Python 3.10+ or Python 3.11+ first.
    pause
    exit /b
)

REM 1. Create Virtual Environment if not present
if not exist venv (
    echo Creating virtual environment (venv)...
    python -m venv venv
)

REM 2. Activate environment and install dependencies
echo Installing dependencies from requirements.txt...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

REM 3. Setup Database (migrations + seed)
echo Setting up local database...
alembic upgrade head
python scripts/seed_admin.py

REM 4. Launch Backend API and Frontend GUI
echo Starting Backend API Server...
start "POS Backend API" /min cmd /k "venv\Scripts\activate && uvicorn backend.main:app --host 127.0.0.1 --port 8000"

echo Starting Desktop Application...
python desktop_app.py

echo Done.
pause
