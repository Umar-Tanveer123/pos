from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
import csv
import io
from datetime import datetime

from backend.core.database import get_db
from backend.models.auth import User, Location
from backend.models.product import Category, Subcategory, Brand, Unit, Product, ProductVariant
from backend.models.ledger import InventoryTransaction, TransactionType
from backend.models.purchase import PriceAuditLog, PurchaseItem, PurchaseInvoice
from backend.models.partner import Supplier
from backend.api.auth import get_current_active_user

router = APIRouter()

# ----------------- Schemas -----------------

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    class Config:
        from_attributes = True

class SubcategoryBase(BaseModel):
    name: str
    category_id: int

class SubcategoryCreate(SubcategoryBase):
    pass

class SubcategoryResponse(SubcategoryBase):
    id: int
    class Config:
        from_attributes = True

class BrandBase(BaseModel):
    name: str
    description: str | None = None

class BrandCreate(BrandBase):
    pass

class BrandResponse(BrandBase):
    id: int
    class Config:
        from_attributes = True

class UnitBase(BaseModel):
    name: str

class UnitCreate(UnitBase):
    pass

class UnitResponse(UnitBase):
    id: int
    class Config:
        from_attributes = True

class LocationStockInput(BaseModel):
    location_id: int
    quantity: float

class LocationStockResponse(BaseModel):
    location_id: int
    location_name: str
    quantity: float

class ProductVariantBase(BaseModel):
    name: str
    sku: str | None = None
    barcode: str | None = None
    purchase_price: float | None = None
    retail_price: float | None = None
    wholesale_price: float | None = None
    special_price: float | None = None

class ProductVariantCreate(ProductVariantBase):
    initial_stock: List[LocationStockInput] = []

class ProductVariantResponse(ProductVariantBase):
    id: int
    product_id: int
    stock: List[LocationStockResponse] = []
    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    sku: str | None = None
    barcode: str | None = None
    internal_barcode: str | None = None
    category_id: int | None = None
    subcategory_id: int | None = None
    brand_id: int | None = None
    unit_id: int | None = None
    secondary_unit_id: int | None = None
    conversion_factor: float | None = 1.0
    purchase_price: float = 0.0
    retail_price: float = 0.0
    wholesale_price: float = 0.0
    special_price: float = 0.0
    low_stock_threshold: int = 10
    is_active: bool = True

class ProductCreate(ProductBase):
    variants: List[ProductVariantCreate] = []
    initial_stock: List[LocationStockInput] = []
    supplier_ids: List[int] = []

class ProductResponse(ProductBase):
    id: int
    internal_id: str
    category_name: str | None = None
    subcategory_name: str | None = None
    brand_name: str | None = None
    unit_name: str | None = None
    secondary_unit_name: str | None = None
    variants: List[ProductVariantResponse] = []
    stock: List[LocationStockResponse] = []
    supplier_ids: List[int] = []

    class Config:
        from_attributes = True

# ----------------- Helper Functions -----------------

def get_stock_for_item(db: Session, product_id: int, variant_id: Optional[int] = None) -> List[LocationStockResponse]:
    locations = db.query(Location).filter(Location.is_active == True).all()
    stock_list = []
    for loc in locations:
        q_filter = (
            (InventoryTransaction.product_id == product_id) &
            (InventoryTransaction.location_id == loc.id)
        )
        if variant_id is not None:
            q_filter = q_filter & (InventoryTransaction.variant_id == variant_id)
        else:
            q_filter = q_filter & (InventoryTransaction.variant_id == None)
            
        qty = db.query(func.sum(InventoryTransaction.quantity)).filter(q_filter).scalar() or 0.0
        stock_list.append(
            LocationStockResponse(
                location_id=loc.id,
                location_name=loc.name,
                quantity=float(qty)
            )
        )
    return stock_list

