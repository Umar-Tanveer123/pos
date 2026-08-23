import requests

class APIClient:
    def __init__(self, base_url="http://127.0.0.1:8000/api/v1"):
        self.base_url = base_url
        self.token = None

    def set_token(self, token: str):
        self.token = token

    def get_headers(self):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def login(self, username, password):
        url = f"{self.base_url}/auth/login"
        data = {"username": username, "password": password}
        response = requests.post(url, data=data) # OAuth2PasswordRequestForm expects form data
        if response.status_code == 200:
            token_data = response.json()
            self.set_token(token_data.get("access_token"))
            return True, None
        return False, response.json().get("detail", "Login failed")

    def get_me(self):
        url = f"{self.base_url}/auth/me"
        response = requests.get(url, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        return None

    # --- Locations API ---
    def get_locations(self):
        url = f"{self.base_url}/locations/"
        response = requests.get(url, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        return []

    def create_location(self, name: str, address: str | None = None, is_active: bool = True):
        url = f"{self.base_url}/locations/"
        data = {"name": name, "address": address, "is_active": is_active}
        response = requests.post(url, json=data, headers=self.get_headers())
        if response.status_code == 201:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create location")

    def update_location(self, location_id: int, name: str, address: str | None = None, is_active: bool = True):
        url = f"{self.base_url}/locations/{location_id}"
        data = {"name": name, "address": address, "is_active": is_active}
        response = requests.put(url, json=data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to update location")

    # --- Catalog API ---
    def get_categories(self):
        url = f"{self.base_url}/products/categories"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def create_category(self, name: str):
        url = f"{self.base_url}/products/categories"
        response = requests.post(url, json={"name": name}, headers=self.get_headers())
        if response.status_code == 201:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create category")

    def get_subcategories(self):
        url = f"{self.base_url}/products/subcategories"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def create_subcategory(self, name: str, category_id: int):
        url = f"{self.base_url}/products/subcategories"
        response = requests.post(url, json={"name": name, "category_id": category_id}, headers=self.get_headers())
        if response.status_code == 201:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create subcategory")

    def get_brands(self):
        url = f"{self.base_url}/products/brands"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def create_brand(self, name: str, description: str | None = None):
        url = f"{self.base_url}/products/brands"
        response = requests.post(url, json={"name": name, "description": description}, headers=self.get_headers())
        if response.status_code == 201:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create brand")

    def get_units(self):
        url = f"{self.base_url}/products/units"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def create_unit(self, name: str):
        url = f"{self.base_url}/products/units"
        response = requests.post(url, json={"name": name}, headers=self.get_headers())
        if response.status_code == 201:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create unit")

    # --- Products API ---
    def get_products(self, search=None, category_id=None, brand_id=None, is_active=None, supplier_id=None):
        url = f"{self.base_url}/products/"
        params = {}
        if search:
            params["search"] = search
        if category_id is not None:
            params["category_id"] = category_id
        if brand_id is not None:
            params["brand_id"] = brand_id
        if is_active is not None:
            params["is_active"] = is_active
        if supplier_id is not None:
            params["supplier_id"] = supplier_id
        response = requests.get(url, params=params, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def create_product(self, product_data: dict):
        url = f"{self.base_url}/products/"
        response = requests.post(url, json=product_data, headers=self.get_headers())
        if response.status_code == 201:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create product")

    def update_product(self, product_id: int, product_data: dict):
        url = f"{self.base_url}/products/{product_id}"
        response = requests.put(url, json=product_data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to update product")

    def delete_product(self, product_id: int):
        url = f"{self.base_url}/products/{product_id}"
        response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, None
        return False, response.json().get("detail", "Failed to delete product")

    def delete_category(self, category_id: int):
        url = f"{self.base_url}/products/categories/{category_id}"
        response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, None
        return False, response.json().get("detail", "Failed to delete category")

    def delete_subcategory(self, subcategory_id: int):
        url = f"{self.base_url}/products/subcategories/{subcategory_id}"
        response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, None
        return False, response.json().get("detail", "Failed to delete subcategory")

    def delete_brand(self, brand_id: int):
        url = f"{self.base_url}/products/brands/{brand_id}"
        response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, None
        return False, response.json().get("detail", "Failed to delete brand")

    def delete_unit(self, unit_id: int):
        url = f"{self.base_url}/products/units/{unit_id}"
        response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, None
        return False, response.json().get("detail", "Failed to delete unit")

    def delete_location(self, location_id: int):
        url = f"{self.base_url}/locations/{location_id}"
        response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, None
        return False, response.json().get("detail", "Failed to delete location")

    # --- Suppliers API ---
    def get_suppliers(self, search=None):
        url = f"{self.base_url}/suppliers/"
        params = {}
        if search:
            params["search"] = search
        response = requests.get(url, params=params, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def get_supplier(self, supplier_id: int):
        url = f"{self.base_url}/suppliers/{supplier_id}"
        response = requests.get(url, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        return None

    def create_supplier(self, supplier_data: dict):
        url = f"{self.base_url}/suppliers/"
        response = requests.post(url, json=supplier_data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create supplier")

    def update_supplier(self, supplier_id: int, supplier_data: dict):
        url = f"{self.base_url}/suppliers/{supplier_id}"
        response = requests.put(url, json=supplier_data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to update supplier")

    def delete_supplier(self, supplier_id: int):
        url = f"{self.base_url}/suppliers/{supplier_id}"
        response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, None
        return False, response.json().get("detail", "Failed to delete supplier")

    def get_supplier_statement(self, supplier_id: int):
        url = f"{self.base_url}/suppliers/{supplier_id}/statement"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def record_supplier_payment(self, supplier_id: int, payment_data: dict):
        url = f"{self.base_url}/suppliers/{supplier_id}/payments"
        response = requests.post(url, json=payment_data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to record payment")

    def get_supplier_profit_report(self, supplier_id=None):
        url = f"{self.base_url}/suppliers/reports/profit-report"
        params = {}
        if supplier_id:
            params["supplier_id"] = supplier_id
        response = requests.get(url, params=params, headers=self.get_headers())
        return response.json() if response.status_code == 200 else {"suppliers": [], "products": []}

    # --- Purchases API ---
    def get_purchases(self, supplier_id=None, location_id=None):
        url = f"{self.base_url}/purchases/"
        params = {}
        if supplier_id:
            params["supplier_id"] = supplier_id
        if location_id:
            params["location_id"] = location_id
        response = requests.get(url, params=params, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def get_purchase(self, purchase_id: int):
        url = f"{self.base_url}/purchases/{purchase_id}"
        response = requests.get(url, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        return None

    def create_purchase(self, purchase_data: dict):
        url = f"{self.base_url}/purchases/"
        response = requests.post(url, json=purchase_data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to record purchase invoice")

    # --- Pricing & Bulk Imports ---
    def bulk_price_update(self, data: dict):
        url = f"{self.base_url}/products/bulk-price-update"
        response = requests.post(url, json=data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to update prices")

    def get_price_audit_logs(self):
        url = f"{self.base_url}/products/price-audit-logs"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def import_products_csv(self, file_path: str, supplier_id: int = None):
        url = f"{self.base_url}/products/import-csv"
        params = {}
        if supplier_id is not None:
            params["supplier_id"] = supplier_id
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.split("/")[-1], f, "text/csv")}
                response = requests.post(url, files=files, params=params, headers=self.get_headers())
                if response.status_code == 200:
                    return response.json()
                return {"success": False, "errors": [{"row": 0, "error": response.json().get("detail", "Failed to parse CSV upload on backend")}]}
        except Exception as e:
            return {"success": False, "errors": [{"row": 0, "error": f"Failed to read local file: {str(e)}"}]}

    # --- Supplier Returns & Exchange ---
    def get_supplier_returns(self, supplier_id=None, return_type=None):
        url = f"{self.base_url}/supplier-returns/"
        params = {}
        if supplier_id:
            params["supplier_id"] = supplier_id
        if return_type:
            params["return_type"] = return_type
        response = requests.get(url, params=params, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def get_returnable_items(self, purchase_id: int):
        url = f"{self.base_url}/supplier-returns/purchase/{purchase_id}/returnable"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def create_supplier_return(self, data: dict):
        url = f"{self.base_url}/supplier-returns/"
        response = requests.post(url, json=data, headers=self.get_headers())
        if response.status_code == 201:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create return")

    def complete_exchange(self, return_id: int):
        url = f"{self.base_url}/supplier-returns/{return_id}/complete-exchange"
        response = requests.post(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to complete exchange")

    # --- Customers ---
    def get_customer_types(self):
        url = f"{self.base_url}/customers/types"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def get_customers(self, search=None, customer_type_id=None, is_active=None):
        url = f"{self.base_url}/customers/"
        params = {}
        if search:
            params["search"] = search
        if customer_type_id is not None:
            params["customer_type_id"] = customer_type_id
        if is_active is not None:
            params["is_active"] = is_active
        response = requests.get(url, params=params, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def get_customer(self, customer_id: int):
        url = f"{self.base_url}/customers/{customer_id}"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else None

    def create_customer(self, data: dict):
        url = f"{self.base_url}/customers/"
        response = requests.post(url, json=data, headers=self.get_headers())
        if response.status_code == 201:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create customer")

    def update_customer(self, customer_id: int, data: dict):
        url = f"{self.base_url}/customers/{customer_id}"
        response = requests.put(url, json=data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to update customer")

    def delete_customer(self, customer_id: int):
        url = f"{self.base_url}/customers/{customer_id}"
        response = requests.delete(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, None
        return False, response.json().get("detail", "Failed to delete customer")

    def get_customer_statement(self, customer_id: int):
        url = f"{self.base_url}/customers/{customer_id}/statement"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def record_customer_payment(self, customer_id: int, data: dict):
        url = f"{self.base_url}/customers/{customer_id}/payments"
        response = requests.post(url, json=data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to record payment")

    # --- Sales / POS API ---
    def get_sales(self, customer_id=None, location_id=None):
        url = f"{self.base_url}/sales/"
        params = {}
        if customer_id:
            params["customer_id"] = customer_id
        if location_id:
            params["location_id"] = location_id
        response = requests.get(url, params=params, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def get_sale(self, sale_id: int):
        url = f"{self.base_url}/sales/{sale_id}"
        response = requests.get(url, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        return None

    def create_sale(self, sale_data: dict):
        url = f"{self.base_url}/sales/"
        response = requests.post(url, json=sale_data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to record sales invoice")

    def get_payment_methods(self):
        url = f"{self.base_url}/sales/payment-methods"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else ["Cash"]

    def return_sale(self, sale_id: int):
        url = f"{self.base_url}/sales/{sale_id}/return"
        response = requests.post(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to process return")

    def cancel_sale(self, sale_id: int):
        url = f"{self.base_url}/sales/{sale_id}/cancel"
        response = requests.post(url, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to cancel sale")

    def get_invoice_templates(self):
        url = f"{self.base_url}/sales/templates"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def update_invoice_template(self, template_id: int, data: dict):
        url = f"{self.base_url}/sales/templates/{template_id}"
        response = requests.put(url, json=data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to update template")

    def get_returnable_items(self, sale_id: int):
        url = f"{self.base_url}/customer-returns/sale/{sale_id}/returnable"
        response = requests.get(url, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        return []

    def process_customer_return(self, return_data: dict):
        url = f"{self.base_url}/customer-returns/"
        response = requests.post(url, json=return_data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to process return")

    # --- Inventory Management ---
    def get_stock_transfers(self):
        url = f"{self.base_url}/inventory/transfer"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def create_stock_transfer(self, data: dict):
        url = f"{self.base_url}/inventory/transfer"
        response = requests.post(url, json=data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create transfer")

    def create_stock_adjustment(self, data: dict):
        url = f"{self.base_url}/inventory/adjust"
        response = requests.post(url, json=data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create adjustment")

    def get_low_stock_alerts(self):
        url = f"{self.base_url}/inventory/low-stock"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    # --- Expenses ---
    def get_expenses(self):
        url = f"{self.base_url}/expenses/"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def create_expense(self, data: dict):
        url = f"{self.base_url}/expenses/"
        response = requests.post(url, json=data, headers=self.get_headers())
        if response.status_code == 200:
            return True, response.json()
        return False, response.json().get("detail", "Failed to create expense")

    # --- Reports ---
    def get_dashboard_metrics(self, period: str = "all", start: str = None, end: str = None):
        url = f"{self.base_url}/reports/dashboard"
        params = {"period": period}
        if start: params["start"] = start
        if end: params["end"] = end
        response = requests.get(url, params=params, headers=self.get_headers())
        return response.json() if response.status_code == 200 else {}

    def get_financial_summary(self):
        url = f"{self.base_url}/reports/financials"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else {}

    # --- System Settings (SRS 49) ---
    def get_settings(self):
        url = f"{self.base_url}/settings/"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else {}

    def update_settings(self, settings_dict: dict):
        url = f"{self.base_url}/settings/"
        response = requests.post(url, json={"settings": settings_dict}, headers=self.get_headers())
        if response.status_code == 200:
            return True
        raise Exception(response.json().get("detail", "Failed to update settings"))

    # --- Backups (SRS 48) ---
    def create_backup(self):
        url = f"{self.base_url}/backup/backup"
        response = requests.post(url, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        raise Exception(response.json().get("detail", "Failed to create backup"))

    def list_backups(self):
        url = f"{self.base_url}/backup/"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

    def restore_backup(self, filename: str):
        url = f"{self.base_url}/backup/restore"
        response = requests.post(url, params={"filename": filename}, headers=self.get_headers())
        if response.status_code == 200:
            return True
        raise Exception(response.json().get("detail", "Failed to restore backup"))

    # --- Audit Logs (SRS 46) ---
    def get_audit_logs(self):
        url = f"{self.base_url}/audit/"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else []

# Global instance for the app to use
client = APIClient()
