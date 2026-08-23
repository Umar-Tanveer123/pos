from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.core.database import Base
from datetime import datetime, timezone

class SaleInvoice(Base):
    __tablename__ = "sale_invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True) # e.g. INV-000001
    customer_id = Column(Integer, ForeignKey("customers.id"))
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    location_id = Column(Integer, ForeignKey("locations.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Financial fields
    discount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    balance_owed = Column(Float, default=0.0) # amount on credit
    due_date = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
    
    # Status: COMPLETED, RETURNED, CANCELLED
    status = Column(String, default="COMPLETED")
    
    # Relationships
    customer = relationship("Customer")
    location = relationship("Location")
    user = relationship("User")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    payments = relationship("SalePayment", back_populates="sale", cascade="all, delete-orphan")

class SaleItem(Base):
    __tablename__ = "sale_items"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sale_invoices.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    quantity = Column(Float)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    unit_price = Column(Float) # price charged to customer
    discount = Column(Float, default=0.0)
    total = Column(Float)
    returned_quantity = Column(Float, default=0.0)
    
    # Relationships
    sale = relationship("SaleInvoice", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
    unit = relationship("Unit")

class SalePayment(Base):
    __tablename__ = "sale_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sale_invoices.id"))
    payment_method = Column(String) # Cash, Bank Transfer, Card, JazzCash, Easypaisa
    amount = Column(Float, default=0.0)
    reference = Column(String, nullable=True) # transaction reference / cheque number etc.
    
    sale = relationship("SaleInvoice", back_populates="payments")

class InvoiceTemplate(Base):
    __tablename__ = "invoice_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Compact, Standard, Wholesale
    is_default = Column(Boolean, default=False)
    
    # Customizable fields
    logo_path = Column(String, nullable=True)
    header_text = Column(String, nullable=True)
    footer_text = Column(String, nullable=True)
    business_name = Column(String, nullable=True)
    business_address = Column(String, nullable=True)
    business_phone = Column(String, nullable=True)
    business_email = Column(String, nullable=True)
    
    # Visibility toggles
    show_logo = Column(Boolean, default=True)
    show_customer_info = Column(Boolean, default=True)
    show_payment_info = Column(Boolean, default=True)
    show_notes = Column(Boolean, default=True)
    show_discount_column = Column(Boolean, default=True)
    show_sku = Column(Boolean, default=False)
    
    paper_size = Column(String, default="A4") # A4, A5, 80mm, 58mm
    template_type = Column(String, default="Standard") # Compact, Standard, Wholesale


class CustomerReturn(Base):
    __tablename__ = "customer_returns"
    
    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True) # e.g. RET-000001
    sale_id = Column(Integer, ForeignKey("sale_invoices.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    total_refund = Column(Float, default=0.0)
    notes = Column(String, nullable=True)
    
    sale = relationship("SaleInvoice")
    customer = relationship("Customer")
    location = relationship("Location")
    user = relationship("User")
    items = relationship("CustomerReturnItem", back_populates="customer_return", cascade="all, delete-orphan")

class CustomerReturnItem(Base):
    __tablename__ = "customer_return_items"
    
    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(Integer, ForeignKey("customer_returns.id"))
    sale_item_id = Column(Integer, ForeignKey("sale_items.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)
    
    quantity = Column(Float)
    refund_amount = Column(Float, default=0.0)
    is_damaged = Column(Boolean, default=False)
    
    customer_return = relationship("CustomerReturn", back_populates="items")
    sale_item = relationship("SaleItem")
    product = relationship("Product")
    variant = relationship("ProductVariant")
