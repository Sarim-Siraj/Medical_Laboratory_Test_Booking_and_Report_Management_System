from app import db


class Staff(db.Model):

    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    staff_type = db.Column(db.String(30), nullable=False)  # receptionist, lab_technician, pathologist
    license_no = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(50), nullable=True)

    user = db.relationship("User", backref="staff_profile")

    def __repr__(self):
        return f"<Staff {self.staff_type}>"