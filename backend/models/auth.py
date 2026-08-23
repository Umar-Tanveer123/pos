from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from backend.core.database import Base

# Association table for User and Location (since a user can have access to multiple locations)
user_location_assoc = Table(
    'user_location_assoc', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('location_id', Integer, ForeignKey('locations.id'), primary_key=True)
)

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # Owner, Admin, Manager, Cashier, etc.
    description = Column(String, nullable=True)

    users = relationship("User", back_populates="role")

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # Warehouse, Retail Shop, etc.
    address = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    users = relationship("User", secondary=user_location_assoc, back_populates="locations")
    # Inventory will be related to location

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    
    role_id = Column(Integer, ForeignKey("roles.id"))
    role = relationship("Role", back_populates="users")

    locations = relationship("Location", secondary=user_location_assoc, back_populates="users")
