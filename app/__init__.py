from flask import Flask, redirect, url_for  
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail

from config import Config

mail = Mail()
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
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

    @app.route("/")
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for("auth.dashboard"))
        return redirect(url_for("auth.login"))

    return app