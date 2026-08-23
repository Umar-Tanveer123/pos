from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox, QDialog,
    QFormLayout, QComboBox, QTextEdit, QDoubleSpinBox
)
from PySide6.QtCore import Qt
from datetime import datetime
from frontend.api_client import client
from frontend.theme import fix_comboboxes

class ExpenseFormDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Expense")
        self.setMinimumWidth(400)
        
        self.setStyleSheet("""
            QDialog { background-color: #121212; color: #ffffff; }
            QLabel { color: #ffffff; }
            QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox { background-color: #2a2a2a; color: white; border: 1px solid #444; padding: 4px; }
            QPushButton { background-color: #0984e3; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #74b9ff; }
        """)
        
        layout = QFormLayout(self)
        
        self.combo_category = QComboBox()
        self.combo_category.addItems(["Rent", "Utilities", "Payroll", "Marketing", "Supplies", "Other"])
        fix_comboboxes(self.combo_category)
        layout.addRow("Category:", self.combo_category)
        
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0.01, 10000000)
        self.spin_amount.setValue(100.0)
        layout.addRow("Amount:", self.spin_amount)
        
        self.combo_payment = QComboBox()
        self.combo_payment.addItems(["Cash", "Bank Transfer", "Card", "Cheque"])
        fix_comboboxes(self.combo_payment)
        layout.addRow("Payment Method:", self.combo_payment)
        
        self.txt_desc = QLineEdit()
        layout.addRow("Description:", self.txt_desc)
        
        self.txt_notes = QTextEdit()
        self.txt_notes.setMaximumHeight(60)
        layout.addRow("Notes:", self.txt_notes)
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #636e72;")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save Expense")
        btn_save.clicked.connect(self.save)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        
        layout.addRow(btn_layout)
        
    def save(self):
        data = {
            "category": self.combo_category.currentText(),
            "amount": self.spin_amount.value(),
            "payment_method": self.combo_payment.currentText(),
            "description": self.txt_desc.text().strip(),
            "notes": self.txt_notes.toPlainText().strip()
        }
        
        success, res = client.create_expense(data)
        if success:
            QMessageBox.information(self, "Success", "Expense recorded.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", f"Failed to save: {res}")


class ExpensesScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #ffffff; }
            QTableWidget { background-color: #1e1e1e; color: white; border: 1px solid #2a2a2a; }
            QHeaderView::section { background-color: #2a2a2a; color: white; padding: 4px; font-weight: bold; border: 1px solid #333; }
        """)
        
        layout = QVBoxLayout(self)
        
        top_bar = QHBoxLayout()
        title = QLabel("🏢 Expenses Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #74b9ff;")
        top_bar.addWidget(title)
        
        top_bar.addStretch()
        
        btn_add = QPushButton("➕ Add Expense")
        btn_add.setStyleSheet("""
            QPushButton { background-color: #0984e3; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #74b9ff; }
        """)
        btn_add.clicked.connect(self.add_expense)
        top_bar.addWidget(btn_add)
        
        layout.addLayout(top_bar)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Date", "Category", "Description", "Method", "Amount (Rs.)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        self.load_data()
        
    def load_data(self):
        expenses = client.get_expenses()
        self.table.setRowCount(len(expenses))
        for row, exp in enumerate(expenses):
            self.table.setItem(row, 0, QTableWidgetItem(exp["internal_id"]))
            
            date_str = exp["date"]
            try:
                dt = datetime.fromisoformat(date_str)
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
                
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            self.table.setItem(row, 2, QTableWidgetItem(exp["category"]))
            self.table.setItem(row, 3, QTableWidgetItem(exp["description"] or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(exp["payment_method"]))
            self.table.setItem(row, 5, QTableWidgetItem(f"{exp['amount']:,.2f}"))
            
    def add_expense(self):
        dlg = ExpenseFormDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()
