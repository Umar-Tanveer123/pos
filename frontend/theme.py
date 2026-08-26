import csv
from PySide6.QtWidgets import QFileDialog, QMessageBox

# A modern dark mode theme for the POS system

def export_table_to_csv(table, parent):
    if table.rowCount() == 0:
        QMessageBox.warning(parent, "Export Error", "No data to export.")
        return
        
    path, _ = QFileDialog.getSaveFileName(parent, "Save CSV", "", "CSV Files (*.csv)")
    if path:
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                headers = []
                for col in range(table.columnCount()):
                    header_item = table.horizontalHeaderItem(col)
                    headers.append(header_item.text() if header_item else f"Column {col+1}")
                writer.writerow(headers)
                
                for row in range(table.rowCount()):
                    row_data = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            QMessageBox.information(parent, "Export Successful", f"Data exported to:\n{path}")
        except Exception as e:
            QMessageBox.warning(parent, "Export Error", f"Failed to save file:\n{e}")

GLOBAL_STYLESHEET = """
QWidget {
    background-color: #121212;
    color: #E2E8F0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 12px;
}

QMainWindow {
    background-color: #0B0F19;
}

/* Beautiful Inputs */
QLineEdit {
    background-color: #1A1F2C;
    border: 1px solid #2D3748;
    border-radius: 6px;
    padding: 6px 10px;
    color: #FFFFFF;
    font-size: 12px;
    selection-background-color: #6C5CE7;
}

QLineEdit:focus {
    border: 1.5px solid #6C5CE7;
    background-color: #1F2638;
}

/* Modern Premium Buttons */
QPushButton {
    background-color: #6C5CE7;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 600;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #7D6DF2;
}

QPushButton:pressed {
    background-color: #5849C4;
}

/* Action Buttons inside Tables */
QPushButton#EditAction {
    background-color: #1E293B;
    color: #94A3B8;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
    min-height: 22px;
    min-width: 52px;
    max-width: 64px;
}

QPushButton#EditAction:hover {
    background-color: #6C5CE7;
    border-color: #6C5CE7;
    color: #FFFFFF;
}

QPushButton#DeleteAction {
    background-color: #2D1A1A;
    color: #FCA5A5;
    border: 1px solid #4E2323;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
    min-height: 22px;
    min-width: 52px;
    max-width: 64px;
}

QPushButton#DeleteAction:hover {
    background-color: #EF4444;
    border-color: #EF4444;
    color: #FFFFFF;
}

QPushButton#ViewAction {
    background-color: #064E3B;
    color: #A7F3D0;
    border: 1px solid #047857;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
    min-height: 22px;
    min-width: 52px;
    max-width: 64px;
}

QPushButton#ViewAction:hover {
    background-color: #10B981;
    border-color: #10B981;
    color: #FFFFFF;
}

/* Cards & Groupboxes */
QFrame#Card {
    background-color: #1A1F2C;
    border-radius: 10px;
    border: 1px solid #2D3748;
}

QGroupBox {
    background-color: #151922;
    border: 1px solid #242B35;
    border-radius: 6px;
    margin-top: 10px;
    padding: 12px;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #94A3B8;
    font-size: 11px;
}

QLabel {
    background-color: transparent;
}

QLabel#Title {
    font-size: 18px;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -0.5px;
}

QLabel#ErrorMsg {
    color: #EF4444;
    font-size: 11px;
    font-weight: 600;
}

/* Sidebar Styling */
QFrame#Sidebar {
    background-color: #0F131E;
    border-right: 1px solid #1E293B;
}

QPushButton#SidebarBtn {
    background-color: transparent;
    color: #94A3B8;
    text-align: left;
    padding: 8px 10px;
    font-size: 11px;
    font-weight: 500;
    border-radius: 6px;
    border: none;
    min-width: 0px;
}

QPushButton#SidebarBtn:hover {
    background-color: #1E293B;
    color: #FFFFFF;
}

QPushButton#SidebarBtn:checked {
    background-color: #6C5CE7;
    color: #FFFFFF;
    font-weight: 600;
}

/* Custom Styled Dropdowns (QComboBox) */
QComboBox {
    background-color: #1A1F2C;
    border: 1px solid #2D3748;
    border-radius: 6px;
    padding: 6px 30px 6px 10px;
    color: #FFFFFF;
    min-height: 16px;
    font-size: 12px;
}

QComboBox:hover {
    border-color: #4A5568;
}

QComboBox:focus {
    border: 1.5px solid #6C5CE7;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 26px;
    border: none;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid #94A3B8;
    width: 0;
    height: 0;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1A1F2C;
    border: 1px solid #2D3748;
    border-radius: 6px;
    color: #E2E8F0;
    padding: 4px;
    outline: 0px;
    selection-background-color: #6C5CE7;
}

QComboBox QAbstractItemView::item {
    padding: 7px 10px;
    border-radius: 4px;
    color: #E2E8F0;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #6C5CE7;
    color: #FFFFFF;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #2D3748;
    color: #FFFFFF;
}

/* Modern Tables styling */
QTableWidget {
    background-color: #151922;
    border: 1px solid #242B35;
    gridline-color: #1E293B;
    border-radius: 6px;
    outline: none;
    font-size: 12px;
}

QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #1E293B;
}

QTableWidget::item:selected {
    background-color: #2D3748;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #0F131E;
    color: #94A3B8;
    padding: 7px 8px;
    border: none;
    border-bottom: 1px solid #242B35;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Tabs UI Styling */
QTabWidget::pane {
    border: 1px solid #242B35;
    background-color: #151922;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #0F131E;
    color: #94A3B8;
    padding: 7px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 3px;
    font-weight: 500;
    font-size: 12px;
}

QTabBar::tab:hover {
    background-color: #1A1F2C;
    color: #FFFFFF;
}

QTabBar::tab:selected {
    background-color: #151922;
    color: #FFFFFF;
    border-bottom: 2px solid #6C5CE7;
    font-weight: 600;
}

/* Dialog Styles */
QDialog {
    background-color: #0F131E;
    border: 1px solid #242B35;
}

/* Modern Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #0B0F19;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #2D3748;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4A5568;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Checkboxes */
QCheckBox {
    background-color: transparent;
    color: #94A3B8;
    font-size: 12px;
    spacing: 6px;
}

QCheckBox:hover {
    color: #FFFFFF;
}

QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border-radius: 3px;
    border: 1px solid #2D3748;
    background-color: #1A1F2C;
}

QCheckBox::indicator:hover {
    border-color: #6C5CE7;
}

QCheckBox::indicator:checked {
    background-color: #6C5CE7;
    border-color: #6C5CE7;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiIHdpZHRoPSIxNnB4IiBoZWlnaHQ9IjE2cHgiPjxwYXRoIGQ9Ik0wIDBoMjR2MjRIMHoiIGZpbGw9Im5vbmUiLz48cGF0aCBkPSJNOSAxNi4xN0w0LjgzIDEybC0xLjQyIDEuNDFMOSAxOWwxMiAxMkwxOS41OSA1Ljg1TDkgMTYuMTd6Ii8+PC9zdmc+);
}
"""


def fix_comboboxes(widget):
    """
    Recursively walk every child of `widget` and, for each QComboBox found,
    set the size-adjust policy so the popup is as wide as the longest item.
    Call this once after the main window has been fully built.
    """
    from PySide6.QtWidgets import QComboBox
    for combo in widget.findChildren(QComboBox):
        combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        if combo.view():
            combo.view().setMinimumWidth(320)
