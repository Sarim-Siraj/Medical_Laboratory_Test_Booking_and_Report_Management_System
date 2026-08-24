from app import create_app, db
from app.models.user import User
from app.models.role import Role
from app.models.staff import Staff

app = create_app()

with app.app_context():

    # Har role ke liye ek test account
    accounts = [
        {"name": "Reception Desk", "email": "reception@medlab.com", "password": "pass123", "role_name": "Receptionist"},
        {"name": "Lab Tech Ali", "email": "labtech@medlab.com", "password": "pass123", "role_name": "Lab Technician"},
        {"name": "Dr. Pathologist", "email": "pathologist@medlab.com", "password": "pass123", "role_name": "Pathologist"},
        {"name": "Admin User", "email": "admin@medlab.com", "password": "pass123", "role_name": "Administrator"},
    ]

    for acc in accounts:

        existing = User.query.filter_by(email=acc["email"]).first()

        if existing:
            print(f"⚠️ Already exists: {acc['email']}")
            continue

        role = Role.query.filter_by(name=acc["role_name"]).first()

        if not role:
            print(f"❌ Role not found: {acc['role_name']}")
            continue

        user = User(name=acc["name"], email=acc["email"], role=role)
        user.set_password(acc["password"])
        db.session.add(user)
        db.session.flush()   # user.id turant mil jaye, commit se pehle

        # Staff table mein bhi entry (Receptionist, Lab Tech, Pathologist ke liye)
        if acc["role_name"] != "Administrator":
            staff = Staff(user_id=user.id, staff_type=acc["role_name"])
            db.session.add(staff)

        print(f"✅ Created: {acc['email']} / {acc['role_name']}")

    db.session.commit()