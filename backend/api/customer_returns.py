from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.core.database import get_db
from backend.models.sale import SaleInvoice, SaleItem, CustomerReturn, CustomerReturnItem
from backend.models.partner import Customer, CustomerLedger
from backend.models.product import Product
from backend.models.ledger import InventoryTransaction, TransactionType
from backend.models.auth import User
from backend.api.auth import get_current_active_user

router = APIRouter()

class ReturnableItemResponse(BaseModel):
    sale_item_id: int
    product_id: int
    variant_id: Optional[int]
    product_name: str
    unit_name: Optional[str]
    purchased_qty: float
    returned_qty: float
    returnable_qty: float
    unit_price: float
    discount_per_unit: float

class ReturnItemRequest(BaseModel):
    sale_item_id: int
    quantity: float
    is_damaged: bool

class ReturnRequest(BaseModel):
    sale_id: int
    items: List[ReturnItemRequest]
    notes: Optional[str] = None

class ReturnResponse(BaseModel):
    id: int
    internal_id: str
    sale_id: int
    total_refund: float
    
    class Config:
        from_attributes = True

@router.get("/sale/{sale_id}/returnable", response_model=List[ReturnableItemResponse])
def get_returnable_items(
    sale_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    sale = db.query(SaleInvoice).filter(SaleInvoice.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale invoice not found")
        
    result = []
    for item in sale.items:
        returnable = item.quantity - (item.returned_quantity or 0.0)
        if returnable > 0:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                continue
                
            unit_name = "Unit"
            if product.unit:
                unit_name = product.unit.name
                
            p_name = product.name
            if item.variant_id:
                for v in product.variants:
                    if v.id == item.variant_id:
                        p_name += f" - {v.name}"
                        break
                        
            # Calc discount per unit for accurate refund calculation
            discount_per_unit = 0.0
            if item.quantity > 0:
                discount_per_unit = item.discount / item.quantity
                
            result.append(ReturnableItemResponse(
                sale_item_id=item.id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                product_name=p_name,
                unit_name=unit_name,
                purchased_qty=item.quantity,
                returned_qty=item.returned_quantity or 0.0,
                returnable_qty=returnable,
                unit_price=item.unit_price,
                discount_per_unit=discount_per_unit
            ))
            
    return result

@router.post("/", response_model=ReturnResponse)
def process_customer_return(
    req: ReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sale = db.query(SaleInvoice).filter(SaleInvoice.id == req.sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
        
    if sale.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Cannot return items from a cancelled sale.")
        
    customer = db.query(Customer).filter(Customer.id == sale.customer_id).first()
    
    max_id = db.query(func.max(CustomerReturn.id)).scalar() or 0
    from backend.api.settings import get_prefix
    ret_prefix = get_prefix(db, "prefix_return", "RET-")
    internal_id = f"{ret_prefix}{max_id + 1:06d}"
    
    ret_obj = CustomerReturn(
        internal_id=internal_id,
        sale_id=sale.id,
        customer_id=sale.customer_id,
        location_id=sale.location_id,
        user_id=current_user.id,
        notes=req.notes
    )
    db.add(ret_obj)
    db.flush()
    
    total_refund = 0.0
    all_fully_returned = True
    
    for req_item in req.items:
        if req_item.quantity <= 0:
            continue
            
        sale_item = db.query(SaleItem).filter(SaleItem.id == req_item.sale_item_id, SaleItem.sale_id == sale.id).first()
        if not sale_item:
            raise HTTPException(status_code=404, detail=f"Sale item {req_item.sale_item_id} not found in this sale.")
            
        returnable = sale_item.quantity - (sale_item.returned_quantity or 0.0)
        if req_item.quantity > returnable:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot return {req_item.quantity}. Only {returnable} available to return."
            )
            
        # Calculate refund for this item (price - discount_per_unit)
        discount_per_unit = 0.0
        if sale_item.quantity > 0:
            discount_per_unit = sale_item.discount / sale_item.quantity
            
        refund_amount = req_item.quantity * (sale_item.unit_price - discount_per_unit)
        total_refund += refund_amount
        
        # Update sale item returned qty
        sale_item.returned_quantity = (sale_item.returned_quantity or 0.0) + req_item.quantity
        
        if sale_item.returned_quantity < sale_item.quantity:
            all_fully_returned = False
            
        # Create return item
        ri = CustomerReturnItem(
            return_id=ret_obj.id,
            sale_item_id=sale_item.id,
            product_id=sale_item.product_id,
            variant_id=sale_item.variant_id,
            quantity=req_item.quantity,
            refund_amount=refund_amount,
            is_damaged=req_item.is_damaged
        )
        db.add(ri)
        
        # Inventory update
        product = db.query(Product).filter(Product.id == sale_item.product_id).first()
        qty_in_base_units = req_item.quantity
        item_unit_id = sale_item.unit_id or (product.unit_id if product else None)
        
        if product and item_unit_id and product.secondary_unit_id == item_unit_id and product.conversion_factor:
            qty_in_base_units = req_item.quantity * product.conversion_factor
            
        # Add back to available stock
        inv_trans = InventoryTransaction(
            product_id=sale_item.product_id,
            variant_id=sale_item.variant_id,
            location_id=sale.location_id,
            transaction_type=TransactionType.CUSTOMER_RETURN,
            quantity=qty_in_base_units,  # Positive = stock restored
            reference_id=internal_id,
            user_id=current_user.id
        )
        db.add(inv_trans)
        
        # If it's damaged, we immediately subtract it again via ADJUSTMENT so it's not available for sale
        if req_item.is_damaged:
            inv_trans_dmg = InventoryTransaction(
                product_id=sale_item.product_id,
                variant_id=sale_item.variant_id,
                location_id=sale.location_id,
                transaction_type=TransactionType.ADJUSTMENT,
                quantity=-qty_in_base_units,  # Negative to move out of resalable stock
                reference_id=f"{internal_id}-DAMAGED",
                user_id=current_user.id
            )
            db.add(inv_trans_dmg)
            
    # Check if we need to mark the whole sale as RETURNED
    for si in sale.items:
        if si.returned_quantity < si.quantity:
            all_fully_returned = False
            break
            
    if all_fully_returned:
        sale.status = "RETURNED"
        
    ret_obj.total_refund = total_refund
    
    # Process Refund (credit to customer balance)
    if customer and total_refund > 0:
        # Note: Return amount decreases the owed balance. 
        # If balance goes negative, it implies we owe the customer cash, which is correct for customer ledger logic.
        customer.balance -= total_refund
        
        return_ledger = CustomerLedger(
            customer_id=customer.id,
            transaction_type="RETURN",
            reference_id=internal_id,
            amount=-total_refund,
            balance_after=customer.balance,
            notes=f"Refund from customer return {internal_id}"
        )
        db.add(return_ledger)
        
    db.commit()
    db.refresh(ret_obj)
    return ret_obj
