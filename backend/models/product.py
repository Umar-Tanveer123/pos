from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from backend.core.database import Base

product_supplier_assoc = Table(
    'product_supplier_assoc', Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('supplier_id', Integer, ForeignKey('suppliers.id'), primary_key=True)
)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    subcategories = relationship("Subcategory", back_populates="category")
    products = relationship("Product", back_populates="category")

class Subcategory(Base):
    __tablename__ = "subcategories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="subcategories")
    products = relationship("Product", back_populates="subcategory")

class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    products = relationship("Product", back_populates="brand")

class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Piece, Kg, Box
    products = relationship("Product", back_populates="unit", foreign_keys="[Product.unit_id]")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String, unique=True, index=True) # Auto-generated PRD-000001
    name = Column(String, index=True)
    sku = Column(String, unique=True, index=True, nullable=True)
    barcode = Column(String, unique=True, index=True, nullable=True)
    internal_barcode = Column(String, unique=True, index=True, nullable=True)
    
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category", back_populates="products")
    
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=True)
    subcategory = relationship("Subcategory", back_populates="products")
    
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    brand = relationship("Brand", back_populates="products")
    
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    unit = relationship("Unit", foreign_keys=[unit_id], back_populates="products")
    
    secondary_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    secondary_unit = relationship("Unit", foreign_keys=[secondary_unit_id])
    
    conversion_factor = Column(Float, default=1.0)
    
    # Prices
    purchase_price = Column(Float, default=0.0)
    retail_price = Column(Float, default=0.0)
    wholesale_price = Column(Float, default=0.0)
    special_price = Column(Float, default=0.0)
    
    low_stock_threshold = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)

    suppliers = relationship("Supplier", secondary=product_supplier_assoc, back_populates="products")
    variants = relationship("ProductVariant", back_populates="product")

class ProductVariant(Base):
    __tablename__ = "product_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product", back_populates="variants")
    
    name = Column(String) # e.g., 180ml, 360ml
    sku = Column(String, unique=True, index=True, nullable=True)
    barcode = Column(String, unique=True, index=True, nullable=True)
    
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    unit = relationship("Unit", foreign_keys=[unit_id])
    
    secondary_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    secondary_unit = relationship("Unit", foreign_keys=[secondary_unit_id])
    
    conversion_factor = Column(Float, default=1.0)
    
    # Optional variant specific pricing, otherwise fallback to product
    purchase_price = Column(Float, nullable=True)
    retail_price = Column(Float, nullable=True)
    wholesale_price = Column(Float, nullable=True)
    special_price = Column(Float, nullable=True)
