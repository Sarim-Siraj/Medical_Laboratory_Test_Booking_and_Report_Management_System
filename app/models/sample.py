from datetime import datetime, timezone

from app import db


class Sample(db.Model):

    __tablename__ = "samples"

    id = db.Column(db.Integer, primary_key=True)

    booking_item_id = db.Column(
        db.Integer,
        db.ForeignKey("booking_items.id"),
        nullable=False
    )

    sample_code = db.Column(
        db.String(30),
        unique=True,
        nullable=False
    )

    collected_by = db.Column(
        db.Integer,
        db.ForeignKey("staff.id"),
        nullable=True
    )

    collected_at = db.Column(db.DateTime, nullable=True)

    status = db.Column(
        db.String(30),
        default="Pending Collection",
        nullable=False
    )   # Pending Collection, Collected, Received in Lab, Processing, Completed, Rejected

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    booking_item = db.relationship(
    "BookingItem",
    backref=db.backref("sample", uselist=False))
    collector = db.relationship("Staff")

    def __repr__(self):
        return f"<Sample {self.sample_code} - {self.status}>"