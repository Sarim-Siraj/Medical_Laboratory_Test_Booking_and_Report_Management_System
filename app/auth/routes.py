from app.models.patient import Patient
from datetime import datetime, timezone



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
    recent_bookings = []
    queue = []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if role_name == "Patient":
        section = "patient"

        my_patient = Patient.query.filter_by(user_id=current_user.id).first()

        if my_patient:
            base_q = Booking.query.filter_by(patient_id=my_patient.id)

            stats["total_bookings"]     = base_q.count()
            stats["pending_bookings"]   = base_q.filter_by(status="Pending").count()
            stats["completed_bookings"] = base_q.filter_by(status="Completed").count()

            recent_bookings = base_q.order_by(Booking.created_at.desc()).limit(5).all()
        else:
            stats["total_bookings"]     = 0
            stats["pending_bookings"]   = 0
            stats["completed_bookings"] = 0

    elif role_name == "Administrator":
        section = "admin"

        stats["total_patients"] = Patient.query.count()
        stats["total_bookings"] = Booking.query.count()
        stats["total_revenue"]  = db.session.query(
            db.func.coalesce(db.func.sum(BookingItem.price), 0)
        ).scalar()

        recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()

    elif role_name == "Receptionist":
        section = "reception"

        pending_q = BookingItem.query.filter(~BookingItem.sample.has())

        stats["pending_samples"] = pending_q.count()
        stats["today_bookings"]  = Booking.query.filter(
            db.func.date(Booking.created_at) == today
        ).count()

        queue = pending_q.order_by(BookingItem.id.desc()).limit(6).all()

    elif role_name == "Lab Technician":
        section = "lab"

        collected_q = Sample.query.filter_by(status="Collected")

        stats["pending_results"] = collected_q.count()
        stats["today_collected"] = Sample.query.filter(
            db.func.date(Sample.collected_at) == today
        ).count()

        queue = collected_q.order_by(Sample.id.desc()).limit(6).all()

    else:
        section = "other"

    return render_template(
        "auth/dashboard.html",
        section=section,
        stats=stats,
        recent_bookings=recent_bookings,
        queue=queue,
        today_label=datetime.now(timezone.utc).strftime("%d %b %Y")
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