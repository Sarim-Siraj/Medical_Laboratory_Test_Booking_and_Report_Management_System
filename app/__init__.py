from flask import Flask, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
import os

from config import Config

mail = Mail()
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    mail.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    from app.models import user, role, patient, staff, test, booking, sample, test_result, report, notification, complaint, audit_log, payment
    from app.auth.routes import auth
    app.register_blueprint(auth)

    from app.medlab.routes import book_test
    from app.medlab import medlab
    app.register_blueprint(medlab)

    from app.api.routes import api
    app.register_blueprint(api, url_prefix="/api")

    from flask_login import current_user

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("auth.dashboard"))

        from app.models.test import Test
        tests = Test.query.limit(6).all()
        return render_template("landing.html", tests=tests)

    return app