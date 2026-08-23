from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.core.database import Base
from backend.models.product import product_supplier_assoc
from datetime import datetime, timezone

class CustomerType(Base):
    __tablename__ = "customer_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # Retail, Wholesale, Special
    customers = relationship("Customer", back_populates="customer_type")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True)  # CUS-000001
    name = Column(String, index=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    customer_type_id = Column(Integer, ForeignKey("customer_types.id"), nullable=True)
    customer_type = relationship("CustomerType", back_populates="customers")
    credit_limit = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)  # amount owed BY customer (positive = they owe us)
    notes = Column(String, nullable=True)
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive

    ledger = relationship("CustomerLedger", back_populates="customer", cascade="all, delete-orphan")
    payments = relationship("CustomerPayment", back_populates="customer", cascade="all, delete-orphan")

class CustomerLedger(Base):
    __tablename__ = "customer_ledger"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    transaction_type = Column(String)  # SALE, PAYMENT, RETURN, CREDIT_ADJ
    reference_id = Column(String, nullable=True)  # invoice/payment ID
    amount = Column(Float)  # positive = customer owes more, negative = reduces balance
    balance_after = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(String, nullable=True)

    customer = relationship("Customer", back_populates="ledger")

class CustomerPayment(Base):
    __tablename__ = "customer_payments"

    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True)  # CPAY-000001
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    amount = Column(Float)
    payment_method = Column(String)  # Cash, Bank, Credit Note
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(String, nullable=True)

    customer = relationship("Customer", back_populates="payments")

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True)  # SUP-000001
    name = Column(String, index=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    tax_details = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    balance = Column(Float, default=0.0)

    products = relationship("Product", secondary=product_supplier_assoc, back_populates="suppliers")
