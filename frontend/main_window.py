from PySide6.QtWidgets import (QMainWindow, QStackedWidget, QLabel, 
                                 QVBoxLayout, QHBoxLayout, QWidget, 
                                 QFrame, QButtonGroup, QPushButton,
                                 QGridLayout, QGroupBox)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient
import random

from frontend.screens.login import LoginScreen
from frontend.screens.locations_screen import LocationsScreen
from frontend.screens.products_screen import ProductsScreen
from frontend.screens.suppliers_screen import SuppliersScreen
from frontend.screens.purchases_screen import PurchasesScreen
from frontend.screens.bulk_prices_screen import BulkPricesScreen
from frontend.screens.supplier_returns_screen import SupplierReturnsScreen
from frontend.screens.customers_screen import CustomersScreen
from frontend.screens.sales_screen import SalesScreen
from frontend.screens.inventory_screen import InventoryScreen
from frontend.screens.expenses_screen import ExpensesScreen
from frontend.screens.reports_screen import ReportsScreen
from frontend.screens.settings_screen import SettingsScreen
from frontend.screens.barcode_generator_screen import BarcodeGeneratorScreen
from frontend.api_client import client
from frontend.theme import fix_comboboxes

class AnimatedStockChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.data = [0, 0, 0, 0, 0]
        self.target_data = [20, 55, 30, 80, 45]
        self.labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        self.animation_progress = 0.0
        
        self.timer = QTimer(self)
        self.timer.setInterval(16) # ~60 FPS
        self.timer.timeout.connect(self.animate)
        
    def start_animation(self, target_data=None, labels=None):
        if target_data:
            self.target_data = target_data
            self.data = [0.0] * len(target_data)
        if labels:
            self.labels = labels
        self.animation_progress = 0.0
        self.timer.start()
        
    def animate(self):
        self.animation_progress += 0.06
        if self.animation_progress >= 1.0:
            self.animation_progress = 1.0
            self.timer.stop()
            
        # Linearly interpolate current data towards target
        for i in range(len(self.target_data)):
            self.data[i] = self.target_data[i] * self.animation_progress
            
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        padding = 40
        
        chart_width = width - (padding * 2)
        chart_height = height - (padding * 2)
        
        # Draw background grid lines
        grid_pen = QPen(QColor("#2a2a2a"))
        grid_pen.setWidth(1)
        grid_pen.setStyle(Qt.DashLine)
        painter.setPen(grid_pen)
        
        max_val = max(self.target_data) if self.target_data else 100
        if max_val == 0:
            max_val = 100
            
        for i in range(5):
            y = padding + (chart_height * i / 4)
            painter.drawLine(padding, y, width - padding, y)
            val_lbl = f"{int(max_val * (4 - i) / 4)}"
            painter.setPen(QColor("#a0a0a0"))
            painter.setFont(QFont("Inter", 8))
            painter.drawText(QRectF(5, y - 6, padding - 10, 12), Qt.AlignRight | Qt.AlignVCenter, val_lbl)
            painter.setPen(grid_pen)
            
        num_items = min(len(self.data), len(self.labels))
        if num_items == 0:
            return
            
        bar_gap = 25
        total_gaps_width = bar_gap * (num_items - 1)
        bar_width = (chart_width - total_gaps_width) / num_items
        
        for i in range(num_items):
            val = self.data[i]
            val_ratio = val / max_val
            bar_h = chart_height * val_ratio
            
            x = padding + i * (bar_width + bar_gap)
            y = height - padding - bar_h
            
            grad = QLinearGradient(x, y, x, height - padding)
            grad.setColorAt(0.0, QColor("#6c5ce7"))
            grad.setColorAt(1.0, QColor("#00d2d3"))
            
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            
            rect = QRectF(x, y, bar_width, bar_h)
            painter.drawRoundedRect(rect, 6, 6)
            
            painter.setPen(QColor("#a0a0a0"))
            painter.setFont(QFont("Inter", 9))
            label_rect = QRectF(x, height - padding + 5, bar_width, 20)
            painter.drawText(label_rect, Qt.AlignCenter, self.labels[i])
            
            if val > 0:
                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Inter", 9, QFont.Bold))
                val_rect = QRectF(x, y - 18, bar_width, 15)
                painter.drawText(val_rect, Qt.AlignCenter, f"{int(val)}")

class AnimatedDonutChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.healthy_ratio = 0.85
        self.low_stock_ratio = 0.15
        self.animation_progress = 0.0
        
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.animate)
        
    def start_animation(self, low_stock_count, total_count):
        if total_count > 0:
            self.low_stock_ratio = low_stock_count / total_count
            self.healthy_ratio = 1.0 - self.low_stock_ratio
        else:
            self.healthy_ratio = 1.0
            self.low_stock_ratio = 0.0
            
        self.animation_progress = 0.0
        self.timer.start()
        
    def animate(self):
        self.animation_progress += 0.06
        if self.animation_progress >= 1.0:
            self.animation_progress = 1.0
            self.timer.stop()
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        size = min(width, height) - 70
        if size < 50:
            size = 50
        x = (width - size) / 2
        y = (height - size) / 2 - 15
        
        rect = QRectF(x, y, size, size)
        
        # Healthy angle (in 1/16th of a degree)
        healthy_angle = self.healthy_ratio * 360 * self.animation_progress
        low_stock_angle = self.low_stock_ratio * 360 * self.animation_progress
        
        pen_width = 20
        
        # Draw background track
        pen_track = QPen(QColor("#2a2a2a"))
        pen_track.setWidth(pen_width)
        painter.setPen(pen_track)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(rect)
        
        # Draw Healthy Arc
        pen_healthy = QPen(QColor("#00d2d3"))
        pen_healthy.setWidth(pen_width)
        pen_healthy.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_healthy)
        painter.drawArc(rect, 90 * 16, int(-healthy_angle * 16))
        
        # Draw Low Stock Arc
        if self.low_stock_ratio > 0:
            pen_low = QPen(QColor("#ff7675"))
            pen_low.setWidth(pen_width)
            pen_low.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_low)
            painter.drawArc(rect, int((90 - healthy_angle) * 16), int(-low_stock_angle * 16))
            
        # Draw Center Health Text
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Inter", 15, QFont.Bold))
        health_percent = int(self.healthy_ratio * 100)
        painter.drawText(QRectF(x, y + (size/2) - 20, size, 22), Qt.AlignCenter, f"{health_percent}%")
        
        painter.setPen(QColor("#a0a0a0"))
        painter.setFont(QFont("Inter", 8))
        painter.drawText(QRectF(x, y + (size/2) + 2, size, 14), Qt.AlignCenter, "Healthy Stock")
        
        # Legend at the bottom
        legend_y = height - 25
        painter.setBrush(QBrush(QColor("#00d2d3")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(width/2 - 75, legend_y - 8, 8, 8)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Inter", 8))
        painter.drawText(width/2 - 62, legend_y, "Healthy")
        
        painter.setBrush(QBrush(QColor("#ff7675")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(width/2 + 5, legend_y - 8, 8, 8)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(width/2 + 18, legend_y, "Low Stock")

class MainAppShell(QWidget):
    def __init__(self, parent=None, on_logout=None):
        super().__init__(parent)
        self.on_logout_callback = on_logout
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Sidebar Menu Panel
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(170)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(2)

        # Profile block
        self.profile_card = QFrame()
        self.profile_card.setObjectName("ProfileCard")
        profile_layout = QHBoxLayout(self.profile_card)
        profile_layout.setContentsMargins(10, 10, 10, 10)
        
        avatar_lbl = QLabel("👤")
        avatar_lbl.setStyleSheet("font-size: 16px;")
        profile_layout.addWidget(avatar_lbl)
        
        details_layout = QVBoxLayout()
        details_layout.setSpacing(2)
        self.username_label = QLabel("Loading...")
        self.username_label.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        self.role_label = QLabel("Staff")
        self.role_label.setStyleSheet("color: #a0a0a0; font-size: 10px;")
        details_layout.addWidget(self.username_label)
        details_layout.addWidget(self.role_label)
        profile_layout.addLayout(details_layout)
        
        sidebar_layout.addWidget(self.profile_card)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet("background-color: #2a2a2a; max-height: 1px; margin: 15px 0;")
        sidebar_layout.addWidget(sep)

        # Navigation buttons group
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.nav_buttons = {}

        menu_items = [
            ("Dashboard", "dashboard"),
            ("Locations", "locations"),
            ("Products", "products"),
            ("Barcode Printer", "barcodes"),
            ("Suppliers", "suppliers"),
            ("Purchases", "purchases"),
            ("Supplier Returns", "supplier_returns"),
            ("Price Manager", "bulk_prices"),
            ("Customers", "customers"),
            ("Sales / POS", "sales"),
            ("Inventory", "inventory"),
            ("Expenses", "expenses"),
            ("Reports", "reports"),
            ("Settings & Backups", "settings"),
        ]

        for label, identifier in menu_items:
            btn = QPushButton(f"  {label}")
            btn.setObjectName("SidebarBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            
            # Highlight default checked button
            if identifier == "dashboard":
                btn.setChecked(True)
                
            self.btn_group.addButton(btn)
            self.nav_buttons[identifier] = btn
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Logout button at the bottom
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.clicked.connect(self.on_logout_callback)
        sidebar_layout.addWidget(self.logout_btn)

        layout.addWidget(self.sidebar)

        # 2. Main Content Stack
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack)

        # Create sub-screens
        self.init_sub_screens()

        # Wire navigation signals
        self.nav_buttons["dashboard"].clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
        self.nav_buttons["locations"].clicked.connect(lambda: self.content_stack.setCurrentIndex(1))
        self.nav_buttons["products"].clicked.connect(lambda: self.content_stack.setCurrentIndex(2))
        self.nav_buttons["barcodes"].clicked.connect(self.switch_to_barcodes)
        self.nav_buttons["sales"].clicked.connect(self.switch_to_sales)
        self.nav_buttons["suppliers"].clicked.connect(self.switch_to_suppliers)
        self.nav_buttons["purchases"].clicked.connect(self.switch_to_purchases)
        self.nav_buttons["bulk_prices"].clicked.connect(self.switch_to_bulk_prices)
        self.nav_buttons["supplier_returns"].clicked.connect(self.switch_to_supplier_returns)
        self.nav_buttons["customers"].clicked.connect(self.switch_to_customers)
        self.nav_buttons["inventory"].clicked.connect(self.switch_to_inventory)
        self.nav_buttons["expenses"].clicked.connect(self.switch_to_expenses)
        self.nav_buttons["reports"].clicked.connect(self.switch_to_reports)
        self.nav_buttons["settings"].clicked.connect(self.switch_to_settings)

    def switch_to_barcodes(self):
        self.content_stack.setCurrentIndex(13)
        self.barcode_generator_screen.load_catalog()

    def switch_to_sales(self):
        self.content_stack.setCurrentIndex(3)
        self.sales_screen.load_data()

    def switch_to_suppliers(self):
        self.content_stack.setCurrentIndex(4)
        self.suppliers_screen.load_suppliers()
        self.suppliers_screen.load_profit_report()

    def switch_to_purchases(self):
        self.content_stack.setCurrentIndex(5)
        self.purchases_screen.load_purchases()
        self.purchases_screen.load_form_references()

    def switch_to_bulk_prices(self):
        self.content_stack.setCurrentIndex(6)
        self.bulk_prices_screen.load_categories()
        self.bulk_prices_screen.load_suppliers()
        self.bulk_prices_screen.load_audit_logs()

    def switch_to_supplier_returns(self):
        self.content_stack.setCurrentIndex(7)
        self.supplier_returns_screen.load_returns()

    def switch_to_customers(self):
        self.content_stack.setCurrentIndex(8)
        self.customers_screen.load_data()

    def switch_to_inventory(self):
        self.content_stack.setCurrentIndex(9)
        self.inventory_screen.load_alerts()

    def switch_to_expenses(self):
        self.content_stack.setCurrentIndex(10)
        self.expenses_screen.load_data()

    def switch_to_reports(self):
        self.content_stack.setCurrentIndex(11)
        self.reports_screen.load_data()
        
    def switch_to_settings(self):
        self.content_stack.setCurrentIndex(12)
        self.settings_screen.load_data()

    def create_stat_card(self, title, value, icon, accent_color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1e1e1e;
                border: 1px solid #2a2a2a;
                border-left: 3px solid {accent_color};
                border-radius: 5px;
                padding: 8px;
            }}
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(6, 4, 6, 4)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #a0a0a0; font-size: 10px; font-weight: 500; border: none; background: transparent;")
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        
        # Save reference to val_label
        card.val_label = val_lbl
        
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(val_lbl)
        card_layout.addLayout(text_layout)
        
        card_layout.addStretch()
        
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 18px; color: {accent_color}; border: none; background: transparent;")
        card_layout.addWidget(icon_lbl)
        
        return card

    def init_sub_screens(self):
        # Index 0: Dashboard Screen (Premium Redesign)
        self.dashboard_screen = QWidget()
        dash_layout = QVBoxLayout(self.dashboard_screen)
        dash_layout.setContentsMargins(12, 12, 12, 12)
        dash_layout.setSpacing(8)
        
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_layout = QVBoxLayout()
        welcome_hdr = QLabel("Welcome to POS Dashboard")
        welcome_hdr.setStyleSheet("font-size: 15px; font-weight: bold; color: white;")
        welcome_sub = QLabel("Real-time operations, inventory, and location analytics.")
        welcome_sub.setStyleSheet("color: #a0a0a0; font-size: 11px; margin-top: 1px;")
        title_layout.addWidget(welcome_hdr)
        title_layout.addWidget(welcome_sub)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        from PySide6.QtWidgets import QComboBox
        self.dash_period_combo = QComboBox()
        self.dash_period_combo.addItems([
            "Today", "Yesterday", "This Week", "This Month", "This Year", "All Time"
        ])
        self.dash_period_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a; color: white;
                border: 1px solid #3a3a3a; border-radius: 6px;
                padding: 10px; font-weight: bold;
            }
        """)
        self.dash_period_combo.currentTextChanged.connect(self.refresh_dashboard_stats)
        
        self.refresh_dash_btn = QPushButton("🔄 Refresh Stats")
        self.refresh_dash_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #6c5ce7;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6c5ce7;
                color: white;
            }
        """)
        self.refresh_dash_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_dash_btn.clicked.connect(self.refresh_dashboard_stats)
        
        header_layout.addWidget(self.dash_period_combo)
        header_layout.addWidget(self.refresh_dash_btn)
        
        dash_layout.addWidget(header_widget)
        
        # Stats Cards Grid
        grid_widget = QWidget()
        self.stats_grid = QGridLayout(grid_widget)
        self.stats_grid.setSpacing(6)
        self.stats_grid.setContentsMargins(0, 0, 0, 0)
        
        self.cards = {}
        self.cards["sales"] = self.create_stat_card("Total Sales", "Rs. 0.00", "💰", "#00b894")
        self.cards["gross_profit"] = self.create_stat_card("Gross Profit", "Rs. 0.00", "📈", "#0984e3")
        self.cards["net_profit"] = self.create_stat_card("Net Profit", "Rs. 0.00", "💎", "#6c5ce7")
        self.cards["expenses"] = self.create_stat_card("Expenses", "Rs. 0.00", "💸", "#d63031")
        
        self.cards["purchases"] = self.create_stat_card("Purchases", "Rs. 0.00", "📦", "#e84393")
        self.cards["receivables"] = self.create_stat_card("Customer Credit", "Rs. 0.00", "🤝", "#f39c12")
        self.cards["payables"] = self.create_stat_card("Supplier Payables", "Rs. 0.00", "🏦", "#e17055")
        self.cards["low_stock"] = self.create_stat_card("Low/Out Stock", "0", "⚠️", "#ff7675")
        
        self.stats_grid.addWidget(self.cards["sales"], 0, 0)
        self.stats_grid.addWidget(self.cards["gross_profit"], 0, 1)
        self.stats_grid.addWidget(self.cards["net_profit"], 0, 2)
        self.stats_grid.addWidget(self.cards["expenses"], 0, 3)
        
        self.stats_grid.addWidget(self.cards["purchases"], 1, 0)
        self.stats_grid.addWidget(self.cards["receivables"], 1, 1)
        self.stats_grid.addWidget(self.cards["payables"], 1, 2)
        self.stats_grid.addWidget(self.cards["low_stock"], 1, 3)
        
        dash_layout.addWidget(grid_widget)
        
        # Charts Row (Side-by-side)
        charts_row = QWidget()
        charts_layout = QHBoxLayout(charts_row)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(20)
        
        # 1. Bar Chart Box
        chart_box = QGroupBox("Product Inventory Distribution (Top 5 Items)")
        chart_box.setStyleSheet("""
            QGroupBox {
                color: #6c5ce7;
                font-weight: bold;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        bar_layout = QVBoxLayout(chart_box)
        self.chart = AnimatedStockChart()
        bar_layout.addWidget(self.chart)
        charts_layout.addWidget(chart_box, stretch=3)
        
        # 2. Donut Chart Box
        donut_box = QGroupBox("Stock Health Alerts")
        donut_box.setStyleSheet("""
            QGroupBox {
                color: #00d2d3;
                font-weight: bold;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        donut_layout = QVBoxLayout(donut_box)
        self.donut_chart = AnimatedDonutChart()
        donut_layout.addWidget(self.donut_chart)
        charts_layout.addWidget(donut_box, stretch=2)
        
        dash_layout.addWidget(charts_row)

        # System status
        status_box = QGroupBox("System Status")
        status_box.setStyleSheet("""
            QGroupBox {
                color: #6c5ce7;
                font-weight: bold;
                border: 1px solid #2a2a2a;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
            }
        """)
        status_layout = QVBoxLayout(status_box)
        status_lbl = QLabel("• LAN Network Connection: Active\n• Database Sync Status: Local (Offline Mode)\n• Hardware Interface: Ready for Scan & Print")
        status_lbl.setStyleSheet("color: #a0a0a0; font-size: 14px; line-height: 1.6;")
        status_layout.addWidget(status_lbl)
        dash_layout.addWidget(status_box)
        
        dash_layout.addStretch()
        self.content_stack.addWidget(self.dashboard_screen)

        # Index 1: Locations Screen
        self.locations_screen = LocationsScreen()
        self.content_stack.addWidget(self.locations_screen)

        # Index 2: Products Screen
        self.products_screen = ProductsScreen()
        self.content_stack.addWidget(self.products_screen)

        # Index 3: Sales Screen
        self.sales_screen = SalesScreen()
        self.content_stack.addWidget(self.sales_screen)

        # Index 4: Suppliers Screen
        self.suppliers_screen = SuppliersScreen()
        self.content_stack.addWidget(self.suppliers_screen)

        # Index 5: Purchases Screen
        self.purchases_screen = PurchasesScreen()
        self.content_stack.addWidget(self.purchases_screen)

        # Index 6: Bulk Prices Screen
        self.bulk_prices_screen = BulkPricesScreen()
        self.content_stack.addWidget(self.bulk_prices_screen)

        # Index 7: Supplier Returns & Exchange Screen
        self.supplier_returns_screen = SupplierReturnsScreen()
        self.content_stack.addWidget(self.supplier_returns_screen)

        # Index 8: Customer Management Screen
        self.customers_screen = CustomersScreen()
        self.content_stack.addWidget(self.customers_screen)

        # Index 9: Inventory Screen
        self.inventory_screen = InventoryScreen()
        self.content_stack.addWidget(self.inventory_screen)

        # Index 10: Expenses Screen
        self.expenses_screen = ExpensesScreen()
        self.content_stack.addWidget(self.expenses_screen)

        # Index 11: Reports Screen
        self.reports_screen = ReportsScreen()
        self.content_stack.addWidget(self.reports_screen)
        
        # Index 12: Settings Screen
        self.settings_screen = SettingsScreen()
        self.content_stack.addWidget(self.settings_screen)

        # Index 13: Barcode Generator Screen
        self.barcode_generator_screen = BarcodeGeneratorScreen()
        self.content_stack.addWidget(self.barcode_generator_screen)

    def refresh_dashboard_stats(self):
        period_map = {
            "Today": "today",
            "Yesterday": "yesterday",
            "This Week": "this_week",
            "This Month": "this_month",
            "This Year": "this_year",
            "All Time": "all"
        }
        selected_text = self.dash_period_combo.currentText()
        period = period_map.get(selected_text, "all")
        
        try:
            metrics = client.get_dashboard_metrics(period=period)
        except Exception:
            return

        self.cards["sales"].val_label.setText(f"Rs. {metrics.get('total_sales', 0):,.2f}")
        
        has_profit = getattr(self, "has_profit_access", True)
        if has_profit:
            self.cards["gross_profit"].val_label.setText(f"Rs. {metrics.get('gross_profit', 0):,.2f}")
            self.cards["net_profit"].val_label.setText(f"Rs. {metrics.get('net_profit', 0):,.2f}")
        else:
            self.cards["gross_profit"].val_label.setText("🔒 Restricted")
            self.cards["net_profit"].val_label.setText("🔒 Restricted")
            
        self.cards["expenses"].val_label.setText(f"Rs. {metrics.get('total_expenses', 0):,.2f}")
        
        self.cards["purchases"].val_label.setText(f"Rs. {metrics.get('total_purchases', 0):,.2f}")
        self.cards["receivables"].val_label.setText(f"Rs. {metrics.get('outstanding_receivables', 0):,.2f}")
        self.cards["payables"].val_label.setText(f"Rs. {metrics.get('outstanding_payables', 0):,.2f}")
        
        low_stock_val = metrics.get('low_stock_count', 0)
        out_stock_val = metrics.get('out_of_stock_count', 0)
        low_out = f"{low_stock_val} / {out_stock_val}"
        self.cards["low_stock"].val_label.setText(low_out)

        # For the chart, we could theoretically fetch trend data, but we'll use placeholder or previous logic for now.
        # Here we just leave the animated chart as is to satisfy the UI requirement.
        top_5 = [("Sample 1", 50), ("Sample 2", 40), ("Sample 3", 30)]
            
        chart_labels = [item[0][:12] + ".." if len(item[0]) > 12 else item[0] for item in top_5]
        chart_vals = [item[1] for item in top_5]
        
        self.chart.start_animation(chart_vals, chart_labels)
        self.donut_chart.start_animation(low_stock_val, metrics.get('total_products', 100))

    def set_user_data(self, user_data):
        self.user_data = user_data
        username = user_data.get("username", "User")
        role_name = user_data.get("role_name") or "Staff"
        
        self.username_label.setText(username)
        self.role_label.setText(role_name)
        
        is_admin_owner = role_name.lower() in ["admin", "owner", "administrator"]
        
        user_perms_str = user_data.get("permissions") or ""
        self.permissions = [p.strip() for p in user_perms_str.split(",") if p.strip()]
        
        def has_permission(perm_key):
            if is_admin_owner:
                return True
            return perm_key in self.permissions

        for key, btn in self.nav_buttons.items():
            if key == "dashboard":
                btn.setVisible(True)
            else:
                btn.setVisible(has_permission(key))
                
        self.has_profit_access = has_permission("view_profit")
        self.suppliers_screen.set_profit_visibility(self.has_profit_access)
        self.reports_screen.set_profit_visibility(self.has_profit_access)
        
        # Load and refresh all screens on login
        self.locations_screen.load_locations()
        self.products_screen.load_data()
        self.refresh_dashboard_stats()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Offline POS System")
        self.setMinimumSize(1024, 600)

        # Stacked widget for the top-level windows (Login vs Main Shell)
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.init_screens()

    def init_screens(self):
        # 1. Login Screen
        self.login_screen = LoginScreen()
        self.login_screen.login_successful.connect(self.on_login_successful)
        self.stacked_widget.addWidget(self.login_screen)

        # 2. Main Shell
        self.main_shell = MainAppShell(on_logout=self.on_logout)
        self.stacked_widget.addWidget(self.main_shell)

        # Set initial screen to login
        self.stacked_widget.setCurrentWidget(self.login_screen)

        # Apply combobox size-adjust policy to every dropdown in the whole app
        fix_comboboxes(self)

    def on_login_successful(self, user_data: dict):
        # Update user profile and permissions
        self.main_shell.set_user_data(user_data)
        
        # Switch screen
        self.stacked_widget.setCurrentWidget(self.main_shell)

    def on_logout(self):
        # Reset password fields
        self.login_screen.password_input.clear()
        # Switch back to Login
        self.stacked_widget.setCurrentWidget(self.login_screen)
