from datetime import datetime, timezone
from app import db

class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(30), default="Cash")
    status = db.Column(db.String(20), default="Confirmed")
    screenshot_path = db.Column(db.String(255), nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    paid_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    booking = db.relationship("Booking", backref="payments")