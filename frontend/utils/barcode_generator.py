"""
Barcode Generator & Label Renderer Utility Module for POS System.
Provides 100% self-contained Code-128 and EAN-13 encoding and high-fidelity PySide6 QPixmap rendering.
"""
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QBrush, QImage
from PySide6.QtCore import Qt, QRectF, QSize, QPointF
import io

# ==============================================================================
# 1. CODE-128 ENCODER
# ==============================================================================
CODE128_PATTERNS = [
    [2,1,2,2,2,2], [2,2,2,1,2,2], [2,2,2,2,2,1], [1,2,1,2,2,3], [1,2,1,3,2,2],
    [1,3,1,2,2,2], [1,2,2,2,1,3], [1,2,2,3,1,2], [1,3,2,2,1,2], [2,2,1,2,1,3],
    [2,2,1,3,1,2], [2,3,1,2,1,2], [1,1,2,2,3,2], [1,2,2,1,3,2], [1,2,2,2,3,1],
    [1,1,3,2,2,2], [1,2,3,1,2,2], [1,2,3,2,2,1], [2,2,3,2,1,1], [2,2,1,1,3,2],
    [2,2,1,2,3,1], [2,1,3,2,1,2], [2,2,3,1,1,2], [3,1,2,1,3,1], [3,1,1,2,2,2],
    [3,2,1,1,2,2], [3,2,1,2,2,1], [3,1,2,2,1,2], [3,2,2,1,1,2], [3,2,2,2,1,1],
    [2,1,2,1,2,3], [2,1,2,3,2,1], [2,3,2,1,2,1], [1,1,1,3,2,3], [1,3,1,1,2,3],
    [1,3,1,3,2,1], [1,1,2,3,1,3], [1,3,2,1,1,3], [1,3,2,3,1,1], [2,1,1,3,1,3],
    [2,3,1,1,1,3], [2,3,1,3,1,1], [1,1,2,1,3,3], [1,1,2,3,3,1], [1,3,2,1,3,1],
    [1,1,3,1,2,3], [1,1,3,3,2,1], [1,3,3,1,2,1], [3,1,3,1,2,1], [2,1,1,3,3,1],
    [2,3,1,1,3,1], [2,1,3,1,1,3], [2,1,3,3,1,1], [2,1,3,1,3,1], [3,1,1,1,2,3],
    [3,1,1,3,2,1], [3,3,1,1,2,1], [3,1,2,1,1,3], [3,1,2,3,1,1], [3,3,2,1,1,1],
    [3,1,4,1,1,1], [2,2,1,4,1,1], [4,3,1,1,1,1], [1,1,1,2,2,4], [1,1,1,4,2,2],
    [1,2,1,1,2,4], [1,2,1,4,2,1], [1,4,1,1,2,2], [1,4,1,2,2,1], [1,1,2,2,1,4],
    [1,1,2,4,1,2], [1,2,2,1,1,4], [1,2,2,4,1,1], [1,4,2,1,1,2], [1,4,2,2,1,1],
    [2,4,1,2,1,1], [2,2,1,1,1,4], [4,1,3,1,1,1], [2,4,1,1,1,2], [1,3,4,1,1,1],
    [1,1,1,2,4,2], [1,2,1,1,4,2], [1,2,1,2,4,1], [1,1,4,2,1,2], [1,2,4,1,1,2],
    [1,2,4,2,1,1], [4,1,1,2,1,2], [4,2,1,1,1,2], [4,2,1,2,1,1], [2,1,2,1,4,1],
    [2,1,4,1,2,1], [4,1,2,1,2,1], [1,1,1,1,4,3], [1,1,1,3,4,1], [1,3,1,1,4,1],
    [1,1,4,1,1,3], [1,1,4,3,1,1], [4,1,1,1,1,3], [4,1,1,3,1,1], [1,1,3,1,4,1],
    [1,1,4,1,3,1], [3,1,1,1,4,1], [4,1,1,1,3,1], [2,1,1,4,1,2], [2,1,1,2,1,4],
    [2,1,1,2,3,2], [2,3,3,1,1,1,2] # 106: STOP character (7 elements: bar/space/bar/space/bar/space/bar)
]

START_CODE_B = 104
STOP_CODE = 106

