import random
from datetime import datetime, timezone
from app import db

class OTP(db.Model):
    __tablename__ = "otps"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_used = db.Column(db.Boolean, default=False)

def generate_otp():
    return str(random.randint(100000, 999999))