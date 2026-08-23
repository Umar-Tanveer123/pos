from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.core.database import get_db
from backend.models.purchase import PurchaseInvoice, PurchaseItem, SupplierLedger, SupplierPayment, PriceAuditLog
from backend.models.partner import Supplier
from backend.models.product import Product
from backend.models.ledger import InventoryTransaction, TransactionType
from backend.models.auth import User
from backend.api.auth import get_current_active_user

router = APIRouter()

# --- Pydantic Schemas ---
class PurchaseItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: float
    unit_id: Optional[int] = None
    purchase_price: float
    discount: Optional[float] = 0.0

class PurchaseCreate(BaseModel):
    supplier_id: int
    location_id: int
    supplier_invoice_number: Optional[str] = None
    discount: Optional[float] = 0.0
    paid_amount: Optional[float] = 0.0
    notes: Optional[str] = None
    items: List[PurchaseItemCreate]
    due_date: Optional[datetime] = None

class PurchaseItemResponse(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int]
    quantity: float
    unit_id: Optional[int]
    purchase_price: float
    discount: float
    total: float

    class Config:
        from_attributes = True

class PurchaseResponse(BaseModel):
    id: int
    internal_id: str
    supplier_id: int
    supplier_invoice_number: Optional[str]
    date: datetime
    location_id: int
    user_id: int
    discount: float
    total_amount: float
    paid_amount: float
    payable_amount: float
    due_date: Optional[datetime]
    notes: Optional[str]
    items: List[PurchaseItemResponse]

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.get("/", response_model=List[PurchaseResponse])
def get_purchases(
    supplier_id: Optional[int] = None,
    location_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(PurchaseInvoice)
    if supplier_id:
        query = query.filter(PurchaseInvoice.supplier_id == supplier_id)
    if location_id:
        query = query.filter(PurchaseInvoice.location_id == location_id)
    return query.order_by(PurchaseInvoice.date.desc()).all()

@router.get("/{purchase_id}", response_model=PurchaseResponse)
def get_purchase(
    purchase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    purchase = db.query(PurchaseInvoice).filter(PurchaseInvoice.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase invoice not found")
    return purchase

@router.post("/", response_model=PurchaseResponse)
def create_purchase(
    purchase_in: PurchaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Role validation: Admin or Manager only
    if not current_user.role or current_user.role.name not in ["Admin", "Manager"]:
        raise HTTPException(status_code=403, detail="Only Admins or Managers can record purchases.")
        
    if not purchase_in.items:
        raise HTTPException(status_code=400, detail="A purchase must contain at least one item.")
        
    supplier = db.query(Supplier).filter(Supplier.id == purchase_in.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    # Calculate totals
    subtotal = 0.0
    items_to_create = []
    
    for item in purchase_in.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {item.product_id} not found")
            

        # Total cost for this item line
        item_total = (item.quantity * item.purchase_price) - (item.discount or 0.0)
        if item_total < 0:
            item_total = 0.0
        subtotal += item_total
        
        items_to_create.append((product, item, item_total))
        
    total_amount = subtotal - (purchase_in.discount or 0.0)
    if total_amount < 0:
        total_amount = 0.0
        
    paid = purchase_in.paid_amount or 0.0
    payable = total_amount - paid
    
    # Auto-generate unique Purchase ID
    max_id = db.query(func.max(PurchaseInvoice.id)).scalar() or 0
    from backend.api.settings import get_prefix
    pur_prefix = get_prefix(db, "prefix_purchase", "PUR-")
    internal_id = f"{pur_prefix}{max_id + 1:06d}"
    
    # 1. Create Purchase Invoice
    purchase = PurchaseInvoice(
        internal_id=internal_id,
        supplier_id=purchase_in.supplier_id,
        supplier_invoice_number=purchase_in.supplier_invoice_number,
        location_id=purchase_in.location_id,
        user_id=current_user.id,
        discount=purchase_in.discount or 0.0,
        total_amount=total_amount,
        paid_amount=paid,
        payable_amount=payable,
        due_date=purchase_in.due_date,
        notes=purchase_in.notes
    )
    db.add(purchase)
    db.flush() # populated purchase.id for items
    
    # 2. Add Supplier Ledger Purchases entries
    # Update supplier balance
    supplier.balance += payable
    
    # Add Purchase Ledger record (+total_amount)
    purchase_ledger = SupplierLedger(
        supplier_id=supplier.id,
        transaction_type="PURCHASE",
        reference_id=internal_id,
        amount=total_amount,
        balance_after=supplier.balance + paid, # Before payment is deducted
        notes=f"Purchase invoice {internal_id} recorded"
    )
    db.add(purchase_ledger)
    
    # If there is a payment at the time of purchase, log a payment ledger entry (-paid_amount)
    if paid > 0:
        # Create Supplier Payment
        max_pay_id = db.query(func.max(SupplierPayment.id)).scalar() or 0
        from backend.api.settings import get_prefix
        spay_prefix = get_prefix(db, "prefix_supplier_pay", "SPAY-")
        payment_internal_id = f"{spay_prefix}{max_pay_id + 1:06d}"
        
        payment = SupplierPayment(
            internal_id=payment_internal_id,
            supplier_id=supplier.id,
            purchase_id=purchase.id,
            amount=paid,
            payment_method="Cash", # Default to Cash for instant payment
            notes=f"Downpayment on purchase {internal_id}"
        )
        db.add(payment)
        
        payment_ledger = SupplierLedger(
            supplier_id=supplier.id,
            transaction_type="PAYMENT",
            reference_id=payment_internal_id,
            amount=-paid,
            balance_after=supplier.balance,
            notes=f"Downpayment for purchase {internal_id}"
        )
        db.add(payment_ledger)
        
    # 3. Create items, update catalog cost price, write price logs, adjust stock ledger
    for product, item, item_total in items_to_create:
        if supplier not in product.suppliers:
            product.suppliers.append(supplier)
            
        db_item = PurchaseItem(
            purchase_id=purchase.id,
            product_id=product.id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_id=item.unit_id or product.unit_id,
            purchase_price=item.purchase_price,
            discount=item.discount or 0.0,
            total=item_total
        )
        db.add(db_item)
        
        # Audit log the price update if it changes
        if product.purchase_price != item.purchase_price:
            audit_log = PriceAuditLog(
                product_id=product.id,
                user_id=current_user.id,
                old_purchase_price=product.purchase_price,
                new_purchase_price=item.purchase_price,
                old_retail_price=product.retail_price,
                new_retail_price=product.retail_price,
                old_wholesale_price=product.wholesale_price,
                new_wholesale_price=product.wholesale_price,
                old_special_price=product.special_price,
                new_special_price=product.special_price,
                change_type="PURCHASE"
            )
            db.add(audit_log)
            # Update product's current cost
            product.purchase_price = item.purchase_price
            
        # 4. Inventory Transaction to increase stock at target location
        # Check for unit conversion
        qty_in_base_units = item.quantity
        item_unit_id = item.unit_id or product.unit_id
        if item_unit_id and product.secondary_unit_id == item_unit_id and product.conversion_factor:
            qty_in_base_units = item.quantity * product.conversion_factor

        inv_trans = InventoryTransaction(
            product_id=product.id,
            variant_id=item.variant_id,
            location_id=purchase_in.location_id,
            transaction_type=TransactionType.PURCHASE,
            quantity=qty_in_base_units,
            reference_id=internal_id,
            user_id=current_user.id
        )
        db.add(inv_trans)
        
    db.commit()
    db.refresh(purchase)
    return purchase
