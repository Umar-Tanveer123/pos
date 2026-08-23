from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.core.database import get_db
from backend.models.auth import User, Location
from backend.models.purchase import (
    PurchaseInvoice, PurchaseItem, SupplierReturn, SupplierReturnItem,
    SupplierLedger, SupplierPayment
)
from backend.models.partner import Supplier
from backend.models.product import Product
from backend.models.ledger import InventoryTransaction, TransactionType
from backend.api.auth import get_current_active_user

router = APIRouter()

# ── Schemas ──────────────────────────────────────────────────────────────────

class ReturnItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: float

class SupplierReturnCreate(BaseModel):
    purchase_id: int
    location_id: int
    return_type: str = "RETURN"   # "RETURN" or "EXCHANGE"
    reason: Optional[str] = None
    notes: Optional[str] = None
    items: List[ReturnItemCreate]

class ReturnItemResponse(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int]
    quantity: float
    purchase_price: float
    product_name: Optional[str] = None

    class Config:
        from_attributes = True

class SupplierReturnResponse(BaseModel):
    id: int
    internal_id: str
    purchase_id: int
    purchase_ref: Optional[str] = None
    supplier_id: int
    supplier_name: Optional[str] = None
    location_id: int
    return_type: str
    reason: Optional[str]
    notes: Optional[str]
    status: str
    created_at: datetime
    items: List[ReturnItemResponse] = []
    total_credit: float = 0.0

    class Config:
        from_attributes = True

# ── Helper ────────────────────────────────────────────────────────────────────

