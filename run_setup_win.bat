@echo off
echo Starting POS System Setup...

rem If the venv was created on a Mac, delete it and recreate it for Windows
if exist venv if not exist venv\Scripts\activate.bat rmdir /s /q venv

if not exist venv (
    echo Creating Windows virtual environment...
    python -m venv venv
)

echo Activating environment...
call venv\Scripts\activate

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Running database setup...
alembic upgrade head
python scripts/seed_admin.py

echo Launching POS application...
python desktop_app.py

echo Done.
pause
