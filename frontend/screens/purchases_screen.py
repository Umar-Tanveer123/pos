from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox, QDialog,
    QFormLayout, QTextEdit, QComboBox, QTabWidget, QFrame, QGridLayout,
    QInputDialog
)
from PySide6.QtCore import Qt
from datetime import datetime
from frontend.api_client import client
from frontend.theme import fix_comboboxes

class PurchaseDetailDialog(QDialog):
    def __init__(self, purchase, parent=None):
        super().__init__(parent)
        self.purchase = purchase
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"Purchase Invoice Detail: {self.purchase['internal_id']}")
        self.setMinimumSize(600, 450)
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #ffffff;
            }
            QLabel {
                color: #a0a0a0;
                font-size: 13px;
            }
            QTableWidget {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #2a2a2a;
            }
            QPushButton {
                background-color: #2e2e2e;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Details Grid
        grid = QGridLayout()
        grid.setSpacing(10)
        
        grid.addWidget(QLabel("Purchase ID:"), 0, 0)
        lbl_id = QLabel(self.purchase["internal_id"])
        lbl_id.setStyleSheet("color: white; font-weight: bold;")
        grid.addWidget(lbl_id, 0, 1)
        
        grid.addWidget(QLabel("Supplier Invoice #:"), 0, 2)
        lbl_inv = QLabel(self.purchase["supplier_invoice_number"] or "N/A")
        lbl_inv.setStyleSheet("color: white;")
        grid.addWidget(lbl_inv, 0, 3)
        
        # Format Date
        dt_str = self.purchase["date"]
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            formatted_date = dt_str
            
        grid.addWidget(QLabel("Date:"), 1, 0)
        lbl_date = QLabel(formatted_date)
        lbl_date.setStyleSheet("color: white;")
        grid.addWidget(lbl_date, 1, 1)
        
        # Look up supplier name
        sup_name = "Loading..."
        sup_id = self.purchase["supplier_id"]
        sup = client.get_supplier(sup_id)
        if sup:
            sup_name = sup["name"]
            
        grid.addWidget(QLabel("Supplier:"), 1, 2)
        lbl_sup = QLabel(sup_name)
        lbl_sup.setStyleSheet("color: white; font-weight: bold;")
        grid.addWidget(lbl_sup, 1, 3)
        
        # Look up location name
        loc_name = "Loading..."
        loc_id = self.purchase["location_id"]
        locations = client.get_locations()
        for loc in locations:
            if loc["id"] == loc_id:
                loc_name = loc["name"]
                break
                
        grid.addWidget(QLabel("Target Stock Location:"), 2, 0)
        lbl_loc = QLabel(loc_name)
        lbl_loc.setStyleSheet("color: white;")
        grid.addWidget(lbl_loc, 2, 1)
        
        grid.addWidget(QLabel("Recorded Notes:"), 2, 2)
        lbl_notes = QLabel(self.purchase["notes"] or "N/A")
        lbl_notes.setStyleSheet("color: white;")
        grid.addWidget(lbl_notes, 2, 3)
        
        layout.addLayout(grid)
        
        # Items Table
        layout.addWidget(QLabel("Items List:"))
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Product Name", "SKU", "Quantity", "Purchase Price (Rs.)", "Discount (Rs.)", "Total Cost (Rs.)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Populate Items
        items = self.purchase.get("items", [])
        self.table.setRowCount(len(items))
        prod_list = client.get_products(is_active=None)
        for row, item in enumerate(items):
            p_name = f"Product ID: {item['product_id']}"
            p_sku = "N/A"
            for p in prod_list:
                if p["id"] == item["product_id"]:
                    p_name = p["name"]
                    p_sku = p["sku"] or "N/A"
                    break
                    
            self.table.setItem(row, 0, QTableWidgetItem(p_name))
            self.table.setItem(row, 1, QTableWidgetItem(p_sku))
            self.table.setItem(row, 2, QTableWidgetItem(f"{item['quantity']:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"Rs. {item['purchase_price']:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"Rs. {item['discount']:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"Rs. {item['total']:.2f}"))
            
        # Financial summary block
        fin_layout = QHBoxLayout()
        fin_layout.addStretch()
        
        summary_form = QFormLayout()
        lbl_tot = QLabel(f"Rs. {self.purchase['total_amount']:.2f}")
        lbl_tot.setStyleSheet("color: #6c5ce7; font-weight: bold; font-size: 14px;")
        summary_form.addRow("Grand Total:", lbl_tot)
        
        lbl_paid = QLabel(f"Rs. {self.purchase['paid_amount']:.2f}")
        lbl_paid.setStyleSheet("color: #2ed573; font-weight: bold;")
        summary_form.addRow("Cash Downpayment:", lbl_paid)
        
        lbl_pay = QLabel(f"Rs. {self.purchase['payable_amount']:.2f}")
        lbl_pay.setStyleSheet("color: #ff4757; font-weight: bold;")
        summary_form.addRow("Supplier Credit (Owed):", lbl_pay)
        
        fin_layout.addLayout(summary_form)
        layout.addLayout(fin_layout)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

class PurchasesScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.purchase_items = [] # Active draft purchase items
        self.all_products = []
        self.current_selected_supplier_id = None
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
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
        
        self.tab_history = QWidget()
        self.tab_record = QWidget()
        
        self.tabs.addTab(self.tab_history, "📋 Purchase Invoices History")
        self.tabs.addTab(self.tab_record, "📥 Record Purchase Receipt")
        
        self.setup_history_tab()
        self.setup_record_tab()
        
        main_layout.addWidget(self.tabs)
        
        # Load data initially
        self.load_purchases()
        self.load_form_references()
        fix_comboboxes(self)

    # --- 1. History Tab Setup ---
    def setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Filters controls
        filters_layout = QHBoxLayout()
        
        filters_layout.addWidget(QLabel("Filter by Supplier:"))
        self.filter_supplier = QComboBox()
        self.filter_supplier.currentIndexChanged.connect(self.load_purchases)
        filters_layout.addWidget(self.filter_supplier, stretch=2)
        
        filters_layout.addWidget(QLabel("Filter by Location:"))
        self.filter_location = QComboBox()
        self.filter_location.currentIndexChanged.connect(self.load_purchases)
        filters_layout.addWidget(self.filter_location, stretch=2)
        
        layout.addLayout(filters_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Invoice ID", "Date", "Supplier", "Invoice Ref #", "Total (Rs.)", "Paid (Rs.)", "Owed (Rs.)", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 150)
        self.table.verticalHeader().setDefaultSectionSize(45)
        layout.addWidget(self.table)
        
    def load_purchases(self):
        self.table.setRowCount(0)
        
        sup_id = self.filter_supplier.currentData()
        loc_id = self.filter_location.currentData()
        
        purchases = client.get_purchases(supplier_id=sup_id, location_id=loc_id)
        self.table.setRowCount(len(purchases))
        
        suppliers = client.get_suppliers()
        sup_map = {s["id"]: s["name"] for s in suppliers}
        
        for row, pur in enumerate(purchases):
            # Format Date
            dt_str = pur["date"]
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                formatted_date = dt_str
                
            self.table.setItem(row, 0, QTableWidgetItem(pur["internal_id"]))
            self.table.setItem(row, 1, QTableWidgetItem(formatted_date))
            
            s_name = sup_map.get(pur["supplier_id"], f"Supplier ID: {pur['supplier_id']}")
            self.table.setItem(row, 2, QTableWidgetItem(s_name))
            self.table.setItem(row, 3, QTableWidgetItem(pur["supplier_invoice_number"] or "N/A"))
            self.table.setItem(row, 4, QTableWidgetItem(f"Rs. {pur['total_amount']:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"Rs. {pur['paid_amount']:.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(f"Rs. {pur['payable_amount']:.2f}"))
            
            # Action Panel
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            
            view_btn = QPushButton("View")
            view_btn.setObjectName("ViewAction")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setProperty("purchase", pur)
            view_btn.clicked.connect(self.open_purchase_details)
            action_layout.addWidget(view_btn)
            
            action_widget.setLayout(action_layout)
            self.table.setCellWidget(row, 7, action_widget)

    def open_purchase_details(self):
        btn = self.sender()
        if not btn:
            return
        pur = btn.property("purchase")
        
        # Load fresh details (with items)
        fresh_pur = client.get_purchase(pur["id"])
        if fresh_pur:
            dialog = PurchaseDetailDialog(fresh_pur, self)
            dialog.exec()

    # --- 2. Record Purchase Tab Setup ---
    def setup_record_tab(self):
        layout = QVBoxLayout(self.tab_record)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Grid layout for Header Controls
        form_panel = QFrame()
        form_panel.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel {
                font-weight: bold;
                color: #a0a0a0;
            }
            QComboBox, QLineEdit {
                background-color: #121212;
                color: white;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        form_grid = QGridLayout(form_panel)
        form_grid.setSpacing(10)
        
        form_grid.addWidget(QLabel("Supplier * :"), 0, 0)
        self.form_supplier = QComboBox()
        self.form_supplier.currentIndexChanged.connect(self.update_product_dropdown)
        form_grid.addWidget(self.form_supplier, 0, 1)
        
        form_grid.addWidget(QLabel("Target Stock Location *:"), 0, 2)
        self.form_location = QComboBox()
        form_grid.addWidget(self.form_location, 0, 3)
        
        form_grid.addWidget(QLabel("Supplier Invoice #:"), 1, 0)
        self.form_invoice_num = QLineEdit()
        form_grid.addWidget(self.form_invoice_num, 1, 1)
        
        form_grid.addWidget(QLabel("Purchase Notes:"), 1, 2)
        self.form_notes = QLineEdit()
        form_grid.addWidget(self.form_notes, 1, 3)
        
        layout.addWidget(form_panel)
        
        # Items entry layout
        item_entry_row = QHBoxLayout()
        item_entry_row.addWidget(QLabel("Add Product to Purchase:"))
        self.form_product_combo = QComboBox()
        item_entry_row.addWidget(self.form_product_combo, stretch=3)
        
        add_item_btn = QPushButton("➕ Add Item Row")
        add_item_btn.setStyleSheet("background-color: #6c5ce7; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        add_item_btn.clicked.connect(self.add_product_to_purchase_list)
        item_entry_row.addWidget(add_item_btn)
        layout.addLayout(item_entry_row)
        
        # Items Draft Table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels([
            "Product Name", "SKU", "Quantity", "Purchase Price (Rs.)", "Discount (Rs.)", "Action"
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.verticalHeader().setDefaultSectionSize(38)
        self.items_table.itemChanged.connect(self.on_table_item_changed)
        layout.addWidget(self.items_table)
        
        # Bottom Billing Summaries Layout
        billing_row = QHBoxLayout()
        
        # Note on workflow
        workflow_lbl = QLabel("⚠️ Note: Record purchase ONLY when physical goods are received.\nThis transaction increments inventory and updates cost prices.")
        workflow_lbl.setStyleSheet("color: #ff9f43; font-style: italic; font-size: 11px;")
        billing_row.addWidget(workflow_lbl, stretch=2)
        
        billing_summary = QFrame()
        billing_summary.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel {
                font-weight: bold;
            }
        """)
        billing_form = QFormLayout(billing_summary)
        
        self.lbl_subtotal = QLabel("Rs. 0.00")
        billing_form.addRow("Subtotal:", self.lbl_subtotal)
        
        self.input_discount = QLineEdit("0.00")
        self.input_discount.textChanged.connect(self.recalculate_grand_totals)
        billing_form.addRow("Overall Discount (Rs.):", self.input_discount)
        
        self.lbl_grand_total = QLabel("Rs. 0.00")
        self.lbl_grand_total.setStyleSheet("color: #6c5ce7; font-size: 16px; font-weight: bold;")
        billing_form.addRow("Grand Total Payable:", self.lbl_grand_total)
        
        self.input_paid = QLineEdit("0.00")
        self.input_paid.textChanged.connect(self.recalculate_grand_totals)
        billing_form.addRow("Downpayment Paid (Rs.):", self.input_paid)
        
        self.lbl_owed = QLabel("Rs. 0.00")
        self.lbl_owed.setStyleSheet("color: #ff4757; font-weight: bold;")
        billing_form.addRow("Remaining Credit Owed:", self.lbl_owed)
        
        billing_row.addWidget(billing_summary, stretch=1)
        layout.addLayout(billing_row)
        
        # Submit Button
        self.submit_btn = QPushButton("📥 Submit Purchase & Update Inventory")
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ed573;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #26af5f;
            }
        """)
        self.submit_btn.clicked.connect(self.submit_purchase_receipt)
        layout.addWidget(self.submit_btn)

    def load_form_references(self):
        # 1. Load Suppliers
        suppliers = client.get_suppliers()
        
        self.filter_supplier.blockSignals(True)
        self.filter_supplier.clear()
        self.filter_supplier.addItem("All Suppliers", None)
        self.filter_supplier.blockSignals(False)
        
        self.form_supplier.blockSignals(True)
        self.form_supplier.clear()
        self.form_supplier.addItem("-- Select Supplier --", None)
        for s in suppliers:
            self.filter_supplier.addItem(s["name"], s["id"])
            self.form_supplier.addItem(s["name"], s["id"])
        self.form_supplier.blockSignals(False)
        
        # 2. Load Locations
        locations = client.get_locations()
        
        self.filter_location.blockSignals(True)
        self.filter_location.clear()
        self.filter_location.addItem("All Locations", None)
        self.filter_location.blockSignals(False)
        
        self.form_location.blockSignals(True)
        self.form_location.clear()
        self.form_location.addItem("-- Select Location --", None)
        for loc in locations:
            self.filter_location.addItem(loc["name"], loc["id"])
            self.form_location.addItem(loc["name"], loc["id"])
        self.form_location.blockSignals(False)
        
        # 3. Load Products for combo dropdown
        self.all_products = client.get_products()
        self.update_product_dropdown()

    def update_product_dropdown(self):
        supplier_id = self.form_supplier.currentData()
        
        # If there are items in the purchase list, warn and clear or reset supplier
        if self.purchase_items and supplier_id != self.current_selected_supplier_id:
            reply = QMessageBox.question(
                self,
                "Change Supplier?",
                "Changing the supplier will clear the current draft items. Proceed?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.purchase_items.clear()
                self.render_items_table()
                self.current_selected_supplier_id = supplier_id
            else:
                # Revert selection
                self.form_supplier.blockSignals(True)
                idx = self.form_supplier.findData(self.current_selected_supplier_id)
                self.form_supplier.setCurrentIndex(idx if idx != -1 else 0)
                self.form_supplier.blockSignals(False)
                return
        else:
            self.current_selected_supplier_id = supplier_id

        self.form_product_combo.blockSignals(True)
        self.form_product_combo.clear()
        
        if not supplier_id:
            self.form_product_combo.addItem("-- Please Select a Supplier First --", None)
            self.form_product_combo.blockSignals(False)
            return
            
        self.form_product_combo.addItem("-- Search & Select Product to Add --", None)
        filtered = [p for p in self.all_products if supplier_id in p.get("supplier_ids", [])]
        
        for p in filtered:
            sku_str = f" [{p['sku']}]" if p['sku'] else ""
            self.form_product_combo.addItem(f"{p['name']}{sku_str} - Cost: Rs. {p['purchase_price']:.2f}", p)
            
        if not filtered:
            self.form_product_combo.setItemText(0, "-- No Products Linked to this Supplier --")
            
        self.form_product_combo.blockSignals(False)

    def add_product_to_purchase_list(self):
        idx = self.form_product_combo.currentIndex()
        if idx <= 0:
            return
            
        product = self.form_product_combo.currentData()
        if not product:
            return
            
        # Check if already added to purchase draft list
        for p_item in self.purchase_items:
            if p_item["id"] == product["id"]:
                QMessageBox.information(self, "Product Added", "Product is already in the items list. Please edit the quantity directly in the table.")
                return
                
        # Add to local list
        p_item = {
            "id": product["id"],
            "name": product["name"],
            "sku": product["sku"] or "N/A",
            "quantity": 1.0,
            "purchase_price": product["purchase_price"] or 0.0,
            "discount": 0.0
        }
        self.purchase_items.append(p_item)
        self.render_items_table()
        
    def render_items_table(self):
        self.items_table.blockSignals(True)
        self.items_table.setRowCount(len(self.purchase_items))
        
        for row, item in enumerate(self.purchase_items):
            self.items_table.setItem(row, 0, QTableWidgetItem(item["name"]))
            
            sku_widget = QTableWidgetItem(item["sku"])
            sku_widget.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.items_table.setItem(row, 1, sku_widget)
            
            self.items_table.setItem(row, 2, QTableWidgetItem(str(item["quantity"])))
            self.items_table.setItem(row, 3, QTableWidgetItem(str(item["purchase_price"])))
            self.items_table.setItem(row, 4, QTableWidgetItem(str(item["discount"])))
            
            # Action Remove
            rem_btn = QPushButton("Remove")
            rem_btn.setObjectName("DeleteAction")
            rem_btn.setCursor(Qt.PointingHandCursor)
            rem_btn.setProperty("row_index", row)
            rem_btn.clicked.connect(self.remove_item_row)
            self.items_table.setCellWidget(row, 5, rem_btn)
            
        self.items_table.blockSignals(False)
        self.recalculate_grand_totals()

    def remove_item_row(self):
        btn = self.sender()
        if not btn:
            return
        row = btn.property("row_index")
        if 0 <= row < len(self.purchase_items):
            self.purchase_items.pop(row)
            self.render_items_table()

    def on_table_item_changed(self, item_widget):
        row = item_widget.row()
        col = item_widget.column()
        
        if 0 <= row < len(self.purchase_items):
            text = item_widget.text().strip()
            try:
                val = float(text)
            except ValueError:
                val = 0.0
                
            if col == 2: # Quantity
                self.purchase_items[row]["quantity"] = val if val > 0 else 1.0
            elif col == 3: # Price
                self.purchase_items[row]["purchase_price"] = val if val >= 0 else 0.0
            elif col == 4: # Discount
                self.purchase_items[row]["discount"] = val if val >= 0 else 0.0
                
            self.render_items_table()

    def recalculate_grand_totals(self):
        # Calculate Subtotal
        subtotal = 0.0
        for item in self.purchase_items:
            subtotal += (item["quantity"] * item["purchase_price"]) - item["discount"]
            
        if subtotal < 0:
            subtotal = 0.0
            
        self.lbl_subtotal.setText(f"Rs. {subtotal:.2f}")
        
        # Calculate Grand Total
        try:
            discount = float(self.input_discount.text().strip())
        except ValueError:
            discount = 0.0
            
        grand_total = subtotal - discount
        if grand_total < 0:
            grand_total = 0.0
            
        self.lbl_grand_total.setText(f"Rs. {grand_total:.2f}")
        
        # Calculate Remaining Credit Owed
        try:
            paid = float(self.input_paid.text().strip())
        except ValueError:
            paid = 0.0
            
        owed = grand_total - paid
        if owed < 0:
            owed = 0.0
            
        self.lbl_owed.setText(f"Rs. {owed:.2f}")

    def submit_purchase_receipt(self):
        # Validation
        supplier_id = self.form_supplier.currentData()
        location_id = self.form_location.currentData()
        
        if not supplier_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Supplier.")
            return
        if not location_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Target Stock Location.")
            return
        if not self.purchase_items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one product to the purchase draft list.")
            return
            
        try:
            discount = float(self.input_discount.text().strip())
        except ValueError:
            discount = 0.0
            
        try:
            paid = float(self.input_paid.text().strip())
        except ValueError:
            paid = 0.0
            
        # Build items payload
        items_payload = []
        for item in self.purchase_items:
            items_payload.append({
                "product_id": item["id"],
                "quantity": item["quantity"],
                "purchase_price": item["purchase_price"],
                "discount": item["discount"]
            })
            
        payload = {
            "supplier_id": supplier_id,
            "location_id": location_id,
            "supplier_invoice_number": self.form_invoice_num.text().strip() or None,
            "discount": discount,
            "paid_amount": paid,
            "notes": self.form_notes.text().strip() or None,
            "items": items_payload
        }
        
        success, res = client.create_purchase(payload)
        if success:
            QMessageBox.information(self, "Purchase Saved", f"Successfully recorded purchase receipt invoice {res['internal_id']}!\nCatalog cost prices have been synchronized, and target location stock was credited.")
            
            # Clear Draft Form
            self.purchase_items = []
            self.form_invoice_num.clear()
            self.form_notes.clear()
            self.input_discount.setText("0.00")
            self.input_paid.setText("0.00")
            self.form_supplier.setCurrentIndex(0)
            self.form_location.setCurrentIndex(0)
            self.form_product_combo.setCurrentIndex(0)
            
            self.render_items_table()
            
            # Reload History list
            self.load_purchases()
            
            # Switch back to history tab
            self.tabs.setCurrentIndex(0)
        else:
            QMessageBox.critical(self, "API Error", res)
