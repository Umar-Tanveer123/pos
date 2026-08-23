from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from backend.core.database import get_db
from backend.models.sale import SaleInvoice, SaleItem, CustomerReturn
from backend.models.purchase import PurchaseInvoice
from backend.models.expense import Expense
from backend.models.partner import Customer, Supplier
from backend.models.product import Product, ProductVariant
from backend.models.ledger import InventoryTransaction
from backend.api.auth import get_current_active_user
from backend.models.auth import User, Role

router = APIRouter()

def parse_date_range(period: str):
    now = datetime.now(timezone.utc)
    start_date = None
    end_date = None
    
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif period == "yesterday":
        end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=1)
    elif period == "this_week":
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == "this_month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == "this_year":
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        
    return start_date, end_date

@router.get("/dashboard")
def get_dashboard_metrics(
    period: str = Query("all", description="today, yesterday, this_week, this_month, this_year, all"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    start_date, end_date = parse_date_range(period)
    
    # Custom overrides if provided
    if start:
        try: start_date = datetime.fromisoformat(start)
        except: pass
    if end:
        try: end_date = datetime.fromisoformat(end)
        except: pass

    # Helpers
    def apply_dates(query, model_col):
        if start_date: query = query.filter(model_col >= start_date)
        if end_date: query = query.filter(model_col < end_date)
        return query

    # 1. Total Sales (Revenue)
    sales_q = db.query(SaleInvoice).filter(SaleInvoice.status != "CANCELLED")
    sales_q = apply_dates(sales_q, SaleInvoice.date)
    sales = sales_q.all()
    
    total_sales = sum(s.total_amount for s in sales)
    invoices_count = len(sales)
    
    # 2. COGS & Gross Profit
    cogs = 0.0
    for s in sales:
        for item in s.items:
            # We estimate COGS using current product purchase price
            # In a real ERP, we'd lock the cost at the time of sale.
            p = item.product
            v = item.variant
            cost = v.purchase_price if v and v.purchase_price else (p.purchase_price if p else 0.0)
            cogs += (item.quantity * cost)
            
    gross_profit = total_sales - cogs
    
    # 3. Expenses
    exp_q = db.query(func.sum(Expense.amount))
    exp_q = apply_dates(exp_q, Expense.date)
    total_expenses = exp_q.scalar() or 0.0
    
    # 4. Net Profit
    net_profit = gross_profit - total_expenses
    
    # 5. Total Purchases
    purch_q = db.query(func.sum(PurchaseInvoice.total_amount))
    purch_q = apply_dates(purch_q, PurchaseInvoice.date)
    total_purchases = purch_q.scalar() or 0.0
    
    # 6. Outstanding Receivables & Payables (Usually global, not date-bound)
    receivables = db.query(func.sum(Customer.balance)).filter(Customer.balance > 0).scalar() or 0.0
    payables = db.query(func.sum(Supplier.balance)).filter(Supplier.balance > 0).scalar() or 0.0
    
    # 7. Returns Total
    ret_q = db.query(func.sum(CustomerReturn.total_refund))
    ret_q = apply_dates(ret_q, CustomerReturn.date)
    returns = ret_q.scalar() or 0.0
    
    # 8. Low Stock Count
    low_stock_count = 0
    out_of_stock_count = 0
    
    products = db.query(Product).filter(Product.is_active == True).all()
    for p in products:
        threshold = p.low_stock_threshold or 0
        current_stock = db.query(func.sum(InventoryTransaction.quantity)).filter(
            InventoryTransaction.product_id == p.id
        ).scalar() or 0.0
        
        if current_stock <= 0:
            out_of_stock_count += 1
        elif current_stock <= threshold:
            low_stock_count += 1
            
    return {
        "total_sales": total_sales,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "total_purchases": total_purchases,
        "outstanding_receivables": receivables,
        "outstanding_payables": payables,
        "returns_total": returns,
        "invoices_count": invoices_count,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "total_products": len(products)
    }

@router.get("/financials")
def get_financial_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Overarching P&L
    sales = db.query(func.sum(SaleInvoice.total_amount)).filter(SaleInvoice.status != "CANCELLED").scalar() or 0.0
    purchases = db.query(func.sum(PurchaseInvoice.total_amount)).scalar() or 0.0
    expenses = db.query(func.sum(Expense.amount)).scalar() or 0.0
    
    receivables = db.query(func.sum(Customer.balance)).filter(Customer.balance > 0).scalar() or 0.0
    payables = db.query(func.sum(Supplier.balance)).filter(Supplier.balance > 0).scalar() or 0.0
    
    return {
        "revenue": sales,
        "purchases": purchases,
        "expenses": expenses,
        "receivables": receivables,
        "payables": payables
    }
