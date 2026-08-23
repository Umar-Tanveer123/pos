from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.core.database import Base
from datetime import datetime, timezone

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True) # e.g. EXP-000001
    
    category = Column(String) # e.g., Utilities, Rent, Payroll, Marketing
    amount = Column(Float, default=0.0)
    
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    payment_method = Column(String) # Cash, Bank, etc.
    description = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
