# Medical Laboratory Test Booking and Report Management System

Flask-based lab management system — patient registration, test booking, sample collection, lab processing, verification, and report delivery.

## Tech Stack
Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate, SQLite (dev), Bootstrap + Tailwind

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
python seed_roles.py
python create_staff_users.py
python seed_tests.py
python run.py
```

Open: http://127.0.0.1:5000 (auto-redirects to login)

## Test Accounts

| Role | Email | Password |
|---|---|---|
| Receptionist | reception@medlab.com | pass123 |
| Lab Technician | labtech@medlab.com | pass123 |
| Pathologist | pathologist@medlab.com | pass123 |
| Administrator | admin@medlab.com | pass123 |

Patient account: register at `/auth/register`, or Receptionist can create a walk-in patient (no login needed, gets a unique Patient ID).

## Features

- Role-based auth (Patient, Receptionist, Lab Technician, Pathologist, Administrator)
- Unique Patient ID for every patient (online-registered or walk-in)
- Test catalog + booking with payment method
- Sample collection tracking with barcode-style sample codes
- Lab result entry with validation
- Report generation + Pathologist verification
- PDF report download
- Patient complaints, Admin audit logs
- Search across patients/samples

## Demo Flow

1. Register a patient (or create walk-in via Receptionist)
2. Book a test as that patient/receptionist
3. Receptionist collects the sample
4. Lab Technician enters results
5. Pathologist verifies the report
6. Patient views/downloads the report
