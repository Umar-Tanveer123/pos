import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import SessionLocal
from backend.models.auth import Role, User
from backend.core.security import get_password_hash

def seed_admin():
    db = SessionLocal()
    
    # Check if admin role exists
    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    if not admin_role:
        admin_role = Role(name="Admin", description="Full system access")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)
        print("Created Admin role.")
        
    # Check if admin user exists
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed_password = get_password_hash("admin123")
        admin_user = User(
            username="admin",
            hashed_password=hashed_password,
            role_id=admin_role.id,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print("Created default admin user (admin/admin123).")
    else:
        print("Admin user already exists.")
        
    db.close()

if __name__ == "__main__":
    seed_admin()
