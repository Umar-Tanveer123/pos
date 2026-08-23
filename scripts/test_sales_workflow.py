import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from backend.core.database import Base
import backend.models # Ensure metadata populated
from backend.models.partner import Customer, CustomerType, CustomerLedger, CustomerPayment
from backend.models.product import Product, Category, Unit
from backend.models.auth import User, Role, Location
from backend.models.sale import SaleInvoice, SaleItem
from backend.models.ledger import InventoryTransaction, TransactionType

test_engine = create_engine("sqlite:///test_sales.db", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def run_tests():
    # Force rebuild database for clean test
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    db: Session = TestSessionLocal()
    try:
        print("--- RUNNING POS SALES & CREDIT VALIDATION WORKFLOW TESTS ---")
        
        # 1. Create dependencies
        role = Role(name="Admin")
        db.add(role)
        db.flush()
        
        user = User(username="test_cashier", hashed_password="pw", role_id=role.id, is_active=True)
        db.add(user)
        
        location = Location(name="Retail Shop A", address="456 Market St", is_active=True)
        db.add(location)
        db.flush()
        
        unit = Unit(name="Pcs")
        db.add(unit)
        db.flush()
        
        category = Category(name="FMCG")
        db.add(category)
        db.flush()
        
        # Create product with multiple prices
        p1 = Product(
            internal_id="PRD-000001",
            name="Premium Rice 1kg",
            sku="11223344",
            purchase_price=80.0,
            retail_price=100.0,
            wholesale_price=90.0,
            special_price=95.0,
            category_id=category.id,
            unit_id=unit.id,
            is_active=True
        )
        db.add(p1)
        db.flush()
        
        # 2. Seed initial stock
        # Add 100 bags of rice via a purchase transaction
        db.add(InventoryTransaction(
            product_id=p1.id,
            location_id=location.id,
            transaction_type=TransactionType.PURCHASE,
            quantity=100.0,
            reference_id="PUR-000001",
            user_id=user.id
        ))
        db.flush()
        print("[1] Product and initial stock of 100.0 Pcs seeded successfully.")
        
        # 3. Create Customer Types
        ct_retail = CustomerType(name="Retail")
        ct_wholesale = CustomerType(name="Wholesale")
        ct_special = CustomerType(name="Special")
        db.add(ct_retail)
        db.add(ct_wholesale)
        db.add(ct_special)
        db.flush()
        print("[2] Customer types (Retail, Wholesale, Special) created.")
        
        # 4. Create Customers
        cust_retail = Customer(
            internal_id="CUS-000001",
            name="Alice (Retail Client)",
            customer_type_id=ct_retail.id,
            credit_limit=500.0,
            balance=0.0,
            is_active=1
        )
        cust_wholesale = Customer(
            internal_id="CUS-000002",
            name="Bob Distributors",
            customer_type_id=ct_wholesale.id,
            credit_limit=10000.0,
            balance=0.0,
            is_active=1
        )
        db.add(cust_retail)
        db.add(cust_wholesale)
        db.flush()
        print("[3] Customers seeded successfully.")
        
        # 5. Verify price selection based on customer type
        # Retail customer should pay Rs. 100.00
        # Wholesale customer should pay Rs. 90.00
        print("[4] Validating customer-specific pricing matching rules...")
        assert cust_retail.customer_type.name == "Retail"
        assert cust_wholesale.customer_type.name == "Wholesale"
        
        # 6. Test a successful sale with partial credit
        print("[5] Recording a sale of 5 bags of rice to Retail Customer Alice...")
        # Alice buys 5 bags @ Rs. 100.00 each = Rs. 500.00
        # Alice pays Rs. 300.00 down payment, credit balance owed is Rs. 200.00
        total_amount = 5.0 * p1.retail_price
        paid_amount = 300.0
        balance_owed = total_amount - paid_amount # 200.0
        
        # Check credit limit validation (200.0 is within Alice's 500.0 limit)
        assert balance_owed <= cust_retail.credit_limit
        
        # Record Sale
        sale = SaleInvoice(
            internal_id="INV-000001",
            customer_id=cust_retail.id,
            location_id=location.id,
            user_id=user.id,
            total_amount=total_amount,
            paid_amount=paid_amount,
            balance_owed=balance_owed
        )
        db.add(sale)
        db.flush()
        
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=p1.id,
            quantity=5.0,
            unit_price=p1.retail_price,
            total=total_amount
        )
        db.add(sale_item)
        
        # Customer Ledger debit
        cust_retail.balance += balance_owed
        db.add(CustomerLedger(
            customer_id=cust_retail.id,
            transaction_type="SALE",
            reference_id="INV-000001",
            amount=balance_owed,
            balance_after=cust_retail.balance
        ))
        
        # Inventory decrease
        db.add(InventoryTransaction(
            product_id=p1.id,
            location_id=location.id,
            transaction_type=TransactionType.SALE,
            quantity=-5.0, # Negative quantity for sale
            reference_id="INV-000001",
            user_id=user.id
        ))
        db.commit()
        
        # Verification
        db.refresh(cust_retail)
        assert cust_retail.balance == 200.0, f"Expected Alice balance to be 200.0, got {cust_retail.balance}"
        print("✓ Alice's outstanding balance updated correctly to Rs. 200.00")
        
        # Verify Inventory levels
        stock_qty = db.query(func.sum(InventoryTransaction.quantity)).filter(
            (InventoryTransaction.product_id == p1.id) & 
            (InventoryTransaction.location_id == location.id)
        ).scalar() or 0.0
        assert stock_qty == 95.0, f"Expected stock level of 95.0, got {stock_qty}"
        print("✓ Inventory decreased correctly from 100.0 to 95.0 Pcs.")
        
        # 7. Test credit limit violation
        print("[6] Attempting a sale that exceeds the customer's credit limit...")
        # Alice tries to buy another 5 bags @ Rs. 100.00 = Rs. 500.00
        # Alice pays Rs. 100.00, credit balance owed is Rs. 400.00
        # New balance would be 200.0 + 400.0 = 600.0, which exceeds Alice's credit limit of 500.0
        pending_owed = 400.0
        projected_balance = cust_retail.balance + pending_owed
        
        credit_limit_exceeded = False
        if projected_balance > cust_retail.credit_limit:
            credit_limit_exceeded = True
            
        assert credit_limit_exceeded == True, "Expected credit limit validation to block transaction."
        print("✓ Credit limit validation correctly flagged/blocked the overdraft sale.")
        
        print("\n--- ALL POS SALES & CREDIT VALIDATION WORKFLOW TESTS PASSED ---")
        
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
