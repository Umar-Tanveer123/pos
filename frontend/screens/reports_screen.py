from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QComboBox, QDateEdit, QFormLayout, QFrame
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime
from frontend.api_client import client
from frontend.theme import export_table_to_csv

class ReportsScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #ffffff; }
            QTableWidget { background-color: #1e1e1e; color: white; border: 1px solid #2a2a2a; }
            QHeaderView::section { background-color: #2a2a2a; color: white; padding: 6px; font-weight: bold; border: 1px solid #333; }
            QDateEdit, QComboBox { background-color: #1e1e1e; color: white; border: 1px solid #333; padding: 4px; border-radius: 4px; }
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("📊 Comprehensive Business Reports")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #a29bfe;")
        layout.addWidget(title)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2a2a2a; background-color: #121212; border-radius: 8px; }
            QTabBar::tab { background-color: #1e1e1e; color: #a0a0a0; padding: 10px 20px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; font-weight: bold; }
            QTabBar::tab:selected { background-color: #121212; color: #6c5ce7; border-bottom: 2px solid #6c5ce7; }
        """)
        
        self.tab_sales = QWidget()
        self.setup_sales_tab(self.tab_sales)
        self.tabs.addTab(self.tab_sales, "📈 Sales Reports")
        
        self.tab_purchases = QWidget()
        self.setup_purchases_tab(self.tab_purchases)
        self.tabs.addTab(self.tab_purchases, "📥 Purchase Reports")
        
        self.tab_financials = QWidget()
        self.setup_financials_tab(self.tab_financials)
        self.tabs.addTab(self.tab_financials, "💰 Financial Reports")
        
        layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
    def on_tab_changed(self, index):
        if index == 0:
            self.load_sales_report()
        elif index == 1:
            self.load_purchases_report()
        elif index == 2:
            self.load_financials_report()
            
    def load_data(self):
        self.on_tab_changed(self.tabs.currentIndex())

    # --- Sales Tab ---
    def setup_sales_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.sales_type_combo = QComboBox()
        self.sales_type_combo.addItems([
            "Daily Sales Summary", "Monthly Sales Summary", "Best-Selling Products", "Sales by Payment Method"
        ])
        filter_layout.addWidget(QLabel("Report Type:"))
        filter_layout.addWidget(self.sales_type_combo)

        filter_layout.addWidget(QLabel("From:"))
        self.sales_start_date = QDateEdit()
        self.sales_start_date.setCalendarPopup(True)
        self.sales_start_date.setDate(QDate.currentDate().addDays(-30))
        filter_layout.addWidget(self.sales_start_date)

        filter_layout.addWidget(QLabel("To:"))
        self.sales_end_date = QDateEdit()
        self.sales_end_date.setCalendarPopup(True)
        self.sales_end_date.setDate(QDate.currentDate())
        filter_layout.addWidget(self.sales_end_date)
        
        btn_run = QPushButton("⚡ Generate Report")
        btn_run.clicked.connect(self.load_sales_report)
        btn_run.setStyleSheet("background-color: #0984e3; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;")
        filter_layout.addWidget(btn_run)
        
        btn_export = QPushButton("📄 Export CSV")
        btn_export.clicked.connect(lambda: export_table_to_csv(self.sales_table, self))
        btn_export.setStyleSheet("background-color: #e17055; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;")
        filter_layout.addWidget(btn_export)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(4)
        self.sales_table.setHorizontalHeaderLabels(["Metric / Group", "Transactions", "Total Amount (Rs.)", "Avg / Note"])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.sales_table)
        
    def load_sales_report(self):
        start_str = self.sales_start_date.date().toString("yyyy-MM-dd")
        end_str = self.sales_end_date.date().toString("yyyy-MM-dd")
        
        sales = client.get_sales(start_date=start_str, end_date=end_str)
        report_type = self.sales_type_combo.currentText()
        
        self.sales_table.setRowCount(0)
        
        if report_type == "Sales by Payment Method":
            self.sales_table.setColumnCount(3)
            self.sales_table.setHorizontalHeaderLabels(["Payment Method", "Order Count", "Total Revenue (Rs.)"])
            agg = {}
            for s in sales:
                pm = s.get("payment_method") or "Cash"
                if pm not in agg:
                    agg[pm] = {"count": 0, "amount": 0.0}
                agg[pm]["count"] += 1
                agg[pm]["amount"] += s.get("total_amount", 0.0)
                
            self.sales_table.setRowCount(len(agg))
            for i, (k, v) in enumerate(agg.items()):
                self.sales_table.setItem(i, 0, QTableWidgetItem(str(k)))
                self.sales_table.setItem(i, 1, QTableWidgetItem(str(v["count"])))
                self.sales_table.setItem(i, 2, QTableWidgetItem(f"Rs. {v['amount']:,.2f}"))

        elif report_type == "Daily Sales Summary":
            self.sales_table.setColumnCount(4)
            self.sales_table.setHorizontalHeaderLabels(["Date", "Total Invoices", "Total Sales (Rs.)", "Avg Sale Value (Rs.)"])
            agg = {}
            for s in sales:
                dt_str = s.get("date", "")[:10]
                if not dt_str: continue
                if dt_str not in agg:
                    agg[dt_str] = {"count": 0, "amount": 0.0}
                agg[dt_str]["count"] += 1
                agg[dt_str]["amount"] += s.get("total_amount", 0.0)

            sorted_dates = sorted(agg.keys(), reverse=True)
            self.sales_table.setRowCount(len(sorted_dates))
            for i, dt_key in enumerate(sorted_dates):
                v = agg[dt_key]
                avg = v["amount"] / v["count"] if v["count"] > 0 else 0.0
                self.sales_table.setItem(i, 0, QTableWidgetItem(dt_key))
                self.sales_table.setItem(i, 1, QTableWidgetItem(str(v["count"])))
                self.sales_table.setItem(i, 2, QTableWidgetItem(f"Rs. {v['amount']:,.2f}"))
                self.sales_table.setItem(i, 3, QTableWidgetItem(f"Rs. {avg:,.2f}"))

        elif report_type == "Monthly Sales Summary":
            self.sales_table.setColumnCount(4)
            self.sales_table.setHorizontalHeaderLabels(["Month", "Total Invoices", "Total Sales (Rs.)", "Avg Sale Value (Rs.)"])
            agg = {}
            for s in sales:
                m_str = s.get("date", "")[:7]
                if not m_str: continue
                if m_str not in agg:
                    agg[m_str] = {"count": 0, "amount": 0.0}
                agg[m_str]["count"] += 1
                agg[m_str]["amount"] += s.get("total_amount", 0.0)

            sorted_months = sorted(agg.keys(), reverse=True)
            self.sales_table.setRowCount(len(sorted_months))
            for i, m_key in enumerate(sorted_months):
                v = agg[m_key]
                avg = v["amount"] / v["count"] if v["count"] > 0 else 0.0
                self.sales_table.setItem(i, 0, QTableWidgetItem(m_key))
                self.sales_table.setItem(i, 1, QTableWidgetItem(str(v["count"])))
                self.sales_table.setItem(i, 2, QTableWidgetItem(f"Rs. {v['amount']:,.2f}"))
                self.sales_table.setItem(i, 3, QTableWidgetItem(f"Rs. {avg:,.2f}"))

        elif report_type == "Best-Selling Products":
            self.sales_table.setColumnCount(3)
            self.sales_table.setHorizontalHeaderLabels(["Product Name", "Qty Sold", "Total Revenue (Rs.)"])
            prod_agg = {}
            for s in sales:
                items = s.get("items", [])
                for item in items:
                    p_id = item.get("product_id")
                    qty = item.get("quantity", 0.0)
                    tot = item.get("total", 0.0)
                    if p_id not in prod_agg:
                        prod_agg[p_id] = {"qty": 0.0, "amount": 0.0}
                    prod_agg[p_id]["qty"] += qty
                    prod_agg[p_id]["amount"] += tot

            all_prods = {p["id"]: p["name"] for p in client.get_products(is_active=None)}
            sorted_prods = sorted(prod_agg.items(), key=lambda x: x[1]["qty"], reverse=True)
            
            self.sales_table.setRowCount(len(sorted_prods))
            for i, (p_id, data) in enumerate(sorted_prods):
                p_name = all_prods.get(p_id, f"Product #{p_id}")
                self.sales_table.setItem(i, 0, QTableWidgetItem(p_name))
                self.sales_table.setItem(i, 1, QTableWidgetItem(f"{data['qty']:.2f}"))
                self.sales_table.setItem(i, 2, QTableWidgetItem(f"Rs. {data['amount']:,.2f}"))

    # --- Purchases Tab ---
    def setup_purchases_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.pur_type_combo = QComboBox()
        self.pur_type_combo.addItems([
            "Daily Purchases Summary", "Purchases by Supplier"
        ])
        filter_layout.addWidget(QLabel("Report Type:"))
        filter_layout.addWidget(self.pur_type_combo)

        btn_run = QPushButton("⚡ Generate Report")
        btn_run.clicked.connect(self.load_purchases_report)
        btn_run.setStyleSheet("background-color: #0984e3; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;")
        filter_layout.addWidget(btn_run)

        btn_export = QPushButton("📄 Export CSV")
        btn_export.clicked.connect(lambda: export_table_to_csv(self.pur_table, self))
        btn_export.setStyleSheet("background-color: #e17055; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;")
        filter_layout.addWidget(btn_export)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.pur_table = QTableWidget()
        self.pur_table.setColumnCount(3)
        self.pur_table.setHorizontalHeaderLabels(["Group / Supplier", "Invoices Count", "Total Purchase Cost (Rs.)"])
        self.pur_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.pur_table)

    def load_purchases_report(self):
        purchases = client.get_purchases()
        report_type = self.pur_type_combo.currentText()
        self.pur_table.setRowCount(0)

        if report_type == "Daily Purchases Summary":
            agg = {}
            for p in purchases:
                dt_str = p.get("date", "")[:10]
                if not dt_str: continue
                if dt_str not in agg:
                    agg[dt_str] = {"count": 0, "amount": 0.0}
                agg[dt_str]["count"] += 1
                agg[dt_str]["amount"] += p.get("total_amount", 0.0)

            sorted_dates = sorted(agg.keys(), reverse=True)
            self.pur_table.setRowCount(len(sorted_dates))
            for i, dt_key in enumerate(sorted_dates):
                v = agg[dt_key]
                self.pur_table.setItem(i, 0, QTableWidgetItem(dt_key))
                self.pur_table.setItem(i, 1, QTableWidgetItem(str(v["count"])))
                self.pur_table.setItem(i, 2, QTableWidgetItem(f"Rs. {v['amount']:,.2f}"))

        elif report_type == "Purchases by Supplier":
            suppliers = {s["id"]: s["name"] for s in client.get_suppliers()}
            agg = {}
            for p in purchases:
                sup_id = p.get("supplier_id")
                if sup_id not in agg:
                    agg[sup_id] = {"count": 0, "amount": 0.0}
                agg[sup_id]["count"] += 1
                agg[sup_id]["amount"] += p.get("total_amount", 0.0)

            self.pur_table.setRowCount(len(agg))
            for i, (sup_id, v) in enumerate(agg.items()):
                sup_name = suppliers.get(sup_id, f"Supplier #{sup_id}")
                self.pur_table.setItem(i, 0, QTableWidgetItem(sup_name))
                self.pur_table.setItem(i, 1, QTableWidgetItem(str(v["count"])))
                self.pur_table.setItem(i, 2, QTableWidgetItem(f"Rs. {v['amount']:,.2f}"))

    # --- Financials Tab ---
    def setup_financials_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        top = QHBoxLayout()
        btn_run = QPushButton("🔄 Refresh Financial Report")
        btn_run.clicked.connect(self.load_financials_report)
        btn_run.setStyleSheet("background-color: #00b894; color: white; padding: 8px 16px; font-weight: bold; border-radius: 4px;")
        top.addWidget(btn_run)
        
        btn_export = QPushButton("📄 Export CSV")
        btn_export.clicked.connect(lambda: export_table_to_csv(self.fin_table, self))
        btn_export.setStyleSheet("background-color: #e17055; color: white; padding: 8px 16px; font-weight: bold; border-radius: 4px;")
        top.addWidget(btn_export)
        top.addStretch()
        
        layout.addLayout(top)
        
        self.fin_table = QTableWidget()
        self.fin_table.setColumnCount(2)
        self.fin_table.setHorizontalHeaderLabels(["Financial Metric", "Value (Rs.)"])
        self.fin_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.fin_table)
        
    def load_financials_report(self):
        metrics = client.get_financial_summary()
        
        rev = metrics.get("revenue", 0.0)
        pur = metrics.get("purchases", 0.0)
        exp = metrics.get("expenses", 0.0)
        rec = metrics.get("receivables", 0.0)
        pay = metrics.get("payables", 0.0)
        est_net = rev - pur - exp
        
        items = [
            ("Total Gross Sales Revenue", rev),
            ("Total Stock Purchases Cost", pur),
            ("Total Operating Expenses", exp),
            ("Estimated Net Profit / Loss", est_net),
            ("Customer Receivables (Outstanding Credits)", rec),
            ("Supplier Payables (Outstanding Debts)", pay),
        ]
        
        self.fin_table.setRowCount(len(items))
        for i, (k, v) in enumerate(items):
            item_k = QTableWidgetItem(k)
            item_v = QTableWidgetItem(f"Rs. {v:,.2f}")
            if k == "Estimated Net Profit / Loss":
                item_k.setStyleSheet("font-weight: bold; color: #00b894;")
                item_v.setStyleSheet("font-weight: bold; color: #00b894;" if v >= 0 else "font-weight: bold; color: #ff4757;")
            self.fin_table.setItem(i, 0, item_k)
            self.fin_table.setItem(i, 1, item_v)

    def set_profit_visibility(self, visible):
        self.tabs.setTabEnabled(2, visible)
        if not visible:
            if self.tabs.count() == 3:
                self.tabs.removeTab(2)
        else:
            if self.tabs.count() == 2:
                self.tabs.addTab(self.tab_financials, "💰 Financial Reports")

