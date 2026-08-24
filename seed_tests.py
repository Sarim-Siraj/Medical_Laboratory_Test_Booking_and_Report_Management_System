from app import create_app, db
from app.models.test import TestCategory, Test

app = create_app()

with app.app_context():

    categories_data = {
        "Hematology": [
            {"name": "Complete Blood Count (CBC)", "code": "CBC001", "price": 800, "sample_type": "Blood", "turnaround_hours": 6},
            {"name": "Erythrocyte Sedimentation Rate (ESR)", "code": "ESR001", "price": 400, "sample_type": "Blood", "turnaround_hours": 4},
        ],
        "Biochemistry": [
            {"name": "Liver Function Test (LFT)", "code": "LFT001", "price": 1500, "sample_type": "Blood", "turnaround_hours": 8},
            {"name": "Kidney Function Test (KFT)", "code": "KFT001", "price": 1400, "sample_type": "Blood", "turnaround_hours": 8},
            {"name": "Fasting Blood Sugar (FBS)", "code": "FBS001", "price": 300, "sample_type": "Blood", "turnaround_hours": 3},
        ],
        "Microbiology": [
            {"name": "Urine Routine Examination", "code": "URE001", "price": 500, "sample_type": "Urine", "turnaround_hours": 4},
        ],
    }

    for category_name, tests in categories_data.items():

        category = TestCategory.query.filter_by(name=category_name).first()

        if not category:
            category = TestCategory(name=category_name)
            db.session.add(category)
            db.session.flush()   # category.id turant milega commit se pehle
            print(f"✅ Category created: {category_name}")

        for t in tests:

            existing_test = Test.query.filter_by(code=t["code"]).first()

            if existing_test:
                print(f"⚠️ Already exists: {t['name']}")
                continue

            new_test = Test(
                category_id=category.id,
                name=t["name"],
                code=t["code"],
                price=t["price"],
                sample_type=t["sample_type"],
                turnaround_hours=t["turnaround_hours"]
            )

            db.session.add(new_test)
            print(f"✅ Test added: {t['name']}")

    db.session.commit()
    print("✅ Seeding complete.")