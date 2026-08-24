from app import create_app, db
from app.models.user import User
from app.models.patient import Patient

app = create_app()

with app.app_context():

    patient_role_users = User.query.filter(
        User.role.has(name="Patient")
    ).all()

    for u in patient_role_users:

        existing = Patient.query.filter_by(user_id=u.id).first()

        if not existing:
            p = Patient(user_id=u.id, full_name=u.name)
            db.session.add(p)
            print(f"✅ Patient profile created for: {u.email}")

    db.session.commit()