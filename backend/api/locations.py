from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from backend.core.database import get_db
from backend.models.auth import Location, User
from backend.api.auth import get_current_active_user
from backend.models.ledger import InventoryTransaction

router = APIRouter()

class LocationBase(BaseModel):
    name: str
    address: str | None = None
    is_active: bool = True

class LocationCreate(LocationBase):
    pass

class LocationUpdate(LocationBase):
    pass

class LocationResponse(LocationBase):
    id: int

    class Config:
        from_attributes = True

@router.get("/", response_model=List[LocationResponse])
def get_locations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Admins see all, manager/cashier might be restricted to active ones in production
    # But for config management, we return all locations
    return db.query(Location).all()

@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    location_in: LocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Only Admin/Owner can create locations
    if current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if name already exists
    existing = db.query(Location).filter(Location.name == location_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location with this name already exists"
        )
        
    db_location = Location(
        name=location_in.name,
        address=location_in.address,
        is_active=location_in.is_active
    )
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location

@router.put("/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: int,
    location_in: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
        
    db_location = db.query(Location).filter(Location.id == location_id).first()
    if not db_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
        
    # Check name uniqueness if changed
    if db_location.name != location_in.name:
        existing = db.query(Location).filter(Location.name == location_in.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Location with this name already exists"
            )
            
    db_location.name = location_in.name
    db_location.address = location_in.address
    db_location.is_active = location_in.is_active
    
    db.commit()
    db.refresh(db_location)
    return db_location

@router.delete("/{location_id}", status_code=status.HTTP_200_OK)
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
        
    db_loc = db.query(Location).filter(Location.id == location_id).first()
    if not db_loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
        
    # Delete inventory transactions for this location first
    db.query(InventoryTransaction).filter(InventoryTransaction.location_id == location_id).delete()
    db.delete(db_loc)
    db.commit()
    return {"detail": "Location deleted successfully"}