def encode_code128(text: str) -> str:
    """
    Encodes an ASCII text string into a binary sequence of '1's (bars) and '0's (spaces) using Code 128 (Subset B).
    """
    if not text:
        text = "000000"

    # Limit to ASCII 32..126
    values = [START_CODE_B]
    for char in text:
        ascii_val = ord(char)
        if 32 <= ascii_val <= 126:
            values.append(ascii_val - 32)
        else:
            values.append(0) # space fallback

    # Checksum calculation: (StartVal + sum(pos * val)) % 103
    checksum = values[0]
    for pos, val in enumerate(values[1:], start=1):
        checksum += pos * val
    checksum %= 103
    values.append(checksum)
    values.append(STOP_CODE)

    # Convert values to bit stream
    bit_stream = []
    for code_idx in values:
        pattern = CODE128_PATTERNS[code_idx]
        is_bar = True
        for width in pattern:
            bit_stream.append(('1' if is_bar else '0') * width)
            is_bar = not is_bar

    return "".join(bit_stream)


# ==============================================================================
# 2. EAN-13 ENCODER
# ==============================================================================
EAN_L_CODES = [
    "0001101", "0011001", "0010011", "0111101", "0100011",
    "0110001", "0101111", "0111011", "0110111", "0001011"
]
EAN_G_CODES = [
    "0100111", "0110011", "0011011", "0100001", "0011101",
    "0111001", "0000101", "0010001", "0001001", "0010111"
]
EAN_R_CODES = [
    "1110010", "1100110", "1101100", "1000010", "1011100",
    "1001110", "1010000", "1000100", "1001000", "1110100"
]
EAN_STRUCTURE = [
    "LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
    "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"
]

def calculate_ean13_checksum(digits_12: str) -> str:
    """Calculates the 13th modulo-10 check digit for a 12-digit string."""
    digits = [int(d) for d in digits_12 if d.isdigit()]
    if len(digits) < 12:
        digits = [0] * (12 - len(digits)) + digits
    digits = digits[:12]
    
    odd_sum = sum(digits[i] for i in range(0, 12, 2))
    even_sum = sum(digits[i] for i in range(1, 12, 2))
    total = odd_sum + (even_sum * 3)
    check_digit = (10 - (total % 10)) % 10
    
    return "".join(map(str, digits)) + str(check_digit)

def encode_ean13(barcode_str: str) -> str:
    """
    Encodes a 12 or 13 digit string into EAN-13 binary bitstream.
    Automatically generates valid check digit if only 12 digits provided.
    """
    digits_only = "".join([c for c in barcode_str if c.isdigit()])
    if len(digits_only) == 12:
        barcode_str = calculate_ean13_checksum(digits_only)
    elif len(barcode_str) != 13:
        # Fallback padding to 13 digits starting with 200
        barcode_str = calculate_ean13_checksum("200" + digits_only.zfill(9)[:9])

    first_digit = int(barcode_str[0])
    left_structure = EAN_STRUCTURE[first_digit]

    bits = []
    # Guard Left: 101
    bits.append("101")

    # Left 6 digits
    for i in range(6):
        digit = int(barcode_str[i + 1])
        code_type = left_structure[i]
        bits.append(EAN_L_CODES[digit] if code_type == "L" else EAN_G_CODES[digit])

    # Guard Center: 01010
    bits.append("01010")

    # Right 6 digits
    for i in range(6):
        digit = int(barcode_str[i + 7])
        bits.append(EAN_R_CODES[digit])

    # Guard Right: 101
    bits.append("101")

    return "".join(bits), barcode_str


# ==============================================================================
# 3. BARCODE & LABEL PREVIEW RENDERER
# ==============================================================================
def render_barcode_pixmap(text: str, barcode_type: str = "Code-128", width: int = 320, height: int = 80, show_text: bool = True) -> QPixmap:
    """
    Renders a crisp vector-style barcode binary pattern into a QPixmap.
    """
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.white)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, False) # Crisp hard edges for barcode lines

    if barcode_type.upper() in ["EAN13", "EAN-13"]:
        bit_stream, display_text = encode_ean13(text)
    else:
        bit_stream = encode_code128(text)
        display_text = text

    quiet_zone_bits = 10
    total_bits = len(bit_stream) + (quiet_zone_bits * 2)
    module_width = width / total_bits
    
    barcode_height = height - 20 if show_text else height

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("black")))

    # Draw Bars
    for i, bit in enumerate(bit_stream):
        if bit == '1':
            x = (i + quiet_zone_bits) * module_width
            painter.drawRect(QRectF(x, 4, module_width + 0.1, barcode_height - 4))

    # Draw Text Below Barcode
    if show_text:
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QColor("#111111"))
        font = QFont("Arial", 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, height - 18, width, 18), Qt.AlignCenter, display_text)

    painter.end()
    return pixmap


