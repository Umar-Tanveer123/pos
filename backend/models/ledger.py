from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from backend.core.database import Base
from datetime import datetime, timezone
import enum

class TransactionType(enum.Enum):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    CUSTOMER_RETURN = "CUSTOMER_RETURN"
    SUPPLIER_RETURN = "SUPPLIER_RETURN"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUSTMENT = "ADJUSTMENT"

class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), index=True)
    
    transaction_type = Column(SQLEnum(TransactionType))
    quantity = Column(Float) # Positive or negative based on type
    
    # Reference to original documents
    reference_id = Column(String, index=True, nullable=True) # e.g., INV-000001, PUR-000001
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    product = relationship("Product")
    location = relationship("Location")
    user = relationship("User")

# We can also add financial ledger transactions here in the future
