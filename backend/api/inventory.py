from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.core.database import get_db
from backend.models.inventory import StockTransfer, StockTransferItem, StockAdjustment, StockAdjustmentItem
from backend.models.ledger import InventoryTransaction, TransactionType
from backend.models.product import Product, ProductVariant
from backend.models.auth import User, Role
from backend.api.auth import get_current_active_user

router = APIRouter()

# --- Schemas ---

class TransferItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: float

class TransferCreate(BaseModel):
    source_location_id: int
    destination_location_id: int
    items: List[TransferItem]
    notes: Optional[str] = None

class AdjustmentItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    actual_quantity: float

class AdjustmentCreate(BaseModel):
    location_id: int
    items: List[AdjustmentItem]
    reason: Optional[str] = None

# --- Low Stock Alert Endpoint (SRS 33) ---
@router.get("/low-stock")
def get_low_stock_alerts(db: Session = Depends(get_db)):
    # Calculate total stock per product variant across all locations
    # (Simplified: Just check product total, or variant total if variants exist)
    
    alerts = []
    products = db.query(Product).filter(Product.is_active == True).all()
    
    for p in products:
        threshold = p.low_stock_threshold or 0
        
        if not p.variants:
            current_stock = db.query(func.sum(InventoryTransaction.quantity)).filter(
                InventoryTransaction.product_id == p.id
            ).scalar() or 0.0
            
            if current_stock <= threshold:
                alerts.append({
                    "product_id": p.id,
                    "product_name": p.name,
                    "variant_name": None,
                    "current_stock": current_stock,
                    "threshold": threshold
                })
        else:
            for v in p.variants:
                current_stock = db.query(func.sum(InventoryTransaction.quantity)).filter(
                    InventoryTransaction.product_id == p.id,
                    InventoryTransaction.variant_id == v.id
                ).scalar() or 0.0
                
                if current_stock <= threshold:
                    alerts.append({
                        "product_id": p.id,
                        "product_name": p.name,
                        "variant_name": v.name,
                        "current_stock": current_stock,
                        "threshold": threshold
                    })
                    
    return alerts


# --- Stock Transfer Endpoints (SRS 31) ---

@router.post("/transfer")
def create_transfer(
    req: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if req.source_location_id == req.destination_location_id:
        raise HTTPException(status_code=400, detail="Source and destination cannot be the same.")
        
    max_id = db.query(func.max(StockTransfer.id)).scalar() or 0
    from backend.api.settings import get_prefix
    trf_prefix = get_prefix(db, "prefix_transfer", "TRF-")
    internal_id = f"{trf_prefix}{max_id + 1:06d}"
    
    transfer = StockTransfer(
        internal_id=internal_id,
        source_location_id=req.source_location_id,
        destination_location_id=req.destination_location_id,
        user_id=current_user.id,
        notes=req.notes
    )
    db.add(transfer)
    db.flush()
    
    for item in req.items:
        # Check source inventory
        current_stock = db.query(func.sum(InventoryTransaction.quantity)).filter(
            InventoryTransaction.product_id == item.product_id,
            InventoryTransaction.variant_id == item.variant_id,
            InventoryTransaction.location_id == req.source_location_id
        ).scalar() or 0.0
        
        if current_stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for product ID {item.product_id} at source location.")
            
        t_item = StockTransferItem(
            transfer_id=transfer.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity
        )
        db.add(t_item)
        
        # Transfer Out (Source)
        db.add(InventoryTransaction(
            product_id=item.product_id,
            variant_id=item.variant_id,
            location_id=req.source_location_id,
            transaction_type=TransactionType.TRANSFER_OUT,
            quantity=-item.quantity,
            reference_id=internal_id,
            user_id=current_user.id
        ))
        
        # Transfer In (Destination)
        db.add(InventoryTransaction(
            product_id=item.product_id,
            variant_id=item.variant_id,
            location_id=req.destination_location_id,
            transaction_type=TransactionType.TRANSFER_IN,
            quantity=item.quantity,
            reference_id=internal_id,
            user_id=current_user.id
        ))
        
    db.commit()
    db.refresh(transfer)
    return transfer

@router.get("/transfer")
def get_transfers(db: Session = Depends(get_db)):
    # Very basic list for frontend tracking
    transfers = db.query(StockTransfer).order_by(StockTransfer.date.desc()).all()
    res = []
    for t in transfers:
        res.append({
            "id": t.id,
            "internal_id": t.internal_id,
            "source_location_id": t.source_location_id,
            "destination_location_id": t.destination_location_id,
            "date": t.date,
            "user_id": t.user_id,
            "status": t.status,
            "notes": t.notes
        })
    return res


# --- Stock Adjustment Endpoints (SRS 32) ---

@router.post("/adjust")
def create_adjustment(
    req: AdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # RBAC Check: Only Admin or Manager
    if not current_user.role or current_user.role.name not in ["Owner", "Admin", "Manager"]:
        raise HTTPException(status_code=403, detail="Only Admin or Manager can perform stock adjustments.")
        
    max_id = db.query(func.max(StockAdjustment.id)).scalar() or 0
    from backend.api.settings import get_prefix
    adj_prefix = get_prefix(db, "prefix_adjustment", "ADJ-")
    internal_id = f"{adj_prefix}{max_id + 1:06d}"
    
    adjustment = StockAdjustment(
        internal_id=internal_id,
        location_id=req.location_id,
        user_id=current_user.id,
        reason=req.reason
    )
    db.add(adjustment)
    db.flush()
    
    for item in req.items:
        current_stock = db.query(func.sum(InventoryTransaction.quantity)).filter(
            InventoryTransaction.product_id == item.product_id,
            InventoryTransaction.variant_id == item.variant_id,
            InventoryTransaction.location_id == req.location_id
        ).scalar() or 0.0
        
        diff = item.actual_quantity - current_stock
        
        if diff != 0:
            a_item = StockAdjustmentItem(
                adjustment_id=adjustment.id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                system_quantity=current_stock,
                actual_quantity=item.actual_quantity,
                difference=diff
            )
            db.add(a_item)
            
            db.add(InventoryTransaction(
                product_id=item.product_id,
                variant_id=item.variant_id,
                location_id=req.location_id,
                transaction_type=TransactionType.ADJUSTMENT,
                quantity=diff,
                reference_id=internal_id,
                user_id=current_user.id
            ))
            
    db.commit()
    db.refresh(adjustment)
    return adjustment
