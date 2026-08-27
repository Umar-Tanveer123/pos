from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QMessageBox, QDialog,
    QFormLayout, QTextEdit, QSpinBox, QDoubleSpinBox, QTabWidget, QFrame,
    QGroupBox, QLineEdit, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from frontend.api_client import client
from frontend.theme import fix_comboboxes


RETURN_REASONS = [
    "Damaged / Defective",
    "Wrong Product Delivered",
    "Expired / Near-Expiry",
    "Quality Issue",
    "Overstock / Excess",
    "Other",
]


class ReturnItemRow(QWidget):
    """A single row in the return item builder: product label + qty spinbox."""
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        name_lbl = QLabel(f"{item['product_name']}")
        name_lbl.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        name_lbl.setMinimumWidth(220)
        layout.addWidget(name_lbl)

        unit_str = f" {item.get('unit_name', '')}" if item.get('unit_name') else ""
        max_lbl = QLabel(f"(max {item['returnable_qty']:.0f}{unit_str})")
        max_lbl.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        layout.addWidget(max_lbl)

        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0.0, item["returnable_qty"])
        self.qty_spin.setDecimals(2)
        self.qty_spin.setValue(0.0)
        self.qty_spin.setFixedWidth(100)
        self.qty_spin.setStyleSheet(
            "QDoubleSpinBox { background-color: #1e1e1e; color: white; border: 1px solid #444; "
            "border-radius: 4px; padding: 4px; }"
        )
        layout.addWidget(self.qty_spin)

        price_lbl = QLabel(f"@ Rs.{item['purchase_price']:.2f}")
        price_lbl.setStyleSheet("color: #6c5ce7; font-size: 12px; min-width: 100px;")
        layout.addWidget(price_lbl)
        layout.addStretch()


