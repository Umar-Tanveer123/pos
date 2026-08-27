from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox, QDialog,
    QFormLayout, QTextEdit, QComboBox, QTabWidget, QFrame
)
from PySide6.QtCore import Qt
from datetime import datetime
from frontend.api_client import client
from frontend.theme import fix_comboboxes

class SupplierDialog(QDialog):
    def __init__(self, parent=None, supplier=None):
        super().__init__(parent)
        self.supplier = supplier
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Edit Supplier" if self.supplier else "Add Supplier")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #ffffff;
            }
            QLabel {
                color: #a0a0a0;
                font-weight: bold;
            }
            QLineEdit, QTextEdit {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton {
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.address_input = QLineEdit()
        self.contact_input = QLineEdit()
        self.tax_input = QLineEdit()
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        
        form.addRow("Name *:", self.name_input)
        form.addRow("Phone:", self.phone_input)
        form.addRow("Email:", self.email_input)
        form.addRow("Address:", self.address_input)
        form.addRow("Contact Person:", self.contact_input)
        form.addRow("Tax/Reg Details:", self.tax_input)
        form.addRow("Notes:", self.notes_input)
        
        layout.addLayout(form)
        
        # Populate if editing
        if self.supplier:
            self.name_input.setText(self.supplier.get("name", ""))
            self.phone_input.setText(self.supplier.get("phone", "") or "")
            self.email_input.setText(self.supplier.get("email", "") or "")
            self.address_input.setText(self.supplier.get("address", "") or "")
            self.contact_input.setText(self.supplier.get("contact_person", "") or "")
            self.tax_input.setText(self.supplier.get("tax_details", "") or "")
            self.notes_input.setPlainText(self.supplier.get("notes", "") or "")
            
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("background-color: #6c5ce7; color: white;")
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #2e2e2e; color: white;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "phone": self.phone_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "address": self.address_input.text().strip() or None,
            "contact_person": self.contact_input.text().strip() or None,
            "tax_details": self.tax_input.text().strip() or None,
            "notes": self.notes_input.toPlainText().strip() or None
        }

class PaymentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Record Supplier Payment")
        self.setMinimumWidth(350)
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #ffffff;
            }
            QLabel {
                color: #a0a0a0;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton {
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.amount_input = QLineEdit()
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "Bank Transfer", "Cheque", "Credit Note"])
        self.notes_input = QLineEdit()
        
        form.addRow("Amount (Rs.) *:", self.amount_input)
        form.addRow("Payment Method *:", self.method_combo)
        form.addRow("Notes / Ref:", self.notes_input)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Submit Payment")
        save_btn.setStyleSheet("background-color: #ff9f43; color: white;")
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #2e2e2e; color: white;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        fix_comboboxes(self)

    def get_data(self):
        try:
            amt = float(self.amount_input.text().strip())
        except ValueError:
            amt = 0.0
        return {
            "amount": amt,
            "payment_method": self.method_combo.currentText(),
            "notes": self.notes_input.text().strip() or None
        }

class SuppliersScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # Tabs container
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2a2a2a;
                background-color: #121212;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #1e1e1e;
                color: #a0a0a0;
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #121212;
                color: #6c5ce7;
                border-bottom: 2px solid #6c5ce7;
            }
        """)
        
        # Setup the 4 tabs
        self.tab_registry = QWidget()
        self.tab_ledger = QWidget()
        self.tab_products = QWidget()
        self.tab_profit = QWidget()
        
        self.tabs.addTab(self.tab_registry, "📋 Supplier Registry")
        self.tabs.addTab(self.tab_ledger, "💰 Ledger & Statements")
        self.tabs.addTab(self.tab_products, "📦 Supplier Products")
        self.tabs.addTab(self.tab_profit, "📈 Profit Analysis")
        
        # Initialize each tab layout
        self.setup_registry_tab()
        self.setup_ledger_tab()
        self.setup_products_tab()
        self.setup_profit_tab()
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tabs)
        
        # Refresh registry list initially
        self.load_suppliers()
        self.load_profit_report()

    # --- 1. Registry Tab Setup ---
    def setup_registry_tab(self):
        layout = QVBoxLayout(self.tab_registry)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header Controls
        ctrl_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search suppliers by name, ID, or contact person...")
        self.search_input.textChanged.connect(self.load_suppliers)
        ctrl_layout.addWidget(self.search_input)
        
        add_btn = QPushButton("➕ Add Supplier")
        add_btn.setObjectName("PrimaryButton")
        add_btn.setStyleSheet("""
            QPushButton#PrimaryButton {
                background-color: #6c5ce7;
                color: white;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #8172ea;
            }
        """)
        add_btn.clicked.connect(self.open_add_supplier)
        ctrl_layout.addWidget(add_btn)
        layout.addLayout(ctrl_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Supplier Name", "Contact Person", "Phone", "Email", "Balance Owed (Rs.)", "Actions"
        ])
        
        # Design Table Header
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(45) # Prevents layout squeezing
        layout.addWidget(self.table)
        
    def load_suppliers(self):
        self.table.setRowCount(0)
        search = self.search_input.text().strip() or None
        suppliers = client.get_suppliers(search)
        self.table.setRowCount(len(suppliers))
        
        # Also clear ledger combos
        self.ledger_supplier_combo.blockSignals(True)
        self.ledger_supplier_combo.clear()
        self.ledger_supplier_combo.addItem("-- Select Supplier --", None)
        
        self.prod_supplier_combo.blockSignals(True)
        self.prod_supplier_combo.clear()
        self.prod_supplier_combo.addItem("-- Select Supplier --", None)
        
        for row, sup in enumerate(suppliers):
            self.table.setItem(row, 0, QTableWidgetItem(sup["internal_id"]))
            self.table.setItem(row, 1, QTableWidgetItem(sup["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(sup["contact_person"] or "N/A"))
            self.table.setItem(row, 3, QTableWidgetItem(sup["phone"] or "N/A"))
            self.table.setItem(row, 4, QTableWidgetItem(sup["email"] or "N/A"))
            self.table.setItem(row, 5, QTableWidgetItem(f"Rs. {sup['balance']:.2f}"))
            
            # Action Panel
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("EditAction")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setProperty("supplier", sup)
            edit_btn.clicked.connect(self.open_edit_supplier)
            action_layout.addWidget(edit_btn)
            
            del_btn = QPushButton("Delete")
            del_btn.setObjectName("DeleteAction")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setProperty("supplier", sup)
            del_btn.clicked.connect(self.on_delete_supplier)
            action_layout.addWidget(del_btn)
            
            action_widget.setLayout(action_layout)
            self.table.setCellWidget(row, 6, action_widget)
            
            # Add to dropdown combos
            self.ledger_supplier_combo.addItem(f"{sup['name']} ({sup['internal_id']})", sup["id"])
            self.prod_supplier_combo.addItem(f"{sup['name']} ({sup['internal_id']})", sup["id"])
            
        self.ledger_supplier_combo.blockSignals(False)
        self.prod_supplier_combo.blockSignals(False)

    def open_add_supplier(self):
        dialog = SupplierDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Validation Error", "Supplier Name is required.")
                return
            success, res = client.create_supplier(data)
            if success:
                self.load_suppliers()
            else:
                QMessageBox.critical(self, "API Error", res)

    def open_edit_supplier(self):
        btn = self.sender()
        if not btn:
            return
        sup = btn.property("supplier")
        dialog = SupplierDialog(self, supplier=sup)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Validation Error", "Supplier Name is required.")
                return
            success, res = client.update_supplier(sup["id"], data)
            if success:
                self.load_suppliers()
            else:
                QMessageBox.critical(self, "API Error", res)

    def on_delete_supplier(self):
        btn = self.sender()
        if not btn:
            return
        sup = btn.property("supplier")
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete supplier '{sup['name']}'?\n"
            "This action is permanent and only allowed if there is no active transactional log history.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, err = client.delete_supplier(sup["id"])
            if success:
                self.load_suppliers()
            else:
                QMessageBox.critical(self, "Delete Error", err)


    # --- 2. Ledger & Statements Tab Setup ---
    def setup_ledger_tab(self):
        layout = QVBoxLayout(self.tab_ledger)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Filter controls
        filters_layout = QHBoxLayout()
        
        filters_layout.addWidget(QLabel("Select Supplier:"))
        self.ledger_supplier_combo = QComboBox()
        self.ledger_supplier_combo.currentIndexChanged.connect(self.load_ledger_statement)
        filters_layout.addWidget(self.ledger_supplier_combo, stretch=2)
        
        self.payment_btn = QPushButton("💸 Record Payment")
        self.payment_btn.setEnabled(False)
        self.payment_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9f43;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #fca858;
            }
            QPushButton:disabled {
                background-color: #4a4a4a;
                color: #8a8a8a;
            }
        """)
        self.payment_btn.clicked.connect(self.open_record_payment)
        filters_layout.addWidget(self.payment_btn)
        
        layout.addLayout(filters_layout)
        
        # Balance Summary frame
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel {
                font-weight: bold;
            }
        """)
        summary_layout = QHBoxLayout(self.summary_frame)
        self.lbl_outstanding = QLabel("Outstanding Payable: Rs. 0.00")
        self.lbl_outstanding.setStyleSheet("color: #ff7675; font-size: 15px;")
        summary_layout.addWidget(self.lbl_outstanding)
        summary_layout.addStretch()
        layout.addWidget(self.summary_frame)
        
        # Ledger table
        self.ledger_table = QTableWidget()
        self.ledger_table.setColumnCount(6)
        self.ledger_table.setHorizontalHeaderLabels([
            "Date", "Transaction Type", "Reference ID", "Amount (Rs.)", "Balance After (Rs.)", "Notes"
        ])
        self.ledger_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ledger_table.verticalHeader().setDefaultSectionSize(38)
        layout.addWidget(self.ledger_table)
        
    def load_ledger_statement(self):
        self.ledger_table.setRowCount(0)
        supplier_id = self.ledger_supplier_combo.currentData()
        
        if not supplier_id:
            self.payment_btn.setEnabled(False)
            self.lbl_outstanding.setText("Outstanding Payable: Rs. 0.00")
            return
            
        self.payment_btn.setEnabled(True)
        
        # Get supplier outstanding details
        sup = client.get_supplier(supplier_id)
        if sup:
            self.lbl_outstanding.setText(f"Outstanding Payable: Rs. {sup['balance']:.2f}")
            
        statement = client.get_supplier_statement(supplier_id)
        self.ledger_table.setRowCount(len(statement))
        
        for row, entry in enumerate(statement):
            # Format Date
            dt_str = entry["created_at"]
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                formatted_date = dt_str
                
            self.ledger_table.setItem(row, 0, QTableWidgetItem(formatted_date))
            
            type_item = QTableWidgetItem(entry["transaction_type"])
            if entry["transaction_type"] == "PURCHASE":
                type_item.setForeground(Qt.red)
            else:
                type_item.setForeground(Qt.green)
            self.ledger_table.setItem(row, 1, type_item)
            
            self.ledger_table.setItem(row, 2, QTableWidgetItem(entry["reference_id"] or "N/A"))
            self.ledger_table.setItem(row, 3, QTableWidgetItem(f"Rs. {entry['amount']:.2f}"))
            self.ledger_table.setItem(row, 4, QTableWidgetItem(f"Rs. {entry['balance_after']:.2f}"))
            self.ledger_table.setItem(row, 5, QTableWidgetItem(entry["notes"] or ""))

    def open_record_payment(self):
        supplier_id = self.ledger_supplier_combo.currentData()
        if not supplier_id:
            return
            
        dialog = PaymentDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if data["amount"] <= 0:
                QMessageBox.warning(self, "Validation Error", "Payment amount must be greater than zero.")
                return
                
            success, res = client.record_supplier_payment(supplier_id, data)
            if success:
                # Refresh statement and list
                self.load_ledger_statement()
                # Reload registry balances
                self.load_suppliers()
            else:
                QMessageBox.critical(self, "API Error", res)


    # --- 3. Products Tab Setup ---
    def setup_products_tab(self):
        layout = QVBoxLayout(self.tab_products)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Selector controls
        filters_layout = QHBoxLayout()
        filters_layout.addWidget(QLabel("Select Supplier:"))
        self.prod_supplier_combo = QComboBox()
        self.prod_supplier_combo.currentIndexChanged.connect(self.load_supplier_products)
        filters_layout.addWidget(self.prod_supplier_combo, stretch=2)
        filters_layout.addStretch()
        layout.addLayout(filters_layout)
        
        # Products table
        self.sup_prod_table = QTableWidget()
        self.sup_prod_table.setColumnCount(6)
        self.sup_prod_table.setHorizontalHeaderLabels([
            "ID", "Product Name", "SKU", "Barcode", "Current Cost (Rs.)", "Retail Price (Rs.)"
        ])
        self.sup_prod_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sup_prod_table.verticalHeader().setDefaultSectionSize(38)
        layout.addWidget(self.sup_prod_table)
        
    def load_supplier_products(self):
        self.sup_prod_table.setRowCount(0)
        supplier_id = self.prod_supplier_combo.currentData()
        if not supplier_id:
            return
            
        # Get products associated with this supplier directly from backend
        sup_products = client.get_products(supplier_id=supplier_id)
                    
        self.sup_prod_table.setRowCount(len(sup_products))
        for row, p in enumerate(sup_products):
            self.sup_prod_table.setItem(row, 0, QTableWidgetItem(p["internal_id"]))
            self.sup_prod_table.setItem(row, 1, QTableWidgetItem(p["name"]))
            self.sup_prod_table.setItem(row, 2, QTableWidgetItem(p["sku"] or "N/A"))
            self.sup_prod_table.setItem(row, 3, QTableWidgetItem(p["barcode"] or "N/A"))
            self.sup_prod_table.setItem(row, 4, QTableWidgetItem(f"Rs. {p['purchase_price']:.2f}"))
            self.sup_prod_table.setItem(row, 5, QTableWidgetItem(f"Rs. {p['retail_price']:.2f}"))

    # --- 4. Profit Analysis Tab Setup ---
    def setup_profit_tab(self):
        layout = QVBoxLayout(self.tab_profit)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        guide = QLabel("Analyze profit margins and sales statistics either globally by Supplier or detailed by Product.")
        guide.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        layout.addWidget(guide)
        
        layout.addWidget(QLabel("<b>Supplier-wise Profit Summary:</b>"))
        self.supplier_profit_table = QTableWidget()
        self.supplier_profit_table.setColumnCount(6)
        self.supplier_profit_table.setHorizontalHeaderLabels([
            "Supplier ID", "Supplier Name", "Total Sales Revenue (Rs.)", "Total Cost of Goods (Rs.)", "Net Profit (Rs.)", "Margin (%)"
        ])
        self.supplier_profit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.supplier_profit_table.verticalHeader().setDefaultSectionSize(38)
        self.supplier_profit_table.itemSelectionChanged.connect(self.on_profit_supplier_selection_changed)
        layout.addWidget(self.supplier_profit_table)
        
        self.lbl_product_profit_header = QLabel("<b>Product-wise Profit Breakdown (Select a supplier above to load):</b>")
        layout.addWidget(self.lbl_product_profit_header)
        
        self.product_profit_table = QTableWidget()
        self.product_profit_table.setColumnCount(6)
        self.product_profit_table.setHorizontalHeaderLabels([
            "Product SKU", "Product Name", "Units Sold", "Sales Revenue (Rs.)", "Cost of Goods (Rs.)", "Profit (Rs.)"
        ])
        self.product_profit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.product_profit_table.verticalHeader().setDefaultSectionSize(38)
        layout.addWidget(self.product_profit_table)

    def on_tab_changed(self, index):
        if index == 3:
            self.load_profit_report()

    def load_profit_report(self):
        self.supplier_profit_table.blockSignals(True)
        self.supplier_profit_table.setRowCount(0)
        self.product_profit_table.setRowCount(0)
        self.lbl_product_profit_header.setText("<b>Product-wise Profit Breakdown (Select a supplier above to load):</b>")
        
        res = client.get_supplier_profit_report()
        sups = res.get("suppliers", [])
        
        self.supplier_profit_table.setRowCount(len(sups))
        for row, s in enumerate(sups):
            id_item = QTableWidgetItem(s["supplier_code"])
            id_item.setData(Qt.UserRole, s["supplier_id"])
            self.supplier_profit_table.setItem(row, 0, id_item)
            
            name_item = QTableWidgetItem(s["supplier_name"])
            self.supplier_profit_table.setItem(row, 1, name_item)
            
            rev_item = QTableWidgetItem(f"Rs. {s['total_sales_revenue']:.2f}")
            self.supplier_profit_table.setItem(row, 2, rev_item)
            
            cost_item = QTableWidgetItem(f"Rs. {s['total_purchase_cost']:.2f}")
            self.supplier_profit_table.setItem(row, 3, cost_item)
            
            profit_val = s['net_profit']
            profit_item = QTableWidgetItem(f"Rs. {profit_val:.2f}")
            if profit_val > 0:
                profit_item.setForeground(Qt.green)
            elif profit_val < 0:
                profit_item.setForeground(Qt.red)
            self.supplier_profit_table.setItem(row, 4, profit_item)
            
            margin_item = QTableWidgetItem(f"{s['profit_margin_pct']:.1f}%")
            self.supplier_profit_table.setItem(row, 5, margin_item)
            
        self.supplier_profit_table.blockSignals(False)

    def on_profit_supplier_selection_changed(self):
        selected_ranges = self.supplier_profit_table.selectedRanges()
        if not selected_ranges:
            return
        row = selected_ranges[0].topRow()
        id_item = self.supplier_profit_table.item(row, 0)
        if not id_item:
            return
            
        supplier_id = id_item.data(Qt.UserRole)
        supplier_name = self.supplier_profit_table.item(row, 1).text()
        
        self.lbl_product_profit_header.setText(f"<b>Product-wise Profit Breakdown for '{supplier_name}':</b>")
        
        res = client.get_supplier_profit_report(supplier_id)
        prods = res.get("products", [])
        
        self.product_profit_table.setRowCount(len(prods))
        for row, p in enumerate(prods):
            sku_item = QTableWidgetItem(p["sku"] or "N/A")
            self.product_profit_table.setItem(row, 0, sku_item)
            
            name_item = QTableWidgetItem(p["product_name"])
            self.product_profit_table.setItem(row, 1, name_item)
            
            qty_item = QTableWidgetItem(f"{p['total_qty_sold']:.2f}")
            self.product_profit_table.setItem(row, 2, qty_item)
            
            rev_item = QTableWidgetItem(f"Rs. {p['total_sales_revenue']:.2f}")
            self.product_profit_table.setItem(row, 3, rev_item)
            
            cost_item = QTableWidgetItem(f"Rs. {p['total_purchase_cost']:.2f}")
            self.product_profit_table.setItem(row, 4, cost_item)
            
            profit_val = p['net_profit']
            profit_item = QTableWidgetItem(f"Rs. {profit_val:.2f}")
            if profit_val > 0:
                profit_item.setForeground(Qt.green)
            elif profit_val < 0:
                profit_item.setForeground(Qt.red)
            self.product_profit_table.setItem(row, 5, profit_item)
