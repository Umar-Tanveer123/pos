from fastapi import FastAPI
from backend.core.config import settings
from backend.api import auth, users, locations, products, suppliers, purchases, supplier_returns, customers, sales, customer_returns, inventory, expenses, reports, audit, backup, settings as api_settings
from backend.core.database import Base, engine, SessionLocal
from backend.models.partner import CustomerType, Customer
import backend.models

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

def seed_database(db):
    try:
        # Alter users table to add permissions column if it doesn't exist
        from sqlalchemy import text
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN permissions VARCHAR DEFAULT '';"))
            db.commit()
        except Exception:
            pass

        # 1. Seed Roles (SRS 43)
        from backend.models.auth import Role
        app_roles = ["Owner", "Admin", "Manager", "Cashier", "Storekeeper", "Purchase Employee", "Accountant"]
        for r_name in app_roles:
            if not db.query(Role).filter(Role.name == r_name).first():
                db.add(Role(name=r_name))
        db.commit()

        # 2. Customer Types
        types = ["Retail", "Wholesale", "Special"]
        for t_name in types:
            if not db.query(CustomerType).filter(CustomerType.name == t_name).first():
                db.add(CustomerType(name=t_name))
        db.commit()
        
        # 3. Walk-in Customer
        retail_type = db.query(CustomerType).filter(CustomerType.name == "Retail").first()
        if retail_type:
            walkin = db.query(Customer).filter(Customer.name == "Walk-in Customer").first()
            if not walkin:
                db.add(Customer(
                    internal_id="CUS-000000",
                    name="Walk-in Customer",
                    phone="—",
                    address="—",
                    customer_type_id=retail_type.id,
                    credit_limit=0.0,
                    balance=0.0,
                    is_active=1
                ))
                db.commit()
        # 4. Seed Settings & Prefixes (SRS 49 & 50)
        from backend.models.setting import SystemSetting
        default_settings = {
            "business_name": "Antigravity POS Ltd.",
            "business_address": "123 Main St, Central City",
            "business_phone": "+92 300 1234567",
            "currency": "Rs.",
            "prefix_product": "PRD-",
            "prefix_customer": "CUS-",
            "prefix_supplier": "SUP-",
            "prefix_invoice": "INV-",
            "prefix_purchase": "PUR-",
            "prefix_return": "RET-",
            "prefix_supplier_return": "SRET-",
            "prefix_transfer": "TRF-",
            "prefix_adjustment": "ADJ-",
            "prefix_customer_pay": "CPAY-",
            "prefix_supplier_pay": "SPAY-",
            "prefix_expense": "EXP-"
        }
        for k, v in default_settings.items():
            if not db.query(SystemSetting).filter(SystemSetting.key == k).first():
                db.add(SystemSetting(key=k, value=v))
        db.commit()
    except Exception as e:
        print(f"Error seeding default customer/types: {e}")

db = SessionLocal()
try:
    seed_database(db)
finally:
    db.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(locations.router, prefix=f"{settings.API_V1_STR}/locations", tags=["locations"])
app.include_router(products.router, prefix=f"{settings.API_V1_STR}/products", tags=["products"])
app.include_router(suppliers.router, prefix=f"{settings.API_V1_STR}/suppliers", tags=["suppliers"])
app.include_router(purchases.router, prefix=f"{settings.API_V1_STR}/purchases", tags=["purchases"])
app.include_router(supplier_returns.router, prefix=f"{settings.API_V1_STR}/supplier-returns", tags=["supplier-returns"])
app.include_router(customers.router, prefix=f"{settings.API_V1_STR}/customers", tags=["customers"])
app.include_router(sales.router, prefix=f"{settings.API_V1_STR}/sales", tags=["sales"])
app.include_router(customer_returns.router, prefix=f"{settings.API_V1_STR}/customer-returns", tags=["customer-returns"])
app.include_router(inventory.router, prefix=f"{settings.API_V1_STR}/inventory", tags=["inventory"])
app.include_router(expenses.router, prefix=f"{settings.API_V1_STR}/expenses", tags=["expenses"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["reports"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["audit"])
app.include_router(backup.router, prefix=f"{settings.API_V1_STR}/backup", tags=["backup"])
app.include_router(api_settings.router, prefix=f"{settings.API_V1_STR}/settings", tags=["settings"])

@app.get("/")
def root():
    return {"message": "Welcome to the POS System API"}


