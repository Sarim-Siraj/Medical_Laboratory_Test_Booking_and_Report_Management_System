from app import create_app, db
from app.models.role import Role
from app.models.user import User

app = create_app()

with app.app_context():

    # Create database tables
    db.create_all()

    roles = [
        "Patient",
        "Receptionist",
        "Lab Technician",
        "Pathologist",
        "Administrator"
    ]

    for role_name in roles:

        existing_role = Role.query.filter_by(
            name=role_name
        ).first()

        if not existing_role:
            role = Role(name=role_name)
            db.session.add(role)

    db.session.commit()

    print("✅ Database tables created successfully.")
    print("✅ Roles created successfully.")