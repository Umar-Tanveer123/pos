import sys
import subprocess
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

        # Enhance HTML for thermal printer dimensions
        width_css = "280px" if paper_width_mm == 80 else ("200px" if paper_width_mm == 58 else "100%")
        font_size_css = "11px" if paper_width_mm == 80 else ("9px" if paper_width_mm == 58 else "13px")
        
        styled_html = f"""
        <html>
        <head>
        <style>
            @page {{ margin: 0; }}
            body {{ width: {width_css}; margin: 0 auto; padding: 2px; font-family: 'Courier New', monospace; font-size: {font_size_css}; color: #000000; line-height: 1.2; }}
            table {{ width: 100%; table-layout: fixed; border-collapse: collapse; margin: 4px 0; }}
            td, th {{ font-size: {font_size_css}; padding: 2px 1px; word-wrap: break-word; overflow-wrap: break-word; vertical-align: top; }}
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

        doc = QTextDocument()
        doc.setHtml(styled_html)
        
        rect_width = printer.pageRect(QPrinter.Point).width()
        if rect_width > 0:
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
