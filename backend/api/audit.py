from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from backend.core.database import get_db
from backend.models.audit import AuditLog
from backend.api.auth import get_current_active_user
from backend.models.auth import User

router = APIRouter()

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    username: Optional[str]
    timestamp: datetime
    action: str
    record_id: Optional[str]
    location_id: Optional[int]
    location_name: Optional[str]
    details: Optional[str]

    class Config:
        from_attributes = True

def log_action(db: Session, user_id: Optional[int], action: str, record_id: Optional[str] = None, location_id: Optional[int] = None, details: Optional[str] = None):
    try:
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            record_id=record_id,
            location_id=location_id,
            details=details
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print(f"Error logging action: {e}")
        db.rollback()

@router.get("/", response_model=List[AuditLogResponse])
def get_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    # Limit to admin/owner/manager
    # We will relax this for demo, but let's check roles
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
    res = []
    for log in logs:
        res.append(AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            username=log.user.username if log.user else "System",
            timestamp=log.timestamp,
            action=log.action,
            record_id=log.record_id,
            location_id=log.location_id,
            location_name=log.location.name if log.location else None,
            details=log.details
        ))
    return res
