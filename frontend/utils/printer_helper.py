import sys
import subprocess
from datetime import datetime
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo, QPrintDialog
from PySide6.QtGui import QTextDocument, QPageLayout, QPageSize
from PySide6.QtCore import QSizeF, QMarginsF

def get_available_printers():
    """Return list of printer names registered on the system."""
    try:
        return [p.printerName() for p in QPrinterInfo.availablePrinters()]
    except Exception:
        return []

def get_default_printer_name():
    """Return the default system printer name."""
    try:
        return QPrinterInfo.defaultPrinterName()
    except Exception:
        return ""

def generate_receipt_html(sale: dict, template: dict = None, settings: dict = None, paper_width_mm: int = 80) -> str:
    """
    Generates high-fidelity responsive HTML matching thermal receipt standard (Image 2 style).
    Automatically adjusts text sizing, table layout, borders, and margins based on paper width.
    """
    if not template:
        template = {}
    if not settings:
        settings = {}

    biz_name = template.get("business_name") or settings.get("business_name") or "MIAN KHALID SUPERSTORE"
    biz_address = template.get("business_address") or settings.get("business_address") or "Basement Mian Khalid Super Store Chnda Qila Main GT road Gujranwala"
    biz_phone = template.get("business_phone") or settings.get("business_phone") or "0317-6421883, 0300-6421883"
    header_text = template.get("header_text") or "Bill / Invoice"
    footer_text = template.get("footer_text") or "Software By: gmtechnologies.pk 03007282865"

    logo_data = settings.get("receipt_logo_data") or settings.get("receipt_logo_path")
    show_logo = template.get("show_logo", True)
    show_customer_info = template.get("show_customer_info", True)
    show_payment_info = template.get("show_payment_info", True)
    show_disc_col = template.get("show_discount_column", True)
    show_sku = template.get("show_sku", False)
    show_notes = template.get("show_notes", True)

    # Date formatting
    sale_date = sale.get("date", "")
    try:
        dt = datetime.fromisoformat(str(sale_date).replace("Z", "+00:00"))
        formatted_date = dt.strftime("%d-%m-%y %H:%M:%S")
    except Exception:
        formatted_date = str(sale_date)

    # Customer Name
    cust_name = sale.get("customer_name") or "Cash"

    # Salesman / Cashier Name
    salesman_name = sale.get("salesman_name") or sale.get("user_name") or "Waleed"

    # Pay Type
    payments = sale.get("payments", [])
    if payments and len(payments) > 0:
        pay_type = ", ".join(p.get("payment_method", "Cash") for p in payments)
    else:
        pay_type = "Cash"

    # Font sizing & spacing based on paper size
    if paper_width_mm == 58:
        base_font_pt = "8.5pt"
        title_font_pt = "12pt"
        rec_font_pt = "9.5pt"
        meta_font_pt = "8pt"
    elif paper_width_mm == 210:
        base_font_pt = "11pt"
        title_font_pt = "16pt"
        rec_font_pt = "12pt"
        meta_font_pt = "10.5pt"
    else:
        # 80mm default
        base_font_pt = "9.5pt"
        title_font_pt = "14pt"
        rec_font_pt = "10.5pt"
        meta_font_pt = "9pt"

    # Split store name for Arch badge if multi-word
    words = biz_name.strip().split()
    if len(words) > 1:
        arch_top = " ".join(words[:-1])
        arch_sub = words[-1]
    else:
        arch_top = biz_name
        arch_sub = ""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{ margin: 0; }}
    * {{ box-sizing: border-box; }}
    body {{
        font-family: Arial, 'Segoe UI', Helvetica, sans-serif;
        font-size: {base_font_pt};
        margin: 0 auto;
        padding: 4px;
        color: #000000;
        line-height: 1.25;
        width: 100%;
    }}
    .center {{ text-align: center; }}
    .logo-arch {{
        border: 2px solid #000000;
        border-radius: 50% 50% 0 0 / 100% 100% 0 0;
        padding: 10px 6px 4px 6px;
        margin: 0 auto 4px auto;
        width: 86%;
        text-align: center;
    }}
    .arch-title {{
        font-size: {title_font_pt};
        font-weight: 900;
        letter-spacing: 1px;
        text-transform: uppercase;
        line-height: 1.1;
    }}
    .tagline {{
        font-style: italic;
        font-size: 8.5pt;
        text-align: center;
        margin-bottom: 4px;
        font-family: Georgia, 'Times New Roman', serif;
    }}
    .store-info {{
        font-size: 8.5pt;
        text-align: center;
        line-height: 1.25;
        margin-bottom: 6px;
    }}
    .box-header {{
        border: 1px solid #000000;
        text-align: center;
        font-weight: bold;
        font-size: 11pt;
        padding: 3px 0;
        margin: 6px 0;
        letter-spacing: 0.5px;
    }}
    .meta-table {{
        width: 100%;
        table-layout: fixed;
        border-collapse: collapse;
        margin-bottom: 6px;
        font-size: {meta_font_pt};
    }}
    .meta-table td {{
        padding: 1px 0;
        vertical-align: top;
    }}
    .items-table {{
        width: 100%;
        table-layout: fixed;
        border-collapse: collapse;
        margin-bottom: 6px;
        font-size: {meta_font_pt};
        border: 1px solid #000000;
    }}
    .items-table th, .items-table td {{
        border: 1px solid #000000;
        padding: 3px 2px;
        word-wrap: break-word;
    }}
    .items-table th {{
        font-weight: bold;
        background-color: #f5f5f5;
    }}
    .summary-table {{
        width: 100%;
        table-layout: fixed;
        border-collapse: collapse;
        font-size: {meta_font_pt};
        margin-top: 4px;
        border: 1px solid #000000;
    }}
    .summary-table td {{
        border: 1px solid #000000;
        padding: 3px 4px;
    }}
    .summary-table .bold-row td {{
        font-weight: bold;
    }}
    .summary-table .rec-row td {{
        font-size: {rec_font_pt};
        font-weight: bold;
    }}
    .footer-text {{
        text-align: center;
        margin-top: 8px;
        font-size: 8.5pt;
    }}
    .notes-box {{
        margin-top: 6px;
        font-size: 8.5pt;
        border-top: 1px dashed #000;
        padding-top: 4px;
    }}
