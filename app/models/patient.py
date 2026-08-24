from datetime import date

from app import db


class Patient(db.Model):

    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True   # walk-in patients bina login ke bhi ho sakte hain
    )

    full_name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", backref="patient_profile")

    def __repr__(self):
        return f"<Patient {self.full_name}>"