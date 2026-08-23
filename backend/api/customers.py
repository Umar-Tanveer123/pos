from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.core.database import get_db
from backend.models.auth import User
from backend.models.partner import Customer, CustomerType, CustomerLedger, CustomerPayment
from backend.api.auth import get_current_active_user

router = APIRouter()

# ── Schemas ──────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    customer_type_id: Optional[int] = None
    credit_limit: float = 0.0
    notes: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    customer_type_id: Optional[int] = None
    credit_limit: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[int] = None

class CustomerResponse(BaseModel):
    id: int
    internal_id: str
    name: str
    phone: Optional[str]
    address: Optional[str]
    customer_type_id: Optional[int]
    customer_type_name: Optional[str] = None
    credit_limit: float
    balance: float
    notes: Optional[str]
    is_active: int

    class Config:
        from_attributes = True

class CustomerLedgerResponse(BaseModel):
    id: int
    customer_id: int
    transaction_type: str
    reference_id: Optional[str]
    amount: float
    balance_after: float
    created_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True

class CustomerPaymentCreate(BaseModel):
    amount: float
    payment_method: str
    notes: Optional[str] = None

class CustomerPaymentResponse(BaseModel):
    id: int
    internal_id: str
    customer_id: int
    amount: float
    payment_method: str
    created_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True

class CustomerTypeResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

# ── Helpers ───────────────────────────────────────────────────────────────────

def to_customer_response(c: Customer) -> CustomerResponse:
    return CustomerResponse(
        id=c.id,
        internal_id=c.internal_id,
        name=c.name,
        phone=c.phone,
        address=c.address,
        customer_type_id=c.customer_type_id,
        customer_type_name=c.customer_type.name if c.customer_type else None,
        credit_limit=c.credit_limit,
        balance=c.balance,
        notes=c.notes,
        is_active=c.is_active,
    )

# ── Customer Type Endpoints ────────────────────────────────────────────────────

@router.get("/types", response_model=List[CustomerTypeResponse])
def get_customer_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return db.query(CustomerType).all()

# ── Customer CRUD ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[CustomerResponse])
def get_customers(
    search: Optional[str] = None,
    customer_type_id: Optional[int] = None,
    is_active: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(Customer)
    if search:
        query = query.filter(
            (Customer.name.ilike(f"%{search}%")) |
            (Customer.internal_id.ilike(f"%{search}%")) |
            (Customer.phone.ilike(f"%{search}%"))
        )
    if customer_type_id is not None:
        query = query.filter(Customer.customer_type_id == customer_type_id)
    if is_active is not None:
        query = query.filter(Customer.is_active == is_active)
    customers = query.order_by(Customer.name).all()
    return [to_customer_response(c) for c in customers]


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return to_customer_response(c)


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    max_id = db.query(func.max(Customer.id)).scalar() or 0
    from backend.api.settings import get_prefix
    cus_prefix = get_prefix(db, "prefix_customer", "CUS-")
    internal_id = f"{cus_prefix}{max_id + 1:06d}"

    c = Customer(
        internal_id=internal_id,
        name=customer_in.name,
        phone=customer_in.phone,
        address=customer_in.address,
        customer_type_id=customer_in.customer_type_id,
        credit_limit=customer_in.credit_limit,
        balance=0.0,
        notes=customer_in.notes,
        is_active=1,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return to_customer_response(c)


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    for field, val in customer_in.model_dump(exclude_unset=True).items():
        setattr(c, field, val)
    db.commit()
    db.refresh(c)
    return to_customer_response(c)


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    if c.balance > 0:
        raise HTTPException(status_code=400, detail="Cannot delete customer with outstanding balance.")
    db.delete(c)
    db.commit()
    return {"detail": "Customer deleted successfully"}

# ── Customer Ledger ───────────────────────────────────────────────────────────

@router.get("/{customer_id}/statement", response_model=List[CustomerLedgerResponse])
def get_customer_statement(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return (
        db.query(CustomerLedger)
        .filter(CustomerLedger.customer_id == customer_id)
        .order_by(CustomerLedger.created_at.asc())
        .all()
    )

# ── Customer Payments ─────────────────────────────────────────────────────────

@router.post("/{customer_id}/payments", response_model=CustomerPaymentResponse)
def record_customer_payment(
    customer_id: int,
    payment_in: CustomerPaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")

    max_id = db.query(func.max(CustomerPayment.id)).scalar() or 0
    from backend.api.settings import get_prefix
    cpay_prefix = get_prefix(db, "prefix_customer_pay", "CPAY-")
    internal_id = f"{cpay_prefix}{max_id + 1:06d}"

    payment = CustomerPayment(
        internal_id=internal_id,
        customer_id=customer_id,
        amount=payment_in.amount,
        payment_method=payment_in.payment_method,
        notes=payment_in.notes,
    )
    db.add(payment)

    c.balance -= payment_in.amount

    ledger_entry = CustomerLedger(
        customer_id=customer_id,
        transaction_type="PAYMENT",
        reference_id=internal_id,
        amount=-payment_in.amount,
        balance_after=c.balance,
        notes=payment_in.notes or f"Payment via {payment_in.payment_method}",
    )
    db.add(ledger_entry)

    db.commit()
    db.refresh(payment)
    return payment
