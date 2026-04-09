from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from flask_mail import Message
import re

from app.models.users import Users
from app import db, mail

auth_bp = Blueprint("auth", __name__)


def password_is_strong(password):
    """Valida mínimos de seguridad para una contraseña."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        return False
    return True


def find_user_for_login(identifier):
    """Permite iniciar sesión por nombre; para el super admin solo se acepta `joserojas`."""
    normalized_identifier = (identifier or "").strip().lower()
    if not normalized_identifier:
        return None

    user = Users.query.filter(db.func.lower(Users.nombre) == normalized_identifier).first()
    if user:
        return user

    user = Users.query.filter(db.func.lower(Users.correo).like(f"{normalized_identifier}@%")).first()
    if user and not user.is_base_super_admin:
        return user

    user = Users.query.filter(db.func.lower(Users.correo) == normalized_identifier).first()
    if user and not user.is_base_super_admin:
        return user

    return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password")
        user = find_user_for_login(username)

        if user and user.check_password(password):
            login_user(user)
            if getattr(user, "must_change_password", False):
                return redirect(url_for("auth.force_password_change"))
            return redirect(url_for("main.home"))

        flash("Usuario o contraseña incorrectos", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/cambiar-password-inicial", methods=["GET", "POST"])
def force_password_change():
    """Obliga al usuario a definir una contraseña nueva al primer ingreso."""
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    if not getattr(current_user, "must_change_password", False):
        return redirect(url_for("main.home"))

    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Las contraseñas no coinciden", "danger")
        elif not password_is_strong(password):
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula y un carácter especial", "danger")
        elif current_user.has_used_password(password):
            flash("No puedes reutilizar una contraseña que ya fue usada anteriormente", "danger")
        else:
            current_user.update_password(password)
            current_user.must_change_password = False
            db.session.commit()
            flash("Contraseña actualizada exitosamente", "success")
            return redirect(url_for("main.home"))

    return render_template("force_password_change.html")


@auth_bp.route("/recuperar", methods=["GET", "POST"])
def recover_request():
    """Página para solicitar recuperación de contraseña"""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    
    if request.method == "POST":
        correo = request.form.get("correo")
        user = Users.query.filter_by(correo=correo).first()
        
        if user:
            # Generar token de recuperación
            token = user.generate_recovery_token()
            db.session.commit()
            
            # Enviar correo con el token
            try:
                reset_url = url_for("auth.reset_password", user_id=user.id, token=token, _external=True)
                msg = Message(
                    subject="Recuperacion de Contrasena - Sistema de Competencias SENA",
                    recipients=[correo],
                    body=f"""
Hola {user.nombre},

Has solicitado recuperar tu contrasena en el Sistema de Competencias SENA.

Tu usuario para iniciar sesion es: {user.login_username}

O puedes hacer clic en el siguiente enlace para restablecer tu contrasena:
{reset_url}

Este token expira en 1 hora.

Si no solicitaste este cambio, por favor ignora este correo.

Saludos,
Sistema de Competencias SENA
"""
                )
                mail.send(msg)
                flash(f"Se ha enviado un correo con las instrucciones a {correo}", "success")
                return redirect(url_for("auth.login"))
            except Exception as e:
                error_msg = str(e)
                flash(f"No se pudo enviar el correo: {error_msg}", "warning")
                return redirect(url_for("auth.recover_request"))
        else:
            flash("El correo electrónico no está registrado", "danger")
    
    return render_template("recover_request.html")


@auth_bp.route("/recuperar/<int:user_id>/<token>", methods=["GET", "POST"])
def recover_token(user_id, token):
    """Página para mostrar el token y verificar"""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    
    user = Users.query.get_or_404(user_id)
    
    if request.method == "POST":
        input_token = request.form.get("token")
        
        if user.verify_recovery_token(input_token):
            return redirect(url_for("auth.reset_password", user_id=user.id, token=input_token))
        else:
            flash("Token inválido o expirado", "danger")
    
    return render_template("recover_token.html", user=user, token=token)


@auth_bp.route("/reset-password/<int:user_id>/<token>", methods=["GET", "POST"])
def reset_password(user_id, token):
    """Página para establecer nueva contraseña"""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    
    user = Users.query.get_or_404(user_id)
    
    # Verificar que el token sea válido antes de mostrar el formulario
    if not user.verify_recovery_token(token):
        flash("Token inválido o expirado. Por favor, solicite una nueva recuperación de contraseña.", "danger")
        return redirect(url_for("auth.recover_request"))
    
    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if password != confirm_password:
            flash("Las contraseñas no coinciden", "danger")
        elif not password_is_strong(password):
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula y un carácter especial", "danger")
        elif user.has_used_password(password):
            flash("No puedes reutilizar una contraseña que ya fue usada anteriormente", "danger")
        else:
            # Actualizar la contraseña
            user.update_password(password)
            # Si llegó por enlace de activación/recuperación, ya cumplió el cambio obligatorio.
            user.must_change_password = False
            user.clear_recovery_token()
            db.session.commit()
            
            flash("Contraseña actualizada exitosamente. Ahora puede iniciar sesión.", "success")
            return redirect(url_for("auth.login"))
    
    return render_template("reset_password.html", user=user, token=token)
