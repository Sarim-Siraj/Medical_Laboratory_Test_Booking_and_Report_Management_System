from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

from config import Config


db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    from app.models import user, role, patient, staff, test, booking

    from app.auth.routes import auth
    app.register_blueprint(auth)

    from app.medlab.routes import book_test
    from app.medlab import medlab
    app.register_blueprint(medlab)

    return app