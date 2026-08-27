from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.core.database import get_db
from backend.models.sale import SaleInvoice, SaleItem, SalePayment, InvoiceTemplate
from backend.models.partner import Customer, CustomerLedger, CustomerPayment
from backend.models.product import Product, ProductVariant
from backend.models.ledger import InventoryTransaction, TransactionType
from backend.models.auth import User
from backend.api.auth import get_current_active_user

router = APIRouter()

# ── Payment Methods ──
PAYMENT_METHODS = ["Cash", "Bank Transfer", "Card", "JazzCash", "Easypaisa"]

# --- Pydantic Schemas ---
class SaleItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: float
    unit_id: Optional[int] = None
    unit_price: float
    discount: Optional[float] = 0.0

class SalePaymentCreate(BaseModel):
    payment_method: str  # Cash, Bank Transfer, Card, JazzCash, Easypaisa
    amount: float
    reference: Optional[str] = None

class SaleCreate(BaseModel):
    customer_id: int
    location_id: int
    discount: Optional[float] = 0.0
    paid_amount: Optional[float] = 0.0
    notes: Optional[str] = None
    items: List[SaleItemCreate]
    payments: Optional[List[SalePaymentCreate]] = None  # Split payment support
    due_date: Optional[datetime] = None

class SaleItemResponse(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int]
    quantity: float
    unit_id: Optional[int]
    unit_price: float
    discount: float
    total: float

    class Config:
        from_attributes = True

class SalePaymentResponse(BaseModel):
    id: int
    payment_method: str
    amount: float
    reference: Optional[str]

    class Config:
        from_attributes = True

class SaleResponse(BaseModel):
    id: int
    internal_id: str
    customer_id: int
    date: datetime
    location_id: int
    user_id: int
    discount: float
    total_amount: float
    paid_amount: float
    balance_owed: float
    due_date: Optional[datetime]
    notes: Optional[str]
    status: Optional[str] = "COMPLETED"
    items: List[SaleItemResponse]
    payments: List[SalePaymentResponse] = []

    class Config:
        from_attributes = True

# Invoice Template schemas
class InvoiceTemplateResponse(BaseModel):
    id: int
    name: str
    is_default: bool
    logo_path: Optional[str]
    header_text: Optional[str]
    footer_text: Optional[str]
    business_name: Optional[str]
    business_address: Optional[str]
    business_phone: Optional[str]
    business_email: Optional[str]
    show_logo: bool
    show_customer_info: bool
    show_payment_info: bool
    show_notes: bool
    show_discount_column: bool
    show_sku: bool
    paper_size: str
    template_type: str

    class Config:
        from_attributes = True

class InvoiceTemplateUpdate(BaseModel):
    name: Optional[str] = None
    is_default: Optional[bool] = None
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    business_name: Optional[str] = None
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    business_email: Optional[str] = None
    show_logo: Optional[bool] = None
    show_customer_info: Optional[bool] = None
    show_payment_info: Optional[bool] = None
    show_notes: Optional[bool] = None
    show_discount_column: Optional[bool] = None
    show_sku: Optional[bool] = None
    paper_size: Optional[str] = None

class InvoiceTemplateCreate(BaseModel):
    name: str
    is_default: Optional[bool] = False
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    business_name: Optional[str] = None
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    business_email: Optional[str] = None
    show_logo: Optional[bool] = True
    show_customer_info: Optional[bool] = True
    show_payment_info: Optional[bool] = True
    show_notes: Optional[bool] = True
    show_discount_column: Optional[bool] = True
    show_sku: Optional[bool] = False
    paper_size: Optional[str] = "80mm"
    template_type: Optional[str] = "Standard"

# --- Endpoints ---

@router.get("/payment-methods")
def get_payment_methods():
    return PAYMENT_METHODS

