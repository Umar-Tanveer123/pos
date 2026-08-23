from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                                 QLabel, QPushButton, QTableWidget, 
                                 QTableWidgetItem, QHeaderView, QDialog,
                                 QLineEdit, QCheckBox, QFormLayout, QMessageBox)
from PySide6.QtCore import Qt
from frontend.api_client import client

class LocationDialog(QDialog):
    def __init__(self, location_data=None, parent=None):
        super().__init__(parent)
        self.location_data = location_data
        self.setWindowTitle("Edit Location" if location_data else "Add Location")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Edit Location" if self.location_data else "Add New Location")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; margin-bottom: 10px;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Retail Shop")
        form_layout.addRow("Name *", self.name_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("e.g. 123 Main Street")
        form_layout.addRow("Address", self.address_input)

        self.active_cb = QCheckBox("Active Status")
        self.active_cb.setChecked(True)
        form_layout.addRow("", self.active_cb)

        layout.addLayout(form_layout)

        # Prepopulate if editing
        if self.location_data:
            self.name_input.setText(self.location_data.get("name", ""))
            self.address_input.setText(self.location_data.get("address", ""))
            self.active_cb.setChecked(self.location_data.get("is_active", True))

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #333333; color: white;")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.handle_save)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def handle_save(self):
        name = self.name_input.text().strip()
        address = self.address_input.text().strip() or None
        is_active = self.active_cb.isChecked()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Location name is required.")
            return

        if self.location_data:
            # Update existing
            success, res = client.update_location(
                self.location_data["id"], name, address, is_active
            )
        else:
            # Create new
            success, res = client.create_location(name, address, is_active)

        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "API Error", res)


class LocationsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header Row
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("Locations Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        subtitle = QLabel("Configure supermarket outlets, wholesale warehouses, and branches.")
        subtitle.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        self.add_btn = QPushButton("+ Add Location")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.open_add_dialog)
        header_layout.addWidget(self.add_btn)

        layout.addLayout(header_layout)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Address", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 180)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

    def load_locations(self):
        self.table.setRowCount(0)
        locations = client.get_locations()
        self.table.setRowCount(len(locations))

        for row, loc in enumerate(locations):
            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(loc["id"])))
            
            # Name
            self.table.setItem(row, 1, QTableWidgetItem(loc["name"]))
            
            # Address
            addr = loc["address"] or "N/A"
            self.table.setItem(row, 2, QTableWidgetItem(addr))
            
            # Status
            status_str = "Active" if loc["is_active"] else "Inactive"
            status_item = QTableWidgetItem(status_str)
            if loc["is_active"]:
                status_item.setForeground(Qt.green)
            else:
                status_item.setForeground(Qt.red)
            self.table.setItem(row, 3, status_item)
            
            # Actions Panel
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)

            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("EditAction")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setProperty("location", loc)
            edit_btn.clicked.connect(self.on_edit_clicked)
            action_layout.addWidget(edit_btn)

            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("DeleteAction")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setProperty("location", loc)
            delete_btn.clicked.connect(self.on_delete_clicked)
            action_layout.addWidget(delete_btn)
            
            action_widget.setLayout(action_layout)
            self.table.setCellWidget(row, 4, action_widget)

    def on_edit_clicked(self):
        btn = self.sender()
        if btn:
            loc = btn.property("location")
            if loc:
                self.open_edit_dialog(loc)

    def on_delete_clicked(self):
        btn = self.sender()
        if btn:
            loc = btn.property("location")
            if loc:
                reply = QMessageBox.question(
                    self, 
                    "Confirm Delete", 
                    f"Are you sure you want to permanently delete the location '{loc['name']}'?\n"
                    "This will also delete all associated inventory transactions.",
                    QMessageBox.Yes | QMessageBox.No, 
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    try:
                        success, err = client.delete_location(loc["id"])
                        if success:
                            QMessageBox.information(self, "Success", "Location deleted successfully.")
                            self.load_locations()
                        else:
                            QMessageBox.critical(self, "Error", f"Failed to delete location: {err}")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")

    def open_add_dialog(self):
        dialog = LocationDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.load_locations()

    def open_edit_dialog(self, location):
        dialog = LocationDialog(location_data=location, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.load_locations()
