from datetime import datetime, timezone

from app import db


class Booking(db.Model):

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False
    )

    booked_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="Pending",
        nullable=False
    )   # Pending, Sample Collected, Processing, Completed, Cancelled

    scheduled_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    patient = db.relationship("Patient", backref="bookings")
    items = db.relationship("BookingItem", back_populates="booking", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Booking {self.id} - {self.status}>"


class BookingItem(db.Model):

    __tablename__ = "booking_items"

    id = db.Column(db.Integer, primary_key=True)

    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id"),
        nullable=False
    )

    test_id = db.Column(
        db.Integer,
        db.ForeignKey("tests.id"),
        nullable=False
    )

    price = db.Column(db.Float, nullable=False)   # booking time ka price snapshot

    booking = db.relationship("Booking", back_populates="items")
    test = db.relationship("Test")

    def __repr__(self):
        return f"<BookingItem test={self.test_id}>"