def render_label_pixmap(item: dict, config: dict) -> QPixmap:
    """
    Renders a complete barcode product sticker label QPixmap based on user dimensions & toggles.
    
    item = {
        'name': 'Coca-Cola 1.5L',
        'price': 280.00,
        'barcode': '2001234567890',
        'sku': 'COKE-15',
        'store_name': 'SUPERMARKET'
    }
    
    config = {
        'width_mm': 50,
        'height_mm': 25,
        'barcode_type': 'Code-128',
        'show_store_name': True,
        'show_product_name': True,
        'show_price': True,
        'show_sku': True,
        'show_barcode_text': True,
        'custom_header': 'MY STORE'
    }
    """
    # 300 DPI Rendering Scale (~11.8 pixels per mm)
    dpi_scale = 11.811
    w_px = max(180, int(config.get('width_mm', 50) * dpi_scale))
    h_px = max(100, int(config.get('height_mm', 25) * dpi_scale))

    pixmap = QPixmap(w_px, h_px)
    pixmap.fill(Qt.white)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)

    current_y = 6.0
    margin_x = 10.0
    content_width = w_px - (margin_x * 2)

    # 1. Store Header Name
    if config.get('show_store_name', True):
        store_text = config.get('custom_header') or item.get('store_name') or "MY STORE"
        store_text = store_text.upper()
        font_store = QFont("Arial", max(7, int(h_px * 0.05)), QFont.Bold)
        painter.setFont(font_store)
        painter.setPen(QColor("#222222"))
        
        rect_store = QRectF(margin_x, current_y, content_width, 16)
        painter.drawText(rect_store, Qt.AlignCenter | Qt.TextSingleLine, store_text)
        current_y += 18.0

    # 2. Product Name
    if config.get('show_product_name', True):
        prod_name = item.get('name', 'Product Name')
        font_name = QFont("Arial", max(8, int(h_px * 0.065)), QFont.Bold)
        painter.setFont(font_name)
        painter.setPen(QColor("#000000"))
        
        rect_name = QRectF(margin_x, current_y, content_width, 22)
        # Truncate if long name
        metrics = painter.fontMetrics()
        elided_name = metrics.elidedText(prod_name, Qt.ElideRight, int(content_width))
        painter.drawText(rect_name, Qt.AlignCenter | Qt.TextSingleLine, elided_name)
        current_y += 22.0

    # Calculate Barcode Area Height
    remaining_height = h_px - current_y - 8.0
    if config.get('show_price', True):
        remaining_height -= 26.0

    barcode_h = max(35.0, remaining_height)

    # 3. Barcode Graphic
    barcode_type = config.get('barcode_type', 'Code-128')
    barcode_str = item.get('barcode') or item.get('sku') or "1000000000"
    show_code_text = config.get('show_barcode_text', True)

    barcode_pixmap = render_barcode_pixmap(
        text=barcode_str,
        barcode_type=barcode_type,
        width=int(content_width),
        height=int(barcode_h),
        show_text=show_code_text
    )

    painter.drawPixmap(int(margin_x), int(current_y), barcode_pixmap)
    current_y += barcode_h + 4.0

    # 4. Price & SKU Footer
    if config.get('show_price', True) or config.get('show_sku', True):
        footer_rect = QRectF(margin_x, current_y, content_width, 24)
        
        if config.get('show_sku', True) and item.get('sku'):
            sku_text = f"SKU: {item['sku']}"
            font_sku = QFont("Arial", max(7, int(h_px * 0.045)))
            painter.setFont(font_sku)
            painter.setPen(QColor("#444444"))
            painter.drawText(footer_rect, Qt.AlignLeft | Qt.AlignVCenter, sku_text)

        if config.get('show_price', True):
            price_val = float(item.get('price', 0.0))
            price_text = f"Rs. {price_val:,.2f}"
            font_price = QFont("Arial", max(9, int(h_px * 0.075)), QFont.Bold)
            painter.setFont(font_price)
            painter.setPen(QColor("#000000"))
            painter.drawText(footer_rect, Qt.AlignRight | Qt.AlignVCenter, price_text)

    # Outer border guidelines for preview
    painter.setPen(QPen(QColor("#cccccc"), 1, Qt.DashLine))
    painter.setBrush(Qt.NoBrush)
    painter.drawRect(0, 0, w_px - 1, h_px - 1)

    painter.end()
    return pixmap
