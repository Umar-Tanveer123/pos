from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from backend.core.database import get_db
from backend.core.security import get_password_hash
from backend.models.auth import User, Role
from backend.api.auth import get_current_active_user, UserResponse

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    password: str
    role_id: int | None = None

def get_admin_user(current_user: User = Depends(get_current_active_user)):
    # Basic role check for Admin/Owner. In a real system, we'd check permissions dynamically.
    if current_user.role and current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        hashed_password=hashed_password,
        role_id=user_in.role_id,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    from backend.api.audit import log_action
    log_action(db, user_id=current_admin.id, action="User creation", record_id=str(db_user.id), details=f"User {db_user.username} created")
    
    return db_user

@router.get("/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_admin: User = Depends(get_admin_user)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.delete("/{user_id}", response_model=UserResponse)
def deactivate_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Deactivate instead of deleting permanently (SRS 47)
    user.is_active = False
    db.commit()
    db.refresh(user)
    
    from backend.api.audit import log_action
    log_action(db, user_id=current_admin.id, action="User deactivation", record_id=str(user.id), details=f"User {user.username} deactivated")
    
    return user
