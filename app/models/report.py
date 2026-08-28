from datetime import datetime, timezone
from app import db

class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    generated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(30), default="Pending Verification")  # Pending Verification, Verified, Released

    booking = db.relationship("Booking", backref="report", uselist=False)


class ReportVerification(db.Model):
    __tablename__ = "report_verifications"
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False)
    verified_by = db.Column(db.Integer, db.ForeignKey("staff.id"), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    comments = db.Column(db.String(255), nullable=True)

    report = db.relationship("Report", backref="verification", uselist=False)