import requests
import time

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

    def _request(self, method, url, **kwargs):
        headers = self.get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        
        for attempt in range(3):
            try:
                resp = requests.request(method, url, headers=headers, timeout=10, **kwargs)
                return resp
            except Exception as e:
                if attempt < 2:
                    time.sleep(0.3)
                else:
                    print(f"[APIClient Error] {method} {url}: {e}")
                    return None

    def login(self, username, password):
        url = f"{self.base_url}/auth/login"
        data = {"username": username, "password": password}
        response = self._request("POST", url, data=data)
        if response and response.status_code == 200:
            token_data = response.json()
            self.set_token(token_data.get("access_token"))
            return True, None
        err_msg = response.json().get("detail", "Login failed") if response else "Backend server connection error."
        return False, err_msg

    def get_me(self):
        url = f"{self.base_url}/auth/me"
        response = self._request("GET", url)
        if response and response.status_code == 200:
            return response.json()
        return None

    # --- Locations API ---
    def get_locations(self):
        url = f"{self.base_url}/locations/"
        response = self._request("GET", url)
        if response and response.status_code == 200:
            return response.json()
        return []

    def create_location(self, name: str, address: str | None = None, is_active: bool = True):
        url = f"{self.base_url}/locations/"
        data = {"name": name, "address": address, "is_active": is_active}
        response = self._request("POST", url, json=data)
        if response and response.status_code == 201:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create location") if response else "Connection error"
        return False, err_msg

    def update_location(self, location_id: int, name: str, address: str | None = None, is_active: bool = True):
        url = f"{self.base_url}/locations/{location_id}"
        data = {"name": name, "address": address, "is_active": is_active}
        response = self._request("PUT", url, json=data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to update location") if response else "Connection error"
        return False, err_msg

    # --- Catalog API ---
    def get_categories(self):
        url = f"{self.base_url}/products/categories"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def create_category(self, name: str):
        url = f"{self.base_url}/products/categories"
        response = self._request("POST", url, json={"name": name})
        if response and response.status_code == 201:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create category") if response else "Connection error"
        return False, err_msg

    def get_subcategories(self):
        url = f"{self.base_url}/products/subcategories"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def create_subcategory(self, name: str, category_id: int):
        url = f"{self.base_url}/products/subcategories"
        response = self._request("POST", url, json={"name": name, "category_id": category_id})
        if response and response.status_code == 201:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create subcategory") if response else "Connection error"
        return False, err_msg

    def get_brands(self):
        url = f"{self.base_url}/products/brands"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def create_brand(self, name: str, description: str | None = None):
        url = f"{self.base_url}/products/brands"
        response = self._request("POST", url, json={"name": name, "description": description})
        if response and response.status_code == 201:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create brand") if response else "Connection error"
        return False, err_msg

    def get_units(self):
        url = f"{self.base_url}/products/units"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def create_unit(self, name: str):
        url = f"{self.base_url}/products/units"
        response = self._request("POST", url, json={"name": name})
        if response and response.status_code == 201:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create unit") if response else "Connection error"
        return False, err_msg

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
        response = self._request("GET", url, params=params)
        return response.json() if response and response.status_code == 200 else []

    def create_product(self, product_data: dict):
        url = f"{self.base_url}/products/"
        response = self._request("POST", url, json=product_data)
        if response and response.status_code == 201:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create product") if response else "Connection error"
        return False, err_msg

    def update_product(self, product_id: int, product_data: dict):
        url = f"{self.base_url}/products/{product_id}"
        response = self._request("PUT", url, json=product_data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to update product") if response else "Connection error"
        return False, err_msg

    def delete_product(self, product_id: int):
        url = f"{self.base_url}/products/{product_id}"
        response = self._request("DELETE", url)
        if response and response.status_code == 200:
            return True, None
        err_msg = response.json().get("detail", "Failed to delete product") if response else "Connection error"
        return False, err_msg

    def delete_category(self, category_id: int):
        url = f"{self.base_url}/products/categories/{category_id}"
        response = self._request("DELETE", url)
        if response and response.status_code == 200:
            return True, None
        err_msg = response.json().get("detail", "Failed to delete category") if response else "Connection error"
        return False, err_msg

    def delete_subcategory(self, subcategory_id: int):
        url = f"{self.base_url}/products/subcategories/{subcategory_id}"
        response = self._request("DELETE", url)
        if response and response.status_code == 200:
            return True, None
        err_msg = response.json().get("detail", "Failed to delete subcategory") if response else "Connection error"
        return False, err_msg

    def delete_brand(self, brand_id: int):
        url = f"{self.base_url}/products/brands/{brand_id}"
        response = self._request("DELETE", url)
        if response and response.status_code == 200:
            return True, None
        err_msg = response.json().get("detail", "Failed to delete brand") if response else "Connection error"
        return False, err_msg

    def delete_unit(self, unit_id: int):
        url = f"{self.base_url}/products/units/{unit_id}"
        response = self._request("DELETE", url)
        if response and response.status_code == 200:
            return True, None
        err_msg = response.json().get("detail", "Failed to delete unit") if response else "Connection error"
        return False, err_msg

    def delete_location(self, location_id: int):
        url = f"{self.base_url}/locations/{location_id}"
        response = self._request("DELETE", url)
        if response and response.status_code == 200:
            return True, None
        err_msg = response.json().get("detail", "Failed to delete location") if response else "Connection error"
        return False, err_msg

    # --- Suppliers API ---
    def get_suppliers(self, search=None):
        url = f"{self.base_url}/suppliers/"
        params = {}
        if search:
            params["search"] = search
        response = self._request("GET", url, params=params)
        return response.json() if response and response.status_code == 200 else []

    def get_supplier(self, supplier_id: int):
        url = f"{self.base_url}/suppliers/{supplier_id}"
        response = self._request("GET", url)
        if response and response.status_code == 200:
            return response.json()
        return None

    def create_supplier(self, supplier_data: dict):
        url = f"{self.base_url}/suppliers/"
        response = self._request("POST", url, json=supplier_data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create supplier") if response else "Connection error"
        return False, err_msg

    def update_supplier(self, supplier_id: int, supplier_data: dict):
        url = f"{self.base_url}/suppliers/{supplier_id}"
        response = self._request("PUT", url, json=supplier_data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to update supplier") if response else "Connection error"
        return False, err_msg

    def delete_supplier(self, supplier_id: int):
        url = f"{self.base_url}/suppliers/{supplier_id}"
        response = self._request("DELETE", url)
        if response and response.status_code == 200:
            return True, None
        err_msg = response.json().get("detail", "Failed to delete supplier") if response else "Connection error"
        return False, err_msg

    def get_supplier_statement(self, supplier_id: int):
        url = f"{self.base_url}/suppliers/{supplier_id}/statement"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def record_supplier_payment(self, supplier_id: int, payment_data: dict):
        url = f"{self.base_url}/suppliers/{supplier_id}/payments"
        response = self._request("POST", url, json=payment_data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to record payment") if response else "Connection error"
        return False, err_msg

    def get_supplier_profit_report(self, supplier_id=None):
        url = f"{self.base_url}/suppliers/reports/profit-report"
        params = {}
        if supplier_id:
            params["supplier_id"] = supplier_id
        response = self._request("GET", url, params=params)
        return response.json() if response and response.status_code == 200 else {"suppliers": [], "products": []}

    # --- Purchases API ---
    def get_purchases(self, supplier_id=None, location_id=None):
        url = f"{self.base_url}/purchases/"
        params = {}
        if supplier_id:
            params["supplier_id"] = supplier_id
        if location_id:
            params["location_id"] = location_id
        response = self._request("GET", url, params=params)
        return response.json() if response and response.status_code == 200 else []

    def get_purchase(self, purchase_id: int):
        url = f"{self.base_url}/purchases/{purchase_id}"
        response = self._request("GET", url)
        if response and response.status_code == 200:
            return response.json()
        return None

    def create_purchase(self, purchase_data: dict):
        url = f"{self.base_url}/purchases/"
        response = self._request("POST", url, json=purchase_data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to record purchase invoice") if response else "Connection error"
        return False, err_msg

    # --- Pricing & Bulk Imports ---
    def bulk_price_update(self, data: dict):
        url = f"{self.base_url}/products/bulk-price-update"
        response = self._request("POST", url, json=data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to update prices") if response else "Connection error"
        return False, err_msg

    def get_price_audit_logs(self):
        url = f"{self.base_url}/products/price-audit-logs"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def import_products_csv(self, file_path: str, supplier_id: int = None):
        url = f"{self.base_url}/products/import-csv"
        params = {}
        if supplier_id is not None:
            params["supplier_id"] = supplier_id
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.split("/")[-1], f, "text/csv")}
                response = self._request("POST", url, files=files, params=params)
                if response and response.status_code == 200:
                    return response.json()
                err_msg = response.json().get("detail", "Failed to parse CSV upload on backend") if response else "Connection error"
                return {"success": False, "errors": [{"row": 0, "error": err_msg}]}
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
        response = self._request("GET", url, params=params)
        return response.json() if response and response.status_code == 200 else []

    def get_returnable_items(self, purchase_id: int):
        url = f"{self.base_url}/supplier-returns/purchase/{purchase_id}/returnable"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def create_supplier_return(self, data: dict):
        url = f"{self.base_url}/supplier-returns/"
        response = self._request("POST", url, json=data)
        if response and response.status_code == 201:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create return") if response else "Connection error"
        return False, err_msg

    def complete_exchange(self, return_id: int):
        url = f"{self.base_url}/supplier-returns/{return_id}/complete-exchange"
        response = self._request("POST", url)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to complete exchange") if response else "Connection error"
        return False, err_msg

    # --- Customers ---
    def get_customer_types(self):
        url = f"{self.base_url}/customers/types"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def get_customers(self, search=None, customer_type_id=None, is_active=None):
        url = f"{self.base_url}/customers/"
        params = {}
        if search:
            params["search"] = search
        if customer_type_id is not None:
            params["customer_type_id"] = customer_type_id
        if is_active is not None:
            params["is_active"] = is_active
        response = self._request("GET", url, params=params)
        return response.json() if response and response.status_code == 200 else []

    def get_customer(self, customer_id: int):
        url = f"{self.base_url}/customers/{customer_id}"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else None

    def create_customer(self, data: dict):
        url = f"{self.base_url}/customers/"
        response = self._request("POST", url, json=data)
        if response and response.status_code == 201:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create customer") if response else "Connection error"
        return False, err_msg

    def update_customer(self, customer_id: int, data: dict):
        url = f"{self.base_url}/customers/{customer_id}"
        response = self._request("PUT", url, json=data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to update customer") if response else "Connection error"
        return False, err_msg

    def delete_customer(self, customer_id: int):
        url = f"{self.base_url}/customers/{customer_id}"
        response = self._request("DELETE", url)
        if response and response.status_code == 200:
            return True, None
        err_msg = response.json().get("detail", "Failed to delete customer") if response else "Connection error"
        return False, err_msg

    def get_customer_statement(self, customer_id: int):
        url = f"{self.base_url}/customers/{customer_id}/statement"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def record_customer_payment(self, customer_id: int, data: dict):
        url = f"{self.base_url}/customers/{customer_id}/payments"
        response = self._request("POST", url, json=data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to record payment") if response else "Connection error"
        return False, err_msg

    # --- Sales / POS API ---
    def get_sales(self, customer_id=None, location_id=None):
        url = f"{self.base_url}/sales/"
        params = {}
        if customer_id:
            params["customer_id"] = customer_id
        if location_id:
            params["location_id"] = location_id
        response = self._request("GET", url, params=params)
        return response.json() if response and response.status_code == 200 else []

    def get_sale(self, sale_id: int):
        url = f"{self.base_url}/sales/{sale_id}"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else None

    def create_sale(self, sale_data: dict):
        url = f"{self.base_url}/sales/"
        response = self._request("POST", url, json=sale_data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to record sales invoice") if response else "Connection error"
        return False, err_msg

    def get_payment_methods(self):
        url = f"{self.base_url}/sales/payment-methods"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else ["Cash"]

    def return_sale(self, sale_id: int):
        url = f"{self.base_url}/sales/{sale_id}/return"
        response = self._request("POST", url)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to process return") if response else "Connection error"
        return False, err_msg

    def cancel_sale(self, sale_id: int):
        url = f"{self.base_url}/sales/{sale_id}/cancel"
        response = self._request("POST", url)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to cancel sale") if response else "Connection error"
        return False, err_msg

    def get_invoice_templates(self):
        url = f"{self.base_url}/sales/templates"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def update_invoice_template(self, template_id: int, data: dict):
        url = f"{self.base_url}/sales/templates/{template_id}"
        response = self._request("PUT", url, json=data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to update template") if response else "Connection error"
        return False, err_msg

    def create_invoice_template(self, data: dict):
        url = f"{self.base_url}/sales/templates"
        response = self._request("POST", url, json=data)
        if response and response.status_code in (200, 201):
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create template") if response else "Connection error"
        return False, err_msg

    def get_returnable_items(self, sale_id: int):
        url = f"{self.base_url}/customer-returns/sale/{sale_id}/returnable"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def process_customer_return(self, return_data: dict):
        url = f"{self.base_url}/customer-returns/"
        response = self._request("POST", url, json=return_data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to process return") if response else "Connection error"
        return False, err_msg

    # --- Inventory Management ---
    def get_stock_transfers(self):
        url = f"{self.base_url}/inventory/transfer"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def create_stock_transfer(self, data: dict):
        url = f"{self.base_url}/inventory/transfer"
        response = self._request("POST", url, json=data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create transfer") if response else "Connection error"
        return False, err_msg

    def create_stock_adjustment(self, data: dict):
        url = f"{self.base_url}/inventory/adjust"
        response = self._request("POST", url, json=data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create adjustment") if response else "Connection error"
        return False, err_msg

    def get_low_stock_alerts(self):
        url = f"{self.base_url}/inventory/low-stock"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    # --- Expenses ---
    def get_expenses(self):
        url = f"{self.base_url}/expenses/"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def create_expense(self, data: dict):
        url = f"{self.base_url}/expenses/"
        response = self._request("POST", url, json=data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create expense") if response else "Connection error"
        return False, err_msg

    # --- Reports ---
    def get_dashboard_metrics(self, period: str = "all", start: str = None, end: str = None):
        url = f"{self.base_url}/reports/dashboard"
        params = {"period": period}
        if start: params["start"] = start
        if end: params["end"] = end
        response = self._request("GET", url, params=params)
        return response.json() if response and response.status_code == 200 else {}

    def get_financial_summary(self):
        url = f"{self.base_url}/reports/financials"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else {}

    # --- System Settings ---
    def get_settings(self):
        url = f"{self.base_url}/settings/"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else {}

    def update_settings(self, settings_dict: dict):
        url = f"{self.base_url}/settings/"
        response = self._request("POST", url, json={"settings": settings_dict})
        if response and response.status_code == 200:
            return True
        err_msg = response.json().get("detail", "Failed to update settings") if response else "Connection error"
        raise Exception(err_msg)

    # --- Backups ---
    def create_backup(self):
        url = f"{self.base_url}/backup/backup"
        response = self._request("POST", url)
        if response and response.status_code == 200:
            return response.json()
        err_msg = response.json().get("detail", "Failed to create backup") if response else "Connection error"
        raise Exception(err_msg)

    def list_backups(self):
        url = f"{self.base_url}/backup/"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def restore_backup(self, filename: str):
        url = f"{self.base_url}/backup/restore"
        response = self._request("POST", url, params={"filename": filename})
        if response and response.status_code == 200:
            return True
        err_msg = response.json().get("detail", "Failed to restore backup") if response else "Connection error"
        raise Exception(err_msg)

    # --- Audit Logs ---
    def get_audit_logs(self):
        url = f"{self.base_url}/audit/"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    # --- User Management & Roles ---
    def get_users(self):
        url = f"{self.base_url}/users/"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

    def create_user(self, user_data: dict):
        url = f"{self.base_url}/users/"
        response = self._request("POST", url, json=user_data)
        if response and response.status_code in (200, 201):
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to create user") if response else "Connection error"
        return False, err_msg

    def update_user(self, user_id: int, user_data: dict):
        url = f"{self.base_url}/users/{user_id}"
        response = self._request("PUT", url, json=user_data)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to update user") if response else "Connection error"
        return False, err_msg

    def delete_user(self, user_id: int):
        url = f"{self.base_url}/users/{user_id}"
        response = self._request("DELETE", url)
        if response and response.status_code == 200:
            return True, response.json()
        err_msg = response.json().get("detail", "Failed to deactivate user") if response else "Connection error"
        return False, err_msg

    def get_roles(self):
        url = f"{self.base_url}/users/roles"
        response = self._request("GET", url)
        return response.json() if response and response.status_code == 200 else []

# Global instance for the app to use
client = APIClient()
