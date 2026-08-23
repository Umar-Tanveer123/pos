from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                                 QLabel, QLineEdit, QComboBox, QDoubleSpinBox, 
                                 QSpinBox, QCheckBox, QPushButton, QTableWidget, 
                                 QTableWidgetItem, QHeaderView, QFormLayout, 
                                 QMessageBox, QGroupBox, QScrollArea, QWidget)
from PySide6.QtCore import Qt
import random
from frontend.api_client import client
from frontend.theme import fix_comboboxes

class ProductForm(QDialog):
    def __init__(self, product_data=None, parent=None):
        super().__init__(parent)
        self.product_data = product_data
        self.setWindowTitle("Edit Product" if product_data else "Add Product")
        self.setMinimumSize(850, 750)
        
        self.categories = []
        self.subcategories = []
        self.brands = []
        self.units = []
        self.locations = []
        self.stock_inputs = {} # location_id -> spinbox (for base product)
        self.supplier_checkboxes = {}
        
        self.setup_ui()
        self.load_metadata()
        if self.product_data:
            self.populate_form()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Scrollable container for forms
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        title = QLabel("Edit Product" if self.product_data else "Add New Product")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # 1. Basic Info Section
        basic_group = QGroupBox("Basic Information")
        basic_group.setStyleSheet("QGroupBox { font-weight: bold; color: #6c5ce7; }")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Coca-Cola Coke")
        basic_layout.addRow("Product Name *", self.name_input)

        sku_layout = QHBoxLayout()
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("Leave blank to auto-generate SKU")
        
        self.gen_sku_btn = QPushButton("⚡ Auto Gen")
        self.gen_sku_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #6c5ce7;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                font-size: 13px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #6c5ce7;
                color: white;
            }
        """)
        self.gen_sku_btn.setCursor(Qt.PointingHandCursor)
        self.gen_sku_btn.clicked.connect(self.auto_generate_sku)
        
        sku_layout.addWidget(self.sku_input)
        sku_layout.addWidget(self.gen_sku_btn)
        basic_layout.addRow("SKU / Item Code", sku_layout)

        barcode_layout = QHBoxLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan barcode or auto-generate EAN-13")
        
        self.gen_bar_btn = QPushButton("⚡ Auto Gen")
        self.gen_bar_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #6c5ce7;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                font-size: 13px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #6c5ce7;
                color: white;
            }
        """)
        self.gen_bar_btn.setCursor(Qt.PointingHandCursor)
        self.gen_bar_btn.clicked.connect(self.auto_generate_barcode)
        
        barcode_layout.addWidget(self.barcode_input)
        barcode_layout.addWidget(self.gen_bar_btn)
        basic_layout.addRow("Barcode", barcode_layout)

        # Dropdowns
        self.cat_combo = QComboBox()
        self.cat_combo.currentIndexChanged.connect(self.on_category_changed)
        basic_layout.addRow("Category", self.cat_combo)

        self.subcat_combo = QComboBox()
        basic_layout.addRow("Subcategory", self.subcat_combo)

        self.brand_combo = QComboBox()
        basic_layout.addRow("Brand", self.brand_combo)

        self.unit_combo = QComboBox()
        basic_layout.addRow("Base Unit", self.unit_combo)

        self.sec_unit_combo = QComboBox()
        basic_layout.addRow("Secondary Unit (Optional)", self.sec_unit_combo)

        self.conversion_factor_spin = QDoubleSpinBox()
        self.conversion_factor_spin.setRange(0.0001, 999999.0)
        self.conversion_factor_spin.setValue(1.0)
        self.conversion_factor_spin.setDecimals(4)
        basic_layout.addRow("Conversion Factor", self.conversion_factor_spin)

        layout.addWidget(basic_group)

        # 1.5 Suppliers Selection Section
        suppliers_group = QGroupBox("Suppliers Providing this Product")
        suppliers_group.setStyleSheet("QGroupBox { font-weight: bold; color: #6c5ce7; }")
        suppliers_layout = QVBoxLayout(suppliers_group)
        
        self.suppliers_scroll = QScrollArea()
        self.suppliers_scroll.setWidgetResizable(True)
        self.suppliers_scroll.setMinimumHeight(100)
        self.suppliers_scroll.setMaximumHeight(150)
        self.suppliers_scroll.setStyleSheet("QScrollArea { border: 1px solid #444; background: #1e1e1e; }")
        
        self.suppliers_container = QWidget()
        self.suppliers_inner = QVBoxLayout(self.suppliers_container)
        self.suppliers_inner.setSpacing(4)
        self.suppliers_inner.setContentsMargins(5, 5, 5, 5)
        
        self.suppliers_scroll.setWidget(self.suppliers_container)
        suppliers_layout.addWidget(self.suppliers_scroll)
        layout.addWidget(suppliers_group)

        # 2. Pricing Tiers Section
        pricing_group = QGroupBox("Pricing Tiers (Rs.)")
        pricing_group.setStyleSheet("QGroupBox { font-weight: bold; color: #6c5ce7; }")
        pricing_layout = QFormLayout(pricing_group)
        pricing_layout.setSpacing(10)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 1000000)
        self.cost_spin.setSingleStep(10)
        pricing_layout.addRow("Purchase / Cost Price", self.cost_spin)

        self.retail_spin = QDoubleSpinBox()
        self.retail_spin.setRange(0, 1000000)
        self.retail_spin.setSingleStep(10)
        pricing_layout.addRow("Retail Price", self.retail_spin)

        self.wholesale_spin = QDoubleSpinBox()
        self.wholesale_spin.setRange(0, 1000000)
        self.wholesale_spin.setSingleStep(10)
        pricing_layout.addRow("Wholesale Price", self.wholesale_spin)

        self.special_spin = QDoubleSpinBox()
        self.special_spin.setRange(0, 1000000)
        self.special_spin.setSingleStep(10)
        pricing_layout.addRow("Special Price", self.special_spin)

        layout.addWidget(pricing_group)

        # 3. Stock Levels Section (Dynamically Loaded)
        self.stock_group = QGroupBox("Inventory Levels / Quantity On Hand (QOH)")
        self.stock_group.setStyleSheet("QGroupBox { font-weight: bold; color: #6c5ce7; }")
        self.stock_layout = QFormLayout(self.stock_group)
        self.stock_layout.setSpacing(10)
        layout.addWidget(self.stock_group)

        # 4. Stock Rules Section
        stock_rules_group = QGroupBox("Stock Rules")
        stock_rules_group.setStyleSheet("QGroupBox { font-weight: bold; color: #6c5ce7; }")
        stock_rules_layout = QFormLayout(stock_rules_group)
        stock_rules_layout.setSpacing(10)

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 10000)
        self.threshold_spin.setValue(10)
        stock_rules_layout.addRow("Low-Stock Alert Threshold", self.threshold_spin)

        self.active_cb = QCheckBox("Product is Active")
        self.active_cb.setChecked(True)
        stock_rules_layout.addRow("", self.active_cb)

        layout.addWidget(stock_rules_group)

        # 5. Variants Section
        variant_group = QGroupBox("Product Variants (Optional)")
        variant_group.setStyleSheet("QGroupBox { font-weight: bold; color: #6c5ce7; }")
        variant_layout = QVBoxLayout(variant_group)
        
        variant_desc = QLabel("Variants overrides can have different prices and location stock levels.")
        variant_desc.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        variant_layout.addWidget(variant_desc)

        # Table for Variants
        self.variant_table = QTableWidget()
        self.variant_table.setMinimumHeight(150)
        variant_layout.addWidget(self.variant_table)

        add_var_btn = QPushButton("+ Add Variant Row")
        add_var_btn.setStyleSheet("background-color: #2a2a2a; border: 1px solid #3a3a3a;")
        add_var_btn.clicked.connect(self.add_variant_row_clicked)
        variant_layout.addWidget(add_var_btn)

        layout.addWidget(variant_group)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(15, 10, 15, 10)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #333333; color: white;")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Product")
        save_btn.clicked.connect(self.handle_save)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)
        fix_comboboxes(self)

    def auto_generate_barcode(self):
        # 12 digits starting with 200 (EAN-13 custom code)
        digits = [2, 0, 0] + [random.randint(0, 9) for _ in range(9)]
        odd_sum = sum(digits[i] for i in range(0, 12, 2))
        even_sum = sum(digits[i] for i in range(1, 12, 2))
        total = odd_sum + (even_sum * 3)
        checksum = (10 - (total % 10)) % 10
        digits.append(checksum)
        barcode_str = "".join(map(str, digits))
        self.barcode_input.setText(barcode_str)

    def auto_generate_sku(self):
        name = self.name_input.text().strip()
        prefix = "".join([c for c in name if c.isalnum()]).upper()[:4]
        if not prefix:
            prefix = "ITEM"
        rand_num = random.randint(1000, 9999)
        self.sku_input.setText(f"{prefix}-{rand_num}")


    def load_metadata(self):
        self.categories = client.get_categories()
        self.subcategories = client.get_subcategories()
        self.brands = client.get_brands()
        self.units = client.get_units()
        self.locations = client.get_locations()
        
        # Load Suppliers list
        try:
            suppliers = client.get_suppliers()
        except Exception:
            suppliers = []
            
        while self.suppliers_inner.count():
            child = self.suppliers_inner.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.supplier_checkboxes.clear()
        
        for sup in suppliers:
            cb = QCheckBox(f"{sup['name']} ({sup['internal_id']})")
            self.suppliers_inner.addWidget(cb)
            self.supplier_checkboxes[sup["id"]] = cb
        self.suppliers_inner.addStretch()

        # Categories
        self.cat_combo.clear()
        self.cat_combo.addItem("Select Category...", None)
        for cat in self.categories:
            self.cat_combo.addItem(cat["name"], cat["id"])

        # Brands
        self.brand_combo.clear()
        self.brand_combo.addItem("Select Brand...", None)
        for br in self.brands:
            self.brand_combo.addItem(br["name"], br["id"])

        # Units
        self.unit_combo.clear()
        self.unit_combo.addItem("Select Base Unit...", None)
        for u in self.units:
            self.unit_combo.addItem(u["name"], u["id"])

        self.sec_unit_combo.clear()
        self.sec_unit_combo.addItem("None (No conversion)", None)
        for u in self.units:
            self.sec_unit_combo.addItem(u["name"], u["id"])

        # Base Product stock levels inputs
        while self.stock_layout.count():
            child = self.stock_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.stock_inputs.clear()
        for loc in self.locations:
            spin = QDoubleSpinBox()
            spin.setRange(0, 1000000)
            spin.setSingleStep(10)
            self.stock_layout.addRow(f"QOH at {loc['name']}", spin)
            self.stock_inputs[loc["id"]] = spin

        # Build variant table columns based on locations
        headers = ["Variant Name *", "SKU", "Barcode", "Cost Price", "Retail Price", "Wholesale", "Special"]
        for loc in self.locations:
            headers.append(f"Stock: {loc['name']}")
        headers.append("Action")
        
        self.variant_table.setColumnCount(len(headers))
        self.variant_table.setHorizontalHeaderLabels(headers)
        self.variant_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def on_category_changed(self, index):
        cat_id = self.cat_combo.currentData()
        self.subcat_combo.clear()
        self.subcat_combo.addItem("Select Subcategory...", None)
        
        if cat_id is not None:
            filtered = [s for s in self.subcategories if s["category_id"] == cat_id]
            for s in filtered:
                self.subcat_combo.addItem(s["name"], s["id"])

    def add_variant_row_clicked(self):
        self.add_variant_row()

    def add_variant_row(self, name="", sku="", barcode="", cost=0.0, retail=0.0, wholesale=0.0, special=0.0, stock_map=None):
        if stock_map is None:
            stock_map = {}
            
        row = self.variant_table.rowCount()
        self.variant_table.insertRow(row)

        # Name, SKU, Barcode
        self.variant_table.setItem(row, 0, QTableWidgetItem(name))
        self.variant_table.setItem(row, 1, QTableWidgetItem(sku))
        self.variant_table.setItem(row, 2, QTableWidgetItem(barcode))

        # Prices
        for col, val in enumerate([cost, retail, wholesale, special], start=3):
            item = QTableWidgetItem(f"{val:.2f}" if val else "")
            self.variant_table.setItem(row, col, item)

        # Stock columns dynamically
        col_offset = 7
        for loc in self.locations:
            val = stock_map.get(loc["id"], 0.0)
            item = QTableWidgetItem(f"{val:.2f}")
            self.variant_table.setItem(row, col_offset, item)
            col_offset += 1

        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5252;
                color: white;
                padding: 4px 10px;
                font-size: 11px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ff7d7d;
            }
        """)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(self.remove_variant_row)
        self.variant_table.setCellWidget(row, col_offset, remove_btn)

    def remove_variant_row(self):
        btn = self.sender()
        if btn:
            # Find the row dynamically using the button's position
            index = self.variant_table.indexAt(btn.pos())
            if index.isValid():
                self.variant_table.removeRow(index.row())

    def populate_form(self):
        p = self.product_data
        self.name_input.setText(p.get("name", ""))
        self.sku_input.setText(p.get("sku", ""))
        self.barcode_input.setText(p.get("barcode", ""))
        
        # Populate suppliers
        selected_sup_ids = p.get("supplier_ids", [])
        for sup_id, cb in self.supplier_checkboxes.items():
            cb.setChecked(sup_id in selected_sup_ids)
        
        # Dropdown selection
        cat_id = p.get("category_id")
        idx = self.cat_combo.findData(cat_id)
        if idx != -1:
            self.cat_combo.setCurrentIndex(idx)
            
        subcat_id = p.get("subcategory_id")
        idx = self.subcat_combo.findData(subcat_id)
        if idx != -1:
            self.subcat_combo.setCurrentIndex(idx)

        brand_id = p.get("brand_id")
        idx = self.brand_combo.findData(brand_id)
        if idx != -1:
            self.brand_combo.setCurrentIndex(idx)

        unit_id = p.get("unit_id")
        idx = self.unit_combo.findData(unit_id)
        if idx != -1:
            self.unit_combo.setCurrentIndex(idx)

        sec_unit_id = p.get("secondary_unit_id")
        idx_sec = self.sec_unit_combo.findData(sec_unit_id)
        if idx_sec != -1:
            self.sec_unit_combo.setCurrentIndex(idx_sec)
        else:
            self.sec_unit_combo.setCurrentIndex(0)

        self.conversion_factor_spin.setValue(p.get("conversion_factor") or 1.0)

        # Pricing
        self.cost_spin.setValue(p.get("purchase_price", 0.0))
        self.retail_spin.setValue(p.get("retail_price", 0.0))
        self.wholesale_spin.setValue(p.get("wholesale_price", 0.0))
        self.special_spin.setValue(p.get("special_price", 0.0))

        # Stock Levels (base)
        for item in p.get("stock", []):
            loc_id = item.get("location_id")
            qty = item.get("quantity", 0.0)
            if loc_id in self.stock_inputs:
                self.stock_inputs[loc_id].setValue(qty)

        # Rules
        self.threshold_spin.setValue(p.get("low_stock_threshold", 10))
        self.active_cb.setChecked(p.get("is_active", True))

        # Populate variants with location stock map
        for var in p.get("variants", []):
            stock_map = {item.get("location_id"): item.get("quantity") for item in var.get("stock", [])}
            self.add_variant_row(
                name=var.get("name", ""),
                sku=var.get("sku", "") or "",
                barcode=var.get("barcode", "") or "",
                cost=var.get("purchase_price") or 0.0,
                retail=var.get("retail_price") or 0.0,
                wholesale=var.get("wholesale_price") or 0.0,
                special=var.get("special_price") or 0.0,
                stock_map=stock_map
            )

    def handle_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Product Name is required.")
            return

        sku = self.sku_input.text().strip() or None
        barcode = self.barcode_input.text().strip() or None
        category_id = self.cat_combo.currentData()
        subcategory_id = self.subcat_combo.currentData()
        brand_id = self.brand_combo.currentData()
        unit_id = self.unit_combo.currentData()
        secondary_unit_id = self.sec_unit_combo.currentData()
        conversion_factor = self.conversion_factor_spin.value()

        # Build initial stock payload for base product
        initial_stock_payload = []
        for loc_id, spin in self.stock_inputs.items():
            initial_stock_payload.append({
                "location_id": loc_id,
                "quantity": spin.value()
            })

        # Gather selected supplier IDs
        supplier_ids = [sup_id for sup_id, cb in self.supplier_checkboxes.items() if cb.isChecked()]

        product_data = {
            "name": name,
            "sku": sku,
            "barcode": barcode,
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "brand_id": brand_id,
            "unit_id": unit_id,
            "secondary_unit_id": secondary_unit_id,
            "conversion_factor": conversion_factor,
            "purchase_price": self.cost_spin.value(),
            "retail_price": self.retail_spin.value(),
            "wholesale_price": self.wholesale_spin.value(),
            "special_price": self.special_spin.value(),
            "low_stock_threshold": self.threshold_spin.value(),
            "is_active": self.active_cb.isChecked(),
            "initial_stock": initial_stock_payload,
            "supplier_ids": supplier_ids,
            "variants": []
        }

        # Parse variants
        for row in range(self.variant_table.rowCount()):
            v_name_item = self.variant_table.item(row, 0)
            v_name = v_name_item.text().strip() if v_name_item else ""
            if not v_name:
                QMessageBox.warning(self, "Validation Error", f"Variant name at row {row+1} is required.")
                return

            v_sku_item = self.variant_table.item(row, 1)
            v_sku = v_sku_item.text().strip() if v_sku_item else None
            
            v_bar_item = self.variant_table.item(row, 2)
            v_bar = v_bar_item.text().strip() if v_bar_item else None

            def parse_float(row_idx, col_idx):
                item = self.variant_table.item(row_idx, col_idx)
                if not item or not item.text().strip():
                    return None
                try:
                    return float(item.text().strip())
                except ValueError:
                    return 0.0

            v_cost = parse_float(row, 3)
            v_retail = parse_float(row, 4)
            v_wholesale = parse_float(row, 5)
            v_special = parse_float(row, 6)

            # Extract location stock values from dynamic columns
            v_stock_payload = []
            col_offset = 7
            for loc in self.locations:
                qty = parse_float(row, col_offset) or 0.0
                v_stock_payload.append({
                    "location_id": loc["id"],
                    "quantity": qty
                })
                col_offset += 1

            product_data["variants"].append({
                "name": v_name,
                "sku": v_sku,
                "barcode": v_bar,
                "purchase_price": v_cost,
                "retail_price": v_retail,
                "wholesale_price": v_wholesale,
                "special_price": v_special,
                "initial_stock": v_stock_payload
            })

        if self.product_data:
            success, res = client.update_product(self.product_data["id"], product_data)
        else:
            success, res = client.create_product(product_data)

        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "API Error", res)
