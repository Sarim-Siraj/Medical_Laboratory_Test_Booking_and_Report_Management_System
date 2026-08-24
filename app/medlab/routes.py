from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.medlab import medlab
from app.medlab.forms import BookingForm

from app.models.patient import Patient
from app.models.test import Test
from app.models.booking import Booking, BookingItem


@medlab.route("/book", methods=["GET", "POST"])
@login_required
def book_test():

    form = BookingForm()

    form.test_ids.choices = [
        (t.id, f"{t.name} - Rs.{t.price}") for t in Test.query.all()
    ]

    is_patient = current_user.role.name == "Patient"
    my_patient = None

    if is_patient:
        # Patient sirf apne liye book kar sakta hai
        my_patient = Patient.query.filter_by(user_id=current_user.id).first()
        form.patient_id.choices = [(my_patient.id, my_patient.full_name)]
        form.patient_id.data = my_patient.id
    else:
        # Receptionist/Admin kisi bhi patient ke liye book kar sakte hain
        form.patient_id.choices = [
            (p.id, p.full_name) for p in Patient.query.all()
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

        db.session.commit()

        flash("Booking created successfully!", "success")
        return redirect(url_for("medlab.book_test"))

    return render_template(
        "medlab/book_test.html",
        form=form,
        is_patient=is_patient
    )