</style>
</head>
<body>
"""

    if show_logo and logo_data:
        html += f"<div class='center' style='margin-bottom:6px;'><img src='{logo_data}' style='max-width:140px; max-height:70px; object-fit:contain;' /></div>"
    
    html += f"""
    <div class='logo-arch'>
        <div class='arch-title'>{arch_top}</div>
"""
    if arch_sub:
        html += f"<div class='arch-title' style='font-size:11pt;'>{arch_sub}</div>"

    html += f"""
    </div>
    <div class='tagline'>Amazing Finds Only Here</div>
    <div class='store-info'>
        {biz_address}<br/>
        {biz_phone}
    </div>
    <div class='box-header'>{header_text}</div>

    <table class='meta-table' width="100%" cellspacing="0" cellpadding="1" border="0">
        <tr>
            <td width="48%"><b>Bill No:</b> &nbsp;{sale.get('internal_id', '')}</td>
            <td width="52%" align="right"><b>Date:</b> {formatted_date}</td>
        </tr>
"""
    if show_customer_info or cust_name != "Cash":
        html += f"""
        <tr>
            <td width="50%"><b>Customer:</b> {cust_name}</td>
            <td width="50%" align="right"><b>Pay Type:</b> {pay_type}</td>
        </tr>
"""
    elif show_payment_info:
        html += f"""
        <tr>
            <td width="50%"><b>Pay Type:</b> {pay_type}</td>
            <td width="50%"></td>
        </tr>
"""
    html += """
    </table>
"""

    if show_disc_col:
        w_num, w_name, w_qty, w_price, w_disc, w_tot = "7%", "39%", "12%", "14%", "12%", "16%"
    else:
        w_num, w_name, w_qty, w_price, w_disc, w_tot = "8%", "48%", "14%", "14%", "0%", "16%"

    html += f"""
    <table class='items-table' width="100%" cellspacing="0" cellpadding="2" border="1">
        <thead>
            <tr>
                <th width="{w_num}" align="center">#</th>
                <th width="{w_name}" align="left">Product Name</th>
                <th width="{w_qty}" align="right">Qty</th>
                <th width="{w_price}" align="right">Price</th>
