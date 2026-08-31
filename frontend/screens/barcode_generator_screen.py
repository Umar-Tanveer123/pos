from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                  QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, 
                                  QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, 
                                  QHeaderView, QGroupBox, QFormLayout, QFrame, 
                                  QScrollArea, QMessageBox, QFileDialog, QSplitter)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage, QPainter, QPdfWriter, QPageSize, QPageLayout
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog

from frontend.api_client import client
from frontend.utils.barcode_generator import render_label_pixmap, render_barcode_pixmap, encode_ean13, calculate_ean13_checksum
from frontend.theme import fix_comboboxes
import random

class BarcodeGeneratorScreen(QWidget):
    def __init__(self, parent=None, initial_products=None):
        super().__init__(parent)
        self.initial_products = initial_products or []
        self.print_queue = [] # list of dicts: {'product': prod_dict, 'qty': int}
        self.setup_ui()
        self.load_catalog()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # ----------------- Top Header Toolbar -----------------
        header = QFrame()
        header.setStyleSheet("QFrame { background-color: #1e1e1e; border-radius: 8px; border: 1px solid #2a2a2a; padding: 6px 12px; }")
        hdr_layout = QHBoxLayout(header)
        
        title_box = QVBoxLayout()
        title_lbl = QLabel("🏷️ Barcode & Label Printing Center")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        sub_lbl = QLabel("Design, preview, batch-generate, and print barcode stickers for thermal roll or sheet printers.")
        sub_lbl.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        hdr_layout.addLayout(title_box)

        hdr_layout.addStretch()

        self.btn_auto_gen = QPushButton("⚡ Auto-Gen Missing Barcodes")
        self.btn_auto_gen.setStyleSheet("background-color: #2a2a2a; color: #00d2d3; border: 1px solid #00d2d3; font-weight: bold;")
        self.btn_auto_gen.setCursor(Qt.PointingHandCursor)
        self.btn_auto_gen.clicked.connect(self.auto_generate_missing_barcodes)
        hdr_layout.addWidget(self.btn_auto_gen)

        self.btn_export_pdf = QPushButton("📄 Export PDF")
        self.btn_export_pdf.setStyleSheet("background-color: #2a2a2a; color: #6c5ce7; border: 1px solid #6c5ce7; font-weight: bold;")
        self.btn_export_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_export_pdf.clicked.connect(self.export_pdf_labels)
        hdr_layout.addWidget(self.btn_export_pdf)

        self.btn_print = QPushButton("🖨️ Print Labels")
        self.btn_print.setStyleSheet("""
            QPushButton {
                background-color: #6c5ce7; color: white; border-radius: 6px; 
                padding: 8px 18px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #5b4bc4; }
        """)
        self.btn_print.setCursor(Qt.PointingHandCursor)
        self.btn_print.clicked.connect(self.print_labels)
        hdr_layout.addWidget(self.btn_print)

        main_layout.addWidget(header)

        # ----------------- Splitter Workspace -----------------
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel 1: Template & Layout Settings
        config_widget = self.build_config_panel()
        splitter.addWidget(config_widget)

        # Panel 2: Product Catalog & Print Queue
        queue_widget = self.build_queue_panel()
        splitter.addWidget(queue_widget)

        # Panel 3: Live Preview
        preview_widget = self.build_preview_panel()
        splitter.addWidget(preview_widget)

        splitter.setSizes([300, 500, 320])
        main_layout.addWidget(splitter, stretch=1)
        fix_comboboxes(self)

    # --------------------------------------------------------------------------
    # PANEL 1: CONFIGURATION & TEMPLATES
    # --------------------------------------------------------------------------
    def build_config_panel(self):
        box = QGroupBox("Label Template Settings")
        box.setStyleSheet("QGroupBox { font-weight: bold; color: #6c5ce7; }")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(10)

        # Preset Sizes
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "50mm x 25mm (Standard Thermal 2\" x 1\")",
            "40mm x 30mm (Compact Sticker)",
            "70mm x 35mm (Large Shelf Tag)",
            "38mm x 25mm (Small Jewelry Roll)",
            "Custom Dimensions"
        ])
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        form.addRow("Preset Size", self.preset_combo)

        # Dimensions
        dim_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(15, 210)
        self.width_spin.setValue(50)
        self.width_spin.setSuffix(" mm")
        self.width_spin.valueChanged.connect(self.update_live_preview)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 297)
        self.height_spin.setValue(25)
        self.height_spin.setSuffix(" mm")
        self.height_spin.valueChanged.connect(self.update_live_preview)

        dim_layout.addWidget(self.width_spin)
        dim_layout.addWidget(QLabel("x"))
        dim_layout.addWidget(self.height_spin)
        form.addRow("Label Dimensions", dim_layout)

        # Barcode Standard
        self.barcode_type_combo = QComboBox()
        self.barcode_type_combo.addItems(["Code-128", "EAN-13"])
        self.barcode_type_combo.currentIndexChanged.connect(self.update_live_preview)
        form.addRow("Barcode Format", self.barcode_type_combo)

        # Store Title Input
        self.store_name_input = QLineEdit("MY SUPERMARKET")
        self.store_name_input.textChanged.connect(self.update_live_preview)
        form.addRow("Store Header", self.store_name_input)

        layout.addLayout(form)

        # Toggles Group
        toggles_group = QGroupBox("Label Content Fields")
        toggles_layout = QVBoxLayout(toggles_group)
        toggles_layout.setSpacing(6)

        self.chk_store = QCheckBox("Show Store Name Header")
        self.chk_store.setChecked(True)
        self.chk_store.toggled.connect(self.update_live_preview)

        self.chk_name = QCheckBox("Show Product Name")
        self.chk_name.setChecked(True)
        self.chk_name.toggled.connect(self.update_live_preview)

        self.chk_price = QCheckBox("Show Price Tag (Rs.)")
        self.chk_price.setChecked(True)
        self.chk_price.toggled.connect(self.update_live_preview)

        self.chk_sku = QCheckBox("Show Item SKU")
        self.chk_sku.setChecked(True)
        self.chk_sku.toggled.connect(self.update_live_preview)

        self.chk_code_text = QCheckBox("Show Barcode Digits Below")
        self.chk_code_text.setChecked(True)
        self.chk_code_text.toggled.connect(self.update_live_preview)

        toggles_layout.addWidget(self.chk_store)
        toggles_layout.addWidget(self.chk_name)
        toggles_layout.addWidget(self.chk_price)
        toggles_layout.addWidget(self.chk_sku)
        toggles_layout.addWidget(self.chk_code_text)

        layout.addWidget(toggles_group)

        # Sheet Grid Settings (For Multi-label A4/Continuous Sheets)
        grid_group = QGroupBox("Sheet Layout Options (A4/Sheet)")
        grid_form = QFormLayout(grid_group)
        
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 10)
        self.cols_spin.setValue(3)
        grid_form.addRow("Columns per Row", self.cols_spin)

        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 50)
        self.margin_spin.setValue(5)
        self.margin_spin.setSuffix(" mm")
        grid_form.addRow("Page Margin", self.margin_spin)

        layout.addWidget(grid_group)
        layout.addStretch()

        return box

    def on_preset_changed(self, idx):
        presets = [
            (50, 25),
            (40, 30),
            (70, 35),
            (38, 25),
            (self.width_spin.value(), self.height_spin.value())
        ]
        if idx < len(presets) - 1:
            w, h = presets[idx]
            self.width_spin.setValue(w)
            self.height_spin.setValue(h)
        self.update_live_preview()

    # --------------------------------------------------------------------------
    # PANEL 2: PRODUCT SEARCH & PRINT QUEUE
    # --------------------------------------------------------------------------
    def build_queue_panel(self):
        box = QGroupBox("Products & Print Queue Selection")
        box.setStyleSheet("QGroupBox { font-weight: bold; color: #6c5ce7; }")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search item by Name, SKU, Barcode...")
        self.search_input.textChanged.connect(self.filter_catalog)
        search_layout.addWidget(self.search_input)

        add_all_btn = QPushButton("+ Add All Items")
        add_all_btn.setStyleSheet("background-color: #2a2a2a; color: white;")
        add_all_btn.clicked.connect(self.add_all_to_queue)
        search_layout.addWidget(add_all_btn)

        layout.addLayout(search_layout)

        # Split Queue panel into Catalog table & Selected Queue table
        v_splitter = QSplitter(Qt.Vertical)

        # Catalog Table
        catalog_widget = QWidget()
        cat_layout = QVBoxLayout(catalog_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.addWidget(QLabel("Catalog Items:"))

        self.catalog_table = QTableWidget()
        self.catalog_table.setColumnCount(5)
        self.catalog_table.setHorizontalHeaderLabels(["Name", "SKU", "Barcode", "Price", "Action"])
        self.catalog_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.catalog_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.catalog_table.verticalHeader().setVisible(False)
        cat_layout.addWidget(self.catalog_table)
        v_splitter.addWidget(catalog_widget)

        # Print Queue Table
        queue_widget = QWidget()
        q_layout = QVBoxLayout(queue_widget)
        q_layout.setContentsMargins(0, 0, 0, 0)
        
        q_header = QHBoxLayout()
        q_header.addWidget(QLabel("Print Queue Items:"))
        q_header.addStretch()

        btn_qty_1 = QPushButton("Qty = 1 All")
        btn_qty_1.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        btn_qty_1.clicked.connect(self.set_all_qty_1)
        q_header.addWidget(btn_qty_1)

        btn_clear = QPushButton("Clear Queue")
        btn_clear.setStyleSheet("font-size: 11px; padding: 2px 6px; background-color: #d63031; color: white;")
        btn_clear.clicked.connect(self.clear_queue)
        q_header.addWidget(btn_clear)

        q_layout.addLayout(q_header)

        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(5)
        self.queue_table.setHorizontalHeaderLabels(["Product Name", "SKU", "Barcode", "Label Copies", "Action"])
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.queue_table.verticalHeader().setVisible(False)
        q_layout.addWidget(self.queue_table)

        v_splitter.addWidget(queue_widget)
        layout.addWidget(v_splitter)

        return box

    # --------------------------------------------------------------------------
    # PANEL 3: LIVE INTERACTIVE PREVIEW
    # --------------------------------------------------------------------------
    def build_preview_panel(self):
        box = QGroupBox("Live Sticker Label Preview")
        box.setStyleSheet("QGroupBox { font-weight: bold; color: #6c5ce7; }")
        layout = QVBoxLayout(box)
        layout.setSpacing(15)

        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setStyleSheet("QScrollArea { border: 1px solid #3a3a3a; background-color: #121212; }")

        self.preview_container = QWidget()
        p_layout = QVBoxLayout(self.preview_container)
        p_layout.setContentsMargins(20, 20, 20, 20)
        p_layout.setAlignment(Qt.AlignCenter)

        self.lbl_preview_pixmap = QLabel()
        self.lbl_preview_pixmap.setStyleSheet("border: 2px dashed #6c5ce7; background-color: white;")
        p_layout.addWidget(self.lbl_preview_pixmap)

        preview_scroll.setWidget(self.preview_container)
        layout.addWidget(preview_scroll)

        # Summary Info Label
        self.lbl_summary = QLabel("Total Queue: 0 Labels")
        self.lbl_summary.setStyleSheet("font-size: 14px; font-weight: bold; color: #00d2d3;")
        self.lbl_summary.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_summary)

        return box

    # --------------------------------------------------------------------------
    # DATA LOADING & CATALOG MANAGEMENT
    # --------------------------------------------------------------------------
    def load_catalog(self):
        try:
            self.products = client.get_products()
        except Exception:
            self.products = []

        self.filter_catalog()

        # Preload initial products if passed via args
        if self.initial_products:
            for p in self.initial_products:
                self.add_to_queue(p)

    def filter_catalog(self):
        search_txt = self.search_input.text().strip().lower()
        self.catalog_table.setRowCount(0)

        filtered = []
        for p in self.products:
            name = (p.get("name") or "").lower()
            sku = (p.get("sku") or "").lower()
            barcode = (p.get("barcode") or p.get("internal_barcode") or "").lower()
            if not search_txt or search_txt in name or search_txt in sku or search_txt in barcode:
                filtered.append(p)

        self.catalog_table.setRowCount(len(filtered))
        for row, p in enumerate(filtered):
            self.catalog_table.setItem(row, 0, QTableWidgetItem(p.get("name", "")))
            self.catalog_table.setItem(row, 1, QTableWidgetItem(p.get("sku") or "N/A"))
            self.catalog_table.setItem(row, 2, QTableWidgetItem(p.get("barcode") or p.get("internal_barcode") or "N/A"))
            self.catalog_table.setItem(row, 3, QTableWidgetItem(f"Rs. {p.get('retail_price', 0):.2f}"))

            add_btn = QPushButton("+ Add")
            add_btn.setStyleSheet("background-color: #6c5ce7; color: white; padding: 2px 8px; font-size: 11px;")
            add_btn.setCursor(Qt.PointingHandCursor)
            add_btn.setProperty("product", p)
            add_btn.clicked.connect(self.on_add_catalog_item)
            self.catalog_table.setCellWidget(row, 4, add_btn)

    def on_add_catalog_item(self):
        btn = self.sender()
        if btn:
            prod = btn.property("product")
            if prod:
                self.add_to_queue(prod)

    def add_to_queue(self, product, qty=1):
        # Check if already in queue
        for item in self.print_queue:
            if item['product']['id'] == product['id']:
                item['qty'] += qty
                self.refresh_queue_table()
                return

        self.print_queue.append({'product': product, 'qty': qty})
        self.refresh_queue_table()

    def add_all_to_queue(self):
        for p in self.products:
            self.add_to_queue(p, qty=1)

    def clear_queue(self):
        self.print_queue.clear()
        self.refresh_queue_table()

    def set_all_qty_1(self):
        for item in self.print_queue:
            item['qty'] = 1
        self.refresh_queue_table()

    def refresh_queue_table(self):
        self.queue_table.setRowCount(0)
        self.queue_table.setRowCount(len(self.print_queue))

        total_copies = 0

        for row, item in enumerate(self.print_queue):
            p = item['product']
            qty = item['qty']
            total_copies += qty

            self.queue_table.setItem(row, 0, QTableWidgetItem(p.get("name", "")))
            self.queue_table.setItem(row, 1, QTableWidgetItem(p.get("sku") or "N/A"))
            self.queue_table.setItem(row, 2, QTableWidgetItem(p.get("barcode") or p.get("internal_barcode") or "N/A"))

            # Qty Spinbox
            spin = QSpinBox()
            spin.setRange(1, 9999)
            spin.setValue(qty)
            spin.setProperty("row_idx", row)
            spin.valueChanged.connect(self.on_queue_qty_changed)
            self.queue_table.setCellWidget(row, 3, spin)

            # Remove button
            rem_btn = QPushButton("✕")
            rem_btn.setStyleSheet("background-color: #ff5252; color: white; padding: 2px 6px;")
            rem_btn.setProperty("row_idx", row)
            rem_btn.clicked.connect(self.on_remove_queue_item)
            self.queue_table.setCellWidget(row, 4, rem_btn)

        self.lbl_summary.setText(f"Total Print Queue: {total_copies} Labels across {len(self.print_queue)} Items")
        self.update_live_preview()

    def on_queue_qty_changed(self, new_val):
        spin = self.sender()
        if spin:
            row_idx = spin.property("row_idx")
            if 0 <= row_idx < len(self.print_queue):
                self.print_queue[row_idx]['qty'] = new_val
                total_copies = sum(it['qty'] for it in self.print_queue)
                self.lbl_summary.setText(f"Total Print Queue: {total_copies} Labels across {len(self.print_queue)} Items")

    def on_remove_queue_item(self):
        btn = self.sender()
        if btn:
            row_idx = btn.property("row_idx")
            if 0 <= row_idx < len(self.print_queue):
                self.print_queue.pop(row_idx)
                self.refresh_queue_table()

    # --------------------------------------------------------------------------
    # LIVE PREVIEW & AUTO-GEN
    # --------------------------------------------------------------------------
    def get_current_config(self):
        return {
            'width_mm': self.width_spin.value(),
            'height_mm': self.height_spin.value(),
            'barcode_type': self.barcode_type_combo.currentText(),
            'show_store_name': self.chk_store.isChecked(),
            'show_product_name': self.chk_name.isChecked(),
            'show_price': self.chk_price.isChecked(),
            'show_sku': self.chk_sku.isChecked(),
            'show_barcode_text': self.chk_code_text.isChecked(),
            'custom_header': self.store_name_input.text().strip() or "MY STORE"
        }

    def update_live_preview(self):
        config = self.get_current_config()
        sample_item = {
            'name': 'Sample Product Name',
            'price': 1250.00,
            'barcode': '200849201948',
            'sku': 'PROD-1001',
            'store_name': config['custom_header']
        }

        if self.print_queue:
            p = self.print_queue[0]['product']
            sample_item = {
                'name': p.get('name'),
                'price': p.get('retail_price', 0.0),
                'barcode': p.get('barcode') or p.get('internal_barcode') or '200849201948',
                'sku': p.get('sku') or 'N/A',
                'store_name': config['custom_header']
            }

        pixmap = render_label_pixmap(sample_item, config)
        self.lbl_preview_pixmap.setPixmap(pixmap)

    def auto_generate_missing_barcodes(self):
        count = 0
        for p in self.products:
            if not p.get("barcode"):
                digits = [2, 0, 0] + [random.randint(0, 9) for _ in range(9)]
                new_bar = calculate_ean13_checksum("".join(map(str, digits)))
                try:
                    success, res = client.update_product(p["id"], {"barcode": new_bar})
                    if success:
                        p["barcode"] = new_bar
                        count += 1
                except Exception:
                    pass

        QMessageBox.information(self, "Auto-Gen Complete", f"Successfully auto-generated EAN-13 barcodes for {count} products!")
        self.load_catalog()

    # --------------------------------------------------------------------------
    # PRINTING & EXPORT ENGINE
    # --------------------------------------------------------------------------
    def print_labels(self):
        if not self.print_queue:
            QMessageBox.warning(self, "Empty Queue", "Please add at least one product to the print queue.")
            return

        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            self.execute_print(printer)

    def export_pdf_labels(self):
        if not self.print_queue:
            QMessageBox.warning(self, "Empty Queue", "Please add at least one product to the print queue.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Barcode Labels PDF", "barcode_labels.pdf", "PDF Files (*.pdf)")
        if not file_path:
            return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)
        self.execute_print(printer)

        QMessageBox.information(self, "PDF Export Complete", f"Barcode labels PDF saved successfully to:\n{file_path}")

    def execute_print(self, printer: QPrinter):
        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(self, "Printing Error", "Could not initialize printer painter engine.")
            return

        config = self.get_current_config()
        label_w_mm = config['width_mm']
        label_h_mm = config['height_mm']
        cols = self.cols_spin.value()
        margin_mm = self.margin_spin.value()

        # DPI resolution conversion
        dpi = printer.resolution()
        mm_to_px = dpi / 25.4

        page_rect = printer.pageRect(QPrinter.Millimeters)
        page_w_px = page_rect.width() * mm_to_px
        page_h_px = page_rect.height() * mm_to_px

        lbl_w_px = label_w_mm * mm_to_px
        lbl_h_px = label_h_mm * mm_to_px
        margin_px = margin_mm * mm_to_px

        col = 0
        cur_x = margin_px
        cur_y = margin_px

        is_first_page = True

        for item in self.print_queue:
            p = item['product']
            qty = item['qty']

            item_data = {
                'name': p.get('name'),
                'price': p.get('retail_price', 0.0),
                'barcode': p.get('barcode') or p.get('internal_barcode') or p.get('sku') or '1000000',
                'sku': p.get('sku') or '',
                'store_name': config['custom_header']
            }

            label_pixmap = render_label_pixmap(item_data, config)

            for _ in range(qty):
                if cur_y + lbl_h_px > page_h_px - margin_px:
                    printer.newPage()
                    cur_x = margin_px
                    cur_y = margin_px
                    col = 0

                painter.drawPixmap(int(cur_x), int(cur_y), int(lbl_w_px), int(lbl_h_px), label_pixmap)

                col += 1
                if col >= cols:
                    col = 0
                    cur_x = margin_px
                    cur_y += lbl_h_px + (2 * mm_to_px)
                else:
                    cur_x += lbl_w_px + (2 * mm_to_px)

        painter.end()
