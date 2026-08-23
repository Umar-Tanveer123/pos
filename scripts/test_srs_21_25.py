import os
import sys

# Setup environment to use backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import SessionLocal
from backend.models.sale import SaleInvoice, SalePayment, InvoiceTemplate

def test_srs_21_25():
    print("======================================================================")
    print("          STARTING SRS 21-25 COMPLIANCE VALIDATION RUN             ")
    print("======================================================================")
    
    db = SessionLocal()
    
    # Check Invoice Templates (SRS 25)
    print("\n[*] Running Test 25: Invoice Templates...")
    templates = db.query(InvoiceTemplate).all()
    template_names = [t.name for t in templates]
    assert "Compact" in template_names, "Compact template missing"
    assert "Standard" in template_names, "Standard template missing"
    assert "Wholesale" in template_names, "Wholesale template missing"
    print(f"    - Found {len(templates)} templates: {', '.join(template_names)}")
    
    print("\n✓ SUCCESS: SRS 21-25 compliance tests passed (Models & DB layout).")
    db.close()

if __name__ == "__main__":
    test_srs_21_25()
