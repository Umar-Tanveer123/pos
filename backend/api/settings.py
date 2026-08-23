from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
from pydantic import BaseModel

from backend.core.database import get_db
from backend.models.setting import SystemSetting
from backend.api.auth import get_current_active_user
from backend.models.auth import User
from backend.api.audit import log_action

router = APIRouter()

class SettingsUpdate(BaseModel):
    settings: Dict[str, str]

def get_setting_value(db: Session, key: str, default: str = "") -> str:
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return setting.value if setting else default

def get_prefix(db: Session, key: str, default: str) -> str:
    # Key can be e.g., prefix_invoice
    return get_setting_value(db, key, default)

@router.get("/")
def get_all_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    settings_list = db.query(SystemSetting).all()
    return {s.key: s.value for s in settings_list}

@router.post("/")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    if current_user.role and current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Only Admins can change settings.")

    for k, v in payload.settings.items():
        setting = db.query(SystemSetting).filter(SystemSetting.key == k).first()
        if setting:
            setting.value = v
        else:
            db.add(SystemSetting(key=k, value=v))
            
    db.commit()
    log_action(db, user_id=current_user.id, action="System settings", details=f"Settings updated: {', '.join(payload.settings.keys())}")
    return {"message": "Settings updated successfully"}
