from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                                 QLabel, QLineEdit, QPushButton, QFrame,
                                 QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect, QCheckBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from frontend.api_client import client

class LoginScreen(QWidget):
    # Signal emitted when login is successful, passing the user data
    login_successful = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # The Login Card
        self.card = QFrame()
        self.card.setObjectName("Card")
        self.card.setFixedSize(360, 420)
        
        # Add a subtle drop shadow to the card
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(12)

        # Title
        title_label = QLabel("Welcome Back")
        title_label.setObjectName("Title")
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)

        subtitle = QLabel("Please sign in to access the POS system")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #a0a0a0; margin-bottom: 20px;")
        card_layout.addWidget(subtitle)

        # Error Message Label (Hidden by default)
        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorMsg")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setVisible(False)
        card_layout.addWidget(self.error_label)

        # Inputs
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        card_layout.addWidget(self.username_input)

        # Password input container with integrated show/hide toggle
        pwd_container = QHBoxLayout()
        pwd_container.setSpacing(0)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
            }
        """)

        self.toggle_pwd_btn = QPushButton("👁️")
        self.toggle_pwd_btn.setToolTip("Show / Hide Password")
        self.toggle_pwd_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_pwd_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
                border-left: none;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                padding: 8px 12px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
            }
        """)
        self.toggle_pwd_btn.clicked.connect(self.toggle_password_visibility)

        pwd_container.addWidget(self.password_input, stretch=1)
        pwd_container.addWidget(self.toggle_pwd_btn)
        card_layout.addLayout(pwd_container)

        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        card_layout.addItem(spacer)

        # Login Button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)
        card_layout.addWidget(self.login_btn)

        main_layout.addWidget(self.card)
        
        # Allow hitting Enter to login
        self.password_input.returnPressed.connect(self.login_btn.click)
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.show_error("Please enter both username and password.")
            return

        self.login_btn.setText("Signing in...")
        self.login_btn.setEnabled(False)
        self.error_label.setVisible(False)

        # Call the API client
        success, error_msg = client.login(username, password)
        
        if success:
            # Fetch user details
            user_data = client.get_me()
            if user_data:
                self.login_successful.emit(user_data)
            else:
                self.show_error("Failed to fetch user profile.")
        else:
            self.show_error(error_msg)

        self.login_btn.setText("Sign In")
        self.login_btn.setEnabled(True)

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_pwd_btn.setText("🙈")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_pwd_btn.setText("👁️")
