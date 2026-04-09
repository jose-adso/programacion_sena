from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
import os
import secrets
from urllib.parse import quote_plus
from sqlalchemy import inspect, text
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

    db_host = os.getenv("DB_HOST", "38.242.137.70")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "zJmO99T7siPFYb5BnMy9Ixrhn0UJZZo6hoHJjSmtSCa15T12hMJJ7bJ3Rdx0Nv5B")
    default_database_url = f"postgresql://{db_user}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", default_database_url)
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
    mail_username = os.getenv("MAIL_USERNAME", "ruedamoncadam@gmail.com").strip()
    mail_password = os.getenv("MAIL_PASSWORD", "fhsa hhek fnxg axlq").strip().replace(" ", "")

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
        from app.models import competency, training, users  # noqa: F401

        db.create_all()
        ensure_training_program_columns()
        ensure_competency_text_columns()
        ensure_base_super_admin()

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


def ensure_training_program_columns():
    """Agrega columnas nuevas y ajusta tamaños cuando no existe un sistema de migraciones."""
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    if "training_program" not in table_names:
        return

    columns = {column["name"]: column for column in inspector.get_columns("training_program")}

    if "scheduled_days" not in columns:
        db.session.execute(text("ALTER TABLE training_program ADD COLUMN scheduled_days VARCHAR(100)"))
        db.session.commit()

    program_name_column = columns.get("program_name")
    if program_name_column is not None:
        current_length = getattr(program_name_column["type"], "length", None)
        if current_length is not None and current_length < 255:
            db.session.execute(text("ALTER TABLE training_program ALTER COLUMN program_name TYPE VARCHAR(255)"))
            db.session.commit()

    location_column = columns.get("location_municipality")
    if location_column is not None:
        current_length = getattr(location_column["type"], "length", None)
        if current_length is not None and current_length < 150:
            db.session.execute(text("ALTER TABLE training_program ALTER COLUMN location_municipality TYPE VARCHAR(150)"))
            db.session.commit()


def ensure_competency_text_columns():
    """Amplía columnas de competencias a TEXT para soportar descripciones largas."""
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    for table_name in ("competency_record", "calendar_assignment"):
        if table_name not in table_names:
            continue

        columns = {column["name"]: column for column in inspector.get_columns(table_name)}
        competencia_column = columns.get("competencia")

        if competencia_column is None:
            continue

        current_length = getattr(competencia_column["type"], "length", None)
        if current_length is not None:
            db.session.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN competencia TYPE TEXT"))
            db.session.commit()


def ensure_base_super_admin():
    """Garantiza que la cuenta base de super admin exista y conserve su acceso."""
    from app.models.users import Users

    admin_username = "joserojas"
    admin_email = "jhoset40@gmail.com"
    admin_password = (os.getenv("ADMIN_PASSWORD") or "").strip()

    admin_user = Users.query.filter(
        (db.func.lower(Users.nombre) == admin_username.lower())
        | (db.func.lower(Users.correo) == admin_email)
    ).first()

    if not admin_user:
        password_to_use = admin_password or secrets.token_urlsafe(16)
        admin_user = Users(
            nombre=admin_username,
            correo=admin_email,
            telefono="",
            direccion="",
            rol="super admin",
            must_change_password=False,
            perfil_profesional=""
        )
        admin_user.password = password_to_use
        db.session.add(admin_user)
        db.session.commit()

        if not admin_password:
            print(f"\n🔐 Contraseña temporal del super admin generada: {password_to_use}")
            print("   Guárdala en la variable ADMIN_PASSWORD para mantenerla fija.\n")
        return

    updated = False

    if (admin_user.correo or "").strip().lower() != admin_email:
        admin_user.correo = admin_email
        updated = True

    if admin_user.rol != "super admin":
        admin_user.rol = "super admin"
        updated = True

    if admin_user.temp_rol is not None or admin_user.temp_rol_start is not None or admin_user.temp_rol_end is not None:
        admin_user.temp_rol = None
        admin_user.temp_rol_start = None
        admin_user.temp_rol_end = None
        updated = True

    if admin_user.must_change_password:
        admin_user.must_change_password = False
        updated = True

    if updated:
        db.session.commit()