"""
    if show_disc_col:
        html += f'<th width="{w_disc}" align="right">Disc</th>'
    html += f'<th width="{w_tot}" align="right">Total</th></tr></thead><tbody>'

    total_qty = 0.0
    total_prod_disc = 0.0
    for idx, item in enumerate(sale.get("items", []), 1):
        p_name = item.get("product_name") or f"Item #{idx}"
        if show_sku and item.get("sku"):
            p_name += f" ({item['sku']})"

        qty = float(item.get("quantity", 0.0))
        price = float(item.get("unit_price", 0.0))
        disc = float(item.get("discount", 0.0))
        tot = float(item.get("total", (qty * price) - disc))
        
        total_qty += qty
        total_prod_disc += disc

        # Formatting values: Qty 2.0 or 2, Prices 370.00
        qty_str = f"{qty:.1f}" if qty % 1 != 0 else f"{int(qty)}.0"
        price_str = f"{price:.2f}"
        disc_str = f"{disc:.2f}"
        tot_str = f"{tot:.2f}"

        html += f"""
        <tr>
            <td width="{w_num}" align="center">{idx}</td>
            <td width="{w_name}" align="left">{p_name}</td>
            <td width="{w_qty}" align="right">{qty_str}</td>
            <td width="{w_price}" align="right">{price_str}</td>
"""
        if show_disc_col:
            html += f'<td width="{w_disc}" align="right">{disc_str}</td>'
        html += f'<td width="{w_tot}" align="right">{tot_str}</td></tr>'

    html += "</tbody></table>"

    grand_total = float(sale.get("total_amount", 0.0))
    paid_amount = float(sale.get("paid_amount", 0.0))
    bill_disc = float(sale.get("discount", 0.0))
    receivable = float(sale.get("balance_owed", grand_total - paid_amount))

    if show_disc_col:
        lbl_w = "46%"
        qty_w = "12%"
        val_w = "42%"
        col_span = 3
        sub_lbl_w = "58%"
    else:
        lbl_w = "56%"
        qty_w = "14%"
        val_w = "30%"
        col_span = 2
        sub_lbl_w = "70%"

    html += f"""
    <table class='summary-table' width="100%" cellspacing="0" cellpadding="2" border="1">
        <tr class='bold-row'>
            <td width="{lbl_w}" colspan="2"><b>Total Bill</b></td>
            <td width="{qty_w}" align="center"><b>{total_qty:.1f}</b></td>
            <td width="{val_w}" align="right" colspan="{col_span}"><b>{grand_total:.2f}</b></td>
        </tr>
        <tr>
            <td width="{sub_lbl_w}" colspan="3">Cash Received</td>
            <td width="{val_w}" align="right" colspan="{col_span}">{paid_amount:.2f}</td>
        </tr>
        <tr>
            <td width="{sub_lbl_w}" colspan="3">Discount on bill</td>
            <td width="{val_w}" align="right" colspan="{col_span}">{bill_disc:.2f}</td>
        </tr>
        <tr>
            <td width="{sub_lbl_w}" colspan="3">Discount on Products</td>
            <td width="{val_w}" align="right" colspan="{col_span}">{total_prod_disc:.2f}</td>
        </tr>
        <tr class='rec-row'>
            <td width="{sub_lbl_w}" colspan="3"><b>Receiveable amount:</b></td>
            <td width="{val_w}" align="right" colspan="{col_span}"><b>{receivable:.2f}</b></td>
        </tr>
    </table>

    <div style='margin-top: 6px; font-size: {meta_font_pt};'><b>Salesman:</b> &nbsp;{salesman_name}</div>
"""
    if show_notes and sale.get("notes"):
        html += f"<div class='notes-box'><b>Note:</b> {sale['notes']}</div>"

    html += f"""
    <div class='footer-text'>{footer_text}</div>
