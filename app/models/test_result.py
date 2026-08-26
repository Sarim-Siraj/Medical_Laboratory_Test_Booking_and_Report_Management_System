from datetime import datetime, timezone

from app import db


class TestResult(db.Model):

    __tablename__ = "test_results"

    id = db.Column(db.Integer, primary_key=True)

    sample_id = db.Column(
        db.Integer,
        db.ForeignKey("samples.id"),
        nullable=False
    )

    parameter = db.Column(db.String(100), nullable=False)   # e.g. "Hemoglobin"
    value = db.Column(db.String(50), nullable=False)         # e.g. "13.5"
    unit = db.Column(db.String(20), nullable=True)            # e.g. "g/dL"

    entered_by = db.Column(
        db.Integer,
        db.ForeignKey("staff.id"),
        nullable=True
    )

    entered_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    sample = db.relationship("Sample", backref="results")
    technician = db.relationship("Staff")

    def __repr__(self):
        return f"<TestResult {self.parameter}={self.value}>"