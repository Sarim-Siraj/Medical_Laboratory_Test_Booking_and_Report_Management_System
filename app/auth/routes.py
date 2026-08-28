from app.models.patient import Patient
from datetime import datetime, timezone



from app.models.booking import Booking, BookingItem
from app.models.sample import Sample
from app.models.patient import Patient, generate_patient_code


from app.models.otp import OTP, generate_otp
from flask_mail import Message
from app import mail
from flask import session
from flask import request


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
    current_user,
    
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
        return redirect(url_for("auth.dashboard"))

    form = RegisterForm()

    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("auth.register"))

        session["pending_user"] = {
            "name": form.name.data,
            "email": form.email.data.lower(),
            "phone": form.phone.data,
            "address": form.address.data,
            "password": form.password.data
        }

        code = generate_otp()
        db.session.add(OTP(email=form.email.data.lower(), code=code))
        db.session.commit()

        msg = Message("Your MedLab OTP", recipients=[form.email.data.lower()])
        msg.body = f"Your verification code is: {code}"
        mail.send(msg)

        return redirect(url_for("auth.verify_otp"))

    return render_template("auth/register.html", form=form)


@auth.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    pending = session.get("pending_user")
    if not pending:
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        entered = request.form.get("code", "").strip()
        otp = OTP.query.filter_by(email=pending["email"], code=entered, is_used=False)\
                        .order_by(OTP.id.desc()).first()

        if not otp:
            flash("Invalid or expired code.", "danger")
            return render_template("auth/verify_otp.html")

        otp.is_used = True

        patient_role = Role.query.filter_by(name="Patient").first()
        user = User(name=pending["name"], email=pending["email"], role=patient_role)
        user.set_password(pending["password"])
        db.session.add(user)
        db.session.flush()

        while True:
            code = generate_patient_code()
            if not Patient.query.filter_by(patient_code=code).first():
                break

        db.session.add(Patient(
            user_id=user.id, patient_code=code,
            full_name=pending["name"], phone=pending["phone"], address=pending["address"]
        ))
        db.session.commit()
        session.pop("pending_user", None)

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/verify_otp.html")

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