class CreateReturnDialog(QDialog):
    def __init__(self, parent=None, return_type="RETURN"):
        super().__init__(parent)
        self.return_type = return_type
        title = "Create Supplier Return" if return_type == "RETURN" else "Create Supplier Exchange"
        self.setWindowTitle(title)
        self.setMinimumSize(700, 560)
        self.item_rows: list[ReturnItemRow] = []
        self.setup_ui()
        self.load_purchases()
        fix_comboboxes(self)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header label
        color = "#6c5ce7" if self.return_type == "RETURN" else "#ff9f43"
        header = QLabel(f"{'↩ Return Products to Supplier' if self.return_type == 'RETURN' else '🔄 Exchange Damaged Products'}")
        header.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")
        layout.addWidget(header)

        # Reference purchase
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.purchase_combo = QComboBox()
        self.purchase_combo.currentIndexChanged.connect(self.on_purchase_selected)
        form.addRow("Original Purchase *:", self.purchase_combo)

        self.reason_combo = QComboBox()
        self.reason_combo.addItems(RETURN_REASONS)
        form.addRow("Reason *:", self.reason_combo)

        self.location_combo = QComboBox()
        form.addRow("Return From Location *:", self.location_combo)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional notes…")
        form.addRow("Notes:", self.notes_input)
        layout.addLayout(form)

        # Items area
        items_group = QGroupBox("Select Products & Quantities to Return")
        items_group.setStyleSheet("QGroupBox { color: #a0a0a0; font-weight: bold; border: 1px solid #333; border-radius: 6px; margin-top: 6px; padding-top: 10px; }")
        items_layout = QVBoxLayout(items_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        scroll.setMinimumHeight(160)

        self.items_container = QWidget()
        self.items_inner = QVBoxLayout(self.items_container)
        self.items_inner.setSpacing(4)
        self.items_inner.setContentsMargins(4, 4, 4, 4)

        self.no_items_label = QLabel("← Select a purchase invoice above to load eligible return items.")
        self.no_items_label.setStyleSheet("color: #555; font-style: italic; padding: 10px;")
        self.items_inner.addWidget(self.no_items_label)
        self.items_inner.addStretch()

        scroll.setWidget(self.items_container)
        items_layout.addWidget(scroll)
        layout.addWidget(items_group)

        # Footer
        self.total_lbl = QLabel("Credit Total: Rs. 0.00")
        self.total_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #00b894;")
        layout.addWidget(self.total_lbl)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #2e2e2e; color: white; padding: 8px 20px;")
        cancel_btn.clicked.connect(self.reject)

        label = "Submit Return" if self.return_type == "RETURN" else "Submit Exchange Request"
        submit_btn = QPushButton(label)
        submit_btn.setStyleSheet(
            f"background-color: {'#6c5ce7' if self.return_type == 'RETURN' else '#ff9f43'};"
            "color: white; padding: 8px 24px; font-weight: bold; border-radius: 6px;"
        )
        submit_btn.clicked.connect(self.submit)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(submit_btn)
        layout.addLayout(btn_layout)

    def load_purchases(self):
        purchases = client.get_purchases()
        locations = client.get_locations()

        self.location_combo.clear()
        for loc in locations:
            self.location_combo.addItem(loc["name"], loc["id"])

        self.purchase_combo.clear()
        self.purchase_combo.addItem("-- Select Purchase Invoice --", None)
        suppliers = {s["id"]: s["name"] for s in client.get_suppliers()}
        for p in purchases:
            sup_name = suppliers.get(p["supplier_id"], f"Supplier {p['supplier_id']}")
            self.purchase_combo.addItem(
                f"{p['internal_id']}  —  {sup_name}",
                p["id"]
            )

    def on_purchase_selected(self):
        purchase_id = self.purchase_combo.currentData()
        # Clear existing item rows
        for row in self.item_rows:
            row.setParent(None)
        self.item_rows.clear()

        # Remove stretch
        while self.items_inner.count():
            item = self.items_inner.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        if not purchase_id:
            self.items_inner.addWidget(self.no_items_label)
            self.items_inner.addStretch()
            return

        returnable = client.get_returnable_items(purchase_id)
        if not returnable:
            lbl = QLabel("No returnable items for this purchase (all have been returned).")
            lbl.setStyleSheet("color: #e17055; padding: 10px;")
            self.items_inner.addWidget(lbl)
            self.items_inner.addStretch()
            return

        for item in returnable:
            row = ReturnItemRow(item, self.items_container)
            row.qty_spin.valueChanged.connect(self.update_total)
            self.items_inner.addWidget(row)
            self.item_rows.append(row)
        self.items_inner.addStretch()
        self.update_total()

    def update_total(self):
        total = sum(
            row.qty_spin.value() * row.item["purchase_price"]
            for row in self.item_rows
        )
        self.total_lbl.setText(f"Credit Total: Rs. {total:,.2f}")

    def submit(self):
        purchase_id = self.purchase_combo.currentData()
        location_id = self.location_combo.currentData()
        if not purchase_id:
            QMessageBox.warning(self, "Validation", "Please select a purchase invoice.")
            return
        if not location_id:
            QMessageBox.warning(self, "Validation", "Please select a location.")
            return

        items = [
            {
                "product_id": row.item["product_id"],
                "variant_id": row.item["variant_id"],
                "quantity": row.qty_spin.value(),
            }
            for row in self.item_rows
            if row.qty_spin.value() > 0
        ]
        if not items:
            QMessageBox.warning(self, "Validation", "Please enter a return quantity for at least one product.")
            return

        data = {
            "purchase_id": purchase_id,
            "location_id": location_id,
            "return_type": self.return_type,
            "reason": self.reason_combo.currentText(),
            "notes": self.notes_input.text().strip() or None,
            "items": items,
        }
        success, result = client.create_supplier_return(data)
        if success:
            msg = (
                f"Return {result['internal_id']} created!\n"
                f"Credit: Rs. {result['total_credit']:,.2f}\n"
                f"Stock has been decreased accordingly."
            )
            if self.return_type == "EXCHANGE":
                msg += "\n\nExchange is PENDING. Use 'Complete Exchange' once supplier delivers replacements."
            QMessageBox.information(self, "Success", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", str(result))


class SupplierReturnsScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Supplier Returns & Exchanges")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        ret_btn = QPushButton("↩ New Return")
        ret_btn.setStyleSheet(
            "background-color: #6c5ce7; color: white; padding: 10px 20px; "
            "font-weight: bold; border-radius: 6px; font-size: 13px;"
        )
        ret_btn.clicked.connect(lambda: self.open_create_dialog("RETURN"))
        header_layout.addWidget(ret_btn)

        exc_btn = QPushButton("🔄 New Exchange")
        exc_btn.setStyleSheet(
            "background-color: #ff9f43; color: white; padding: 10px 20px; "
            "font-weight: bold; border-radius: 6px; font-size: 13px;"
        )
        exc_btn.clicked.connect(lambda: self.open_create_dialog("EXCHANGE"))
        header_layout.addWidget(exc_btn)

        main_layout.addLayout(header_layout)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItem("All", None)
        self.type_filter.addItem("Returns Only", "RETURN")
        self.type_filter.addItem("Exchanges Only", "EXCHANGE")
        self.type_filter.currentIndexChanged.connect(self.load_returns)
        filter_layout.addWidget(self.type_filter)
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Return ID", "Type", "Purchase Ref", "Supplier", "Reason", "Credit (Rs.)", "Status", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        main_layout.addWidget(self.table)

        fix_comboboxes(self)

    def load_returns(self):
        return_type = self.type_filter.currentData()
        returns = client.get_supplier_returns(return_type=return_type)
        self.table.setRowCount(len(returns))

        for row, ret in enumerate(returns):
            type_color = "#6c5ce7" if ret["return_type"] == "RETURN" else "#ff9f43"
            status_color = "#00b894" if ret["status"] == "COMPLETED" else \
                           "#00b8a9" if ret["status"] == "EXCHANGED" else "#fdcb6e"

            self.table.setItem(row, 0, QTableWidgetItem(ret["internal_id"]))
            type_item = QTableWidgetItem(ret["return_type"])
            type_item.setForeground(QColor(type_color))
            self.table.setItem(row, 1, type_item)
            self.table.setItem(row, 2, QTableWidgetItem(ret.get("purchase_ref") or "N/A"))
            self.table.setItem(row, 3, QTableWidgetItem(ret.get("supplier_name") or "N/A"))
            self.table.setItem(row, 4, QTableWidgetItem(ret.get("reason") or ""))
            self.table.setItem(row, 5, QTableWidgetItem(f"Rs. {ret['total_credit']:,.2f}"))
            status_item = QTableWidgetItem(ret["status"])
            status_item.setForeground(QColor(status_color))
            self.table.setItem(row, 6, status_item)

            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)

            if ret["return_type"] == "EXCHANGE" and ret["status"] == "PENDING":
                complete_btn = QPushButton("Complete")
                complete_btn.setObjectName("ViewAction")
                complete_btn.setCursor(Qt.PointingHandCursor)
                complete_btn.setProperty("return_id", ret["id"])
                complete_btn.clicked.connect(self.on_complete_exchange)
                action_layout.addWidget(complete_btn)

            action_widget.setLayout(action_layout)
            self.table.setCellWidget(row, 7, action_widget)

    def open_create_dialog(self, return_type: str):
        dialog = CreateReturnDialog(self, return_type=return_type)
        if dialog.exec() == QDialog.Accepted:
            self.load_returns()

    def on_complete_exchange(self):
        btn = self.sender()
        if not btn:
            return
        return_id = btn.property("return_id")
        reply = QMessageBox.question(
            self,
            "Complete Exchange",
            "Mark this exchange as complete? Replacement stock will be added back to inventory.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            success, result = client.complete_exchange(return_id)
            if success:
                QMessageBox.information(self, "Success", "Exchange completed. Replacement stock added.")
                self.load_returns()
            else:
                QMessageBox.critical(self, "Error", str(result))
