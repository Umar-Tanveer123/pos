from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QMessageBox, QDialog,
    QFormLayout, QLineEdit, QDoubleSpinBox, QTabWidget, QFrame, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from frontend.api_client import client
from frontend.theme import fix_comboboxes


WALK_IN_NAME = "Walk-in Customer"


class CustomerPaymentDialog(QDialog):
    def __init__(self, customer: dict, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle(f"Record Payment — {customer['name']}")
        self.setMinimumWidth(380)
        self._setup_ui()
        fix_comboboxes(self)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        bal_lbl = QLabel(f"Outstanding Balance: Rs. {self.customer['balance']:,.2f}")
        bal_lbl.setStyleSheet("color: #ff7675; font-size: 14px; font-weight: bold;")
        layout.addWidget(bal_lbl)

        form = QFormLayout()
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0.01, max(self.customer["balance"], 0.01) * 100)
        self.amount_input.setValue(max(self.customer["balance"], 0.0))
        self.amount_input.setDecimals(2)
        self.amount_input.setSingleStep(100)
        self.amount_input.setStyleSheet(
            "QDoubleSpinBox { background: #1e1e1e; color: white; border: 1px solid #444; border-radius: 4px; padding: 5px; }"
        )
        form.addRow("Amount (Rs.) *:", self.amount_input)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "Bank Transfer", "Cheque", "Credit Note"])
        form.addRow("Payment Method *:", self.method_combo)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional reference / notes")
        form.addRow("Notes:", self.notes_input)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #2e2e2e; color: white; padding: 8px 16px;")
        cancel_btn.clicked.connect(self.reject)
        submit_btn = QPushButton("Record Payment")
        submit_btn.setStyleSheet(
            "background-color: #00b894; color: white; padding: 8px 20px; font-weight: bold; border-radius: 5px;"
        )
        submit_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(submit_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "amount": self.amount_input.value(),
            "payment_method": self.method_combo.currentText(),
            "notes": self.notes_input.text().strip() or None,
        }


