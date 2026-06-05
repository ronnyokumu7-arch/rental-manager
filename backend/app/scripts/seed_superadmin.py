import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.database import SessionLocal
from app.core.security import get_password_hash
from app.models.users import User
from app.core.config import get_settings

settings = get_settings()

def update_password():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@superadmin.com").first()
        if not user:
            print("User not found.")
            return
        user.password_hash = get_password_hash(settings.superadmin_password)
        db.commit()
        print("Password updated successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    update_password()