from datetime import datetime, timezone
from app import db

class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(30), nullable=False)  # Cash, Card, Online
    status = db.Column(db.String(30), default="Paid")  # Paid, Pending
    paid_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    booking = db.relationship("Booking", backref="payment", uselist=False)