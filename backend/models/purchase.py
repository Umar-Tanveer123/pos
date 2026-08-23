from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.core.database import Base
from datetime import datetime, timezone

class PurchaseInvoice(Base):
    __tablename__ = "purchase_invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True) # e.g. PUR-000001
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    supplier_invoice_number = Column(String, nullable=True)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    location_id = Column(Integer, ForeignKey("locations.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Financial fields
    discount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    payable_amount = Column(Float, default=0.0)
    due_date = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
    
    # Relationships
    supplier = relationship("Supplier")
    location = relationship("Location")
    user = relationship("User")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    
    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchase_invoices.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    quantity = Column(Float)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    purchase_price = Column(Float)
    discount = Column(Float, default=0.0)
    total = Column(Float)
    
    # Relationships
    purchase = relationship("PurchaseInvoice", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
    unit = relationship("Unit")

class SupplierLedger(Base):
    __tablename__ = "supplier_ledger"
    
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), index=True)
    transaction_type = Column(String) # "PURCHASE", "PAYMENT", "RETURN", "EXCHANGE", "ADJUSTMENT"
    reference_id = Column(String, index=True, nullable=True) # e.g. PUR-000001, PAY-000001
    amount = Column(Float) # Positive for increasing payable (purchase), negative for decreasing payable (payment/return)
    balance_after = Column(Float) # Supplier balance after this transaction
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(String, nullable=True)
    
    supplier = relationship("Supplier")

class SupplierPayment(Base):
    __tablename__ = "supplier_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True) # PAY-000001
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    purchase_id = Column(Integer, ForeignKey("purchase_invoices.id"), nullable=True) # optional, pay a specific invoice
    amount = Column(Float)
    payment_method = Column(String) # Cash, Bank, Credit
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(String, nullable=True)
    
    supplier = relationship("Supplier")
    purchase = relationship("PurchaseInvoice")

class PriceAuditLog(Base):
    __tablename__ = "price_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    old_purchase_price = Column(Float)
    new_purchase_price = Column(Float)
    old_retail_price = Column(Float)
    new_retail_price = Column(Float)
    old_wholesale_price = Column(Float)
    new_wholesale_price = Column(Float)
    old_special_price = Column(Float)
    new_special_price = Column(Float)
    
    change_type = Column(String) # "MANUAL", "BULK_CATEGORY", "BULK_PRODUCTS", "CSV_IMPORT", "PURCHASE"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    product = relationship("Product")
    user = relationship("User")


class SupplierReturn(Base):
    __tablename__ = "supplier_returns"

    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True)  # RET-000001
    purchase_id = Column(Integer, ForeignKey("purchase_invoices.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    return_type = Column(String, default="RETURN")  # "RETURN" or "EXCHANGE"
    reason = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    status = Column(String, default="PENDING")  # PENDING, COMPLETED, EXCHANGED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    purchase = relationship("PurchaseInvoice")
    supplier = relationship("Supplier")
    location = relationship("Location")
    user = relationship("User")
    items = relationship("SupplierReturnItem", back_populates="supplier_return", cascade="all, delete-orphan")


class SupplierReturnItem(Base):
    __tablename__ = "supplier_return_items"

    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(Integer, ForeignKey("supplier_returns.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    quantity = Column(Float, nullable=False)
    purchase_price = Column(Float, nullable=False)

    supplier_return = relationship("SupplierReturn", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