class CustomerStatementDialog(QDialog):
    def __init__(self, customer: dict, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle(f"Statement — {customer['name']} ({customer['internal_id']})")
        self.setMinimumSize(700, 480)
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        info_layout = QHBoxLayout()
        type_name = self.customer.get("customer_type_name") or "—"
        info_layout.addWidget(QLabel(f"<b>{self.customer['name']}</b>  |  {self.customer['internal_id']}  |  Type: {type_name}"))
        info_layout.addStretch()
        bal_color = "#e17055" if self.customer["balance"] > 0 else "#00b894"
        bal_lbl = QLabel(f"Balance: <b style='color:{bal_color}'>Rs. {self.customer['balance']:,.2f}</b>")
        bal_lbl.setTextFormat(Qt.RichText)
        info_layout.addWidget(bal_lbl)
        layout.addLayout(info_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Type", "Reference", "Amount (Rs.)", "Balance After (Rs.)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background-color: #2e2e2e; color: white; padding: 8px 20px;")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _load(self):
        entries = client.get_customer_statement(self.customer["id"])
        self.table.setRowCount(len(entries))
        for row, e in enumerate(entries):
            date_str = e["created_at"][:10] if e.get("created_at") else "—"
            self.table.setItem(row, 0, QTableWidgetItem(date_str))
            self.table.setItem(row, 1, QTableWidgetItem(e["transaction_type"]))
            self.table.setItem(row, 2, QTableWidgetItem(e.get("reference_id") or "—"))
            amount = e["amount"]
            amount_item = QTableWidgetItem(f"Rs. {amount:+,.2f}")
            amount_item.setForeground(QColor("#e17055" if amount > 0 else "#00b894"))
            self.table.setItem(row, 3, amount_item)
            self.table.setItem(row, 4, QTableWidgetItem(f"Rs. {e['balance_after']:,.2f}"))


class CustomerDialog(QDialog):
    def __init__(self, parent=None, customer=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle("Edit Customer" if customer else "Add Customer")
        self.setMinimumWidth(420)
        self._setup_ui()
        self._load_types()
        if customer:
            self._populate()
        fix_comboboxes(self)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Edit Customer" if self.customer else "Add New Customer")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Customer name *")
        form.addRow("Name *:", self.name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("e.g. +92-300-1234567")
        form.addRow("Phone:", self.phone_input)

        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(60)
        self.address_input.setPlaceholderText("Optional address")
        form.addRow("Address:", self.address_input)

        self.type_combo = QComboBox()
        form.addRow("Customer Type:", self.type_combo)

        self.credit_limit_spin = QDoubleSpinBox()
        self.credit_limit_spin.setRange(0, 10_000_000)
        self.credit_limit_spin.setDecimals(2)
        self.credit_limit_spin.setSingleStep(1000)
        self.credit_limit_spin.setPrefix("Rs. ")
        self.credit_limit_spin.setStyleSheet(
            "QDoubleSpinBox { background: #1e1e1e; color: white; border: 1px solid #444; border-radius: 4px; padding: 5px; }"
        )
        form.addRow("Credit Limit:", self.credit_limit_spin)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional notes")
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #2e2e2e; color: white; padding: 8px 16px;")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Customer")
        save_btn.setStyleSheet(
            "background-color: #6c5ce7; color: white; padding: 8px 24px; font-weight: bold; border-radius: 5px;"
        )
        save_btn.clicked.connect(self._save)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _load_types(self):
        self.type_combo.clear()
        self.type_combo.addItem("-- None --", None)
        for t in client.get_customer_types():
            self.type_combo.addItem(t["name"], t["id"])

    def _populate(self):
        c = self.customer
        self.name_input.setText(c.get("name", ""))
        self.phone_input.setText(c.get("phone") or "")
        self.address_input.setPlainText(c.get("address") or "")
        self.notes_input.setText(c.get("notes") or "")
        self.credit_limit_spin.setValue(c.get("credit_limit", 0.0))
        type_id = c.get("customer_type_id")
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == type_id:
                self.type_combo.setCurrentIndex(i)
                break

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Customer name is required.")
            return
        data = {
            "name": name,
            "phone": self.phone_input.text().strip() or None,
            "address": self.address_input.toPlainText().strip() or None,
            "customer_type_id": self.type_combo.currentData(),
            "credit_limit": self.credit_limit_spin.value(),
            "notes": self.notes_input.text().strip() or None,
        }
        if self.customer:
            success, result = client.update_customer(self.customer["id"], data)
        else:
            success, result = client.create_customer(data)

        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Error", str(result))


class CustomersScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # ── Header ──────────────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        title = QLabel("Customer Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        add_btn = QPushButton("+ Add Customer")
        add_btn.setStyleSheet(
            "background-color: #6c5ce7; color: white; padding: 10px 20px; "
            "font-weight: bold; border-radius: 6px; font-size: 13px;"
        )
        add_btn.clicked.connect(self.open_add_customer)
        header_layout.addWidget(add_btn)
        main_layout.addLayout(header_layout)

        # ── Summary Cards ────────────────────────────────────────────────────
        self.cards_layout = QHBoxLayout()
        self.total_card = self._make_card("Total Customers", "0", "#6c5ce7")
        self.balance_card = self._make_card("Total Outstanding", "Rs. 0", "#e17055")
        self.credit_card = self._make_card("Total Credit Limit", "Rs. 0", "#00b894")
        self.cards_layout.addWidget(self.total_card)
        self.cards_layout.addWidget(self.balance_card)
        self.cards_layout.addWidget(self.credit_card)
        main_layout.addLayout(self.cards_layout)

        # ── Filters ─────────────────────────────────────────────────────────
        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, ID or phone…")
        self.search_input.textChanged.connect(self.load_customers)
        self.search_input.setFixedWidth(260)
        filter_layout.addWidget(self.search_input)

        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types", None)
        self.type_filter.currentIndexChanged.connect(self.load_customers)
        filter_layout.addWidget(self.type_filter)
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        # ── Table ────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Phone", "Type", "Credit Limit", "Balance", "Status", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 320)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        main_layout.addWidget(self.table)

        fix_comboboxes(self)

    def _make_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1e1e1e;
                border: 1px solid #2a2a2a;
                border-left: 5px solid {color};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(card)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #a0a0a0; font-size: 13px;")
        v_lbl = QLabel(value)
        v_lbl.setStyleSheet(f"color: white; font-size: 20px; font-weight: bold;")
        v_lbl.setObjectName(f"val_{title.replace(' ', '_')}")
        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        card.val_label = v_lbl
        return card

    def load_data(self):
        self._load_type_filter()
        self.load_customers()

    def _load_type_filter(self):
        self.type_filter.blockSignals(True)
        self.type_filter.clear()
        self.type_filter.addItem("All Types", None)
        for t in client.get_customer_types():
            self.type_filter.addItem(t["name"], t["id"])
        self.type_filter.blockSignals(False)

    def load_customers(self):
        search = self.search_input.text().strip() or None
        type_id = self.type_filter.currentData()
        customers = client.get_customers(search=search, customer_type_id=type_id)

        self.table.setRowCount(len(customers))
        total_balance = 0.0
        total_credit = 0.0

        for row, c in enumerate(customers):
            self.table.setItem(row, 0, QTableWidgetItem(c["internal_id"]))
            self.table.setItem(row, 1, QTableWidgetItem(c["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(c.get("phone") or "—"))
            type_name = c.get("customer_type_name") or "—"
            self.table.setItem(row, 3, QTableWidgetItem(type_name))
            self.table.setItem(row, 4, QTableWidgetItem(f"Rs. {c['credit_limit']:,.2f}"))

            balance = c["balance"]
            bal_item = QTableWidgetItem(f"Rs. {balance:,.2f}")
            bal_item.setForeground(QColor("#e17055" if balance > 0 else "#a0a0a0"))
            self.table.setItem(row, 5, bal_item)

            status = "Active" if c.get("is_active", 1) else "Inactive"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor("#00b894" if status == "Active" else "#a0a0a0"))
            self.table.setItem(row, 6, status_item)

            total_balance += balance
            total_credit += c["credit_limit"]

            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignCenter)

            stmt_btn = QPushButton("Statement")
            stmt_btn.setObjectName("ViewAction")
            stmt_btn.setCursor(Qt.PointingHandCursor)
            stmt_btn.setProperty("customer", c)
            stmt_btn.clicked.connect(self.on_view_statement)
            action_layout.addWidget(stmt_btn)

            pay_btn = QPushButton("Pay")
            pay_btn.setObjectName("EditAction")
            pay_btn.setCursor(Qt.PointingHandCursor)
            pay_btn.setProperty("customer", c)
            pay_btn.clicked.connect(self.on_record_payment)
            action_layout.addWidget(pay_btn)

            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("EditAction")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setProperty("customer", c)
            edit_btn.clicked.connect(self.on_edit_clicked)
            action_layout.addWidget(edit_btn)

            del_btn = QPushButton("Delete")
            del_btn.setObjectName("DeleteAction")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setProperty("customer", c)
            del_btn.clicked.connect(self.on_delete_clicked)
            action_layout.addWidget(del_btn)

            action_widget.setLayout(action_layout)
            self.table.setCellWidget(row, 7, action_widget)

        # Update summary cards
        self.total_card.val_label.setText(str(len(customers)))
        self.balance_card.val_label.setText(f"Rs. {total_balance:,.2f}")
        self.credit_card.val_label.setText(f"Rs. {total_credit:,.2f}")

    def open_add_customer(self):
        dialog = CustomerDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.load_customers()

    def on_edit_clicked(self):
        btn = self.sender()
        if btn:
            c = btn.property("customer")
            if c:
                dialog = CustomerDialog(parent=self, customer=c)
                if dialog.exec() == QDialog.Accepted:
                    self.load_customers()

    def on_view_statement(self):
        btn = self.sender()
        if btn:
            c = btn.property("customer")
            if c:
                dlg = CustomerStatementDialog(customer=c, parent=self)
                dlg.exec()

    def on_record_payment(self):
        btn = self.sender()
        if btn:
            c = btn.property("customer")
            if c:
                if c["balance"] <= 0:
                    QMessageBox.information(self, "No Balance", f"{c['name']} has no outstanding balance.")
                    return
                dlg = CustomerPaymentDialog(customer=c, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    data = dlg.get_data()
                    success, result = client.record_customer_payment(c["id"], data)
                    if success:
                        QMessageBox.information(self, "Success", f"Payment of Rs. {data['amount']:,.2f} recorded.")
                        self.load_customers()
                    else:
                        QMessageBox.critical(self, "Error", str(result))

    def on_delete_clicked(self):
        btn = self.sender()
        if btn:
            c = btn.property("customer")
            if c:
                reply = QMessageBox.question(
                    self, "Delete Customer",
                    f"Delete customer '{c['name']}'? This cannot be undone.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    success, err = client.delete_customer(c["id"])
                    if success:
                        self.load_customers()
                    else:
                        QMessageBox.critical(self, "Error", str(err))
