import random
import string
import os
from datetime import datetime, timezone, date
from io import BytesIO

from flask import (
    render_template, redirect, url_for, flash,
    request, current_app, abort, send_from_directory, make_response
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from xhtml2pdf import pisa
from flask_mail import Message

from app import db, mail
from app.medlab import medlab
from app.medlab.forms import BookingForm, ResultEntryForm, WalkInPatientForm

from app.models.patient import Patient, generate_patient_code
from app.models.test import Test, TestCategory
from app.models.booking import Booking, BookingItem
from app.models.sample import Sample
from app.models.staff import Staff
from app.models.user import User
from app.models.role import Role
from app.models.test_result import TestResult
from app.models.report import Report, ReportVerification
from app.models.complaint import Complaint
from app.models.audit_log import AuditLog
from app.models.payment import Payment


def generate_sample_code():
    random_part = "".join(random.choices(string.digits, k=6))
    return f"SMP-{random_part}"


def _calc_age(dob):
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


@medlab.route("/book", methods=["GET", "POST"])
@login_required
def book_test():

    form = BookingForm()

    all_tests = Test.query.order_by(Test.name).all()
    form.test_ids.choices = [(t.id, f"{t.name} - Rs.{t.price}") for t in all_tests]

    categories = TestCategory.query.order_by(TestCategory.name).all()

    is_patient = current_user.role.name == "Patient"
    my_patient = None

    if is_patient:
        my_patient = Patient.query.filter_by(user_id=current_user.id).first()
        form.patient_id.choices = [(my_patient.id, my_patient.full_name)]
        form.patient_id.data = my_patient.id
    else:
        form.patient_id.choices = [
            (p.id, f"{p.patient_code} - {p.full_name}") for p in Patient.query.all()
        ]

    if form.validate_on_submit():

        if not is_patient:
            selected_patient = Patient.query.get(form.patient_id.data)
            if not selected_patient:
                flash("Please select a valid patient from the search suggestions.", "danger")
                return redirect(url_for("medlab.book_test"))

        if is_patient and form.patient_id.data != my_patient.id:
            flash("You can only book tests for yourself.", "danger")
            return redirect(url_for("medlab.book_test"))

        new_booking = Booking(
            patient_id=form.patient_id.data,
            booked_by=current_user.id,
            status="Pending"
        )
        db.session.add(new_booking)
        db.session.flush()

        selected_tests = Test.query.filter(Test.id.in_(form.test_ids.data)).all()
        for t in selected_tests:
            db.session.add(BookingItem(booking_id=new_booking.id, test_id=t.id, price=t.price))

        db.session.commit()
        flash("Booking created! Please complete payment.", "success")
        return redirect(url_for("medlab.record_payment", booking_id=new_booking.id))

    return render_template(
        "medlab/book_test.html",
        form=form, is_patient=is_patient, tests=all_tests, categories=categories
    )


@medlab.route("/samples/pending")
@login_required
def pending_samples():

    search = request.args.get("search", "").strip()
    query = BookingItem.query.filter(~BookingItem.sample.has())

    if search:
        query = query.join(Booking).join(Patient).filter(
            db.or_(
                Patient.patient_code.ilike(f"%{search}%"),
                Patient.full_name.ilike(f"%{search}%")
            )
        )

    pending_items = query.all()
    return render_template("medlab/pending_samples.html", items=pending_items, search=search)


@medlab.route("/samples/collect/<int:item_id>", methods=["POST"])
@login_required
def collect_sample(item_id):

    booking_item = BookingItem.query.get_or_404(item_id)
    booking = booking_item.booking
    total = sum(i.price for i in booking.items)
    confirmed_paid = sum(p.amount for p in booking.payments if p.status == "Confirmed")

    if confirmed_paid < total:
        flash("Cannot collect sample — payment not completed.", "danger")
        return redirect(url_for("medlab.pending_samples"))

    if booking_item.sample:
        flash("Sample already collected for this test.", "warning")
        return redirect(url_for("medlab.pending_samples"))

    staff_record = Staff.query.filter_by(user_id=current_user.id).first()

    while True:
        code = generate_sample_code()
        if not Sample.query.filter_by(sample_code=code).first():
            break

    new_sample = Sample(
        booking_item_id=booking_item.id,
        sample_code=code,
        collected_by=staff_record.id if staff_record else None,
        collected_at=datetime.now(timezone.utc),
        status="Collected"
    )
    db.session.add(new_sample)
    db.session.commit()

    flash(f"Sample collected! Code: {code}", "success")
    return redirect(url_for("medlab.pending_samples"))


@medlab.route("/samples/collected")
@login_required
def collected_samples():

    search = request.args.get("search", "").strip()
    query = Sample.query.filter_by(status="Collected")

    if search:
        query = query.join(BookingItem).join(Booking).join(Patient).filter(
            db.or_(
                Patient.patient_code.ilike(f"%{search}%"),
                Patient.full_name.ilike(f"%{search}%"),
                Sample.sample_code.ilike(f"%{search}%")
            )
        )

    samples = query.all()
    return render_template("medlab/collected_samples.html", samples=samples, search=search)


@medlab.route("/samples/review")
@login_required
def samples_under_review():
    if current_user.role.name != "Lab Technician":
        abort(403)

    items = BookingItem.query.join(Booking).filter(Booking.status == "Under Review").all()
    return render_template("medlab/samples_review.html", items=items)


@medlab.route("/samples/<int:sample_id>/enter-result", methods=["GET", "POST"])
@login_required
def enter_result(sample_id):

    sample = Sample.query.get_or_404(sample_id)
    form = ResultEntryForm()

    if form.validate_on_submit():

        TestResult.query.filter_by(sample_id=sample.id, parameter=form.parameter.data).delete()

        staff_record = Staff.query.filter_by(user_id=current_user.id).first()

        new_result = TestResult(
            sample_id=sample.id,
            parameter=form.parameter.data,
            value=form.value.data,
            unit=form.unit.data,
            entered_by=staff_record.id if staff_record else None
        )
        db.session.add(new_result)

        sample.status = "Completed"
        booking = sample.booking_item.booking
        all_done = all(
            item.sample and item.sample.status == "Completed"
            for item in booking.items
        )
        if all_done and not booking.report:
            db.session.add(Report(booking_id=booking.id))
        if all_done:
            booking.status = "Completed"

        db.session.commit()
        flash("Result added successfully!", "success")
        return redirect(url_for("medlab.enter_result", sample_id=sample.id))

    existing_results = TestResult.query.filter_by(sample_id=sample.id).all()
    return render_template("medlab/enter_result.html", sample=sample, form=form, results=existing_results)


@medlab.route("/my-bookings")
@login_required
def my_bookings():

    if current_user.role.name != "Patient":
        flash("This page is only for patients.", "danger")
        return redirect(url_for("auth.dashboard"))

    my_patient = Patient.query.filter_by(user_id=current_user.id).first()
    bookings = Booking.query.filter_by(patient_id=my_patient.id).order_by(Booking.created_at.desc()).all()
    return render_template("medlab/my_bookings.html", bookings=bookings)


@medlab.route("/patients/register", methods=["GET", "POST"])
@login_required
def register_walkin_patient():

    if current_user.role.name not in ["Receptionist", "Administrator"]:
        flash("Only receptionist/admin can register walk-in patients.", "danger")
        return redirect(url_for("auth.dashboard"))

    form = WalkInPatientForm()

    if form.validate_on_submit():

        while True:
            code = generate_patient_code()
            if not Patient.query.filter_by(patient_code=code).first():
                break


        new_patient = Patient(
            user_id=None,
            patient_code=code,
            full_name=form.full_name.data,
            phone=form.phone.data,
            address=form.address.data,
            dob=form.dob.data,
            gender=form.gender.data
        )
        db.session.add(new_patient)
        db.session.commit()

        flash("Patient registered successfully!", "success")
        return render_template("medlab/walkin_slip.html", patient=new_patient)

    return render_template("medlab/register_walkin.html", form=form)



@medlab.route("/reports/pending")
@login_required
def pending_reports():
    if current_user.role.name != "Pathologist":
        abort(403)

    reports = Report.query.filter_by(status="Pending Verification").all()
    return render_template("medlab/pending_reports.html", reports=reports)


@medlab.route("/reports/<int:report_id>/verify", methods=["POST"])
@login_required
def verify_report(report_id):
    report = Report.query.get_or_404(report_id)
    staff_record = Staff.query.filter_by(user_id=current_user.id).first()

    verification = ReportVerification(
        report_id=report.id,
        verified_by=staff_record.id if staff_record else None,
        verified_at=datetime.now(timezone.utc)
    )
    db.session.add(verification)
    report.status = "Verified"

    patient_user = report.booking.patient.user
    if patient_user and patient_user.email and "@medlab.walkin" not in patient_user.email:
        msg = Message("Your Report is Ready", recipients=[patient_user.email])
        msg.body = f"Hi {report.booking.patient.full_name}, your lab report is ready. Login to MedLab to view it."
        mail.send(msg)

    db.session.add(AuditLog(
        user_id=current_user.id, action="Verified Report",
        entity_type="Report", entity_id=report.id
    ))
    db.session.commit()

    flash("Report verified!", "success")
    return redirect(url_for("medlab.pending_reports"))


@medlab.route("/reports/<int:report_id>/unverify", methods=["POST"])
@login_required
def unverify_report(report_id):
    if current_user.role.name != "Pathologist":
        abort(403)

    report = Report.query.get_or_404(report_id)
    report.status = "Pending Verification"

    if report.verification:
        if isinstance(report.verification, list):
            for v in report.verification:
                db.session.delete(v)
        else:
            db.session.delete(report.verification)
    report.booking.status = "Under Review"

    db.session.add(AuditLog(
        user_id=current_user.id, action="Unverified Report",
        entity_type="Report", entity_id=report.id
    ))
    db.session.commit()

    flash("Report unverified. Sent back for review.", "info")
    return redirect(url_for("medlab.pending_reports"))


@medlab.route("/my-reports")
@login_required
def my_reports():
    my_patient = Patient.query.filter_by(user_id=current_user.id).first()
    reports = Report.query.join(Booking).filter(
        Booking.patient_id == my_patient.id,
        Report.status == "Verified"
    ).all()
    return render_template("medlab/my_reports.html", reports=reports)


@medlab.route("/reports/<int:report_id>/view")
@login_required
def view_report(report_id):
    report = Report.query.get_or_404(report_id)
    booking = report.booking
    return render_template("medlab/view_report.html", report=report, booking=booking)


@medlab.route("/reports/<int:report_id>/download")
@login_required
def download_report(report_id):
    report = Report.query.get_or_404(report_id)
    booking = report.booking
    age = _calc_age(booking.patient.dob)

    html = render_template("medlab/report_pdf.html", report=report, booking=booking, age=age)

    pdf_buffer = BytesIO()
    pisa.CreatePDF(html, dest=pdf_buffer)
    pdf_buffer.seek(0)

    response = make_response(pdf_buffer.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename=report_{report.id}.pdf"
    return response


@medlab.route("/reports/lookup", methods=["GET", "POST"])
@login_required
def lookup_report():
    if current_user.role.name not in ["Receptionist", "Administrator"]:
        flash("Not authorized.", "danger")
        return redirect(url_for("auth.dashboard"))

    search = request.args.get("search", "").strip()
    reports = []

    if search:
        reports = Report.query.join(Booking).join(Patient).filter(
            db.or_(
                Patient.patient_code.ilike(f"%{search}%"),
                Patient.full_name.ilike(f"%{search}%")
            ),
            Report.status == "Verified"
        ).all()

    return render_template("medlab/lookup_report.html", reports=reports, search=search)


@medlab.route("/booking/<int:booking_id>/slip")
@login_required
def booking_slip(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    return render_template("medlab/booking_slip.html", booking=booking)


@medlab.route("/bookings/<int:booking_id>/pay", methods=["GET", "POST"])
@login_required
def record_payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    my_patient = Patient.query.filter_by(user_id=current_user.id).first()

    is_owner = my_patient and booking.patient_id == my_patient.id
    is_staff = current_user.role.name in ("Receptionist", "Administrator")
    if not (is_owner or is_staff):
        abort(403)

    total = sum(item.price for item in booking.items)
    confirmed_paid = sum(p.amount for p in booking.payments if p.status == "Confirmed")
    remaining = total - confirmed_paid

    if remaining <= 0:
        flash("This booking is already fully paid.", "info")
        return redirect(url_for("medlab.my_bookings"))

    if request.method == "POST":
        method = request.form.get("method", "Cash")
        status = "Pending" if method == "Cash" else "Confirmed"

        db.session.add(Payment(booking_id=booking.id, amount=remaining, method=method, status=status))
        db.session.commit()
        flash("Payment recorded successfully.", "success")
        return redirect(url_for("medlab.my_bookings"))

    return render_template("medlab/payment_form.html", booking=booking, total=total, remaining=remaining)


@medlab.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    my_patient = Patient.query.filter_by(user_id=current_user.id).first()

    is_owner = my_patient and booking.patient_id == my_patient.id
    is_staff = current_user.role.name in ("Receptionist", "Administrator")
    if not (is_owner or is_staff):
        abort(403)

    booking.status = "Cancelled"
    db.session.commit()
    flash("Booking cancelled.", "info")
    return redirect(url_for("medlab.my_bookings"))


@medlab.route("/payments/<int:payment_id>/mark-received", methods=["POST"])
@login_required
def mark_payment_received(payment_id):
    if current_user.role.name not in ("Receptionist", "Administrator"):
        abort(403)

    payment = Payment.query.get_or_404(payment_id)
    payment.status = "Confirmed"
    db.session.commit()
    flash("Payment marked as received.", "success")
    return redirect(url_for("medlab.pending_samples"))


@medlab.route("/complaints/new", methods=["GET", "POST"])
@login_required
def new_complaint():
    if current_user.role.name != "Patient":
        flash("Only patients can file complaints.", "danger")
        return redirect(url_for("auth.dashboard"))

    my_patient = Patient.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":
        desc = request.form.get("description", "").strip()
        if not desc:
            flash("Description is required.", "danger")
        else:
            db.session.add(Complaint(patient_id=my_patient.id, description=desc))
            db.session.commit()
            flash("Complaint submitted.", "success")
            return redirect(url_for("medlab.new_complaint"))

    my_complaints = Complaint.query.filter_by(patient_id=my_patient.id).order_by(Complaint.created_at.desc()).all()
    return render_template("medlab/complaints.html", complaints=my_complaints)


@medlab.route("/complaints/manage")
@login_required
def manage_complaints():
    if current_user.role.name not in ["Administrator", "Receptionist"]:
        flash("Not authorized.", "danger")
        return redirect(url_for("auth.dashboard"))

    all_complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template("medlab/manage_complaints.html", complaints=all_complaints)


@medlab.route("/complaints/<int:complaint_id>/resolve", methods=["POST"])
@login_required
def resolve_complaint(complaint_id):
    c = Complaint.query.get_or_404(complaint_id)
    c.status = "Resolved"
    db.session.commit()
    flash("Complaint marked resolved.", "success")
    return redirect(url_for("medlab.manage_complaints"))


@medlab.route("/audit-logs")
@login_required
def audit_logs():
    if current_user.role.name != "Administrator":
        flash("Not authorized.", "danger")
        return redirect(url_for("auth.dashboard"))

    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return render_template("medlab/audit_logs.html", logs=logs)


@medlab.route("/admin/tests/add", methods=["GET", "POST"])
@login_required
def add_test():
    if current_user.role.name != "Administrator":
        abort(403)

    categories = TestCategory.query.all()

    if request.method == "POST":
        category_id = request.form.get("category_id")
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip()
        price = request.form.get("price")
        sample_type = request.form.get("sample_type", "").strip()
        turnaround_hours = request.form.get("turnaround_hours")

        if not name or not code or not price:
            flash("Name, code and price are required.", "danger")
            return render_template("medlab/add_test.html", categories=categories)

        if Test.query.filter_by(code=code).first():
            flash("Test code already exists.", "danger")
            return render_template("medlab/add_test.html", categories=categories)

        new_test = Test(
            category_id=category_id,
            name=name,
            code=code,
            price=float(price),
            sample_type=sample_type or None,
            turnaround_hours=int(turnaround_hours) if turnaround_hours else None
        )
        db.session.add(new_test)
        db.session.commit()
        flash("Test added successfully.", "success")
        return redirect(url_for("medlab.add_test"))

    return render_template("medlab/add_test.html", categories=categories)


@medlab.route("/admin/staff/add", methods=["GET", "POST"])
@login_required
def add_staff():
    if current_user.role.name != "Administrator":
        abort(403)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role_name = request.form.get("role_name")

        if not name or not email or not password or not role_name:
            flash("All fields are required.", "danger")
            return render_template("medlab/add_staff.html")

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("medlab/add_staff.html")

        role = Role.query.filter_by(name=role_name).first()
        if not role:
            flash("Invalid role.", "danger")
            return render_template("medlab/add_staff.html")

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if role_name != "Administrator":
            db.session.add(Staff(user_id=user.id, staff_type=role_name))

        db.session.commit()
        flash(f"{role_name} account created successfully.", "success")
        return redirect(url_for("medlab.add_staff"))

    return render_template("medlab/add_staff.html")