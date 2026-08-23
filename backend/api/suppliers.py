from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.core.database import get_db
from backend.models.partner import Supplier
from backend.models.purchase import SupplierLedger, SupplierPayment
from backend.models.auth import User
from backend.api.auth import get_current_active_user

router = APIRouter()

# --- Pydantic Schemas ---
class SupplierBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    tax_details: Optional[str] = None
    notes: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    tax_details: Optional[str] = None
    notes: Optional[str] = None

class SupplierResponse(SupplierBase):
    id: int
    internal_id: str
    balance: float

    class Config:
        from_attributes = True

class SupplierPaymentCreate(BaseModel):
    amount: float
    payment_method: str # e.g. Cash, Bank, Check
    notes: Optional[str] = None
    purchase_id: Optional[int] = None

class SupplierPaymentResponse(BaseModel):
    id: int
    internal_id: str
    supplier_id: int
    purchase_id: Optional[int]
    amount: float
    payment_method: str
    created_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True

class SupplierLedgerResponse(BaseModel):
    id: int
    supplier_id: int
    transaction_type: str
    reference_id: Optional[str]
    amount: float
    balance_after: float
    created_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.get("/", response_model=List[SupplierResponse])
def get_suppliers(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Supplier)
    if search:
        query = query.filter(
            (Supplier.name.ilike(f"%{search}%")) |
            (Supplier.internal_id.ilike(f"%{search}%")) |
            (Supplier.contact_person.ilike(f"%{search}%"))
        )
    return query.all()

@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

@router.post("/", response_model=SupplierResponse)
def create_supplier(
    supplier_in: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Auto-generate SUP ID using max ID to be completely deletion-safe
    max_id = db.query(func.max(Supplier.id)).scalar() or 0
    from backend.api.settings import get_prefix
    sup_prefix = get_prefix(db, "prefix_supplier", "SUP-")
    internal_id = f"{sup_prefix}{max_id + 1:06d}"
    
    supplier = Supplier(
        internal_id=internal_id,
        name=supplier_in.name,
        phone=supplier_in.phone,
        email=supplier_in.email,
        address=supplier_in.address,
        contact_person=supplier_in.contact_person,
        tax_details=supplier_in.tax_details,
        notes=supplier_in.notes,
        balance=0.0
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    supplier_in: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = supplier_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(supplier, field, val)
        
    db.commit()
    db.refresh(supplier)
    return supplier

@router.delete("/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Check if supplier has any ledger entries or purchases
    ledger_count = db.query(SupplierLedger).filter(SupplierLedger.supplier_id == supplier_id).count()
    if ledger_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete supplier with active transaction history.")
        
    db.delete(supplier)
    db.commit()
    return {"detail": "Supplier deleted successfully"}

@router.get("/{supplier_id}/statement", response_model=List[SupplierLedgerResponse])
def get_supplier_statement(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Check supplier exists
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    ledger_entries = db.query(SupplierLedger).filter(
        SupplierLedger.supplier_id == supplier_id
    ).order_by(SupplierLedger.created_at.asc()).all()
    return ledger_entries

@router.post("/{supplier_id}/payments", response_model=SupplierPaymentResponse)
def record_supplier_payment(
    supplier_id: int,
    payment_in: SupplierPaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
        
    # Auto-generate unique Payment ID
    max_id = db.query(func.max(SupplierPayment.id)).scalar() or 0
    from backend.api.settings import get_prefix
    spay_prefix = get_prefix(db, "prefix_supplier_pay", "SPAY-")
    internal_id = f"{spay_prefix}{max_id + 1:06d}"
    
    payment = SupplierPayment(
        internal_id=internal_id,
        supplier_id=supplier_id,
        purchase_id=payment_in.purchase_id,
        amount=payment_in.amount,
        payment_method=payment_in.payment_method,
        notes=payment_in.notes
    )
    
    # Update supplier balance (we reduce what we owe, so balance decreases)
    supplier.balance -= payment_in.amount
    
    # Add SupplierLedger entry (negative amount since it reduces the payable balance)
    ledger_entry = SupplierLedger(
        supplier_id=supplier_id,
        transaction_type="PAYMENT",
        reference_id=internal_id,
        amount=-payment_in.amount,
        balance_after=supplier.balance,
        notes=payment_in.notes or f"Payment recorded via {payment_in.payment_method}"
    )
    
    db.add(payment)
    db.add(ledger_entry)
    db.commit()
    db.refresh(payment)
    return payment

@router.get("/reports/profit-report")
def get_supplier_profit_report(
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from backend.models.product import Product, ProductVariant
    from backend.models.sale import SaleItem
    
    # Retrieve all suppliers
    suppliers = db.query(Supplier).all()
    
    supplier_report = []
    
    for sup in suppliers:
        associated_products = sup.products
        associated_product_ids = [p.id for p in associated_products]
        
        total_sales_revenue = 0.0
        total_purchase_cost = 0.0
        
        if associated_product_ids:
            sale_items = db.query(SaleItem).filter(SaleItem.product_id.in_(associated_product_ids)).all()
            
            for item in sale_items:
                prod = next((p for p in associated_products if p.id == item.product_id), None)
                if not prod:
                    continue
                    
                purchase_price = 0.0
                if item.variant_id:
                    var = next((v for v in prod.variants if v.id == item.variant_id), None) if prod.variants else None
                    if var and var.purchase_price is not None:
                        purchase_price = var.purchase_price
                    else:
                        purchase_price = prod.purchase_price or 0.0
                else:
                    purchase_price = prod.purchase_price or 0.0
                    
                total_sales_revenue += item.total
                total_purchase_cost += item.quantity * purchase_price
                
        net_profit = total_sales_revenue - total_purchase_cost
        margin = (net_profit / total_sales_revenue * 100.0) if total_sales_revenue > 0 else 0.0
        
        supplier_report.append({
            "supplier_id": sup.id,
            "supplier_name": sup.name,
            "supplier_code": sup.internal_id,
            "total_sales_revenue": total_sales_revenue,
            "total_purchase_cost": total_purchase_cost,
            "net_profit": net_profit,
            "profit_margin_pct": margin
        })
        
    product_report = []
    if supplier_id:
        target_sup = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if target_sup:
            for prod in target_sup.products:
                sale_items = db.query(SaleItem).filter(SaleItem.product_id == prod.id).all()
                prod_qty = 0.0
                prod_revenue = 0.0
                prod_cost = 0.0
                
                for item in sale_items:
                    purchase_price = 0.0
                    if item.variant_id:
                        var = next((v for v in prod.variants if v.id == item.variant_id), None) if prod.variants else None
                        if var and var.purchase_price is not None:
                            purchase_price = var.purchase_price
                        else:
                            purchase_price = prod.purchase_price or 0.0
                    else:
                        purchase_price = prod.purchase_price or 0.0
                        
                    prod_qty += item.quantity
                    prod_revenue += item.total
                    prod_cost += item.quantity * purchase_price
                    
                prod_profit = prod_revenue - prod_cost
                prod_margin = (prod_profit / prod_revenue * 100.0) if prod_revenue > 0 else 0.0
                
                product_report.append({
                    "product_id": prod.id,
                    "product_name": prod.name,
                    "sku": prod.sku,
                    "total_qty_sold": prod_qty,
                    "total_sales_revenue": prod_revenue,
                    "total_purchase_cost": prod_cost,
                    "net_profit": prod_profit,
                    "profit_margin_pct": prod_margin
                })
                
    return {
        "suppliers": supplier_report,
        "products": product_report
    }
