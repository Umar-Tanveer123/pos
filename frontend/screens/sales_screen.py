from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox, QDialog,
    QFormLayout, QTextEdit, QComboBox, QTabWidget, QFrame, QGridLayout,
    QDoubleSpinBox, QCompleter, QTextBrowser, QCheckBox
)
from PySide6.QtCore import Qt
from datetime import datetime
from frontend.api_client import client
from frontend.theme import fix_comboboxes

class CustomerReturnDialog(QDialog):
    def __init__(self, sale, parent=None):
        super().__init__(parent)
        self.sale = sale
        self.returnable_items = []
        self.spinboxes = {}
        self.checkboxes = {}
        self.init_ui()
        self.load_items()
        
    def init_ui(self):
        self.setWindowTitle(f"Return Items: {self.sale['internal_id']}")
        self.setMinimumSize(800, 500)
        self.setStyleSheet("""
            QDialog { background-color: #121212; color: #ffffff; }
            QLabel { color: #ffffff; }
            QTableWidget { background-color: #1e1e1e; color: white; border: 1px solid #2a2a2a; }
            QDoubleSpinBox { background-color: #2a2a2a; color: white; border: 1px solid #444; padding: 4px; }
            QCheckBox { color: white; }
        """)
        
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Product", "Unit", "Purchased", "Already Returned", "Return Qty", "Refund (Rs.)", "Damaged?"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Summary & Notes
        bottom_layout = QHBoxLayout()
        notes_layout = QVBoxLayout()
        notes_layout.addWidget(QLabel("Return Notes (Optional):"))
        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(60)
        notes_layout.addWidget(self.txt_notes)
        bottom_layout.addLayout(notes_layout)
        
        self.lbl_total = QLabel("Total Refund: Rs. 0.00")
        self.lbl_total.setStyleSheet("font-size: 16px; font-weight: bold; color: #f39c12;")
        bottom_layout.addWidget(self.lbl_total, alignment=Qt.AlignRight | Qt.AlignVCenter)
        
        layout.addLayout(bottom_layout)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_process = QPushButton("Process Return")
        btn_process.setStyleSheet("background-color: #d63031; color: white; font-weight: bold; padding: 8px 16px;")
        btn_process.clicked.connect(self.process_return)
        btn_layout.addWidget(btn_process)
        
        layout.addLayout(btn_layout)
        
    def load_items(self):
        self.returnable_items = client.get_returnable_items(self.sale["id"])
        self.table.setRowCount(len(self.returnable_items))
        
        for row, item in enumerate(self.returnable_items):
            self.table.setItem(row, 0, QTableWidgetItem(item["product_name"]))
            self.table.setItem(row, 1, QTableWidgetItem(item["unit_name"] or "-"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{item['purchased_qty']:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{item['returned_qty']:.2f}"))
            
            spin = QDoubleSpinBox()
            spin.setRange(0, item["returnable_qty"])
            spin.setValue(0)
            spin.valueChanged.connect(self.update_total)
            self.spinboxes[row] = spin
            self.table.setCellWidget(row, 4, spin)
            
            # Show how much refund they get per item
            refund_price = item["unit_price"] - item["discount_per_unit"]
            self.table.setItem(row, 5, QTableWidgetItem(f"Rs. {refund_price:.2f} / unit"))
            
            chk = QCheckBox("Damaged")
            self.checkboxes[row] = chk
            self.table.setCellWidget(row, 6, chk)
            
    def update_total(self):
        total = 0.0
        for row, item in enumerate(self.returnable_items):
            qty = self.spinboxes[row].value()
            refund_price = item["unit_price"] - item["discount_per_unit"]
            total += qty * refund_price
        self.lbl_total.setText(f"Total Refund: Rs. {total:,.2f}")
        
    def process_return(self):
        items_to_return = []
        for row, item in enumerate(self.returnable_items):
            qty = self.spinboxes[row].value()
            if qty > 0:
                items_to_return.append({
                    "sale_item_id": item["sale_item_id"],
                    "quantity": qty,
                    "is_damaged": self.checkboxes[row].isChecked()
                })
                
        if not items_to_return:
            QMessageBox.warning(self, "No Items", "Please specify a quantity > 0 for at least one item to return.")
            return
            
        data = {
            "sale_id": self.sale["id"],
            "items": items_to_return,
            "notes": self.txt_notes.toPlainText()
        }
        
        success, res = client.process_customer_return(data)
        if success:
            QMessageBox.information(self, "Success", f"Return processed successfully. (ID: {res['internal_id']})")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", f"Failed to process return: {res}")

class PrintPreviewDialog(QDialog):
    def __init__(self, sale, templates, parent=None):
        super().__init__(parent)
        self.sale = sale
        self.templates = templates
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"Print Invoice: {self.sale['internal_id']}")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog { background-color: #121212; color: #ffffff; }
            QLabel { color: #a0a0a0; }
            QTextBrowser { background-color: white; color: black; border: 1px solid #444; }
        """)
        
        layout = QVBoxLayout(self)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel("Select Template:"))
        self.tmpl_combo = QComboBox()
        for t in self.templates:
            self.tmpl_combo.addItem(t["name"], t)
        
        # Set default
        for i, t in enumerate(self.templates):
            if t["is_default"]:
                self.tmpl_combo.setCurrentIndex(i)
                break
                
        self.tmpl_combo.currentIndexChanged.connect(self.render_preview)
        ctrl_layout.addWidget(self.tmpl_combo)
        
        print_btn = QPushButton("Print")
        print_btn.setStyleSheet("background-color: #0984e3; color: white; padding: 6px 12px;")
        print_btn.clicked.connect(self.do_print)
        ctrl_layout.addWidget(print_btn)
        
        layout.addLayout(ctrl_layout)
        
        # Preview area
        self.preview = QTextBrowser()
        layout.addWidget(self.preview)
        
        self.render_preview()
        
    def render_preview(self):
        tmpl = self.tmpl_combo.currentData()
        if not tmpl:
            return

        # Load business settings for header
        try:
            settings = client.get_settings()
        except Exception:
            settings = {}

        biz_name = tmpl.get("business_name") or settings.get("business_name") or "SALE RECEIPT"
        biz_address = tmpl.get("business_address") or settings.get("business_address") or ""
        biz_phone = tmpl.get("business_phone") or settings.get("business_phone") or ""
        header_text = tmpl.get("header_text") or "SALE RECEIPT"
        footer_text = tmpl.get("footer_text") or "<<Thank you for your Shopping>>"

        # Load sale details
        sale_date = self.sale.get("date", "")
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(sale_date.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%d-%b-%Y %I:%M:%S %p")
        except Exception:
            formatted_date = sale_date

        # Load customer
        cust_name = "Walk-in Customer"
        try:
            cust = client.get_customer(self.sale["customer_id"])
            if cust:
                cust_name = cust["name"]
        except Exception:
            pass

        html = """
        <html>
        <head>
        <style>
            body { font-family: 'Courier New', monospace; font-size: 12px; width: 350px; margin: 0 auto; padding: 10px; color: #000; }
            .center { text-align: center; }
            .bold { font-weight: bold; }
            .line { border-top: 1px dashed #000; margin: 6px 0; }
            table { width: 100%; border-collapse: collapse; }
            th { font-weight: bold; text-align: left; border-bottom: 1px solid #000; padding: 2px 4px; font-size: 11px; }
            td { padding: 2px 4px; font-size: 11px; }
            .num { text-align: right; }
            .total-row { font-weight: bold; border-top: 1px solid #000; }
            .grand { font-size: 15px; font-weight: bold; text-align: right; padding: 6px 0; }
            .footer { text-align: center; margin-top: 12px; font-style: italic; font-size: 11px; }
        </style>
        </head>
        <body>
        """

        # Header
        html += f"<div class='center'><div class='bold' style='font-size:15px;'>{header_text}</div>"
        html += f"<div class='bold' style='font-size:13px;'>{biz_name}</div>"
        if biz_address:
            html += f"<div>Address: {biz_address}</div>"
        if biz_phone:
            html += f"<div>Ph: {biz_phone}</div>"
        html += "</div>"

        html += "<div class='line'></div>"
        html += f"<div>Mop: Cash Sales &nbsp;&nbsp;&nbsp; Receipt: {self.sale['internal_id']}</div>"
        html += f"<div>Date: {formatted_date}</div>"
        if tmpl.get("show_customer_info") or cust_name != "Walk-in Customer":
            html += f"<div>Customer: {cust_name}</div>"
        html += "<div class='line'></div>"

        # Items Table
        html += "<table>"
        html += "<tr><th>Sr.</th><th>Product Name</th><th class='num'>Qty</th><th class='num'>Price</th><th class='num'>Disc</th><th class='num'>Amt</th></tr>"

        # Load product names
        try:
            prod_list = client.get_products(is_active=None)
            prod_map = {p["id"]: p for p in prod_list}
        except Exception:
            prod_map = {}

        grand_total = 0.0
        total_qty = 0.0
        for sr, item in enumerate(self.sale.get("items", []), 1):
            prod = prod_map.get(item["product_id"], {})
            p_name = prod.get("name", f"Product #{item['product_id']}")
            if item.get("variant_id"):
                for var in prod.get("variants", []):
                    if var["id"] == item["variant_id"]:
                        p_name += f" {var['name']}"
                        break

            qty = item["quantity"]
            price = item["unit_price"]
            disc = item.get("discount", 0.0)
            amt = item["total"]
            grand_total += amt
            total_qty += qty

            html += f"<tr>"
            html += f"<td>{sr}-</td>"
            html += f"<td>{p_name}</td>"
            html += f"<td class='num'>{qty:.0f}</td>"
            html += f"<td class='num'>{price:.2f}</td>"
            html += f"<td class='num'>{disc:.2f}</td>"
            html += f"<td class='num'>{amt:.2f}</td>"
            html += f"</tr>"

        html += "</table>"
        html += "<div class='line'></div>"

        # Totals row
        html += f"<table>"
        html += f"<tr class='total-row'><td>Total Amount Sold Items</td><td class='num' colspan='5'>{grand_total:.2f}</td></tr>"
        html += f"<tr><td>Total Qty: {total_qty:.0f}</td><td class='num' colspan='5'>{grand_total:.2f} &nbsp; 0 &nbsp; {grand_total:.2f}</td></tr>"
        html += "</table>"

        overall_discount = self.sale.get("discount", 0.0)
        net_total = self.sale.get("total_amount", grand_total)
        html += f"<div class='grand'>Net Total: &nbsp; {net_total:,.2f}</div>"

        if tmpl.get("show_payment_info"):
            html += "<div class='line'></div>"
            payments = self.sale.get("payments", [])
            if payments:
                for p in payments:
                    html += f"<div>{p['payment_method']}: Rs. {p['amount']:,.2f}</div>"
            paid = self.sale.get("paid_amount", 0)
            bal = self.sale.get("balance_owed", 0)
            html += f"<div>Paid: Rs. {paid:,.2f} &nbsp;&nbsp; Balance: Rs. {bal:,.2f}</div>"

        html += f"<div class='line'></div>"
        html += f"<div class='footer'>{footer_text}</div>"
        html += "</body></html>"
        self.preview.setHtml(html)
        
    def do_print(self):
        # In a real app, use QPrinter. For now, simulate success.
        QMessageBox.information(self, "Print Dispatched", "Document sent to the printer successfully.")
        self.accept()

class SaleDetailDialog(QDialog):
    def __init__(self, sale, parent=None):
        super().__init__(parent)
        self.sale = sale
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"Sale Invoice Detail: {self.sale['internal_id']}")
        self.setMinimumSize(650, 480)
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
        
        grid.addWidget(QLabel("Invoice ID:"), 0, 0)
        lbl_id = QLabel(self.sale["internal_id"])
        lbl_id.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        grid.addWidget(lbl_id, 0, 1)
        
        grid.addWidget(QLabel("Date / Time:"), 0, 2)
        dt_str = self.sale["date"]
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            formatted_date = dt_str
        lbl_date = QLabel(formatted_date)
        lbl_date.setStyleSheet("color: white;")
        grid.addWidget(lbl_date, 0, 3)
        
        # Customer Name
        cust_name = "Loading..."
        customer = client.get_customer(self.sale["customer_id"])
        if customer:
            cust_name = f"{customer['name']} ({customer['internal_id']})"
            
        grid.addWidget(QLabel("Customer:"), 1, 0)
        lbl_cust = QLabel(cust_name)
        lbl_cust.setStyleSheet("color: white; font-weight: bold;")
        grid.addWidget(lbl_cust, 1, 1)
        
        # Look up location
        loc_name = "Loading..."
        loc_id = self.sale["location_id"]
        locations = client.get_locations()
        for loc in locations:
            if loc["id"] == loc_id:
                loc_name = loc["name"]
                break
                
        grid.addWidget(QLabel("Sale Location:"), 1, 2)
        lbl_loc = QLabel(loc_name)
        lbl_loc.setStyleSheet("color: white;")
        grid.addWidget(lbl_loc, 1, 3)
        
        grid.addWidget(QLabel("Status:"), 2, 0)
        lbl_status = QLabel(self.sale.get("status", "COMPLETED"))
        status_color = "#2ed573" if lbl_status.text() == "COMPLETED" else "#ff4757"
        lbl_status.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        grid.addWidget(lbl_status, 2, 1)

        grid.addWidget(QLabel("Notes:"), 2, 2)
        lbl_notes = QLabel(self.sale["notes"] or "N/A")
        lbl_notes.setStyleSheet("color: white;")
        grid.addWidget(lbl_notes, 2, 3)
        
        layout.addLayout(grid)
        
        # Items Table
        layout.addWidget(QLabel("Items List:"))
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Product Name", "Quantity", "Unit Price (Rs.)", "Discount (Rs.)", "Total (Rs.)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Populate Items
        items = self.sale.get("items", [])
        self.table.setRowCount(len(items))
        prod_list = client.get_products(is_active=None)
        
        for row, item in enumerate(items):
            p_name = f"Product ID: {item['product_id']}"
            for p in prod_list:
                if p["id"] == item["product_id"]:
                    p_name = p["name"]
                    if item.get("variant_id"):
                        for var in p.get("variants", []):
                            if var["id"] == item["variant_id"]:
                                p_name += f" - {var['name']}"
                                break
                    break
                    
            self.table.setItem(row, 0, QTableWidgetItem(p_name))
            self.table.setItem(row, 1, QTableWidgetItem(f"{item['quantity']:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"Rs. {item['unit_price']:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"Rs. {item['discount']:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"Rs. {item['total']:.2f}"))
            
        # Financial summary block
        fin_layout = QHBoxLayout()
        
        # Split Payments Details
        payments_layout = QVBoxLayout()
        payments = self.sale.get("payments", [])
        if payments:
            payments_layout.addWidget(QLabel("<b>Payments Made:</b>"))
            for p in payments:
                lbl_p = QLabel(f"• {p['payment_method']}: Rs. {p['amount']:,.2f}")
                lbl_p.setStyleSheet("color: #a0a0a0;")
                payments_layout.addWidget(lbl_p)
        else:
            # Fallback for old sales
            if self.sale['paid_amount'] > 0:
                payments_layout.addWidget(QLabel("<b>Payments Made:</b>"))
                lbl_p = QLabel(f"• Cash (Legacy): Rs. {self.sale['paid_amount']:,.2f}")
                lbl_p.setStyleSheet("color: #a0a0a0;")
                payments_layout.addWidget(lbl_p)
        payments_layout.addStretch()
        fin_layout.addLayout(payments_layout)

        fin_layout.addStretch()
        
        summary_form = QFormLayout()
        lbl_tot = QLabel(f"Rs. {self.sale['total_amount']:.2f}")
        lbl_tot.setStyleSheet("color: #6c5ce7; font-weight: bold; font-size: 14px;")
        summary_form.addRow("Grand Total:", lbl_tot)
        
        lbl_paid = QLabel(f"Rs. {self.sale['paid_amount']:.2f}")
        lbl_paid.setStyleSheet("color: #2ed573; font-weight: bold;")
        summary_form.addRow("Total Paid:", lbl_paid)
        
        lbl_pay = QLabel(f"Rs. {self.sale['balance_owed']:.2f}")
        lbl_pay.setStyleSheet("color: #ff4757; font-weight: bold;")
        summary_form.addRow("Credit Balance (Owed):", lbl_pay)
        
        fin_layout.addLayout(summary_form)
        layout.addLayout(fin_layout)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

class SalesScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.cart_items = [] # list of dicts: {product, variant, qty, price, discount}
        self.all_products = []
        self.all_customers = []
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
        self.tab_checkout = QWidget()
        
        self.tabs.addTab(self.tab_checkout, "🛒 POS Checkout Counter")
        self.tabs.addTab(self.tab_history, "📋 Sales Invoices History")
        
        self.setup_checkout_tab()
        self.setup_history_tab()
        
        main_layout.addWidget(self.tabs)
        
    def setup_checkout_tab(self):
        layout = QVBoxLayout(self.tab_checkout)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # --- Top controls row ---
        top_row = QHBoxLayout()
        top_row.setSpacing(15)
        
        # Barcode lookup
        barcode_layout = QVBoxLayout()
        barcode_layout.setSpacing(4)
        barcode_layout.addWidget(QLabel("Barcode Scan (SKU/Barcode):"))
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan item barcode & press Enter...")
        self.barcode_input.setStyleSheet("QLineEdit { font-size: 15px; padding: 8px; }")
        self.barcode_input.returnPressed.connect(self.on_barcode_scanned)
        barcode_layout.addWidget(self.barcode_input)
        top_row.addLayout(barcode_layout, stretch=2)
        
        # Product Search dropdown
        search_layout = QVBoxLayout()
        search_layout.setSpacing(4)
        search_layout.addWidget(QLabel("Search & Add Product (Name/SKU):"))
        self.product_search_combo = QComboBox()
        self.product_search_combo.setEditable(True)
        self.product_search_combo.setInsertPolicy(QComboBox.NoInsert)
        self.product_search_combo.setStyleSheet("QComboBox { font-size: 15px; padding: 6px; }")
        self.product_search_combo.currentIndexChanged.connect(self.on_search_product_selected)
        
        completer = self.product_search_combo.completer()
        if completer:
            completer.setFilterMode(Qt.MatchContains)
            completer.setCompletionMode(QCompleter.PopupCompletion)
            
        search_layout.addWidget(self.product_search_combo)
        top_row.addLayout(search_layout, stretch=2)
        
        # Location Selector
        loc_layout = QVBoxLayout()
        loc_layout.setSpacing(4)
        loc_layout.addWidget(QLabel("Checkout Location:"))
        self.location_combo = QComboBox()
        loc_layout.addWidget(self.location_combo)
        top_row.addLayout(loc_layout, stretch=1)
        
        # Customer Selector
        cust_layout = QVBoxLayout()
        cust_layout.setSpacing(4)
        cust_layout.addWidget(QLabel("Select Customer:"))
        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self.on_customer_changed)
        cust_layout.addWidget(self.customer_combo)
        top_row.addLayout(cust_layout, stretch=2)

        # Quick customer name & type entry
        quick_cust_layout = QVBoxLayout()
        quick_cust_layout.setSpacing(4)
        quick_cust_layout.addWidget(QLabel("Quick Customer Name & Type (optional):"))
        quick_row = QHBoxLayout()
        quick_row.setSpacing(4)
        self.quick_cust_input = QLineEdit()
        self.quick_cust_input.setPlaceholderText("Quick Customer Name...")
        self.quick_cust_input.setStyleSheet("QLineEdit { font-size: 12px; padding: 5px; }")
        self.quick_cust_input.returnPressed.connect(self.on_quick_customer_save)
        quick_row.addWidget(self.quick_cust_input)
        
        self.quick_cust_type_combo = QComboBox()
        self.quick_cust_type_combo.setFixedWidth(100)
        self.quick_cust_type_combo.setStyleSheet("QComboBox { font-size: 12px; padding: 4px; }")
        self.quick_cust_type_combo.currentIndexChanged.connect(self.on_quick_cust_type_changed)
        quick_row.addWidget(self.quick_cust_type_combo)

        quick_cust_btn = QPushButton("+")
        quick_cust_btn.setFixedWidth(32)
        quick_cust_btn.setStyleSheet("QPushButton { background-color: #00b894; color: white; font-weight: bold; font-size: 14px; padding: 4px; border-radius: 4px; min-width: 0; }")
        quick_cust_btn.clicked.connect(self.on_quick_customer_save)
        quick_row.addWidget(quick_cust_btn)
        quick_cust_layout.addLayout(quick_row)
        top_row.addLayout(quick_cust_layout, stretch=2)

        layout.addLayout(top_row)
        
        # --- Main Split Layout ---
        main_split = QHBoxLayout()
        main_split.setSpacing(20)
        
        # Left Cart Table
        cart_box = QVBoxLayout()
        cart_box.addWidget(QLabel("Cart Items:"))
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(7)
        self.cart_table.setHorizontalHeaderLabels([
            "Product / Variant", "Unit", "Quantity", "Price (Rs.)", "Discount (Rs.)", "Total (Rs.)", "Action"
        ])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.cart_table.setStyleSheet("QTableWidget { background-color: #1a1a1a; }")
        cart_box.addWidget(self.cart_table)
        main_split.addLayout(cart_box, stretch=3)
        
        # Right checkout panel
        checkout_panel = QFrame()
        checkout_panel.setStyleSheet("""
            QFrame {
                background-color: #181818;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        checkout_layout = QVBoxLayout(checkout_panel)
        checkout_layout.setSpacing(12)
        
        # Customer Info card
        checkout_layout.addWidget(QLabel("<b>CUSTOMER PROFILE INFO</b>"))
        self.lbl_cust_type = QLabel("Type: —")
        self.lbl_cust_limit = QLabel("Credit Limit: Rs. 0.00")
        self.lbl_cust_bal = QLabel("Owed Balance: Rs. 0.00")
        self.lbl_cust_type.setStyleSheet("color: #a0a0a0;")
        self.lbl_cust_limit.setStyleSheet("color: #a0a0a0;")
        self.lbl_cust_bal.setStyleSheet("color: #ff7675;")
        checkout_layout.addWidget(self.lbl_cust_type)
        checkout_layout.addWidget(self.lbl_cust_limit)
        checkout_layout.addWidget(self.lbl_cust_bal)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet("background-color: #2a2a2a; max-height: 1px; margin: 5px 0;")
        checkout_layout.addWidget(sep)
        
        # Totals
        checkout_layout.addWidget(QLabel("<b>FINANCIAL SUMMARY</b>"))
        
        totals_form = QFormLayout()
        totals_form.setSpacing(8)
        
        self.lbl_subtotal = QLabel("Rs. 0.00")
        self.lbl_subtotal.setStyleSheet("color: white; font-weight: bold;")
        totals_form.addRow("Subtotal:", self.lbl_subtotal)
        
        self.cart_discount_spin = QDoubleSpinBox()
        self.cart_discount_spin.setRange(0, 1000000)
        self.cart_discount_spin.setSingleStep(50)
        self.cart_discount_spin.setStyleSheet("QDoubleSpinBox { background: #121212; color: white; border: 1px solid #333; }")
        self.cart_discount_spin.valueChanged.connect(self.recalc_totals)
        totals_form.addRow("Discount (Rs.):", self.cart_discount_spin)
        
        self.lbl_grand_total = QLabel("Rs. 0.00")
        self.lbl_grand_total.setStyleSheet("color: #6c5ce7; font-weight: bold; font-size: 16px;")
        totals_form.addRow("Grand Total:", self.lbl_grand_total)
        
        checkout_layout.addLayout(totals_form)
        
        # Split Payment Section
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #2a2a2a; max-height: 1px; margin: 5px 0;")
        checkout_layout.addWidget(sep2)
        checkout_layout.addWidget(QLabel("<b>SPLIT PAYMENT</b>"))
        
        self.payment_methods = ["Cash", "Bank Transfer", "Card", "JazzCash", "Easypaisa"]
        self.payment_spins = {}
        pay_form = QFormLayout()
        pay_form.setSpacing(6)
        for method in self.payment_methods:
            spin = QDoubleSpinBox()
            spin.setRange(0, 10000000)
            spin.setSingleStep(100)
            spin.setDecimals(2)
            spin.setStyleSheet("QDoubleSpinBox { background: #121212; color: white; border: 1px solid #333; }")
            spin.valueChanged.connect(self.recalc_totals)
            pay_form.addRow(f"{method}:", spin)
            self.payment_spins[method] = spin
        checkout_layout.addLayout(pay_form)
        
        self.lbl_total_paid = QLabel("Total Paid: Rs. 0.00")
        self.lbl_total_paid.setStyleSheet("color: #2ed573; font-weight: bold;")
        checkout_layout.addWidget(self.lbl_total_paid)
        
        self.lbl_balance_owed = QLabel("Balance Owed: Rs. 0.00")
        self.lbl_balance_owed.setStyleSheet("color: #ff4757; font-weight: bold;")
        checkout_layout.addWidget(self.lbl_balance_owed)
        
        checkout_layout.addStretch()
        
        # Action Buttons
        btn_action_layout = QVBoxLayout()
        btn_action_layout.setSpacing(8)
        
        self.btn_drawer = QPushButton("🗄️ Open Drawer")
        self.btn_drawer.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #f1c40f; }
        """)
        self.btn_drawer.setCursor(Qt.PointingHandCursor)
        self.btn_drawer.clicked.connect(self.on_open_drawer_clicked)
        btn_action_layout.addWidget(self.btn_drawer)
        
        self.btn_checkout = QPushButton("✅ Complete Checkout")
        self.btn_checkout.setStyleSheet("""
            QPushButton {
                background-color: #6c5ce7;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #8172ea;
            }
        """)
        self.btn_checkout.setCursor(Qt.PointingHandCursor)
        self.btn_checkout.clicked.connect(self.on_checkout_clicked)
        btn_action_layout.addWidget(self.btn_checkout)
        
        checkout_layout.addLayout(btn_action_layout)
        
        main_split.addWidget(checkout_panel, stretch=1)
        layout.addLayout(main_split)
        
    def setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        self.history_cust_filter = QComboBox()
        self.history_cust_filter.currentIndexChanged.connect(self.load_sales)
        filter_layout.addWidget(QLabel("Customer Filter:"))
        filter_layout.addWidget(self.history_cust_filter)
        
        self.history_loc_filter = QComboBox()
        self.history_loc_filter.currentIndexChanged.connect(self.load_sales)
        filter_layout.addWidget(QLabel("Location Filter:"))
        filter_layout.addWidget(self.history_loc_filter)
        
        filter_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.setStyleSheet("background-color: #2e2e2e; color: white; padding: 6px 12px;")
        refresh_btn.clicked.connect(self.load_sales)
        filter_layout.addWidget(refresh_btn)
        
        layout.addLayout(filter_layout)
        
        # History Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "Invoice ID", "Customer Name", "Date / Time", "Status", "Total (Rs.)", "Paid (Rs.)", "Owed (Rs.)", "Actions"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        layout.addWidget(self.history_table)
        
    def load_form_references(self):
        # Load Locations
        try:
            locations = client.get_locations()
            self.location_combo.clear()
            self.history_loc_filter.blockSignals(True)
            self.history_loc_filter.clear()
            self.history_loc_filter.addItem("All Locations", None)
            
            for loc in locations:
                if loc.get("is_active"):
                    self.location_combo.addItem(loc["name"], loc["id"])
                    self.history_loc_filter.addItem(loc["name"], loc["id"])
            self.history_loc_filter.blockSignals(False)
        except Exception:
            pass
            
        # Load Customers
        try:
            self.all_customers = client.get_customers()
            self.customer_combo.blockSignals(True)
            self.customer_combo.clear()
            
            self.history_cust_filter.blockSignals(True)
            self.history_cust_filter.clear()
            self.history_cust_filter.addItem("All Customers", None)
            
            # Default Walk-in Customer index
            walkin_idx = 0
            
            for i, cust in enumerate(self.all_customers):
                display = f"{cust['name']} ({cust['internal_id']})"
                self.customer_combo.addItem(display, cust["id"])
                self.history_cust_filter.addItem(display, cust["id"])
                if cust["name"] == "Walk-in Customer":
                    walkin_idx = i
                    
            self.customer_combo.setCurrentIndex(walkin_idx)
            self.customer_combo.blockSignals(False)
            self.history_cust_filter.blockSignals(False)
            
            # Update customer details card
            self.on_customer_changed()
        except Exception:
            pass

        # Load Customer Types
        try:
            cust_types = client.get_customer_types()
            self.quick_cust_type_combo.blockSignals(True)
            self.quick_cust_type_combo.clear()
            for t in cust_types:
                self.quick_cust_type_combo.addItem(t["name"], t["id"])
            self.quick_cust_type_combo.blockSignals(False)
        except Exception:
            pass
            
        # Load all products cache
        try:
            self.all_products = client.get_products()
        except Exception:
            self.all_products = []
            
        self.populate_search_combo()
        fix_comboboxes(self)
        
    def load_data(self):
        self.load_form_references()
        self.load_sales()
        
    def load_sales(self):
        cust_id = self.history_cust_filter.currentData()
        loc_id = self.history_loc_filter.currentData()
        
        sales = client.get_sales(customer_id=cust_id, location_id=loc_id)
        self.history_table.setRowCount(len(sales))
        
        for row, s in enumerate(sales):
            self.history_table.setItem(row, 0, QTableWidgetItem(s["internal_id"]))
            
            # Look up customer
            c_name = "Walk-in Customer"
            for c in self.all_customers:
                if c["id"] == s["customer_id"]:
                    c_name = c["name"]
                    break
            self.history_table.setItem(row, 1, QTableWidgetItem(c_name))
            
            dt_str = s["date"]
            try:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                formatted_date = dt_str
                
            self.history_table.setItem(row, 2, QTableWidgetItem(formatted_date))
            
            status = s.get("status", "COMPLETED")
            status_item = QTableWidgetItem(status)
            if status == "RETURNED":
                status_item.setForeground(Qt.yellow)
            elif status == "CANCELLED":
                status_item.setForeground(Qt.red)
            else:
                status_item.setForeground(Qt.green)
            self.history_table.setItem(row, 3, status_item)
            
            self.history_table.setItem(row, 4, QTableWidgetItem(f"Rs. {s['total_amount']:.2f}"))
            self.history_table.setItem(row, 5, QTableWidgetItem(f"Rs. {s['paid_amount']:.2f}"))
            self.history_table.setItem(row, 6, QTableWidgetItem(f"Rs. {s['balance_owed']:.2f}"))
            
            # Actions Widget
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(5)
            
            # View button
            view_btn = QPushButton("View")
            view_btn.setObjectName("ViewAction")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setProperty("sale", s)
            view_btn.clicked.connect(self.on_view_clicked)
            actions_layout.addWidget(view_btn)
            
            # Print button
            print_btn = QPushButton("Print")
            print_btn.setObjectName("PrintAction")
            print_btn.setStyleSheet("background-color: #0984e3; color: white;")
            print_btn.setCursor(Qt.PointingHandCursor)
            print_btn.setProperty("sale", s)
            print_btn.clicked.connect(self.on_print_clicked)
            actions_layout.addWidget(print_btn)
            
            if status == "COMPLETED":
                # Return button
                return_btn = QPushButton("Return")
                return_btn.setObjectName("ReturnAction")
                return_btn.setStyleSheet("background-color: #f39c12; color: white;")
                return_btn.setCursor(Qt.PointingHandCursor)
                return_btn.setProperty("sale", s)
                return_btn.clicked.connect(self.on_return_clicked)
                actions_layout.addWidget(return_btn)
                
                # Cancel button
                cancel_btn = QPushButton("Cancel")
                cancel_btn.setObjectName("CancelAction")
                cancel_btn.setStyleSheet("background-color: #d63031; color: white;")
                cancel_btn.setCursor(Qt.PointingHandCursor)
                cancel_btn.setProperty("sale", s)
                cancel_btn.clicked.connect(self.on_cancel_clicked)
                actions_layout.addWidget(cancel_btn)
            
            self.history_table.setCellWidget(row, 7, actions_widget)
            
    def on_view_clicked(self):
        btn = self.sender()
        if btn:
            sale = btn.property("sale")
            if sale:
                dlg = SaleDetailDialog(sale, self)
                dlg.exec()
                
    def on_print_clicked(self):
        btn = self.sender()
        if btn:
            sale = btn.property("sale")
            if sale:
                self.print_invoice(sale)
                
    def on_return_clicked(self):
        btn = self.sender()
        if btn:
            sale = btn.property("sale")
            if sale:
                dlg = CustomerReturnDialog(sale, self)
                if dlg.exec() == QDialog.Accepted:
                    self.load_sales()
    def on_cancel_clicked(self):
        btn = self.sender()
        if btn:
            sale = btn.property("sale")
            if sale:
                reply = QMessageBox.question(
                    self, "Cancel Sale", 
                    f"Are you sure you want to cancel invoice {sale['internal_id']}?\nThis will restore inventory and credit the customer.",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    success, res = client.cancel_sale(sale["id"])
                    if success:
                        QMessageBox.information(self, "Success", f"Invoice {sale['internal_id']} cancelled successfully.")
                        self.load_sales()
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to cancel sale: {res}")

    def print_invoice(self, sale):
        templates = client.get_invoice_templates()
        if not templates:
            QMessageBox.warning(self, "No Templates", "No invoice templates found.")
            return
            
        dlg = PrintPreviewDialog(sale, templates, self)
        dlg.exec()
    def on_customer_changed(self):
        cust_id = self.customer_combo.currentData()
        if not cust_id:
            return
            
        selected_cust = None
        for c in self.all_customers:
            if c["id"] == cust_id:
                selected_cust = c
                break
                
        if selected_cust:
            cust_type_name = selected_cust.get('customer_type_name') or 'Retail'
            self.lbl_cust_type.setText(f"Type: {cust_type_name}")
            self.lbl_cust_limit.setText(f"Credit Limit: Rs. {selected_cust.get('credit_limit', 0.0):,.2f}")
            self.lbl_cust_bal.setText(f"Owed Balance: Rs. {selected_cust.get('balance', 0.0):,.2f}")
            
            # Sync the quick customer type combo box
            self.quick_cust_type_combo.blockSignals(True)
            for i in range(self.quick_cust_type_combo.count()):
                if self.quick_cust_type_combo.itemText(i) == cust_type_name:
                    self.quick_cust_type_combo.setCurrentIndex(i)
                    break
            self.quick_cust_type_combo.blockSignals(False)

            # Live recalculation of prices based on customer type
            self.update_cart_prices(cust_type_name)
            
    def on_quick_cust_type_changed(self):
        selected_type = self.quick_cust_type_combo.currentText()
        if selected_type:
            self.update_cart_prices(selected_type)

    def on_quick_customer_save(self):
        name = self.quick_cust_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter a customer name.")
            return

        # Create customer via API with the selected Customer Type
        payload = {
            "name": name, 
            "phone": "", 
            "address": "",
            "customer_type_id": self.quick_cust_type_combo.currentData()
        }
        success, res = client.create_customer(payload)
        if success:
            new_id = res.get("id")
            # Reload customers list and select the new one
            self.all_customers = client.get_customers()
            self.customer_combo.blockSignals(True)
            self.customer_combo.clear()
            select_idx = 0
            for i, cust in enumerate(self.all_customers):
                display = f"{cust['name']} ({cust['internal_id']})"
                self.customer_combo.addItem(display, cust["id"])
                if cust["id"] == new_id:
                    select_idx = i
            self.customer_combo.setCurrentIndex(select_idx)
            self.customer_combo.blockSignals(False)
            self.on_customer_changed()
            self.quick_cust_input.clear()
            QMessageBox.information(self, "✅ Customer Saved", f"Customer '{name}' has been saved and selected.")
        else:
            QMessageBox.warning(self, "Error", f"Failed to create customer: {res}")

    def update_cart_prices(self, customer_type):
        for item in self.cart_items:
            prod = item["product"]
            var = item["variant"]
            
            # Price prioritization: Variant -> Product -> Fallback
            price = 0.0
            if var:
                if customer_type == "Wholesale" and var.get("wholesale_price"):
                    price = var["wholesale_price"]
                elif customer_type == "Special" and var.get("special_price"):
                    price = var["special_price"]
                else:
                    price = var.get("retail_price") or prod.get("retail_price") or 0.0
            else:
                if customer_type == "Wholesale":
                    price = prod.get("wholesale_price") or prod.get("retail_price") or 0.0
                elif customer_type == "Special":
                    price = prod.get("special_price") or prod.get("retail_price") or 0.0
                else:
                    price = prod.get("retail_price") or 0.0
            
            item["price"] = price
            
        self.update_cart_table()
        self.recalc_totals()
        
    def populate_search_combo(self):
        self.product_search_combo.blockSignals(True)
        self.product_search_combo.clear()
        self.product_search_combo.addItem("-- Search & Select Product --", None)
        
        for p in self.all_products:
            # Add base product
            sku_str = f" [{p['sku']}]" if p.get('sku') else ""
            self.product_search_combo.addItem(f"{p['name']}{sku_str} - Rs. {p['retail_price']:.2f}", {"product": p, "variant": None})
            
            # Add variants if any
            for var in p.get("variants", []):
                var_sku = f" [{var['sku']}]" if var.get('sku') else ""
                var_price = var.get('retail_price') or p['retail_price']
                self.product_search_combo.addItem(f"{p['name']} - {var['name']}{var_sku} - Rs. {var_price:.2f}", {"product": p, "variant": var})
                
        self.product_search_combo.blockSignals(False)

    def on_search_product_selected(self, index):
        if index <= 0:
            return
            
        data = self.product_search_combo.itemData(index)
        if not data:
            return
            
        match_prod = data["product"]
        match_var = data["variant"]
        
        self.add_product_to_cart(match_prod, match_var)
        
        # Reset selection and clear search text box
        self.product_search_combo.blockSignals(True)
        self.product_search_combo.setCurrentIndex(0)
        if self.product_search_combo.lineEdit():
            self.product_search_combo.lineEdit().clear()
        self.product_search_combo.blockSignals(False)

    def add_product_to_cart(self, match_prod, match_var):
        # Check if already exists in cart
        existing = None
        for item in self.cart_items:
            if item["product"]["id"] == match_prod["id"]:
                if (match_var and item["variant"] and item["variant"]["id"] == match_var["id"]) or (not match_var and not item["variant"]):
                    existing = item
                    break
                    
        if existing:
            existing["qty"] += 1.0
        else:
            # Determine initial price
            cust_id = self.customer_combo.currentData()
            customer_type = "Retail"
            for c in self.all_customers:
                if c["id"] == cust_id:
                    customer_type = c.get("customer_type_name") or "Retail"
                    break
                    
            price = 0.0
            if match_var:
                if customer_type == "Wholesale" and match_var.get("wholesale_price"):
                    price = match_var["wholesale_price"]
                elif customer_type == "Special" and match_var.get("special_price"):
                    price = match_var["special_price"]
                else:
                    price = match_var.get("retail_price") or match_prod.get("retail_price") or 0.0
            else:
                if customer_type == "Wholesale":
                    price = match_prod.get("wholesale_price") or match_prod.get("retail_price") or 0.0
                elif customer_type == "Special":
                    price = match_prod.get("special_price") or match_prod.get("retail_price") or 0.0
                else:
                    price = match_prod.get("retail_price") or 0.0
                    
            self.cart_items.append({
                "product": match_prod,
                "variant": match_var,
                "qty": 1.0,
                "price": price,
                "discount": 0.0
            })
            
        self.update_cart_table()
        self.recalc_totals()

    def on_barcode_scanned(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return
            
        # Find matching product or variant
        match_prod = None
        match_var = None
        
        for p in self.all_products:
            # Check base product barcode
            if p.get("barcode") == barcode or p.get("sku") == barcode:
                match_prod = p
                break
            # Check variants barcodes
            for var in p.get("variants", []):
                if var.get("barcode") == barcode or var.get("sku") == barcode:
                    match_prod = p
                    match_var = var
                    break
            if match_prod:
                break
                
        if not match_prod:
            QMessageBox.warning(self, "Not Found", f"No product or variant found with barcode/SKU: '{barcode}'")
            self.barcode_input.clear()
            return
            
        self.add_product_to_cart(match_prod, match_var)
        self.barcode_input.clear()
        
    def update_cart_table(self):
        self.cart_table.setRowCount(len(self.cart_items))
        
        for row, item in enumerate(self.cart_items):
            prod = item["product"]
            var = item["variant"]
            
            name = prod["name"]
            if var:
                name += f" - {var['name']}"
                
            self.cart_table.setItem(row, 0, QTableWidgetItem(name))
            
            # Unit Name
            self.cart_table.setItem(row, 1, QTableWidgetItem(prod.get("unit_name") or "Piece"))
            
            # Editable Qty spinbox
            qty_spin = QDoubleSpinBox()
            qty_spin.setRange(0.01, 100000.0)
            qty_spin.setValue(item["qty"])
            qty_spin.setSingleStep(1)
            qty_spin.setStyleSheet("QDoubleSpinBox { background: #121212; color: white; border: none; }")
            qty_spin.valueChanged.connect(lambda val, r=row: self.on_qty_changed(r, val))
            self.cart_table.setCellWidget(row, 2, qty_spin)
            
            # Editable Unit Price spinbox (for authorized override)
            price_spin = QDoubleSpinBox()
            price_spin.setRange(0.0, 1000000.0)
            price_spin.setValue(item["price"])
            price_spin.setSingleStep(10)
            price_spin.setStyleSheet("QDoubleSpinBox { background: #121212; color: white; border: none; }")
            price_spin.valueChanged.connect(lambda val, r=row: self.on_price_changed(r, val))
            self.cart_table.setCellWidget(row, 3, price_spin)
            
            # Editable Line Discount spinbox
            disc_spin = QDoubleSpinBox()
            disc_spin.setRange(0.0, 100000.0)
            disc_spin.setValue(item["discount"])
            disc_spin.setSingleStep(5)
            disc_spin.setStyleSheet("QDoubleSpinBox { background: #121212; color: white; border: none; }")
            disc_spin.valueChanged.connect(lambda val, r=row: self.on_discount_changed(r, val))
            self.cart_table.setCellWidget(row, 4, disc_spin)
            
            # Line Total
            line_tot = (item["qty"] * item["price"]) - item["discount"]
            if line_tot < 0:
                line_tot = 0.0
            self.cart_table.setItem(row, 5, QTableWidgetItem(f"Rs. {line_tot:.2f}"))
            
            # Remove Button
            remove_btn = QPushButton("Remove")
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: #c0392b;
                    color: white;
                    padding: 3px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #e74c3c;
                }
            """)
            remove_btn.setCursor(Qt.PointingHandCursor)
            remove_btn.clicked.connect(lambda _, r=row: self.remove_cart_item(r))
            self.cart_table.setCellWidget(row, 6, remove_btn)
            
    def on_qty_changed(self, row, val):
        if row < len(self.cart_items):
            self.cart_items[row]["qty"] = val
            self.recalc_totals()
            # Update row total cell
            line_tot = (val * self.cart_items[row]["price"]) - self.cart_items[row]["discount"]
            if line_tot < 0:
                line_tot = 0.0
            self.cart_table.setItem(row, 5, QTableWidgetItem(f"Rs. {line_tot:.2f}"))
            
    def on_price_changed(self, row, val):
        if row < len(self.cart_items):
            self.cart_items[row]["price"] = val
            self.recalc_totals()
            # Update row total cell
            line_tot = (self.cart_items[row]["qty"] * val) - self.cart_items[row]["discount"]
            if line_tot < 0:
                line_tot = 0.0
            self.cart_table.setItem(row, 5, QTableWidgetItem(f"Rs. {line_tot:.2f}"))
            
    def on_discount_changed(self, row, val):
        if row < len(self.cart_items):
            self.cart_items[row]["discount"] = val
            self.recalc_totals()
            # Update row total cell
            line_tot = (self.cart_items[row]["qty"] * self.cart_items[row]["price"]) - val
            if line_tot < 0:
                line_tot = 0.0
            self.cart_table.setItem(row, 5, QTableWidgetItem(f"Rs. {line_tot:.2f}"))
            
    def remove_cart_item(self, row):
        if row < len(self.cart_items):
            self.cart_items.pop(row)
            self.update_cart_table()
            self.recalc_totals()
            
    def recalc_totals(self):
        subtotal = 0.0
        for item in self.cart_items:
            line_tot = (item["qty"] * item["price"]) - item["discount"]
            if line_tot < 0:
                line_tot = 0.0
            subtotal += line_tot
            
        self.lbl_subtotal.setText(f"Rs. {subtotal:,.2f}")
        
        discount = self.cart_discount_spin.value()
        grand_total = subtotal - discount
        if grand_total < 0:
            grand_total = 0.0
            
        self.lbl_grand_total.setText(f"Rs. {grand_total:,.2f}")
        
        paid = sum(spin.value() for spin in self.payment_spins.values())
        self.lbl_total_paid.setText(f"Total Paid: Rs. {paid:,.2f}")
        
        owed = grand_total - paid
        if owed < 0:
            owed = 0.0
            
        self.lbl_balance_owed.setText(f"Balance Owed: Rs. {owed:,.2f}")
        
    def on_checkout_clicked(self):
        if not self.cart_items:
            QMessageBox.warning(self, "Empty Cart", "Please scan or add at least one item to cart.")
            return
            
        # Auto-save quick customer if name is entered but not saved/selected yet
        quick_name = self.quick_cust_input.text().strip()
        if quick_name:
            payload = {
                "name": quick_name, 
                "phone": "", 
                "address": "",
                "customer_type_id": self.quick_cust_type_combo.currentData()
            }
            success, res = client.create_customer(payload)
            if success:
                new_id = res.get("id")
                # Reload customer list and select the new customer
                self.all_customers = client.get_customers()
                self.customer_combo.blockSignals(True)
                self.customer_combo.clear()
                select_idx = 0
                for i, cust in enumerate(self.all_customers):
                    display = f"{cust['name']} ({cust['internal_id']})"
                    self.customer_combo.addItem(display, cust["id"])
                    if cust["id"] == new_id:
                        select_idx = i
                self.customer_combo.setCurrentIndex(select_idx)
                self.customer_combo.blockSignals(False)
                self.on_customer_changed()
                self.quick_cust_input.clear()
                customer_id = new_id
            else:
                QMessageBox.warning(self, "Error", f"Failed to auto-create customer: {res}")
                return

        customer_id = self.customer_combo.currentData()
        location_id = self.location_combo.currentData()
        
        if not customer_id or not location_id:
            QMessageBox.warning(self, "Selection Required", "Please select a Customer and a Location.")
            return
            
        items_payload = []
        for item in self.cart_items:
            items_payload.append({
                "product_id": item["product"]["id"],
                "variant_id": item["variant"]["id"] if item["variant"] else None,
                "quantity": item["qty"],
                "unit_id": item["product"].get("unit_id"),
                "unit_price": item["price"],
                "discount": item["discount"]
            })
            
        discount = self.cart_discount_spin.value()
        
        # Build split payments array
        payments = []
        for method, spin in self.payment_spins.items():
            amt = spin.value()
            if amt > 0:
                payments.append({"payment_method": method, "amount": amt})
        
        paid = sum(p["amount"] for p in payments)
        
        sale_data = {
            "customer_id": customer_id,
            "location_id": location_id,
            "discount": discount,
            "paid_amount": paid,
            "payments": payments if payments else None,
            "items": items_payload,
            "notes": f"Checkout from POS Screen at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }
        
        success, result = client.create_sale(sale_data)
        if success:
            # Build payment summary for message
            pay_summary = ""
            if payments:
                pay_lines = [f"  {p['payment_method']}: Rs. {p['amount']:,.2f}" for p in payments]
                pay_summary = "\n" + "\n".join(pay_lines)
            
            QMessageBox.information(
                self, "✅ Checkout Successful",
                f"Invoice {result['internal_id']} has been recorded.\n"
                f"Total: Rs. {result['total_amount']:,.2f}\n"
                f"Paid: Rs. {result['paid_amount']:,.2f}{pay_summary}\n"
                f"Balance Owed: Rs. {result['balance_owed']:,.2f}"
            )
            self.cart_items.clear()
            self.cart_discount_spin.setValue(0.0)
            for spin in self.payment_spins.values():
                spin.setValue(0.0)
            self.update_cart_table()
            self.recalc_totals()
            self.load_data()
            
            # Automatically show the invoice preview dialog
            self.print_invoice(result)
        else:
            QMessageBox.critical(self, "Checkout Failed", str(result))

    def on_open_drawer_clicked(self):
        # Hardware Integration Point for ESC/POS Cash Drawer Command
        QMessageBox.information(
            self, 
            "Cash Drawer", 
            "Signal sent to open Cash Drawer.\n(Hardware integration required for physical operation)."
        )
