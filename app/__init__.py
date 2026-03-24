from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
import os
from sqlalchemy.exc import OperationalError

# Flask extensions (initialized here so they can be imported elsewhere)
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
mail = Mail()


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="../static")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:MB35mESjUg7B%40@75.119.147.138:5432/postgres"
    )
    app.config["APP_BASE_URL"] = os.getenv("APP_BASE_URL", "")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = 300  # 5 minutos en segundos
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": 30,
        "connect_args": {
            "connect_timeout": 10,
        },
    }

    # Configuración de Flask-Mail
    mail_username = os.getenv("MAIL_USERNAME", "jhoset40@gmail.com").strip()
    mail_password = os.getenv("MAIL_PASSWORD", "szdbqxqdhmnsaqei").strip().replace(" ", "")

    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = mail_username
    app.config["MAIL_PASSWORD"] = mail_password
    app.config["MAIL_DEFAULT_SENDER"] = mail_username

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    with app.app_context():
        db.create_all()

    from app.models.users import Users
    from datetime import datetime
    
    @login_manager.user_loader
    def load_user(user_id):
        try:
            user = db.session.get(Users, int(user_id))
        except OperationalError:
            db.session.remove()
            return None

        # Verificar si el rol temporal ha vencido y restaurarlo
        if user and user.temp_rol and user.temp_rol_end:
            hoy = datetime.now().date()
            if hoy > user.temp_rol_end:
                # El rol temporal ha vencido, restaurar al rol original
                # El rol original ya está almacenado en user.rol
                user.temp_rol = None
                user.temp_rol_start = None
                user.temp_rol_end = None
                db.session.commit()
        return user

    @app.before_request
    def enforce_initial_password_change():
        from flask import request, redirect, url_for
        from flask_login import current_user

        if not current_user.is_authenticated:
            return None

        endpoint = request.endpoint or ""
        allowed_endpoints = {"auth.force_password_change", "auth.logout", "static"}

        if getattr(current_user, "must_change_password", False) and endpoint not in allowed_endpoints:
            return redirect(url_for("auth.force_password_change"))

        return None

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.training import training_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(training_bp)

    return app