@router.get("/", response_model=List[SaleResponse])
def get_sales(
    customer_id: Optional[int] = None,
    location_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(SaleInvoice)
    if customer_id:
        query = query.filter(SaleInvoice.customer_id == customer_id)
    if location_id:
        query = query.filter(SaleInvoice.location_id == location_id)
    return query.order_by(SaleInvoice.date.desc()).all()

@router.get("/templates", response_model=List[InvoiceTemplateResponse])
def get_invoice_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return db.query(InvoiceTemplate).all()

@router.put("/templates/{template_id}", response_model=InvoiceTemplateResponse)
def update_invoice_template(
    template_id: int,
    template_in: InvoiceTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    tmpl = db.query(InvoiceTemplate).filter(InvoiceTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    
    for field, value in template_in.model_dump(exclude_unset=True).items():
        setattr(tmpl, field, value)
    
    # If setting as default, un-default others
    if template_in.is_default:
        db.query(InvoiceTemplate).filter(InvoiceTemplate.id != template_id).update({"is_default": False})
    
    db.commit()
    db.refresh(tmpl)
    return tmpl

@router.post("/templates", response_model=InvoiceTemplateResponse, status_code=201)
def create_invoice_template(
    template_in: InvoiceTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    existing = db.query(InvoiceTemplate).filter(InvoiceTemplate.name == template_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template with this name already exists.")
    tmpl = InvoiceTemplate(**template_in.model_dump())
    db.add(tmpl)
    db.commit()
    
    if template_in.is_default:
        db.query(InvoiceTemplate).filter(InvoiceTemplate.id != tmpl.id).update({"is_default": False})
        db.commit()
        
    db.refresh(tmpl)
    return tmpl

@router.get("/{sale_id}", response_model=SaleResponse)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sale = db.query(SaleInvoice).filter(SaleInvoice.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale invoice not found")
    return sale

@router.post("/", response_model=SaleResponse)
def create_sale(
    sale_in: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not sale_in.items:
        raise HTTPException(status_code=400, detail="A sale must contain at least one item.")
        
    customer = db.query(Customer).filter(Customer.id == sale_in.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    # Calculate totals
    subtotal = 0.0
    items_to_create = []
    
    for item in sale_in.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {item.product_id} not found")
            
        # Inventory Check (Negative Stock Validation - SRS 30.2)
        qty_in_base_units = item.quantity
        item_unit_id = item.unit_id or (product.unit_id if product else None)
        if product and item_unit_id and product.secondary_unit_id == item_unit_id and product.conversion_factor:
            qty_in_base_units = item.quantity * product.conversion_factor
            
        current_stock = db.query(func.sum(InventoryTransaction.quantity)).filter(
            InventoryTransaction.product_id == item.product_id,
            InventoryTransaction.variant_id == item.variant_id,
            InventoryTransaction.location_id == sale_in.location_id
        ).scalar() or 0.0
        
        if current_stock < qty_in_base_units:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}. Available: {current_stock}, Requested (Base Units): {qty_in_base_units}"
            )
            
        item_total = (item.quantity * item.unit_price) - (item.discount or 0.0)
        if item_total < 0:
            item_total = 0.0
        subtotal += item_total
        
        items_to_create.append((product, item, item_total, qty_in_base_units))
        
    total_amount = subtotal - (sale_in.discount or 0.0)
    if total_amount < 0:
        total_amount = 0.0
        
    # Calculate total paid from split payments or fallback to paid_amount
    if sale_in.payments:
        paid = sum(p.amount for p in sale_in.payments)
    else:
        paid = sale_in.paid_amount or 0.0
        
    balance_owed = total_amount - paid
    if balance_owed < 0:
        balance_owed = 0.0
    
    # 1. Validation: Credit Limit check
    # Walk-in customer typically shouldn't run on credit, but we check limit
    if balance_owed > 0:
        new_balance = customer.balance + balance_owed
        if customer.credit_limit > 0 and new_balance > customer.credit_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Credit limit exceeded! Customer credit limit is Rs. {customer.credit_limit:,.2f}, but new balance would be Rs. {new_balance:,.2f}."
            )
            
    # Auto-generate unique Invoice ID (SRS 50)
    max_id = db.query(func.max(SaleInvoice.id)).scalar() or 0
    from backend.api.settings import get_prefix
    inv_prefix = get_prefix(db, "prefix_invoice", "INV-")
    internal_id = f"{inv_prefix}{max_id + 1:06d}"
    
    # 2. Create Sale Invoice
    sale = SaleInvoice(
        internal_id=internal_id,
        customer_id=sale_in.customer_id,
        location_id=sale_in.location_id,
        user_id=current_user.id,
        discount=sale_in.discount or 0.0,
        total_amount=total_amount,
        paid_amount=paid,
        balance_owed=balance_owed,
        due_date=sale_in.due_date,
        notes=sale_in.notes,
        status="COMPLETED"
    )
    db.add(sale)
    db.flush() # populated sale.id
    
    # 3. Record split payments
    if sale_in.payments:
        for p in sale_in.payments:
            sp = SalePayment(
                sale_id=sale.id,
                payment_method=p.payment_method,
                amount=p.amount,
                reference=p.reference
            )
            db.add(sp)
    elif paid > 0:
        # Legacy single-payment fallback
        sp = SalePayment(
            sale_id=sale.id,
            payment_method="Cash",
            amount=paid,
            reference=None
        )
        db.add(sp)
    
    # 4. Customer Ledger entry for Sale
    customer.balance += balance_owed
    
    sale_ledger = CustomerLedger(
        customer_id=customer.id,
        transaction_type="SALE",
        reference_id=internal_id,
        amount=balance_owed, # increase customer balance by credit portion
        balance_after=customer.balance,
        notes=f"Sale invoice {internal_id} recorded"
    )
    db.add(sale_ledger)
    
    # If there is a payment at the time of sale, record CustomerPayment
    if paid > 0:
        max_pay_id = db.query(func.max(CustomerPayment.id)).scalar() or 0
        from backend.api.settings import get_prefix
        cpay_prefix = get_prefix(db, "prefix_customer_pay", "CPAY-")
        payment_internal_id = f"{cpay_prefix}{max_pay_id + 1:06d}"
        
        # Build description of payment methods used
        if sale_in.payments:
            methods_desc = ", ".join(f"{p.payment_method}: Rs.{p.amount:.2f}" for p in sale_in.payments)
        else:
            methods_desc = "Cash"
        
        payment = CustomerPayment(
            internal_id=payment_internal_id,
            customer_id=customer.id,
            amount=paid,
            payment_method=methods_desc,
            notes=f"Payment on sale invoice {internal_id}"
        )
        db.add(payment)
        
    # 5. Create items and adjust inventory (negative quantity)
    for product, item, item_total, qty_in_base_units in items_to_create:
        db_item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_id=item.unit_id or product.unit_id,
            unit_price=item.unit_price,
            discount=item.discount or 0.0,
            total=item_total
        )
        db.add(db_item)
        
        # Inventory transaction to decrease stock

        inv_trans = InventoryTransaction(
            product_id=product.id,
            variant_id=item.variant_id,
            location_id=sale_in.location_id,
            transaction_type=TransactionType.SALE,
            quantity=-qty_in_base_units, # Negative for sales
            reference_id=internal_id,
            user_id=current_user.id
        )
        db.add(inv_trans)
        
    db.commit()
    db.refresh(sale)
    
    from backend.api.audit import log_action
    log_action(db, user_id=current_user.id, action="Sale", record_id=sale.internal_id, location_id=sale.location_id, details=f"Sale created. Total: Rs. {sale.total_amount:.2f}")
    
    return sale

# ── Sale Return ──

@router.post("/{sale_id}/return", response_model=SaleResponse)
def return_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Full return: reverses inventory, credits customer, marks invoice RETURNED."""
    sale = db.query(SaleInvoice).filter(SaleInvoice.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale invoice not found")
    if sale.status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"Cannot return sale with status '{sale.status}'.")
    
    customer = db.query(Customer).filter(Customer.id == sale.customer_id).first()
    
    # Reverse inventory for each item
    for item in sale.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        
        qty_in_base_units = item.quantity
        item_unit_id = item.unit_id or (product.unit_id if product else None)
        if product and item_unit_id and product.secondary_unit_id == item_unit_id and product.conversion_factor:
            qty_in_base_units = item.quantity * product.conversion_factor
        
        inv_trans = InventoryTransaction(
            product_id=item.product_id,
            variant_id=item.variant_id,
            location_id=sale.location_id,
            transaction_type=TransactionType.ADJUSTMENT,
            quantity=qty_in_base_units,  # Positive = stock restored
            reference_id=f"RETURN-{sale.internal_id}",
            user_id=current_user.id
        )
        db.add(inv_trans)
    
    # Reverse customer balance: remove the credit portion
    if customer and sale.balance_owed > 0:
        customer.balance -= sale.balance_owed
        
        return_ledger = CustomerLedger(
            customer_id=customer.id,
            transaction_type="RETURN",
            reference_id=f"RETURN-{sale.internal_id}",
            amount=-sale.balance_owed,
            balance_after=customer.balance,
            notes=f"Full return of sale invoice {sale.internal_id}"
        )
        db.add(return_ledger)
    
    sale.status = "RETURNED"
    db.commit()
    db.refresh(sale)
    
    from backend.api.audit import log_action
    log_action(db, user_id=current_user.id, action="Return", record_id=sale.internal_id, location_id=sale.location_id, details=f"Sale invoice {sale.internal_id} returned")
    
    return sale

# ── Sale Cancellation ──

@router.post("/{sale_id}/cancel", response_model=SaleResponse)
def cancel_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a completed sale: reverses inventory, credits customer, marks CANCELLED."""
    sale = db.query(SaleInvoice).filter(SaleInvoice.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale invoice not found")
    if sale.status != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"Cannot cancel sale with status '{sale.status}'.")
    
    customer = db.query(Customer).filter(Customer.id == sale.customer_id).first()
    
    # Reverse inventory for each item
    for item in sale.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        
        qty_in_base_units = item.quantity
        item_unit_id = item.unit_id or (product.unit_id if product else None)
        if product and item_unit_id and product.secondary_unit_id == item_unit_id and product.conversion_factor:
            qty_in_base_units = item.quantity * product.conversion_factor
        
        inv_trans = InventoryTransaction(
            product_id=item.product_id,
            variant_id=item.variant_id,
            location_id=sale.location_id,
            transaction_type=TransactionType.ADJUSTMENT,
            quantity=qty_in_base_units,  # Positive = stock restored
            reference_id=f"CANCEL-{sale.internal_id}",
            user_id=current_user.id
        )
        db.add(inv_trans)
    
    # Reverse customer balance
    if customer and sale.balance_owed > 0:
        customer.balance -= sale.balance_owed
        
        cancel_ledger = CustomerLedger(
            customer_id=customer.id,
            transaction_type="CANCELLATION",
            reference_id=f"CANCEL-{sale.internal_id}",
            amount=-sale.balance_owed,
            balance_after=customer.balance,
            notes=f"Cancellation of sale invoice {sale.internal_id}"
        )
        db.add(cancel_ledger)
    
    sale.status = "CANCELLED"
    db.commit()
    db.refresh(sale)
    return sale
