import sys
import os
from sqlalchemy.orm import Session

# Add workspace directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.database import SessionLocal, engine, Base
from backend.models.partner import Supplier, Customer
from backend.models.product import Product, Category, Brand
from backend.models.sale import SaleInvoice, SaleItem
from backend.models.auth import User, Location
from backend.api.suppliers import get_supplier_profit_report

def run_test():
    print("======================================================================")
    print("             TESTING SUPPLIER & PRODUCT PROFIT REPORTING              ")
    print("======================================================================")

    # Initialize a clean test session
    db: Session = SessionLocal()
    try:
        # Create a mock user for current user session dependency
        mock_user = User(username="test_report_admin", is_active=True, hashed_password="mock")
        
        # 1. Create a Supplier
        sup = Supplier(
            internal_id="SUP-TEST-001",
            name="Alpha Distributors",
            phone="12345678",
            balance=0.0
        )
        db.add(sup)
        
        # 2. Create Category and Brand
        cat = Category(name="Test Category")
        brand = Brand(name="Test Brand")
        db.add(cat)
        db.add(brand)
        db.flush()
        
        # 3. Create a Product and associate it with the Supplier
        prod = Product(
            internal_id="PRD-TEST-001",
            name="Premium Basmati Rice 5kg",
            sku="RICE-BAS-01",
            barcode="888811112222",
            retail_price=950.0,
            wholesale_price=900.0,
            special_price=880.0,
            purchase_price=600.0,  # Profit per unit = 950 - 600 = 350 Rs.
            category_id=cat.id,
            brand_id=brand.id,
            is_active=True
        )
        prod.suppliers.append(sup)
        db.add(prod)
        db.flush()
        
        # 4. Create Location, Customer, and SaleInvoice
        loc = Location(name="Main Store", address="Main Street")
        cust = Customer(name="John Doe Retail", internal_id="CUST-RET-01", balance=0.0)
        db.add(loc)
        db.add(cust)
        db.flush()
        
        sale = SaleInvoice(
            internal_id="INV-TEST-001",
            customer_id=cust.id,
            location_id=loc.id,
            user_id=1,  # Admin/System User
            discount=0.0,
            total_amount=1900.0,  # 2 units * 950
            paid_amount=1900.0,
            balance_owed=0.0
        )
        db.add(sale)
        db.flush()
        
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=prod.id,
            quantity=2.0,
            unit_price=950.0,
            discount=0.0,
            total=1900.0
        )
        db.add(sale_item)
        db.commit()
        
        print("[*] Mock data seeded successfully:")
        print(f"    - Supplier: {sup.name} (ID: {sup.id})")
        print(f"    - Product: {prod.name} (Cost: Rs. {prod.purchase_price}, Retail: Rs. {prod.retail_price})")
        print(f"    - Sale: 2 units sold for Rs. {sale_item.total}")
        
        # 5. Fetch profit report using the backend function
        report = get_supplier_profit_report(supplier_id=sup.id, db=db, current_user=mock_user)
        
        # Verify supplier report
        suppliers_list = report.get("suppliers", [])
        target_sup_report = next((s for s in suppliers_list if s["supplier_id"] == sup.id), None)
        
        assert target_sup_report is not None, "Supplier not found in profit report!"
        assert target_sup_report["total_sales_revenue"] == 1900.0, f"Expected 1900.0 revenue, got {target_sup_report['total_sales_revenue']}"
        assert target_sup_report["total_purchase_cost"] == 1200.0, f"Expected 1200.0 cost (2 * 600), got {target_sup_report['total_purchase_cost']}"
        assert target_sup_report["net_profit"] == 700.0, f"Expected 700.0 profit (1900 - 1200), got {target_sup_report['net_profit']}"
        
        # Margin: (700 / 1900) * 100 = 36.84%
        expected_margin = (700.0 / 1900.0) * 100.0
        assert abs(target_sup_report["profit_margin_pct"] - expected_margin) < 0.01, f"Expected margin {expected_margin}%, got {target_sup_report['profit_margin_pct']}%"
        
        print("[✓] Supplier-wise profit verification PASSED.")
        
        # Verify product report
        products_list = report.get("products", [])
        target_prod_report = next((p for p in products_list if p["product_id"] == prod.id), None)
        
        assert target_prod_report is not None, "Product not found in detailed report!"
        assert target_prod_report["total_qty_sold"] == 2.0, f"Expected 2.0 units sold, got {target_prod_report['total_qty_sold']}"
        assert target_prod_report["total_sales_revenue"] == 1900.0, f"Expected 1900.0 revenue, got {target_prod_report['total_sales_revenue']}"
        assert target_prod_report["total_purchase_cost"] == 1200.0, f"Expected 1200.0 cost, got {target_prod_report['total_purchase_cost']}"
        assert target_prod_report["net_profit"] == 700.0, f"Expected 700.0 profit, got {target_prod_report['net_profit']}"
        
        print("[✓] Product-wise profit verification PASSED.")
        
        # Clean up database after test
        db.delete(sale_item)
        db.delete(sale)
        db.delete(cust)
        db.delete(loc)
        db.delete(prod)
        db.delete(cat)
        db.delete(brand)
        db.delete(sup)
        db.commit()
        print("[*] Cleanup finished successfully.")
        print("\nSUCCESS: All supplier and product profit report validation checks passed!")
        
    except Exception as e:
        db.rollback()
        print(f"\n[!] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
