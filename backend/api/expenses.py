from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.core.database import get_db
from backend.models.expense import Expense
from backend.models.auth import User, Role
from backend.api.auth import get_current_active_user

router = APIRouter()

class ExpenseCreate(BaseModel):
    category: str
    amount: float
    payment_method: str
    description: Optional[str] = None
    notes: Optional[str] = None

class ExpenseResponse(BaseModel):
    id: int
    internal_id: str
    category: str
    amount: float
    date: datetime
    payment_method: str
    description: Optional[str]
    notes: Optional[str]
    user_id: int
    
    class Config:
        from_attributes = True

@router.post("/", response_model=ExpenseResponse)
def create_expense(
    req: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.role or current_user.role.name not in ["Owner", "Admin", "Manager", "Accountant"]:
        raise HTTPException(status_code=403, detail="Only Admin, Manager, or Accountant can manage expenses.")
        
    max_id = db.query(func.max(Expense.id)).scalar() or 0
    from backend.api.settings import get_prefix
    exp_prefix = get_prefix(db, "prefix_expense", "EXP-")
    internal_id = f"{exp_prefix}{max_id + 1:06d}"
    
    exp = Expense(
        internal_id=internal_id,
        category=req.category,
        amount=req.amount,
        payment_method=req.payment_method,
        description=req.description,
        notes=req.notes,
        user_id=current_user.id
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp

@router.get("/", response_model=List[ExpenseResponse])
def get_expenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.role or current_user.role.name not in ["Owner", "Admin", "Manager", "Accountant"]:
        raise HTTPException(status_code=403, detail="Not authorized to view expenses.")
        
    return db.query(Expense).order_by(Expense.date.desc()).all()
