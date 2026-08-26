from app.models.patient import Patient

from app.models.booking import Booking, BookingItem
from app.models.sample import Sample
from app.models.patient import Patient, generate_patient_code


from flask import (
    render_template,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

from app import db, login_manager

from app.auth import auth

from app.auth.forms import (
    LoginForm,
    RegisterForm
)

from app.models.user import User
from app.models.role import Role


@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )

@auth.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(
            url_for("auth.dashboard")
        )

    form = RegisterForm()

    if form.validate_on_submit():

        existing_user = User.query.filter_by(
            email=form.email.data.lower()
        ).first()

        if existing_user:

            flash(
                "Email already registered.",
                "danger"
            )

            return redirect(
                url_for("auth.register")
            )

        patient_role = Role.query.filter_by(
            name="Patient"
        ).first()

        if not patient_role:

            flash(
                "Patient role does not exist.",
                "danger"
            )

            return redirect(
                url_for("auth.register")
            )

        user = User(
            name=form.name.data,
            email=form.email.data.lower(),
            role=patient_role
        )

        user.set_password(
            form.password.data
        )

        db.session.add(user)
        db.session.flush()

        while True:
            code = generate_patient_code()
            if not Patient.query.filter_by(patient_code=code).first():
                break

        patient_profile = Patient(
            user_id=user.id,
            patient_code=code,
            full_name=form.name.data,
            phone=form.phone.data,
            address=form.address.data
        )

        db.session.add(patient_profile)
        db.session.commit()

        flash(
            "Registration successful. Please login.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "auth/register.html",
        form=form
    )

@auth.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(
            url_for("auth.dashboard")
        )

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(
            email=form.email.data.lower()
        ).first()

        if user and user.check_password(
            form.password.data
        ):

            if not user.is_active:

                flash(
                    "Your account is inactive.",
                    "danger"
                )

                return redirect(
                    url_for("auth.login")
                )

            login_user(user)

            flash(
                "Login successful!",
                "success"
            )

            return redirect(
                url_for("auth.dashboard")
            )

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template(
        "auth/login.html",
        form=form
    )


@auth.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "info"
    )

    return redirect(
        url_for("auth.login")
    )



@auth.route("/dashboard")
@login_required
def dashboard():

    role_name = current_user.role.name
    stats = {}

    if role_name == "Patient":
        section = "patient"

        my_patient = Patient.query.filter_by(user_id=current_user.id).first()

        if my_patient:
            stats["total_bookings"] = Booking.query.filter_by(patient_id=my_patient.id).count()
            stats["pending_bookings"] = Booking.query.filter_by(patient_id=my_patient.id, status="Pending").count()
        else:
            stats["total_bookings"] = 0
            stats["pending_bookings"] = 0

    elif role_name == "Administrator":
        section = "admin"

        stats["total_patients"] = Patient.query.count()
        stats["total_bookings"] = Booking.query.count()
        stats["total_revenue"] = db.session.query(
            db.func.coalesce(db.func.sum(BookingItem.price), 0)
        ).scalar()

    elif role_name == "Receptionist":
        section = "staff"

        stats["pending_samples"] = BookingItem.query.filter(
            ~BookingItem.sample.has()
        ).count()
        stats["today_bookings"] = Booking.query.count()   # abhi ke liye total, "aaj" wala filter baad mein

    elif role_name == "Lab Technician":
        section = "staff"

        stats["pending_results"] = Sample.query.filter_by(status="Collected").count()

    else:
        section = "staff"

    return render_template(
        "auth/dashboard.html",
        section=section,
        stats=stats
    )


@auth.route("/profile")
@login_required
def profile():

    patient_profile = None

    if current_user.role.name == "Patient":
        patient_profile = Patient.query.filter_by(user_id=current_user.id).first()

    return render_template(
        "auth/profile.html",
        patient_profile=patient_profile
    )