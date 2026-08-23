import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.core.database import Base
import backend.models # Ensure metadata populated
from backend.models.partner import Supplier
from backend.models.product import Product, Category, Unit
from backend.models.auth import User, Role, Location
from backend.models.purchase import PurchaseInvoice, PurchaseItem, SupplierLedger, SupplierPayment, PriceAuditLog
from backend.models.ledger import InventoryTransaction, TransactionType

test_engine = create_engine("sqlite:///test.db", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def run_tests():
    # Force rebuild database for clean test
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    db: Session = TestSessionLocal()
    try:
        print("--- RUNNING POS ADVANCED INVENTORY WORKFLOW TESTS ---")
        
        # 1. Create dependencies
        role = Role(name="Admin")
        db.add(role)
        db.flush()
        
        user = User(username="test_admin", hashed_password="pw", role_id=role.id, is_active=True)
        db.add(user)
        
        location = Location(name="Warehouse A", address="123 Main St", is_active=True)
        db.add(location)
        db.flush()
        
        unit = Unit(name="Pcs")
        db.add(unit)
        db.flush()
        
        category = Category(name="Electronics")
        db.add(category)
        db.flush()
        
        # Create products
        p1 = Product(
            internal_id="PRD-000001",
            name="Laptop",
            sku="SKU-LAPTOP",
            purchase_price=800.0,
            retail_price=1000.0,
            wholesale_price=950.0,
            special_price=980.0,
            category_id=category.id,
            unit_id=unit.id,
            is_active=True
        )
        p2 = Product(
            internal_id="PRD-000002",
            name="Mouse",
            sku="SKU-MOUSE",
            purchase_price=10.0,
            retail_price=20.0,
            wholesale_price=18.0,
            special_price=19.0,
            category_id=category.id,
            unit_id=unit.id,
            is_active=True
        )
        db.add(p1)
        db.add(p2)
        db.flush()
        
        # Create supplier
        supplier = Supplier(
            internal_id="SUP-000001",
            name="Alpha Distributors",
            balance=0.0
        )
        supplier.products.append(p1)
        supplier.products.append(p2)
        db.add(supplier)
        db.flush()
        
        print("[1] Dependencies seeded successfully.")
        
        # 2. Test Purchase Workflow
        print("[2] Recording purchase invoice...")
        # Items payload:
        # p1: qty 10, cost 850.0 (price change!)
        # p2: qty 50, cost 10.0 (no price change)
        items_in = [
            {"prod": p1, "qty": 10, "cost": 850.0},
            {"prod": p2, "qty": 50, "cost": 10.0}
        ]
        
        total_amount = (10 * 850.0) + (50 * 10.0) # 8500 + 500 = 9000
        paid = 4000.0
        payable = total_amount - paid # 5000.0 credit owed
        
        invoice = PurchaseInvoice(
            internal_id="PUR-000001",
            supplier_id=supplier.id,
            location_id=location.id,
            user_id=user.id,
            total_amount=total_amount,
            paid_amount=paid,
            payable_amount=payable
        )
        db.add(invoice)
        db.flush()
        
        # Add Supplier ledger entry (+total_amount)
        supplier.balance += payable
        purchase_ledger = SupplierLedger(
            supplier_id=supplier.id,
            transaction_type="PURCHASE",
            reference_id=invoice.internal_id,
            amount=total_amount,
            balance_after=supplier.balance + paid
        )
        db.add(purchase_ledger)
        
        # Add Payment ledger entry (-paid_amount)
        payment = SupplierPayment(
            internal_id="PAY-000001",
            supplier_id=supplier.id,
            purchase_id=invoice.id,
            amount=paid,
            payment_method="Cash"
        )
        db.add(payment)
        
        payment_ledger = SupplierLedger(
            supplier_id=supplier.id,
            transaction_type="PAYMENT",
            reference_id="PAY-000001",
            amount=-paid,
            balance_after=supplier.balance
        )
        db.add(payment_ledger)
        
        # Add Items & Inventory Trans
        for item in items_in:
            db_item = PurchaseItem(
                purchase_id=invoice.id,
                product_id=item["prod"].id,
                quantity=item["qty"],
                purchase_price=item["cost"],
                total=item["qty"] * item["cost"]
            )
            db.add(db_item)
            
            # Check price change audit
            if item["prod"].purchase_price != item["cost"]:
                audit = PriceAuditLog(
                    product_id=item["prod"].id,
                    user_id=user.id,
                    old_purchase_price=item["prod"].purchase_price,
                    new_purchase_price=item["cost"],
                    old_retail_price=item["prod"].retail_price,
                    new_retail_price=item["prod"].retail_price,
                    old_wholesale_price=item["prod"].wholesale_price,
                    new_wholesale_price=item["prod"].wholesale_price,
                    old_special_price=item["prod"].special_price,
                    new_special_price=item["prod"].special_price,
                    change_type="PURCHASE"
                )
                db.add(audit)
                item["prod"].purchase_price = item["cost"] # Override cost price!
                
            # Inventory Trans
            inv_trans = InventoryTransaction(
                product_id=item["prod"].id,
                location_id=location.id,
                transaction_type=TransactionType.PURCHASE,
                quantity=item["qty"],
                reference_id=invoice.internal_id,
                user_id=user.id
            )
            db.add(inv_trans)
            
        db.commit()
        print("[3] Purchase workflow complete. Verifying integrity...")
        
        # Reload values
        db.refresh(supplier)
        db.refresh(p1)
        db.refresh(p2)
        
        # Verify supplier balance is 5000.0
        assert supplier.balance == 5000.0, f"Expected supplier balance 5000.0, got {supplier.balance}"
        print("✓ Supplier balance is correct (Rs. 5000.00)")
        
        # Verify p1 purchase_price updated to 850.0
        assert p1.purchase_price == 850.0, f"Expected Laptop purchase price 850.0, got {p1.purchase_price}"
        print("✓ Product cost price updated correctly in catalog (Rs. 850.00)")
        
        # Verify price audit log has 1 entry
        audit_count = db.query(PriceAuditLog).count()
        assert audit_count == 1, f"Expected 1 price audit log entry, got {audit_count}"
        print("✓ Price audit log captured the Laptop cost price override.")
        
        # Verify Inventory Transactions exist for both products
        inv_trans_count = db.query(InventoryTransaction).filter(InventoryTransaction.transaction_type == TransactionType.PURCHASE).count()
        assert inv_trans_count == 2, f"Expected 2 inventory transactions, got {inv_trans_count}"
        print("✓ Stock received inventory transactions recorded successfully.")
        
        # 3. Test Supplier Payment record
        print("[4] Recording a subsequent credit payment of Rs. 1500.00...")
        # Reduce payable
        supplier.balance -= 1500.0
        
        pay2 = SupplierPayment(
            internal_id="PAY-000002",
            supplier_id=supplier.id,
            amount=1500.0,
            payment_method="Bank Transfer"
        )
        db.add(pay2)
        
        pay_ledger2 = SupplierLedger(
            supplier_id=supplier.id,
            transaction_type="PAYMENT",
            reference_id="PAY-000002",
            amount=-1500.0,
            balance_after=supplier.balance
        )
        db.add(pay_ledger2)
        db.commit()
        
        db.refresh(supplier)
        assert supplier.balance == 3500.0, f"Expected supplier balance 3500.0, got {supplier.balance}"
        print("✓ Subsequent supplier payment balance reduction is correct (Rs. 3500.00)")
        
        print("\n--- ALL ADVANCED INVENTORY INTEGRITY TESTS PASSED ---")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILURE: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED TEST ERROR: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
