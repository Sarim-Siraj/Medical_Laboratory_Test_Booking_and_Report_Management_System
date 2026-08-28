from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timezone

from flask import request

from app import db
from app.medlab import medlab
from app.medlab.forms import BookingForm

from app.models.patient import Patient
from app.models.test import Test, TestCategory
from app.models.booking import Booking, BookingItem

from app.models.sample import Sample
from app.models.staff import Staff

from app.models.test_result import TestResult
from app.medlab.forms import ResultEntryForm


from app.models.patient import Patient, generate_patient_code
from app.medlab.forms import WalkInPatientForm

from app.models.report import Report, ReportVerification

from app.models.complaint import Complaint

from app.models.audit_log import AuditLog

from flask import make_response
from xhtml2pdf import pisa
from io import BytesIO

from app.models.payment import Payment


import random
import string

from flask_mail import Message
from app import mail

def generate_sample_code():
    random_part = "".join(random.choices(string.digits, k=6))
    return f"SMP-{random_part}"


@medlab.route("/book", methods=["GET", "POST"])
@login_required
def book_test():

    form = BookingForm()

    all_tests = Test.query.order_by(Test.name).all()

    form.test_ids.choices = [
        (t.id, f"{t.name} - Rs.{t.price}") for t in all_tests
    ]

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

        selected_tests = Test.query.filter(
            Test.id.in_(form.test_ids.data)
        ).all()

        for t in selected_tests:
            item = BookingItem(
                booking_id=new_booking.id,
                test_id=t.id,
                price=t.price
            )
            db.session.add(item)



        total_price = sum(t.price for t in selected_tests)


        db.session.add(Payment(
            booking_id=new_booking.id,
            amount=total_price,
            method=form.payment_method.data,
            status="Paid"
        ))

        db.session.commit()
        flash("Booking created successfully!", "success")

        db.session.commit()

        flash("Booking created successfully!", "success")
        return redirect(url_for("medlab.book_test"))

    return render_template(
        "medlab/book_test.html",
        form=form,
        is_patient=is_patient,
        tests=all_tests,
        categories=categories
    )




from flask import request


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

    return render_template(
        "medlab/pending_samples.html",
        items=pending_items,
        search=search
    )


@medlab.route("/samples/collect/<int:item_id>", methods=["POST"])
@login_required
def collect_sample(item_id):

    booking_item = BookingItem.query.get_or_404(item_id)

    if booking_item.sample:
        flash("Sample already collected for this test.", "warning")
        return redirect(url_for("medlab.pending_samples"))

    staff_record = Staff.query.filter_by(user_id=current_user.id).first()

    # Unique sample code generate karo (agar clash ho toh dobara try karo)
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

    return render_template(
        "medlab/collected_samples.html",
        samples=samples,
        search=search
    )

@medlab.route("/samples/<int:sample_id>/enter-result", methods=["GET", "POST"])
@login_required
def enter_result(sample_id):

    sample = Sample.query.get_or_404(sample_id)
    form = ResultEntryForm()

    if form.validate_on_submit():

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
            for item in booking.items)
        if all_done and not booking.report:
            db.session.add(Report(booking_id=booking.id))

        if all_done:
            booking.status = "Completed"

        db.session.commit()

        flash("Result added successfully!", "success")
        return redirect(url_for("medlab.enter_result", sample_id=sample.id))

    existing_results = TestResult.query.filter_by(sample_id=sample.id).all()

    return render_template(
        "medlab/enter_result.html",
        sample=sample,
        form=form,
        results=existing_results
    )


@medlab.route("/my-bookings")
@login_required
def my_bookings():

    if current_user.role.name != "Patient":
        flash("This page is only for patients.", "danger")
        return redirect(url_for("auth.dashboard"))

    my_patient = Patient.query.filter_by(user_id=current_user.id).first()

    bookings = Booking.query.filter_by(
        patient_id=my_patient.id
    ).order_by(Booking.created_at.desc()).all()

    return render_template(
        "medlab/my_bookings.html",
        bookings=bookings
    )




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
        return render_template(
            "medlab/walkin_slip.html",
            patient=new_patient
        )

    return render_template("medlab/register_walkin.html", form=form)


@medlab.route("/reports/pending")
@login_required
def pending_reports():
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
        user_id=current_user.id,
        action="Verified Report",
        entity_type="Report",
        entity_id=report.id
        ))
    db.session.commit()

    flash("Report verified!", "success")
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

    html = render_template("medlab/report_pdf.html", report=report, booking=booking)

    pdf_buffer = BytesIO()
    pisa.CreatePDF(html, dest=pdf_buffer)
    pdf_buffer.seek(0)

    response = make_response(pdf_buffer.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename=report_{report.id}.pdf"
    return response