def build_return_response(ret: SupplierReturn) -> SupplierReturnResponse:
    items_out = []
    total_credit = 0.0
    for it in ret.items:
        product_name = it.product.name if it.product else None
        items_out.append(ReturnItemResponse(
            id=it.id,
            product_id=it.product_id,
            variant_id=it.variant_id,
            quantity=it.quantity,
            purchase_price=it.purchase_price,
            product_name=product_name,
        ))
        total_credit += it.quantity * it.purchase_price

    return SupplierReturnResponse(
        id=ret.id,
        internal_id=ret.internal_id,
        purchase_id=ret.purchase_id,
        purchase_ref=ret.purchase.internal_id if ret.purchase else None,
        supplier_id=ret.supplier_id,
        supplier_name=ret.supplier.name if ret.supplier else None,
        location_id=ret.location_id,
        return_type=ret.return_type,
        reason=ret.reason,
        notes=ret.notes,
        status=ret.status,
        created_at=ret.created_at,
        items=items_out,
        total_credit=total_credit,
    )

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[SupplierReturnResponse])
def get_supplier_returns(
    supplier_id: Optional[int] = None,
    return_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(SupplierReturn)
    if supplier_id:
        query = query.filter(SupplierReturn.supplier_id == supplier_id)
    if return_type:
        query = query.filter(SupplierReturn.return_type == return_type)
    returns = query.order_by(SupplierReturn.created_at.desc()).all()
    return [build_return_response(r) for r in returns]


@router.get("/{return_id}", response_model=SupplierReturnResponse)
def get_supplier_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    ret = db.query(SupplierReturn).filter(SupplierReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Supplier return not found")
    return build_return_response(ret)


@router.get("/purchase/{purchase_id}/returnable", response_model=List[dict])
def get_returnable_items(
    purchase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns each purchase item alongside how many units are still eligible for return.
    Quantities are expressed in **base units** (e.g. pieces) even when the purchase
    was recorded in a secondary unit (e.g. cartons).  This ensures the user sees
    the same numbers that appear in inventory.
    """
    purchase = db.query(PurchaseInvoice).filter(PurchaseInvoice.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")

    result = []
    for item in purchase.items:
        product = item.product

        # Determine the conversion factor that was applied when inventory was added
        conversion = 1.0
        item_unit_id = item.unit_id
        if (
            item_unit_id
            and product
            and product.secondary_unit_id == item_unit_id
            and product.conversion_factor
        ):
            conversion = product.conversion_factor

        purchased_base = item.quantity * conversion

        already_returned = (
            db.query(func.sum(SupplierReturnItem.quantity))
            .join(SupplierReturn)
            .filter(
                SupplierReturn.purchase_id == purchase_id,
                SupplierReturnItem.product_id == item.product_id,
                SupplierReturnItem.variant_id == item.variant_id,
            )
            .scalar() or 0.0
        )
        returnable_qty = purchased_base - already_returned
        if returnable_qty > 0:
            unit_name = None
            if product and product.unit:
                unit_name = product.unit.name

            result.append({
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "product_name": product.name if product else f"Product {item.product_id}",
                "purchased_qty": purchased_base,
                "already_returned": already_returned,
                "returnable_qty": returnable_qty,
                "purchase_price": item.purchase_price / conversion if conversion > 1 else item.purchase_price,
                "unit_name": unit_name,
            })
    return result


@router.post("/", response_model=SupplierReturnResponse, status_code=status.HTTP_201_CREATED)
def create_supplier_return(
    return_in: SupplierReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not return_in.items:
        raise HTTPException(status_code=400, detail="At least one item is required.")

    purchase = db.query(PurchaseInvoice).filter(PurchaseInvoice.id == return_in.purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase invoice not found")

    supplier = db.query(Supplier).filter(Supplier.id == purchase.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Build purchase item map for validation
    purchase_item_map: dict[tuple, PurchaseItem] = {}
    for pi in purchase.items:
        purchase_item_map[(pi.product_id, pi.variant_id)] = pi

    # Validate quantities (all quantities are now in base units)
    validated_items = []
    total_credit = 0.0
    for it in return_in.items:
        key = (it.product_id, it.variant_id)
        pi = purchase_item_map.get(key)
        if not pi:
            raise HTTPException(
                status_code=400,
                detail=f"Product ID {it.product_id} was not part of purchase {purchase.internal_id}."
            )
        
        # Convert purchased qty to base units (same logic as returnable endpoint)
        conversion = 1.0
        product = pi.product
        if (
            pi.unit_id
            and product
            and product.secondary_unit_id == pi.unit_id
            and product.conversion_factor
        ):
            conversion = product.conversion_factor
        
        purchased_base = pi.quantity * conversion
        
        already_returned = (
            db.query(func.sum(SupplierReturnItem.quantity))
            .join(SupplierReturn)
            .filter(
                SupplierReturn.purchase_id == return_in.purchase_id,
                SupplierReturnItem.product_id == it.product_id,
                SupplierReturnItem.variant_id == it.variant_id,
            )
            .scalar() or 0.0
        )
        returnable = purchased_base - already_returned
        if it.quantity > returnable:
            raise HTTPException(
                status_code=400,
                detail=f"Return qty {it.quantity} exceeds returnable qty {returnable} for product {it.product_id}."
            )
        
        # Per-base-unit purchase price for credit calculation
        per_unit_price = pi.purchase_price / conversion if conversion > 1 else pi.purchase_price
        
        validated_items.append((it, pi, per_unit_price))
        total_credit += it.quantity * per_unit_price

    # Auto-generate ID
    max_id = db.query(func.max(SupplierReturn.id)).scalar() or 0
    from backend.api.settings import get_prefix
    sret_prefix = get_prefix(db, "prefix_supplier_return", "SRET-")
    internal_id = f"{sret_prefix}{max_id + 1:06d}"

    ret = SupplierReturn(
        internal_id=internal_id,
        purchase_id=return_in.purchase_id,
        supplier_id=supplier.id,
        location_id=return_in.location_id,
        user_id=current_user.id,
        return_type=return_in.return_type,
        reason=return_in.reason,
        notes=return_in.notes,
        status="COMPLETED" if return_in.return_type == "RETURN" else "PENDING",
    )
    db.add(ret)
    db.flush()

    for it, pi, per_unit_price in validated_items:
        ret_item = SupplierReturnItem(
            return_id=ret.id,
            product_id=it.product_id,
            variant_id=it.variant_id,
            quantity=it.quantity,  # stored in base units
            purchase_price=per_unit_price,
        )
        db.add(ret_item)

        # Decrease inventory at specified location
        # Quantity is already in base units – no conversion needed
        inv_tx = InventoryTransaction(
            product_id=it.product_id,
            variant_id=it.variant_id,
            location_id=return_in.location_id,
            transaction_type=TransactionType.ADJUSTMENT,
            quantity=-it.quantity,  # negative = stock decrease
            reference_id=internal_id,
            user_id=current_user.id,
        )
        db.add(inv_tx)

    # Credit supplier ledger (return reduces what we owe them)
    supplier.balance -= total_credit
    ledger_entry = SupplierLedger(
        supplier_id=supplier.id,
        transaction_type="RETURN",
        reference_id=internal_id,
        amount=-total_credit,
        balance_after=supplier.balance,
        notes=f"Supplier return {internal_id} against {purchase.internal_id}",
    )
    db.add(ledger_entry)

    db.commit()
    db.refresh(ret)
    return build_return_response(ret)


@router.post("/{return_id}/complete-exchange", response_model=SupplierReturnResponse)
def complete_exchange(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Mark an EXCHANGE return as completed and add replacement stock back to inventory.
    """
    ret = db.query(SupplierReturn).filter(SupplierReturn.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    if ret.return_type != "EXCHANGE":
        raise HTTPException(status_code=400, detail="Only EXCHANGE type returns can be completed here.")
    if ret.status == "EXCHANGED":
        raise HTTPException(status_code=400, detail="Exchange already completed.")

    # Add replacement stock back (quantities are already in base units)
    for item in ret.items:
        inv_tx = InventoryTransaction(
            product_id=item.product_id,
            variant_id=item.variant_id,
            location_id=ret.location_id,
            transaction_type=TransactionType.ADJUSTMENT,
            quantity=item.quantity,  # positive = stock comes back
            reference_id=f"{ret.internal_id}-EXCHANGE",
            user_id=current_user.id,
        )
        db.add(inv_tx)

    ret.status = "EXCHANGED"
    db.commit()
    db.refresh(ret)
    return build_return_response(ret)
