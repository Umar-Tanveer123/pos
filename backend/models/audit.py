from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.core.database import Base
from datetime import datetime, timezone

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    action = Column(String)  # e.g., Login, Logout, Sale, Return, Purchase, etc.
    record_id = Column(String, nullable=True)  # ID or unique number of the record affected
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    details = Column(String, nullable=True)

    user = relationship("User")
    location = relationship("Location")