# ----------------- Categories API -----------------

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category_in: CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    existing = db.query(Category).filter(Category.name == category_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    db_cat = Category(name=category_in.name)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, category_in: CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    db_cat = db.query(Category).filter(Category.id == category_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db_cat.name = category_in.name
    db.commit()
    db.refresh(db_cat)
    return db_cat

# ----------------- Subcategories API -----------------

@router.get("/subcategories", response_model=List[SubcategoryResponse])
def get_subcategories(db: Session = Depends(get_db)):
    return db.query(Subcategory).all()

@router.post("/subcategories", response_model=SubcategoryResponse, status_code=status.HTTP_201_CREATED)
def create_subcategory(sub_in: SubcategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    existing = db.query(Subcategory).filter(Subcategory.name == sub_in.name, Subcategory.category_id == sub_in.category_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subcategory already exists under this category")
    db_sub = Subcategory(name=sub_in.name, category_id=sub_in.category_id)
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub

# ----------------- Brands API -----------------

@router.get("/brands", response_model=List[BrandResponse])
def get_brands(db: Session = Depends(get_db)):
    return db.query(Brand).all()

@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
def create_brand(brand_in: BrandCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    existing = db.query(Brand).filter(Brand.name == brand_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Brand already exists")
    db_brand = Brand(name=brand_in.name, description=brand_in.description)
    db.add(db_brand)
    db.commit()
    db.refresh(db_brand)
    return db_brand

@router.put("/brands/{brand_id}", response_model=BrandResponse)
def update_brand(brand_id: int, brand_in: BrandCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    db_brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    db_brand.name = brand_in.name
    db_brand.description = brand_in.description
    db.commit()
    db.refresh(db_brand)
    return db_brand

# ----------------- Units API -----------------

@router.get("/units", response_model=List[UnitResponse])
def get_units(db: Session = Depends(get_db)):
    return db.query(Unit).all()

@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
def create_unit(unit_in: UnitCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    existing = db.query(Unit).filter(Unit.name == unit_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Unit already exists")
    db_unit = Unit(name=unit_in.name)
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

# ----------------- Products API -----------------

@router.get("/", response_model=List[ProductResponse])
def get_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
        
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
        
    if brand_id is not None:
        query = query.filter(Product.brand_id == brand_id)
        
    if supplier_id is not None:
        purchased_prod_ids = db.query(PurchaseItem.product_id).join(PurchaseInvoice).filter(PurchaseInvoice.supplier_id == supplier_id).distinct().subquery()
        query = query.filter(
            (Product.suppliers.any(Supplier.id == supplier_id)) |
            (Product.id.in_(purchased_prod_ids))
        )
        
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Product.name.like(search_filter)) |
            (Product.sku.like(search_filter)) |
            (Product.barcode.like(search_filter)) |
            (Product.internal_barcode.like(search_filter))
        )
        
    products = query.all()
    
    res = []
    for p in products:
        prod_stock = get_stock_for_item(db, p.id, None)
        
        variant_responses = []
        for v in p.variants:
            v_stock = get_stock_for_item(db, p.id, v.id)
            variant_responses.append(
                ProductVariantResponse(
                    id=v.id,
                    product_id=v.product_id,
                    name=v.name,
                    sku=v.sku,
                    barcode=v.barcode,
                    purchase_price=v.purchase_price,
                    retail_price=v.retail_price,
                    wholesale_price=v.wholesale_price,
                    special_price=v.special_price,
                    stock=v_stock
                )
            )
            
        res.append(
            ProductResponse(
                id=p.id,
                internal_id=p.internal_id,
                name=p.name,
                sku=p.sku,
                barcode=p.barcode,
                internal_barcode=p.internal_barcode,
                category_id=p.category_id,
                subcategory_id=p.subcategory_id,
                brand_id=p.brand_id,
                unit_id=p.unit_id,
                secondary_unit_id=p.secondary_unit_id,
                conversion_factor=p.conversion_factor,
                purchase_price=p.purchase_price,
                retail_price=p.retail_price,
                wholesale_price=p.wholesale_price,
                special_price=p.special_price,
                low_stock_threshold=p.low_stock_threshold,
                is_active=p.is_active,
                category_name=p.category.name if p.category else None,
                subcategory_name=p.subcategory.name if p.subcategory else None,
                brand_name=p.brand.name if p.brand else None,
                unit_name=p.unit.name if p.unit else None,
                secondary_unit_name=p.secondary_unit.name if p.secondary_unit else None,
                variants=variant_responses,
                stock=prod_stock,
                supplier_ids=[s.id for s in p.suppliers]
            )
        )
    return res

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    max_id = db.query(func.max(Product.id)).scalar() or 0
    next_num = max_id + 1
    from backend.api.settings import get_prefix
    prd_prefix = get_prefix(db, "prefix_product", "PRD-")
    internal_id = f"{prd_prefix}{next_num:06d}"

    sku = product_in.sku
    if not sku:
        sku = f"SKU-{internal_id}"
    else:
        existing = db.query(Product).filter(Product.sku == sku).first()
        if existing:
            raise HTTPException(status_code=400, detail="SKU already exists")

    if product_in.barcode:
        existing = db.query(Product).filter(Product.barcode == product_in.barcode).first()
        if existing:
            raise HTTPException(status_code=400, detail="Barcode already exists")

    internal_barcode = product_in.internal_barcode
    if not product_in.barcode and not internal_barcode:
        internal_barcode = f"200{next_num:09d}"
        
    db_product = Product(
        internal_id=internal_id,
        name=product_in.name,
        sku=sku,
        barcode=product_in.barcode,
        internal_barcode=internal_barcode,
        category_id=product_in.category_id,
        subcategory_id=product_in.subcategory_id,
        brand_id=product_in.brand_id,
        unit_id=product_in.unit_id,
        secondary_unit_id=product_in.secondary_unit_id,
        conversion_factor=product_in.conversion_factor,
        purchase_price=product_in.purchase_price,
        retail_price=product_in.retail_price,
        wholesale_price=product_in.wholesale_price,
        special_price=product_in.special_price,
        low_stock_threshold=product_in.low_stock_threshold,
        is_active=product_in.is_active
    )
    
    if product_in.supplier_ids:
        suppliers = db.query(Supplier).filter(Supplier.id.in_(product_in.supplier_ids)).all()
        db_product.suppliers = suppliers

    db.add(db_product)
    db.commit()
    
    # Save base product stock
    for item in product_in.initial_stock:
        if item.quantity > 0:
            tx = InventoryTransaction(
                product_id=db_product.id,
                variant_id=None,
                location_id=item.location_id,
                transaction_type=TransactionType.ADJUSTMENT,
                quantity=item.quantity,
                user_id=current_user.id
            )
            db.add(tx)
            
    # Create variants
    for idx, var in enumerate(product_in.variants, start=1):
        var_sku = var.sku
        if not var_sku:
            var_sku = f"{sku}-V{idx}"
        else:
            existing_var = db.query(ProductVariant).filter(ProductVariant.sku == var_sku).first()
            if existing_var:
                raise HTTPException(status_code=400, detail=f"Variant SKU {var_sku} already exists")

        db_var = ProductVariant(
            product_id=db_product.id,
            name=var.name,
            sku=var_sku,
            barcode=var.barcode,
            purchase_price=var.purchase_price,
            retail_price=var.retail_price,
            wholesale_price=var.wholesale_price,
            special_price=var.special_price
        )
        db.add(db_var)
        db.commit() # commit to get id
        
        # Save variant stock
        for item in var.initial_stock:
            if item.quantity > 0:
                tx = InventoryTransaction(
                    product_id=db_product.id,
                    variant_id=db_var.id,
                    location_id=item.location_id,
                    transaction_type=TransactionType.ADJUSTMENT,
                    quantity=item.quantity,
                    user_id=current_user.id
                )
                db.add(tx)
                
    db.commit()
    db.refresh(db_product)
    
    # Return mapping
    prod_stock = get_stock_for_item(db, db_product.id, None)
    variant_responses = []
    for v in db_product.variants:
        v_stock = get_stock_for_item(db, db_product.id, v.id)
        variant_responses.append(
            ProductVariantResponse(
                id=v.id,
                product_id=v.product_id,
                name=v.name,
                sku=v.sku,
                barcode=v.barcode,
                purchase_price=v.purchase_price,
                retail_price=v.retail_price,
                wholesale_price=v.wholesale_price,
                special_price=v.special_price,
                stock=v_stock
            )
        )
        
    return ProductResponse(
        id=db_product.id,
        internal_id=db_product.internal_id,
        name=db_product.name,
        sku=db_product.sku,
        barcode=db_product.barcode,
        internal_barcode=db_product.internal_barcode,
        category_id=db_product.category_id,
        subcategory_id=db_product.subcategory_id,
        brand_id=db_product.brand_id,
        unit_id=db_product.unit_id,
        secondary_unit_id=db_product.secondary_unit_id,
        conversion_factor=db_product.conversion_factor,
        purchase_price=db_product.purchase_price,
        retail_price=db_product.retail_price,
        wholesale_price=db_product.wholesale_price,
        special_price=db_product.special_price,
        low_stock_threshold=db_product.low_stock_threshold,
        is_active=db_product.is_active,
        category_name=db_product.category.name if db_product.category else None,
        subcategory_name=db_product.subcategory.name if db_product.subcategory else None,
        brand_name=db_product.brand.name if db_product.brand else None,
        unit_name=db_product.unit.name if db_product.unit else None,
        secondary_unit_name=db_product.secondary_unit.name if db_product.secondary_unit else None,
        variants=variant_responses,
        stock=prod_stock,
        supplier_ids=[s.id for s in db_product.suppliers]
    )

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    sku = product_in.sku
    if not sku:
        sku = f"SKU-{db_product.internal_id}"
    else:
        if db_product.sku != sku:
            existing = db.query(Product).filter(Product.sku == sku).first()
            if existing:
                raise HTTPException(status_code=400, detail="SKU already exists")

    if product_in.barcode and db_product.barcode != product_in.barcode:
        existing = db.query(Product).filter(Product.barcode == product_in.barcode).first()
        if existing:
            raise HTTPException(status_code=400, detail="Barcode already exists")
            
    db_product.name = product_in.name
    db_product.sku = sku
    db_product.barcode = product_in.barcode
    db_product.category_id = product_in.category_id
    db_product.subcategory_id = product_in.subcategory_id
    db_product.brand_id = product_in.brand_id
    db_product.unit_id = product_in.unit_id
    db_product.secondary_unit_id = product_in.secondary_unit_id
    db_product.conversion_factor = product_in.conversion_factor
    db_product.purchase_price = product_in.purchase_price
    db_product.retail_price = product_in.retail_price
    db_product.wholesale_price = product_in.wholesale_price
    db_product.special_price = product_in.special_price
    db_product.low_stock_threshold = product_in.low_stock_threshold
    db_product.is_active = product_in.is_active
    
    if product_in.supplier_ids is not None:
        suppliers = db.query(Supplier).filter(Supplier.id.in_(product_in.supplier_ids)).all()
        db_product.suppliers = suppliers
    
    # Adjust base stock levels
    for item in product_in.initial_stock:
        current_qty = db.query(func.sum(InventoryTransaction.quantity)).filter(
            (InventoryTransaction.product_id == product_id) &
            (InventoryTransaction.location_id == item.location_id) &
            (InventoryTransaction.variant_id == None)
        ).scalar() or 0.0
        
        delta = item.quantity - current_qty
        if delta != 0:
            tx = InventoryTransaction(
                product_id=product_id,
                variant_id=None,
                location_id=item.location_id,
                transaction_type=TransactionType.ADJUSTMENT,
                quantity=delta,
                user_id=current_user.id
            )
            db.add(tx)
            
    # Sync variants without complete deletion to avoid orphaning transactions
    existing_vars = {v.name: v for v in db_product.variants}
    new_names = {v.name for v in product_in.variants}
    
    # Delete removed variants
    for name, v in list(existing_vars.items()):
        if name not in new_names:
            db.query(InventoryTransaction).filter(InventoryTransaction.variant_id == v.id).delete()
            db.delete(v)
            del existing_vars[name]
            
    # Add or update variants
    for idx, var in enumerate(product_in.variants, start=1):
        var_sku = var.sku
        if not var_sku:
            var_sku = f"{sku}-V{idx}"
            
        if var.name in existing_vars:
            db_var = existing_vars[var.name]
            db_var.sku = var_sku
            db_var.barcode = var.barcode
            db_var.purchase_price = var.purchase_price
            db_var.retail_price = var.retail_price
            db_var.wholesale_price = var.wholesale_price
            db_var.special_price = var.special_price
        else:
            db_var = ProductVariant(
                product_id=db_product.id,
                name=var.name,
                sku=var_sku,
                barcode=var.barcode,
                purchase_price=var.purchase_price,
                retail_price=var.retail_price,
                wholesale_price=var.wholesale_price,
                special_price=var.special_price
            )
            db.add(db_var)
            db.commit() # commit to get id
            
        # Adjust variant stock levels
        for item in var.initial_stock:
            current_qty = db.query(func.sum(InventoryTransaction.quantity)).filter(
                (InventoryTransaction.product_id == product_id) &
                (InventoryTransaction.variant_id == db_var.id) &
                (InventoryTransaction.location_id == item.location_id)
            ).scalar() or 0.0
            
            delta = item.quantity - current_qty
            if delta != 0:
                tx = InventoryTransaction(
                    product_id=product_id,
                    variant_id=db_var.id,
                    location_id=item.location_id,
                    transaction_type=TransactionType.ADJUSTMENT,
                    quantity=delta,
                    user_id=current_user.id
                )
                db.add(tx)
                
    db.commit()
    db.refresh(db_product)
    
    prod_stock = get_stock_for_item(db, db_product.id, None)
    variant_responses = []
    for v in db_product.variants:
        v_stock = get_stock_for_item(db, db_product.id, v.id)
        variant_responses.append(
            ProductVariantResponse(
                id=v.id,
                product_id=v.product_id,
                name=v.name,
                sku=v.sku,
                barcode=v.barcode,
                purchase_price=v.purchase_price,
                retail_price=v.retail_price,
                wholesale_price=v.wholesale_price,
                special_price=v.special_price,
                stock=v_stock
            )
        )
        
    return ProductResponse(
        id=db_product.id,
        internal_id=db_product.internal_id,
        name=db_product.name,
        sku=db_product.sku,
        barcode=db_product.barcode,
        internal_barcode=db_product.internal_barcode,
        category_id=db_product.category_id,
        subcategory_id=db_product.subcategory_id,
        brand_id=db_product.brand_id,
        unit_id=db_product.unit_id,
        secondary_unit_id=db_product.secondary_unit_id,
        conversion_factor=db_product.conversion_factor,
        purchase_price=db_product.purchase_price,
        retail_price=db_product.retail_price,
        wholesale_price=db_product.wholesale_price,
        special_price=db_product.special_price,
        low_stock_threshold=db_product.low_stock_threshold,
        is_active=db_product.is_active,
        category_name=db_product.category.name if db_product.category else None,
        subcategory_name=db_product.subcategory.name if db_product.subcategory else None,
        brand_name=db_product.brand.name if db_product.brand else None,
        unit_name=db_product.unit.name if db_product.unit else None,
        secondary_unit_name=db_product.secondary_unit.name if db_product.secondary_unit else None,
        variants=variant_responses,
        stock=prod_stock,
        supplier_ids=[s.id for s in db_product.suppliers]
    )

# ----------------- Deletion Operations -----------------

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    # Delete inventory transactions for variants first, then the product itself
    for v in db_product.variants:
        db.query(InventoryTransaction).filter(InventoryTransaction.variant_id == v.id).delete()
        db.delete(v)
        
    db.query(InventoryTransaction).filter(InventoryTransaction.product_id == product_id).delete()
    db.delete(db_product)
    db.commit()
    return {"detail": "Product deleted successfully"}


@router.delete("/categories/{category_id}", status_code=status.HTTP_200_OK)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    db_cat = db.query(Category).filter(Category.id == category_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
        
    # Find all products in this category
    products = db.query(Product).filter(Product.category_id == category_id).all()
    for p in products:
        # Delete variants
        for v in p.variants:
            db.query(InventoryTransaction).filter(InventoryTransaction.variant_id == v.id).delete()
            db.delete(v)
        # Delete product transactions
        db.query(InventoryTransaction).filter(InventoryTransaction.product_id == p.id).delete()
        db.delete(p)
        
    # Delete subcategories in this category
    db.query(Subcategory).filter(Subcategory.category_id == category_id).delete()
    
    db.delete(db_cat)
    db.commit()
    return {"detail": "Category and all its products deleted successfully"}


@router.delete("/subcategories/{subcategory_id}", status_code=status.HTTP_200_OK)
def delete_subcategory(
    subcategory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    db_sub = db.query(Subcategory).filter(Subcategory.id == subcategory_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subcategory not found")
        
    # Dissociate products
    db.query(Product).filter(Product.subcategory_id == subcategory_id).update({Product.subcategory_id: None})
    db.delete(db_sub)
    db.commit()
    return {"detail": "Subcategory deleted successfully"}


@router.delete("/brands/{brand_id}", status_code=status.HTTP_200_OK)
def delete_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    db_brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
        
    # Dissociate products
    db.query(Product).filter(Product.brand_id == brand_id).update({Product.brand_id: None})
    db.delete(db_brand)
    db.commit()
    return {"detail": "Brand deleted successfully"}


@router.delete("/units/{unit_id}", status_code=status.HTTP_200_OK)
def delete_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Owner"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    db_unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not db_unit:
        raise HTTPException(status_code=404, detail="Unit not found")
        
    # Dissociate products
    db.query(Product).filter(Product.unit_id == unit_id).update({Product.unit_id: None})
    db.delete(db_unit)
    db.commit()
    return {"detail": "Unit deleted successfully"}


# --- Bulk Price Management & CSV Import Endpoints ---

class BulkPriceUpdate(BaseModel):
    product_ids: Optional[List[int]] = None
    category_id: Optional[int] = None
    price_field: str # "purchase_price", "retail_price", "wholesale_price", "special_price"
    update_type: str # "PERCENTAGE", "FIXED", "OFFSET"
    value: float

class PriceAuditResponse(BaseModel):
    id: int
    product_id: int
    user_id: int
    old_purchase_price: float
    new_purchase_price: float
    old_retail_price: float
    new_retail_price: float
    old_wholesale_price: float
    new_wholesale_price: float
    old_special_price: float
    new_special_price: float
    change_type: str
    created_at: datetime
    product_name: Optional[str] = None
    username: Optional[str] = None

    class Config:
        from_attributes = True

@router.get("/price-audit-logs")
def get_price_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    logs = db.query(PriceAuditLog).order_by(PriceAuditLog.created_at.desc()).all()
    results = []
    for log in logs:
        results.append({
            "id": log.id,
            "product_id": log.product_id,
            "user_id": log.user_id,
            "old_purchase_price": log.old_purchase_price,
            "new_purchase_price": log.new_purchase_price,
            "old_retail_price": log.old_retail_price,
            "new_retail_price": log.new_retail_price,
            "old_wholesale_price": log.old_wholesale_price,
            "new_wholesale_price": log.new_wholesale_price,
            "old_special_price": log.old_special_price,
            "new_special_price": log.new_special_price,
            "change_type": log.change_type,
            "created_at": log.created_at,
            "product_name": log.product.name if log.product else "Deleted Product",
            "username": log.user.username if log.user else "System"
        })
    return results

@router.post("/bulk-price-update")
def bulk_price_update(
    params: BulkPriceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Manager", "Owner"]:
        raise HTTPException(status_code=403, detail="Not enough permissions to edit prices.")
        
    # Get target products
    query = db.query(Product)
    if params.product_ids is not None:
        query = query.filter(Product.id.in_(params.product_ids))
    elif params.category_id is not None:
        query = query.filter(Product.category_id == params.category_id)
    else:
        raise HTTPException(status_code=400, detail="Must provide product_ids or category_id")
        
    products = query.all()
    if not products:
        return {"detail": "No products matched the search criteria", "count": 0}
        
    field = params.price_field
    if field not in ["purchase_price", "retail_price", "wholesale_price", "special_price"]:
        raise HTTPException(status_code=400, detail="Invalid price field specified.")
        
    count = 0
    for p in products:
        old_val = getattr(p, field) or 0.0
        
        # Calculate new value
        if params.update_type == "FIXED":
            new_val = params.value
        elif params.update_type == "PERCENTAGE":
            new_val = old_val * (1.0 + (params.value / 100.0))
        elif params.update_type == "OFFSET":
            new_val = old_val + params.value
        else:
            raise HTTPException(status_code=400, detail="Invalid update type.")
            
        if new_val < 0:
            new_val = 0.0
            
        # If changed, write to DB and audit log
        if old_val != new_val:
            # Create Audit Log entry
            audit_log = PriceAuditLog(
                product_id=p.id,
                user_id=current_user.id,
                old_purchase_price=p.purchase_price,
                new_purchase_price=new_val if field == "purchase_price" else p.purchase_price,
                old_retail_price=p.retail_price,
                new_retail_price=new_val if field == "retail_price" else p.retail_price,
                old_wholesale_price=p.wholesale_price,
                new_wholesale_price=new_val if field == "wholesale_price" else p.wholesale_price,
                old_special_price=p.special_price,
                new_special_price=new_val if field == "special_price" else p.special_price,
                change_type="BULK_UPDATE"
            )
            db.add(audit_log)
            setattr(p, field, new_val)
            count += 1
            
    db.commit()
    return {"detail": f"Successfully updated prices for {count} products", "count": count}

@router.post("/import-csv")
async def import_products_csv(
    file: UploadFile = File(...),
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role.name not in ["Admin", "Manager", "Owner"]:
        raise HTTPException(status_code=403, detail="Not enough permissions to import products.")
        
    contents = await file.read()
    try:
        decoded = contents.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Please upload a UTF-8 encoded CSV.")
        
    reader = csv.DictReader(io.StringIO(decoded))
    
    # Validation Phase
    errors = []
    rows_to_import = []
    
    # Sets for intra-file uniqueness validation
    seen_skus = set()
    seen_barcodes = set()
    
    # Query all existing SKUs and Barcodes from database to detect duplicates fast
    db_skus = set(x[0] for x in db.query(Product.sku).filter(Product.sku != None).all())
    db_barcodes = set(x[0] for x in db.query(Product.barcode).filter(Product.barcode != None).all())
    
    for row_idx, row in enumerate(reader, start=2):
        # Normalize column keys
        norm = {}
        for k, v in row.items():
            if k is not None:
                norm[k.strip().lower().replace(" ", "_")] = v.strip() if v else ""
                
        # Resolve names
        name = norm.get("product_name") or norm.get("name") or norm.get("title")
        sku = norm.get("sku")
        barcode = norm.get("barcode")
        category_name = norm.get("category")
        subcategory_name = norm.get("subcategory")
        brand_name = norm.get("brand")
        unit_name = norm.get("unit")
        secondary_unit_name = norm.get("secondary_unit")
        conversion_factor_str = norm.get("conversion_factor") or "1.0"
        
        # Prices
        purchase_price_str = norm.get("purchase_price") or norm.get("cost") or "0"
        retail_price_str = norm.get("retail_price") or norm.get("price") or "0"
        wholesale_price_str = norm.get("wholesale_price") or "0"
        special_price_str = norm.get("special_price") or "0"
        low_stock_str = norm.get("low_stock_threshold") or "10"
        
        if not name:
            errors.append({"row": row_idx, "error": "Product name is required."})
            continue
            
        # Parse prices
        try:
            purchase_price = float(purchase_price_str)
            if purchase_price < 0:
                raise ValueError()
        except ValueError:
            errors.append({"row": row_idx, "error": f"Invalid purchase price '{purchase_price_str}'. Must be a non-negative number."})
            continue
            
        try:
            retail_price = float(retail_price_str)
            if retail_price < 0:
                raise ValueError()
        except ValueError:
            errors.append({"row": row_idx, "error": f"Invalid retail price '{retail_price_str}'. Must be a non-negative number."})
            continue
            
        try:
            wholesale_price = float(wholesale_price_str)
            if wholesale_price < 0:
                raise ValueError()
        except ValueError:
            errors.append({"row": row_idx, "error": f"Invalid wholesale price '{wholesale_price_str}'. Must be a non-negative number."})
            continue
            
        try:
            special_price = float(special_price_str)
            if special_price < 0:
                raise ValueError()
        except ValueError:
            errors.append({"row": row_idx, "error": f"Invalid special price '{special_price_str}'. Must be a non-negative number."})
            continue
            
        try:
            low_stock = int(low_stock_str)
            if low_stock < 0:
                raise ValueError()
        except ValueError:
            errors.append({"row": row_idx, "error": f"Invalid low stock threshold '{low_stock_str}'."})
            continue
            
        try:
            conversion_factor = float(conversion_factor_str)
            if conversion_factor <= 0:
                raise ValueError()
        except ValueError:
            errors.append({"row": row_idx, "error": f"Invalid conversion factor '{conversion_factor_str}'. Must be a positive number."})
            continue
            
        # Duplicate Checks
        if sku:
            if sku in seen_skus:
                errors.append({"row": row_idx, "error": f"Duplicate SKU '{sku}' found within the CSV file."})
                continue
            if sku in db_skus:
                errors.append({"row": row_idx, "error": f"SKU '{sku}' already exists in the database."})
                continue
            seen_skus.add(sku)
            
        if barcode:
            if barcode in seen_barcodes:
                errors.append({"row": row_idx, "error": f"Duplicate Barcode '{barcode}' found within the CSV file."})
                continue
            if barcode in db_barcodes:
                errors.append({"row": row_idx, "error": f"Barcode '{barcode}' already exists in the database."})
                continue
            seen_barcodes.add(barcode)
            
        rows_to_import.append({
            "name": name,
            "sku": sku,
            "barcode": barcode,
            "category": category_name,
            "subcategory": subcategory_name,
            "brand": brand_name,
            "unit": unit_name,
            "secondary_unit": secondary_unit_name,
            "conversion_factor": conversion_factor,
            "purchase_price": purchase_price,
            "retail_price": retail_price,
            "wholesale_price": wholesale_price,
            "special_price": special_price,
            "low_stock_threshold": low_stock
        })
        
    if errors:
        return {"success": False, "valid_count": 0, "errors": errors}
        
    # Import Phase (Atomic transaction)
    try:
        # Cache category, subcategory, brand, and unit lookups/creation
        cat_cache = {}
        subcat_cache = {} # key: (cat_id, subcat_name)
        brand_cache = {}
        unit_cache = {}
        
        max_prod_id = db.query(func.max(Product.id)).scalar() or 0
        
        supplier_obj = None
        if supplier_id:
            supplier_obj = db.query(Supplier).filter(Supplier.id == supplier_id).first()
            
        for idx, row in enumerate(rows_to_import):
            # 1. Resolve Category
            category_id = None
            if row["category"]:
                cat_name = row["category"]
                if cat_name not in cat_cache:
                    cat_obj = db.query(Category).filter(Category.name == cat_name).first()
                    if not cat_obj:
                        cat_obj = Category(name=cat_name)
                        db.add(cat_obj)
                        db.flush()
                    cat_cache[cat_name] = cat_obj.id
                category_id = cat_cache[cat_name]
                
            # 2. Resolve Subcategory
            subcategory_id = None
            if row["subcategory"] and category_id:
                subcat_name = row["subcategory"]
                subcat_key = (category_id, subcat_name)
                if subcat_key not in subcat_cache:
                    subcat_obj = db.query(Subcategory).filter(
                        Subcategory.category_id == category_id,
                        Subcategory.name == subcat_name
                    ).first()
                    if not subcat_obj:
                        subcat_obj = Subcategory(name=subcat_name, category_id=category_id)
                        db.add(subcat_obj)
                        db.flush()
                    subcat_cache[subcat_key] = subcat_obj.id
                subcategory_id = subcat_cache[subcat_key]
                
            # 3. Resolve Brand
            brand_id = None
            if row["brand"]:
                br_name = row["brand"]
                if br_name not in brand_cache:
                    br_obj = db.query(Brand).filter(Brand.name == br_name).first()
                    if not br_obj:
                        br_obj = Brand(name=br_name)
                        db.add(br_obj)
                        db.flush()
                    brand_cache[br_name] = br_obj.id
                brand_id = brand_cache[br_name]
                
            # 4. Resolve Unit
            unit_id = None
            if row["unit"]:
                un_name = row["unit"]
                if un_name not in unit_cache:
                    un_obj = db.query(Unit).filter(Unit.name == un_name).first()
                    if not un_obj:
                        un_obj = Unit(name=un_name)
                        db.add(un_obj)
                        db.flush()
                    unit_cache[un_name] = un_obj.id
                unit_id = unit_cache[un_name]
                
            # 4b. Resolve Secondary Unit
            secondary_unit_id = None
            if row["secondary_unit"]:
                sec_un_name = row["secondary_unit"]
                if sec_un_name not in unit_cache:
                    sec_un_obj = db.query(Unit).filter(Unit.name == sec_un_name).first()
                    if not sec_un_obj:
                        sec_un_obj = Unit(name=sec_un_name)
                        db.add(sec_un_obj)
                        db.flush()
                    unit_cache[sec_un_name] = sec_un_obj.id
                secondary_unit_id = unit_cache[sec_un_name]
                
            # Auto-generate Product ID, SKU, and internal barcode
            next_num = max_prod_id + 1 + idx
            from backend.api.settings import get_prefix
            prd_prefix = get_prefix(db, "prefix_product", "PRD-")
            internal_id = f"{prd_prefix}{next_num:06d}"
            
            sku = row["sku"]
            if not sku:
                sku = f"SKU-{internal_id}"
                
            internal_barcode = None
            if not row["barcode"]:
                internal_barcode = f"200{next_num:09d}"
                
            db_prod = Product(
                internal_id=internal_id,
                name=row["name"],
                sku=sku,
                barcode=row["barcode"] or None,
                internal_barcode=internal_barcode,
                category_id=category_id,
                subcategory_id=subcategory_id,
                brand_id=brand_id,
                unit_id=unit_id,
                secondary_unit_id=secondary_unit_id,
                conversion_factor=row["conversion_factor"],
                purchase_price=row["purchase_price"],
                retail_price=row["retail_price"],
                wholesale_price=row["wholesale_price"],
                special_price=row["special_price"],
                low_stock_threshold=row["low_stock_threshold"],
                is_active=True
            )
            if supplier_obj:
                db_prod.suppliers.append(supplier_obj)
            db.add(db_prod)
            
        db.commit()
        return {"success": True, "valid_count": len(rows_to_import), "errors": []}
    except Exception as e:
        db.rollback()
        return {"success": False, "valid_count": 0, "errors": [{"row": 0, "error": f"Database import transaction error: {str(e)}"}]}


