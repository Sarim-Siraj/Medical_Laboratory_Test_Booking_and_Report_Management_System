import random
import string

from app import db


def generate_patient_code():
    random_part = "".join(random.choices(string.digits, k=6))
    return f"PT-{random_part}"


class Patient(db.Model):

    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)

    patient_code = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    full_name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", backref="patient_profile")

    def __repr__(self):
        return f"<Patient {self.patient_code} - {self.full_name}>"