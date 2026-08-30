from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QComboBox, QDateEdit, QFormLayout
)
from PySide6.QtCore import Qt, QDate
from frontend.api_client import client
from frontend.theme import export_table_to_csv

class ReportsScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #ffffff; }
            QTableWidget { background-color: #1e1e1e; color: white; border: 1px solid #2a2a2a; }
            QHeaderView::section { background-color: #2a2a2a; color: white; padding: 4px; font-weight: bold; border: 1px solid #333; }
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("📊 Comprehensive Reports")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #a29bfe;")
        layout.addWidget(title)
        
        self.tabs = QTabWidget()
        
        self.tab_sales = QWidget()
        self.setup_sales_tab(self.tab_sales)
        self.tabs.addTab(self.tab_sales, "Sales Reports")
        
        self.tab_purchases = QWidget()
        self.setup_purchases_tab(self.tab_purchases)
        self.tabs.addTab(self.tab_purchases, "Purchase Reports")
        
        self.tab_financials = QWidget()
        self.setup_financials_tab(self.tab_financials)
        self.tabs.addTab(self.tab_financials, "Financial Reports")
        
        layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
    def on_tab_changed(self, index):
        if index == 0:
            self.load_sales_report()
        elif index == 1:
            pass
        elif index == 2:
            self.load_financials_report()
            
    def load_data(self):
        self.on_tab_changed(self.tabs.currentIndex())

    # --- Sales Tab ---
    def setup_sales_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        filter_layout = QHBoxLayout()
        self.sales_type_combo = QComboBox()
        self.sales_type_combo.addItems(["Daily Sales", "Monthly Sales", "Best-selling Products", "Payment-method Sales"])
        filter_layout.addWidget(QLabel("Report Type:"))
        filter_layout.addWidget(self.sales_type_combo)
        
        btn_run = QPushButton("Run Report")
        btn_run.clicked.connect(self.load_sales_report)
        btn_run.setStyleSheet("background-color: #0984e3; color: white; padding: 6px; font-weight: bold;")
        filter_layout.addWidget(btn_run)
        
        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(lambda: export_table_to_csv(self.sales_table, self))
        btn_export.setStyleSheet("background-color: #e17055; color: white; padding: 6px; font-weight: bold;")
        filter_layout.addWidget(btn_export)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(3)
        self.sales_table.setHorizontalHeaderLabels(["Metric / Group", "Count", "Total Amount (Rs.)"])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.sales_table)
        
    def load_sales_report(self):
        # In a real app, this would call specialized backend reporting endpoints.
        # Here we demonstrate aggregation on the frontend for the prototype.
        sales = client.get_sales()
        report_type = self.sales_type_combo.currentText()
        
        self.sales_table.setRowCount(0)
        
        if report_type == "Payment-method Sales":
            agg = {}
            for s in sales:
                pm = s.get("payment_method", "Unknown")
                if pm not in agg:
                    agg[pm] = {"count": 0, "amount": 0.0}
                agg[pm]["count"] += 1
                agg[pm]["amount"] += s.get("total_amount", 0.0)
                
            self.sales_table.setRowCount(len(agg))
            for i, (k, v) in enumerate(agg.items()):
                self.sales_table.setItem(i, 0, QTableWidgetItem(k))
                self.sales_table.setItem(i, 1, QTableWidgetItem(str(v["count"])))
                self.sales_table.setItem(i, 2, QTableWidgetItem(f"{v['amount']:,.2f}"))

    # --- Purchases Tab ---
    def setup_purchases_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.addWidget(QLabel("Purchase Reports will be displayed here."))
        layout.addStretch()

    # --- Financials Tab ---
    def setup_financials_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        top = QHBoxLayout()
        btn_run = QPushButton("Run Financial Report")
        btn_run.clicked.connect(self.load_financials_report)
        btn_run.setStyleSheet("background-color: #00b894; color: white; padding: 6px; font-weight: bold;")
        top.addWidget(btn_run)
        
        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(lambda: export_table_to_csv(self.fin_table, self))
        btn_export.setStyleSheet("background-color: #e17055; color: white; padding: 6px; font-weight: bold;")
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
        
        self.fin_table.setRowCount(5)
        
        items = [
            ("Revenue (Sales)", metrics.get("revenue", 0.0)),
            ("Total Purchases", metrics.get("purchases", 0.0)),
            ("Total Expenses", metrics.get("expenses", 0.0)),
            ("Customer Receivables", metrics.get("receivables", 0.0)),
            ("Supplier Payables", metrics.get("payables", 0.0)),
        ]
        
        for i, (k, v) in enumerate(items):
            self.fin_table.setItem(i, 0, QTableWidgetItem(k))
            self.fin_table.setItem(i, 1, QTableWidgetItem(f"{v:,.2f}"))

    def set_profit_visibility(self, visible):
        self.tabs.setTabEnabled(2, visible)
        if not visible:
            if self.tabs.count() == 3:
                self.tabs.removeTab(2)
        else:
            if self.tabs.count() == 2:
                self.tabs.addTab(self.tab_financials, "Financial Reports")
