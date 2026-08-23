from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.core.database import Base
from datetime import datetime, timezone

class StockTransfer(Base):
    __tablename__ = "stock_transfers"
    
    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True) # e.g. TRN-000001
    source_location_id = Column(Integer, ForeignKey("locations.id"))
    destination_location_id = Column(Integer, ForeignKey("locations.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    status = Column(String, default="COMPLETED") # PENDING, COMPLETED, CANCELLED
    notes = Column(String, nullable=True)
    
    source_location = relationship("Location", foreign_keys=[source_location_id])
    destination_location = relationship("Location", foreign_keys=[destination_location_id])
    user = relationship("User")
    items = relationship("StockTransferItem", back_populates="transfer", cascade="all, delete-orphan")

class StockTransferItem(Base):
    __tablename__ = "stock_transfer_items"
    
    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(Integer, ForeignKey("stock_transfers.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    
    quantity = Column(Float)
    
    transfer = relationship("StockTransfer", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")


class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"
    
    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True) # e.g. ADJ-000001
    location_id = Column(Integer, ForeignKey("locations.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    reason = Column(String, nullable=True)
    
    location = relationship("Location")
    user = relationship("User")
    items = relationship("StockAdjustmentItem", back_populates="adjustment", cascade="all, delete-orphan")

class StockAdjustmentItem(Base):
    __tablename__ = "stock_adjustment_items"
    
    id = Column(Integer, primary_key=True, index=True)
    adjustment_id = Column(Integer, ForeignKey("stock_adjustments.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    
    system_quantity = Column(Float)
    actual_quantity = Column(Float)
    difference = Column(Float) # actual_quantity - system_quantity
    
    adjustment = relationship("StockAdjustment", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
