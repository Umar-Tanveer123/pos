@echo off
echo.
echo Starting POS System Setup...
echo.

python --version >nul 2>&1
if errorlevel 1 goto nopython

if not exist venv (
    echo Creating virtual environment (venv)...
    python -m venv venv
)

echo Installing dependencies...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Running database migrations...
alembic upgrade head
python scripts/seed_admin.py

echo Launching POS application...
python desktop_app.py

echo Done.
pause
exit /b

:nopython
echo [ERROR] Python is not installed or not added to your Windows PATH.
echo Please install Python 3.10+ or 3.11+ first, and check "Add Python to PATH".
pause
exit /b
