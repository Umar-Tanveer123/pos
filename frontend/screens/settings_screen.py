from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QLineEdit, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from frontend.api_client import client
from frontend.theme import export_table_to_csv

class SettingsScreen(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #ffffff; }
            QLineEdit { background-color: #2d2d2d; color: white; border: 1px solid #444; padding: 6px; border-radius: 4px; }
            QTableWidget { background-color: #1e1e1e; color: white; border: 1px solid #2a2a2a; }
            QHeaderView::section { background-color: #2a2a2a; color: white; padding: 4px; font-weight: bold; border: 1px solid #333; }
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("⚙️ Settings, Backups & Audit Trail")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00cec9;")
        layout.addWidget(title)
        
        self.tabs = QTabWidget()
        
        # 1. System Settings Tab
        self.tab_settings = QWidget()
        self.setup_settings_tab(self.tab_settings)
        self.tabs.addTab(self.tab_settings, "System Configurations")
        
        # 2. Backup & Restore Tab
        self.tab_backup = QWidget()
        self.setup_backup_tab(self.tab_backup)
        self.tabs.addTab(self.tab_backup, "Backup & Restore")
        
        # 3. Audit Logs Tab
        self.tab_audit = QWidget()
        self.setup_audit_tab(self.tab_audit)
        self.tabs.addTab(self.tab_audit, "Audit Logs")
        
        layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Initial load
        self.load_settings()
        
    def on_tab_changed(self, index):
        if index == 0:
            self.load_settings()
        elif index == 1:
            self.load_backups()
        elif index == 2:
            self.load_audit_logs()
            
    def load_data(self):
        self.on_tab_changed(self.tabs.currentIndex())

    # --- Settings Tab ---
    def setup_settings_tab(self, parent):
        layout = QVBoxLayout(parent)
        form = QFormLayout()
        
        self.fields = {}
        fields_config = [
            ("business_name", "Business Name"),
            ("business_address", "Address"),
            ("business_phone", "Phone"),
            ("currency", "Currency Symbol"),
            ("prefix_product", "Product ID Prefix"),
            ("prefix_customer", "Customer ID Prefix"),
            ("prefix_supplier", "Supplier ID Prefix"),
            ("prefix_invoice", "Invoice Prefix"),
            ("prefix_purchase", "Purchase Prefix"),
            ("prefix_return", "Customer Return Prefix"),
            ("prefix_supplier_return", "Supplier Return Prefix"),
            ("prefix_transfer", "Transfer Prefix"),
            ("prefix_adjustment", "Adjustment Prefix"),
            ("prefix_customer_pay", "Customer Pay Prefix"),
            ("prefix_supplier_pay", "Supplier Pay Prefix"),
            ("prefix_expense", "Expense Prefix")
        ]
        
        for key, label in fields_config:
            self.fields[key] = QLineEdit()
            form.addRow(QLabel(label + ":"), self.fields[key])
            
        layout.addLayout(form)
        
        btn_save = QPushButton("Save Configurations")
        btn_save.clicked.connect(self.save_settings)
        btn_save.setStyleSheet("background-color: #0984e3; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        layout.addWidget(btn_save)
        layout.addStretch()
        
    def load_settings(self):
        try:
            settings_map = client.get_settings()
            for key, line_edit in self.fields.items():
                if key in settings_map:
                    line_edit.setText(settings_map[key])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load settings: {e}")
            
    def save_settings(self):
        try:
            payload = {key: line_edit.text() for key, line_edit in self.fields.items()}
            client.update_settings(payload)
            QMessageBox.information(self, "Success", "Configurations updated successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update settings: {e}")

    # --- Backup Tab ---
    def setup_backup_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        buttons_layout = QHBoxLayout()
        
        btn_backup = QPushButton("Create Database Backup")
        btn_backup.clicked.connect(self.create_backup)
        btn_backup.setStyleSheet("background-color: #6c5ce7; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        buttons_layout.addWidget(btn_backup)
        
        btn_refresh = QPushButton("Refresh List")
        btn_refresh.clicked.connect(self.load_backups)
        btn_refresh.setStyleSheet("background-color: #2d2d2d; color: white; padding: 8px; border-radius: 4px;")
        buttons_layout.addWidget(btn_refresh)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        layout.addWidget(QLabel("Available Backups:"))
        
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(2)
        self.backup_table.setHorizontalHeaderLabels(["Backup Filename", "Action"])
        self.backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.backup_table)
        
    def load_backups(self):
        try:
            backups = client.list_backups()
            self.backup_table.setRowCount(len(backups))
            for i, filename in enumerate(backups):
                self.backup_table.setItem(i, 0, QTableWidgetItem(filename))
                
                # Restore button for each backup
                btn_restore = QPushButton("Restore")
                btn_restore.setStyleSheet("background-color: #d63031; color: white; max-width: 100px; font-weight: bold;")
                btn_restore.clicked.connect(lambda checked=False, fn=filename: self.restore_backup(fn))
                self.backup_table.setCellWidget(i, 1, btn_restore)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load backups: {e}")
            
    def create_backup(self):
        try:
            res = client.create_backup()
            QMessageBox.information(self, "Success", f"Backup created successfully: {res.get('filename')}")
            self.load_backups()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create backup: {e}")
            
    def restore_backup(self, filename):
        reply = QMessageBox.question(
            self, 'Confirm Restore',
            f"Are you absolutely sure you want to restore from '{filename}'?\nThis will overwrite the current database and reload the POS system state.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                client.restore_backup(filename)
                QMessageBox.information(self, "Success", "Database restored successfully! Please restart the POS system application.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to restore backup: {e}")

    # --- Audit Logs Tab ---
    def setup_audit_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        top = QHBoxLayout()
        btn_refresh = QPushButton("Refresh Logs")
        btn_refresh.clicked.connect(self.load_audit_logs)
        btn_refresh.setStyleSheet("background-color: #2d2d2d; color: white; padding: 6px; border-radius: 4px;")
        top.addWidget(btn_refresh)
        
        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(lambda: export_table_to_csv(self.audit_table, self))
        btn_export.setStyleSheet("background-color: #e17055; color: white; padding: 6px; font-weight: bold; border-radius: 4px;")
        top.addWidget(btn_export)
        top.addStretch()
        layout.addLayout(top)
        
        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(6)
        self.audit_table.setHorizontalHeaderLabels(["Timestamp", "User", "Action", "Record ID", "Location", "Details"])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.audit_table)
        
    def load_audit_logs(self):
        try:
            logs = client.get_audit_logs()
            self.audit_table.setRowCount(len(logs))
            for i, log in enumerate(logs):
                # ISO datetime formatting
                dt = log.get("timestamp", "")
                user = log.get("username") or "System"
                action = log.get("action", "")
                rec_id = log.get("record_id") or "N/A"
                loc = log.get("location_name") or "System"
                details = log.get("details") or ""
                
                self.audit_table.setItem(i, 0, QTableWidgetItem(dt))
                self.audit_table.setItem(i, 1, QTableWidgetItem(user))
                self.audit_table.setItem(i, 2, QTableWidgetItem(action))
                self.audit_table.setItem(i, 3, QTableWidgetItem(rec_id))
                self.audit_table.setItem(i, 4, QTableWidgetItem(loc))
                self.audit_table.setItem(i, 5, QTableWidgetItem(details))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load audit logs: {e}")
