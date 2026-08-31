from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                                 QLabel, QLineEdit, QComboBox, QPushButton, 
                                 QTableWidget, QTableWidgetItem, QHeaderView, 
                                 QTabWidget, QMessageBox, QFormLayout, QFrame,
                                 QDialog)
from PySide6.QtCore import Qt
from frontend.api_client import client
from frontend.screens.product_form import ProductForm
from frontend.screens.barcode_generator_screen import BarcodeGeneratorScreen

class ProductsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Main Title
        title_layout = QVBoxLayout()
        title = QLabel("Product & Catalog Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        subtitle = QLabel("Manage your 20,000+ catalog, categories, subcategories, brands, and sales units.")
        subtitle.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        layout.addLayout(title_layout)

        # Tab Widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Init Tab Content
        self.init_products_tab()
        self.init_categories_tab()
        self.init_brands_tab()
        self.init_units_tab()

    # ----------------- Products Tab -----------------
    def init_products_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Filter Bar
        filter_layout = QHBoxLayout()
        
        self.prod_search = QLineEdit()
        self.prod_search.setPlaceholderText("Search by SKU, Name, Barcode...")
        self.prod_search.setMinimumWidth(300)
        self.prod_search.textChanged.connect(self.load_products)
        filter_layout.addWidget(self.prod_search)

        self.prod_cat_filter = QComboBox()
        self.prod_cat_filter.addItem("All Categories", None)
        self.prod_cat_filter.currentIndexChanged.connect(self.load_products)
        filter_layout.addWidget(self.prod_cat_filter)

        self.prod_brand_filter = QComboBox()
        self.prod_brand_filter.addItem("All Brands", None)
        self.prod_brand_filter.currentIndexChanged.connect(self.load_products)
        filter_layout.addWidget(self.prod_brand_filter)

        filter_layout.addStretch()

        self.btn_print_barcodes = QPushButton("🏷️ Print Labels")
        self.btn_print_barcodes.setStyleSheet("background-color: #2a2a2a; color: #6c5ce7; border: 1px solid #6c5ce7; font-weight: bold;")
        self.btn_print_barcodes.setCursor(Qt.PointingHandCursor)
        self.btn_print_barcodes.clicked.connect(self.open_barcode_printer_dialog)
        filter_layout.addWidget(self.btn_print_barcodes)

        self.add_prod_btn = QPushButton("+ Add Product")
        self.add_prod_btn.setCursor(Qt.PointingHandCursor)
        self.add_prod_btn.clicked.connect(self.open_add_product)
        filter_layout.addWidget(self.add_prod_btn)

        layout.addLayout(filter_layout)

        # Products Table
        self.prod_table = QTableWidget()
        self.prod_table.setColumnCount(10)
        self.prod_table.setHorizontalHeaderLabels([
            "Item ID", "Name", "SKU", "Barcode", "Category", "Brand", "Unit", "Retail Price", "Total Stock", "Actions"
        ])
        self.prod_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.prod_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.prod_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.prod_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.prod_table.verticalHeader().setDefaultSectionSize(45)
        self.prod_table.verticalHeader().setVisible(False)
        self.prod_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.prod_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.prod_table)

        self.tabs.addTab(widget, "Products Catalog")

    # ----------------- Categories Tab -----------------
    def init_categories_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Left Column: List Categories & Subcategories
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        
        left_layout.addWidget(QLabel("Categories list:"))
        self.cat_table = QTableWidget()
        self.cat_table.setColumnCount(3)
        self.cat_table.setHorizontalHeaderLabels(["ID", "Category Name", "Actions"])
        self.cat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.cat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cat_table.verticalHeader().setDefaultSectionSize(45)
        self.cat_table.verticalHeader().setVisible(False)
        left_layout.addWidget(self.cat_table)

        left_layout.addWidget(QLabel("Subcategories list:"))
        self.subcat_table = QTableWidget()
        self.subcat_table.setColumnCount(4)
        self.subcat_table.setHorizontalHeaderLabels(["ID", "Subcategory Name", "Category ID", "Actions"])
        self.subcat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.subcat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.subcat_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.subcat_table.verticalHeader().setDefaultSectionSize(45)
        self.subcat_table.verticalHeader().setVisible(False)
        left_layout.addWidget(self.subcat_table)

        layout.addWidget(left_frame, stretch=2)

        # Right Column: Add Category / Subcategory
        right_frame = QFrame()
        right_frame.setStyleSheet("QFrame { background-color: #1e1e1e; border-radius: 8px; border: 1px solid #2a2a2a; }")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        # Form Category
        cat_title = QLabel("Add Category")
        cat_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        right_layout.addWidget(cat_title)
        
        self.new_cat_input = QLineEdit()
        self.new_cat_input.setPlaceholderText("Category Name")
        right_layout.addWidget(self.new_cat_input)

        add_cat_btn = QPushButton("Save Category")
        add_cat_btn.clicked.connect(self.save_category)
        right_layout.addWidget(add_cat_btn)

        right_layout.addWidget(QFrame()) # spacer line

        # Form Subcategory
        subcat_title = QLabel("Add Subcategory")
        subcat_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        right_layout.addWidget(subcat_title)

        self.subcat_parent_combo = QComboBox()
        right_layout.addWidget(self.subcat_parent_combo)

        self.new_subcat_input = QLineEdit()
        self.new_subcat_input.setPlaceholderText("Subcategory Name")
        right_layout.addWidget(self.new_subcat_input)

        add_subcat_btn = QPushButton("Save Subcategory")
        add_subcat_btn.clicked.connect(self.save_subcategory)
        right_layout.addWidget(add_subcat_btn)

        right_layout.addStretch()
        layout.addWidget(right_frame, stretch=1)

        self.tabs.addTab(widget, "Categories")

    # ----------------- Brands Tab -----------------
    def init_brands_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Left Column: List
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        
        left_layout.addWidget(QLabel("Brands list:"))
        self.brand_table = QTableWidget()
        self.brand_table.setColumnCount(4)
        self.brand_table.setHorizontalHeaderLabels(["ID", "Brand Name", "Description", "Actions"])
        self.brand_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.brand_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.brand_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.brand_table.verticalHeader().setDefaultSectionSize(45)
        self.brand_table.verticalHeader().setVisible(False)
        left_layout.addWidget(self.brand_table)

        layout.addWidget(left_frame, stretch=2)

        # Right Column: Add Form
        right_frame = QFrame()
        right_frame.setStyleSheet("QFrame { background-color: #1e1e1e; border-radius: 8px; border: 1px solid #2a2a2a; }")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        title = QLabel("Add Brand")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        right_layout.addWidget(title)

        self.new_brand_input = QLineEdit()
        self.new_brand_input.setPlaceholderText("Brand Name")
        right_layout.addWidget(self.new_brand_input)

        self.new_brand_desc = QLineEdit()
        self.new_brand_desc.setPlaceholderText("Description (Optional)")
        right_layout.addWidget(self.new_brand_desc)

        add_brand_btn = QPushButton("Save Brand")
        add_brand_btn.clicked.connect(self.save_brand)
        right_layout.addWidget(add_brand_btn)

        right_layout.addStretch()
        layout.addWidget(right_frame, stretch=1)

        self.tabs.addTab(widget, "Brands")

    # ----------------- Units Tab -----------------
    def init_units_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Left Column: List
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        
        left_layout.addWidget(QLabel("Sales Units list:"))
        self.unit_table = QTableWidget()
        self.unit_table.setColumnCount(3)
        self.unit_table.setHorizontalHeaderLabels(["ID", "Unit Name", "Actions"])
        self.unit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.unit_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.unit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.unit_table.verticalHeader().setDefaultSectionSize(45)
        self.unit_table.verticalHeader().setVisible(False)
        left_layout.addWidget(self.unit_table)

        layout.addWidget(left_frame, stretch=2)

        # Right Column: Add Form
        right_frame = QFrame()
        right_frame.setStyleSheet("QFrame { background-color: #1e1e1e; border-radius: 8px; border: 1px solid #2a2a2a; }")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        title = QLabel("Add Unit")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        right_layout.addWidget(title)

        self.new_unit_input = QLineEdit()
        self.new_unit_input.setPlaceholderText("e.g. Kg, Piece, Carton")
        right_layout.addWidget(self.new_unit_input)

        add_unit_btn = QPushButton("Save Unit")
        add_unit_btn.clicked.connect(self.save_unit)
        right_layout.addWidget(add_unit_btn)

        right_layout.addStretch()
        layout.addWidget(right_frame, stretch=1)

        self.tabs.addTab(widget, "Units")

    # ----------------- Load & Refresh Data -----------------
    def load_data(self):
        # Triggered on app login
        self.load_categories()
        self.load_brands()
        self.load_units()
        self.load_products()

    def load_categories(self):
        # 1. Categories List
        self.cat_table.setRowCount(0)
        categories = client.get_categories()
        self.cat_table.setRowCount(len(categories))
        
        # Populate Category Combos for Subcategories / Filters
        self.subcat_parent_combo.clear()
        self.subcat_parent_combo.addItem("Select Parent Category...", None)
        
        self.prod_cat_filter.clear()
        self.prod_cat_filter.addItem("All Categories", None)

        for row, cat in enumerate(categories):
            self.cat_table.setItem(row, 0, QTableWidgetItem(str(cat["id"])))
            self.cat_table.setItem(row, 1, QTableWidgetItem(cat["name"]))
            
            # Action Panel for Category
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            
            del_btn = QPushButton("Delete")
            del_btn.setObjectName("DeleteAction")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setProperty("category", cat)
            del_btn.clicked.connect(self.on_delete_category_clicked)
            action_layout.addWidget(del_btn)
            action_widget.setLayout(action_layout)
            self.cat_table.setCellWidget(row, 2, action_widget)
            
            self.subcat_parent_combo.addItem(cat["name"], cat["id"])
            self.prod_cat_filter.addItem(cat["name"], cat["id"])

        # 2. Subcategories List
        self.subcat_table.setRowCount(0)
        subcategories = client.get_subcategories()
        self.subcat_table.setRowCount(len(subcategories))
        for row, sub in enumerate(subcategories):
            self.subcat_table.setItem(row, 0, QTableWidgetItem(str(sub["id"])))
            self.subcat_table.setItem(row, 1, QTableWidgetItem(sub["name"]))
            self.subcat_table.setItem(row, 2, QTableWidgetItem(str(sub["category_id"])))
            
            # Action Panel for Subcategory
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            
            del_btn = QPushButton("Delete")
            del_btn.setObjectName("DeleteAction")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setProperty("subcategory", sub)
            del_btn.clicked.connect(self.on_delete_subcategory_clicked)
            action_layout.addWidget(del_btn)
            action_widget.setLayout(action_layout)
            self.subcat_table.setCellWidget(row, 3, action_widget)

    def load_brands(self):
        self.brand_table.setRowCount(0)
        brands = client.get_brands()
        self.brand_table.setRowCount(len(brands))

        self.prod_brand_filter.clear()
        self.prod_brand_filter.addItem("All Brands", None)

        for row, br in enumerate(brands):
            self.brand_table.setItem(row, 0, QTableWidgetItem(str(br["id"])))
            self.brand_table.setItem(row, 1, QTableWidgetItem(br["name"]))
            self.brand_table.setItem(row, 2, QTableWidgetItem(br["description"] or ""))
            
            # Action Panel for Brand
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            
            del_btn = QPushButton("Delete")
            del_btn.setObjectName("DeleteAction")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setProperty("brand", br)
            del_btn.clicked.connect(self.on_delete_brand_clicked)
            action_layout.addWidget(del_btn)
            action_widget.setLayout(action_layout)
            self.brand_table.setCellWidget(row, 3, action_widget)
            
            self.prod_brand_filter.addItem(br["name"], br["id"])

    def load_units(self):
        self.unit_table.setRowCount(0)
        units = client.get_units()
        self.unit_table.setRowCount(len(units))
        for row, u in enumerate(units):
            self.unit_table.setItem(row, 0, QTableWidgetItem(str(u["id"])))
            self.unit_table.setItem(row, 1, QTableWidgetItem(u["name"]))

            # Action Panel for Unit
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            
            del_btn = QPushButton("Delete")
            del_btn.setObjectName("DeleteAction")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setProperty("unit", u)
            del_btn.clicked.connect(self.on_delete_unit_clicked)
            action_layout.addWidget(del_btn)
            action_widget.setLayout(action_layout)
            self.unit_table.setCellWidget(row, 2, action_widget)

    def load_products(self):
        self.prod_table.setRowCount(0)
        
        search = self.prod_search.text().strip() or None
        category_id = self.prod_cat_filter.currentData()
        brand_id = self.prod_brand_filter.currentData()

        products = client.get_products(search=search, category_id=category_id, brand_id=brand_id)
        self.prod_table.setRowCount(len(products))

        for row, p in enumerate(products):
            self.prod_table.setItem(row, 0, QTableWidgetItem(p["internal_id"]))
            self.prod_table.setItem(row, 1, QTableWidgetItem(p["name"]))
            self.prod_table.setItem(row, 2, QTableWidgetItem(p["sku"] or "N/A"))
            
            # Show barcode or internal barcode
            bar = p["barcode"] or p["internal_barcode"] or "N/A"
            self.prod_table.setItem(row, 3, QTableWidgetItem(bar))
            
            self.prod_table.setItem(row, 4, QTableWidgetItem(p["category_name"] or "N/A"))
            self.prod_table.setItem(row, 5, QTableWidgetItem(p["brand_name"] or "N/A"))
            self.prod_table.setItem(row, 6, QTableWidgetItem(p["unit_name"] or "N/A"))
            
            # Retail Price
            self.prod_table.setItem(row, 7, QTableWidgetItem(f"Rs. {p['retail_price']:.2f}"))

            # Total Stock QOH
            total_qty = sum(item.get("quantity", 0.0) for item in p.get("stock", []))
            self.prod_table.setItem(row, 8, QTableWidgetItem(f"{total_qty:.2f}"))

            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)

            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("EditAction")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setProperty("product", p)
            edit_btn.clicked.connect(self.on_edit_clicked)
            action_layout.addWidget(edit_btn)

            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("DeleteAction")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setProperty("product", p)
            delete_btn.clicked.connect(self.on_delete_product_clicked)
            action_layout.addWidget(delete_btn)
            
            action_widget.setLayout(action_layout)
            self.prod_table.setCellWidget(row, 9, action_widget)

    # ----------------- Save / Write Operations -----------------
    def save_category(self):
        name = self.new_cat_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Category name is required.")
            return
        success, res = client.create_category(name)
        if success:
            self.new_cat_input.clear()
            self.load_categories()
        else:
            QMessageBox.critical(self, "API Error", res)

    def save_subcategory(self):
        name = self.new_subcat_input.text().strip()
        cat_id = self.subcat_parent_combo.currentData()
        if not name or cat_id is None:
            QMessageBox.warning(self, "Validation Error", "Category selection and Subcategory name are required.")
            return
        success, res = client.create_subcategory(name, cat_id)
        if success:
            self.new_subcat_input.clear()
            self.load_categories()
        else:
            QMessageBox.critical(self, "API Error", res)

    def save_brand(self):
        name = self.new_brand_input.text().strip()
        desc = self.new_brand_desc.text().strip() or None
        if not name:
            QMessageBox.warning(self, "Validation Error", "Brand name is required.")
            return
        success, res = client.create_brand(name, desc)
        if success:
            self.new_brand_input.clear()
            self.new_brand_desc.clear()
            self.load_brands()
        else:
            QMessageBox.critical(self, "API Error", res)

    def save_unit(self):
        name = self.new_unit_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Unit name is required.")
            return
        success, res = client.create_unit(name)
        if success:
            self.new_unit_input.clear()
            self.load_units()
        else:
            QMessageBox.critical(self, "API Error", res)

    def on_edit_clicked(self):
        btn = self.sender()
        if btn:
            prod = btn.property("product")
            if prod:
                self.open_edit_product(prod)

    def open_add_product(self):
        dialog = ProductForm(parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.load_products()

    def open_edit_product(self, product):
        dialog = ProductForm(product_data=product, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.load_products()

    def on_delete_product_clicked(self):
        btn = self.sender()
        if btn:
            prod = btn.property("product")
            if prod:
                reply = QMessageBox.question(
                    self,
                    "Confirm Product Deletion",
                    f"Are you sure you want to permanently delete the product '{prod['name']}'?\n"
                    "This will delete all its variant structures and stock transaction ledgers.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    try:
                        success, err = client.delete_product(prod["id"])
                        if success:
                            QMessageBox.information(self, "Success", "Product deleted successfully.")
                            self.load_products()
                        else:
                            QMessageBox.critical(self, "Error", f"Failed to delete product: {err}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Unexpected error occurred: {str(e)}")

    def on_delete_category_clicked(self):
        btn = self.sender()
        if btn:
            cat = btn.property("category")
            if cat:
                reply = QMessageBox.warning(
                    self,
                    "CRITICAL WARNING: Cascade Category Deletion",
                    f"WARNING: Deleting the category '{cat['name']}' will permanently delete:\n"
                    "• All products and variants within this category\n"
                    "• All related stock transaction histories\n"
                    "• All associated subcategories\n\n"
                    "This action is IRREVERSIBLE. Are you sure you want to proceed?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    try:
                        success, err = client.delete_category(cat["id"])
                        if success:
                            QMessageBox.information(self, "Success", "Category and all cascading records deleted successfully.")
                            self.load_categories()
                            self.load_products()
                        else:
                            QMessageBox.critical(self, "Error", f"Failed to delete category: {err}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Unexpected error occurred: {str(e)}")

    def on_delete_subcategory_clicked(self):
        btn = self.sender()
        if btn:
            sub = btn.property("subcategory")
            if sub:
                reply = QMessageBox.question(
                    self,
                    "Confirm Subcategory Deletion",
                    f"Are you sure you want to delete subcategory '{sub['name']}'?\n"
                    "Products in this subcategory will be set to 'No Subcategory' but will NOT be deleted.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    try:
                        success, err = client.delete_subcategory(sub["id"])
                        if success:
                            QMessageBox.information(self, "Success", "Subcategory deleted successfully.")
                            self.load_categories()
                            self.load_products()
                        else:
                            QMessageBox.critical(self, "Error", f"Failed to delete subcategory: {err}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Unexpected error occurred: {str(e)}")

    def on_delete_brand_clicked(self):
        btn = self.sender()
        if btn:
            br = btn.property("brand")
            if br:
                reply = QMessageBox.question(
                    self,
                    "Confirm Brand Deletion",
                    f"Are you sure you want to delete brand '{br['name']}'?\n"
                    "Products associated with this brand will remain intact but set to 'No Brand'.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    try:
                        success, err = client.delete_brand(br["id"])
                        if success:
                            QMessageBox.information(self, "Success", "Brand deleted successfully.")
                            self.load_brands()
                            self.load_products()
                        else:
                            QMessageBox.critical(self, "Error", f"Failed to delete brand: {err}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Unexpected error occurred: {str(e)}")

    def on_delete_unit_clicked(self):
        btn = self.sender()
        if btn:
            u = btn.property("unit")
            if u:
                reply = QMessageBox.question(
                    self,
                    "Confirm Unit Deletion",
                    f"Are you sure you want to delete sales unit '{u['name']}'?\n"
                    "Associated products will fall back to default unit configuration.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    try:
                        success, err = client.delete_unit(u["id"])
                        if success:
                            QMessageBox.information(self, "Success", "Sales unit deleted successfully.")
                            self.load_units()
                            self.load_products()
                        else:
                            QMessageBox.critical(self, "Error", f"Failed to delete unit: {err}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Unexpected error occurred: {str(e)}")

    def open_barcode_printer_dialog(self, initial_products=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("🏷️ Barcode & Label Printer")
        dialog.setMinimumSize(1000, 650)
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(0, 0, 0, 0)
        gen_screen = BarcodeGeneratorScreen(parent=dialog, initial_products=initial_products)
        d_layout.addWidget(gen_screen)
        dialog.exec()


