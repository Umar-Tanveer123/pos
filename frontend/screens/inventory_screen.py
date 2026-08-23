from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QMessageBox, QDialog,
    QFormLayout, QComboBox, QTextEdit, QDoubleSpinBox
)
from PySide6.QtCore import Qt
from frontend.api_client import client
from frontend.theme import fix_comboboxes
from datetime import datetime

class InventoryScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #ffffff; }
            QTableWidget { background-color: #1e1e1e; color: white; border: 1px solid #2a2a2a; }
            QHeaderView::section { background-color: #2a2a2a; color: white; padding: 4px; font-weight: bold; border: 1px solid #333; }
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("📦 Advanced Inventory Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #f39c12;")
        layout.addWidget(title)
        
        self.tabs = QTabWidget()
        
        # Tab 1: Low Stock Alerts
        self.tab_alerts = QWidget()
        self.setup_alerts_tab(self.tab_alerts)
        self.tabs.addTab(self.tab_alerts, "Low Stock Alerts")
        
        # Tab 2: Stock Transfers
        self.tab_transfers = QWidget()
        self.setup_transfers_tab(self.tab_transfers)
        self.tabs.addTab(self.tab_transfers, "Stock Transfers")
        
        # Tab 3: Stock Adjustments
        self.tab_adjustments = QWidget()
        self.setup_adjustments_tab(self.tab_adjustments)
        self.tabs.addTab(self.tab_adjustments, "Stock Adjustments")
        
        layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        self.load_alerts()
        
    def on_tab_changed(self, index):
        if index == 0:
            self.load_alerts()
        elif index == 1:
            self.load_transfers()
        elif index == 2:
            pass # Load adjustments if we had a get_adjustments API. (For now, just history or empty)
            
    # --- Alerts Tab ---
    def setup_alerts_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        btn_refresh = QPushButton("🔄 Refresh Alerts")
        btn_refresh.clicked.connect(self.load_alerts)
        btn_refresh.setStyleSheet("background-color: #34495e; color: white; padding: 6px; font-weight: bold;")
        
        top = QHBoxLayout()
        top.addStretch()
        top.addWidget(btn_refresh)
        layout.addLayout(top)
        
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(4)
        self.alerts_table.setHorizontalHeaderLabels(["Product", "Variant", "Current Stock", "Threshold"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.alerts_table)
        
    def load_alerts(self):
        alerts = client.get_low_stock_alerts()
        self.alerts_table.setRowCount(len(alerts))
        for row, a in enumerate(alerts):
            self.alerts_table.setItem(row, 0, QTableWidgetItem(a["product_name"]))
            self.alerts_table.setItem(row, 1, QTableWidgetItem(a["variant_name"] or "-"))
            
            stock_item = QTableWidgetItem(f"{a['current_stock']:.2f}")
            if a["current_stock"] <= 0:
                stock_item.setForeground(Qt.red)
            else:
                stock_item.setForeground(Qt.yellow)
            self.alerts_table.setItem(row, 2, stock_item)
            
            self.alerts_table.setItem(row, 3, QTableWidgetItem(f"{a['threshold']:.2f}"))

    # --- Transfers Tab ---
    def setup_transfers_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        top = QHBoxLayout()
        btn_new = QPushButton("➕ New Transfer")
        btn_new.setStyleSheet("background-color: #0984e3; color: white; padding: 6px; font-weight: bold;")
        btn_new.clicked.connect(self.new_transfer)
        top.addStretch()
        top.addWidget(btn_new)
        layout.addLayout(top)
        
        self.transfers_table = QTableWidget()
        self.transfers_table.setColumnCount(4)
        self.transfers_table.setHorizontalHeaderLabels(["ID", "Date", "Status", "Notes"])
        self.transfers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.transfers_table)
        
    def load_transfers(self):
        transfers = client.get_stock_transfers()
        self.transfers_table.setRowCount(len(transfers))
        for row, t in enumerate(transfers):
            self.transfers_table.setItem(row, 0, QTableWidgetItem(t["internal_id"]))
            
            date_str = t["date"]
            try:
                date_str = datetime.fromisoformat(date_str).strftime("%Y-%m-%d %H:%M")
            except: pass
            
            self.transfers_table.setItem(row, 1, QTableWidgetItem(date_str))
            self.transfers_table.setItem(row, 2, QTableWidgetItem(t["status"]))
            self.transfers_table.setItem(row, 3, QTableWidgetItem(t["notes"] or "-"))
            
    def new_transfer(self):
        # We can implement a full dialog here if time permits, for now show message
        QMessageBox.information(self, "Stock Transfer", "To create a transfer, use the dedicated Transfer API endpoint.")

    # --- Adjustments Tab ---
    def setup_adjustments_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        top = QHBoxLayout()
        btn_new = QPushButton("⚖️ New Stock Adjustment")
        btn_new.setStyleSheet("background-color: #e84393; color: white; padding: 6px; font-weight: bold;")
        btn_new.clicked.connect(self.new_adjustment)
        top.addStretch()
        top.addWidget(btn_new)
        layout.addLayout(top)
        
        lbl = QLabel("Stock Adjustments are logged directly to the ledger. This view shows adjustment forms.")
        lbl.setStyleSheet("color: #a0a0a0; font-style: italic;")
        layout.addWidget(lbl)
        layout.addStretch()
        
    def new_adjustment(self):
        QMessageBox.information(self, "Stock Adjustment", "To create an adjustment, use the dedicated Adjustment API endpoint.")