</body>
</html>
"""
    return html

def print_html_receipt(html_content: str, printer_name: str = None, paper_width_mm: int = 80, show_dialog: bool = False, parent=None):
    """
    Prints an HTML receipt to the specified thermal printer or standard printer.
    
    :param html_content: The HTML document string to render.
    :param printer_name: Specific system printer name, or None for system default.
    :param paper_width_mm: 80 (standard thermal), 58 (mini thermal), or 210 (A4).
    :param show_dialog: If True, presents the native OS print selection dialog.
    :param parent: QWidget parent for dialog modal.
    :return: (success: bool, message: str)
    """
    try:
        printer = QPrinter(QPrinter.PrinterResolution)
        
        available = get_available_printers()
        default_name = get_default_printer_name()
        
        # Select target printer if available
        if printer_name and printer_name in available:
            printer.setPrinterName(printer_name)
        elif default_name and default_name in available:
            printer.setPrinterName(default_name)
            
        # Paper width setup
        try:
            if paper_width_mm in [58, 80]:
                page_size = QPageSize(QSizeF(paper_width_mm, 297), QPageSize.Millimeter)
                printer.setPageSize(page_size)
                printer.setPageMargins(QMarginsF(1, 1, 1, 1), QPageLayout.Millimeter)
            else:
                printer.setPageSize(QPageSize(QPageSize.A4))
                printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Millimeter)
        except Exception:
            pass # Fallback to default page size if custom page size fails

        if show_dialog:
            dialog = QPrintDialog(printer, parent)
            dialog.setWindowTitle("Print Thermal Receipt")
            if dialog.exec() != QPrintDialog.Accepted:
                return False, "Print cancelled by user."

        doc = QTextDocument()
        
        if "<html" in html_content.lower():
            styled_html = html_content
        else:
            font_size_css = "9.5pt" if paper_width_mm == 80 else ("8.5pt" if paper_width_mm == 58 else "11pt")
            styled_html = f"""<!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <style>
                @page {{ margin: 0; }}
                * {{ box-sizing: border-box; }}
                body {{ width: 100%; margin: 0 auto; padding: 4px; font-family: Arial, Helvetica, sans-serif; font-size: {font_size_css}; color: #000000; line-height: 1.25; }}
                table {{ width: 100%; table-layout: fixed; border-collapse: collapse; margin: 4px 0; border: 1px solid #000; }}
                td, th {{ font-size: {font_size_css}; padding: 3px 2px; word-wrap: break-word; vertical-align: top; border: 1px solid #000; }}
                .line {{ border-top: 1px dashed #000; margin: 4px 0; }}
                .center {{ text-align: center; }}
                .bold {{ font-weight: bold; }}
                .num {{ text-align: right; }}
            </style>
            </head>
            <body>
            {html_content}
            </body>
            </html>
            """

        doc.setHtml(styled_html)
        
        # Calculate printable width in DevicePixels so QTextDocument layout matches thermal printer canvas width
        rect_width = printer.pageRect(QPrinter.Unit.DevicePixel).width()
        if rect_width <= 0:
            dpi = printer.resolution() if printer.resolution() > 0 else 203
            margin_mm = 2 if paper_width_mm in [58, 80] else 20
            rect_width = (paper_width_mm - margin_mm) * (dpi / 25.4)
            
        doc.setTextWidth(rect_width)
            
        doc.print_(printer)
        return True, "Receipt dispatched to printer successfully."
    except Exception as e:
        return False, f"Thermal printing failed: {str(e)}"

def kick_cash_drawer(printer_name: str = None):
    """
    Sends standard ESC/POS open drawer pulse command (b'\\x1b\\x70\\x00\\x19\\xfa')
    to the target printer spooler.
    """
    raw_escpos_drawer = b'\x1b\x70\x00\x19\xfa'
    
    if sys.platform == 'win32':
        try:
            import win32print
            if not printer_name or printer_name == "System Default Printer":
                printer_name = win32print.GetDefaultPrinter()
                
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Cash Drawer Kick", None, "RAW"))
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, raw_escpos_drawer)
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
            return True, f"Signal sent to open Cash Drawer via printer '{printer_name}'."
        except Exception as e:
            return False, f"Could not kick cash drawer via Win32 print spooler: {str(e)}"
    else:
        # macOS / Linux (CUPS / LPR)
        try:
            cmd = ['lpr']
            if printer_name and printer_name != "System Default Printer":
                cmd.extend(['-P', printer_name])
            cmd.extend(['-o', 'raw'])
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate(input=raw_escpos_drawer)
            if p.returncode == 0:
                return True, "Signal sent to open Cash Drawer."
            else:
                return False, f"LPR drawer signal error: {stderr.decode()}"
        except Exception as e:
            return False, f"Could not send raw pulse to drawer: {str(e)}"

