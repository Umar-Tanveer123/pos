import sys
import os

class DummyStream:
    def write(self, data):
        pass
    def read(self, *args, **kwargs):
        return ""
    def readline(self, *args, **kwargs):
        return ""
    def flush(self):
        pass
    def isatty(self):
        return False

if sys.stdout is None:
    sys.stdout = DummyStream()
if sys.stderr is None:
    sys.stderr = DummyStream()
if sys.stdin is None:
    sys.stdin = DummyStream()

import threading
import uvicorn
import socket
import time
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Programmatic Database Initialization & Seeding
from backend.core.database import engine, Base, SessionLocal
from backend.models.auth import Role, User
from backend.core.security import get_password_hash
from backend.main import app

def init_database():
    # 1. Create database tables if they do not exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Seed initial data (Roles & Admin Account)
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        if not admin_role:
            admin_role = Role(name="Admin", description="Full system access")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
            print("Database Setup: Admin Role created.")
            
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            hashed_password = get_password_hash("admin123")
            admin_user = User(
                username="admin",
                hashed_password=hashed_password,
                role_id=admin_role.id,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("Database Setup: Default Admin User created (admin/admin123).")
    except Exception as e:
        print(f"Database Setup Error: {e}")
    finally:
        db.close()

def wait_for_backend(host="127.0.0.1", port=8000, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(0.1)
    return False

def run_backend():
    try:
        # Running uvicorn in a thread requires disabling signals installation
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning", install_signals=False)
    except Exception as e:
        print(f"[ERROR] Backend thread crashed: {e}")
        import traceback
        traceback.print_exc()

def main():
    # Initialize/update database structure and seed default user
    init_database()
    
    # Launch FastAPI Server in background daemon thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Wait for the backend API port to become active before starting GUI
    if not wait_for_backend(timeout=10):
        print("[WARNING] Backend server did not respond within timeout.")
    
    # Launch PySide6 GUI
    from frontend.theme import GLOBAL_STYLESHEET
    from frontend.main_window import MainWindow

    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(GLOBAL_STYLESHEET)
    
    window = MainWindow()
    window.show()
    
    status = qt_app.exec()
    sys.exit(status)

if __name__ == "__main__":
    main()
