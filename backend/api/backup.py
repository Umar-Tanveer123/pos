import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.config import settings
from backend.models.auth import User
from backend.api.auth import get_current_active_user
from backend.api.audit import log_action

router = APIRouter()

BACKUP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "backups"
)

@router.post("/backup")
def create_backup(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    if current_user.role and current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Only Admins can perform backups.")

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, settings.SQLITE_DB_NAME)

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_name = f"backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_file_name)

    try:
        shutil.copy2(db_path, backup_path)
        log_action(db, user_id=current_user.id, action="System Backup", details=f"Database backed up to {backup_file_name}")
        return {"message": "Backup created successfully", "filename": backup_file_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

@router.get("/")
def list_backups(current_user: User = Depends(get_current_active_user)):
    if current_user.role and current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Not authorized.")

    if not os.path.exists(BACKUP_DIR):
        return []

    files = [f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_") and f.endswith(".db")]
    files.sort(reverse=True)
    return files

@router.post("/restore")
def restore_backup(filename: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    if current_user.role and current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Only Admins can restore backups.")

    backup_path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Backup file not found.")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, settings.SQLITE_DB_NAME)

    try:
        shutil.copy2(backup_path, db_path)
        log_action(db, user_id=current_user.id, action="System Restore", details=f"Database restored from {filename}")
        return {"message": "Restore completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")
