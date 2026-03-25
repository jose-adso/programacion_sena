from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from flask_mail import Message
from app.models.users import Users
from app import db, mail
from datetime import datetime, timedelta
import smtplib
import random
import string
from urllib.parse import urljoin


def enviar_link_activacion(correo_destino, nombre_usuario, reset_url):
    """Envía al usuario un enlace para definir su contraseña inicial."""
    msg = Message(
        subject="Activa tu cuenta - Sistema de Competencias SENA",
        recipients=[correo_destino],
        body=f"""
Hola {nombre_usuario},

Se ha creado una cuenta para ti en el Sistema de Competencias SENA.

Para activar tu acceso, define tu contraseña en el siguiente enlace:
{reset_url}

Este enlace expira en 1 hora.

Si no solicitaste este registro, ignora este correo.

Saludos,
Sistema de Competencias SENA
"""
    )
    try:
        mail.send(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            "No se pudo enviar el correo por autenticación SMTP. "
            "Verifique el correo remitente y la contraseña de aplicación en Gmail."
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            "No se pudo enviar el correo en este momento."
        ) from exc


def construir_reset_url(user_id, token):
    """Construye la URL pública de activación usando APP_BASE_URL si existe."""
    reset_path = url_for("auth.reset_password", user_id=user_id, token=token)
    app_base_url = (current_app.config.get("APP_BASE_URL") or "").strip()

    if app_base_url:
        return urljoin(app_base_url.rstrip("/") + "/", reset_path.lstrip("/"))

    return url_for("auth.reset_password", user_id=user_id, token=token, _external=True)

def generar_password_aleatoria(longitud=8):
    """Genera una contraseña aleatoria con al menos una mayúscula y un carácter especial"""
    # Garantizar al menos una mayúscula y un carácter especial
    mayusculas = string.ascii_uppercase
    especiales = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    digitos = string.digits
    minusculas = string.ascii_lowercase
    
    # Asegurar que tenga los requisitos
    password = [
        random.choice(mayusculas),  # Al menos una mayúscula
        random.choice(especiales),   # Al menos un carácter especial
        random.choice(digitos),      # Al menos un dígito
    ]
    
    # Llenar el resto con caracteres aleatorios
    todos = mayusculas + especiales + digitos + minusculas
    for _ in range(longitud - 3):
        password.append(random.choice(todos))
    
    # Mezclar la contraseña
    random.shuffle(password)
    return ''.join(password)

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/panel")
@login_required
def panel():
    is_base_super_admin = current_user.rol == "super admin"
    can_open_panel = current_user.rol_activo in ["super admin", "administrador", "gestor"] or is_base_super_admin

    # Super admin base puede entrar al panel para recuperar/cambiar su rol activo.
    if not can_open_panel:
        flash("No tienes permiso para acceder al panel de administrador", "danger")
        return redirect(url_for("main.home"))

    can_manage_users = current_user.rol_activo in ["super admin", "administrador"]

    # Si el super admin está actuando como otro rol, solo puede verse a sí mismo para cambiar de rol.
    if can_manage_users or current_user.rol_activo == "gestor":
        users = Users.query.all()
    else:
        users = [current_user]

    return render_template(
        "admin/panel.html",
        users=users,
        can_manage_users=can_manage_users,
        is_base_super_admin=is_base_super_admin,
    )


@admin_bp.route("/enviar-links-instructores", methods=["POST"])
@login_required
def enviar_links_instructores():
    """Envía enlace de asignación de contraseña a todos los instructores."""
    if current_user.rol_activo != "super admin":
        flash("Solo el super admin puede enviar enlaces masivos a instructores", "danger")
        return redirect(url_for("admin.panel"))

    instructors = Users.query.filter_by(rol="instructor").all()
    if not instructors:
        flash("No hay instructores registrados para enviar correos", "warning")
        return redirect(url_for("admin.panel"))

    sent = 0
    failed = 0

    for user in instructors:
        try:
            token = user.generate_recovery_token()
            user.must_change_password = True
            db.session.commit()

            reset_url = construir_reset_url(user.id, token)
            enviar_link_activacion(user.correo, user.nombre, reset_url)
            sent += 1
        except RuntimeError:
            db.session.rollback()
            failed += 1
        except Exception:
            db.session.rollback()
            failed += 1

    if sent:
        flash(f"Se enviaron enlaces de asignación de contraseña a {sent} instructores", "success")
    if failed:
        flash(f"No se pudo enviar el correo a {failed} instructores", "warning")

    return redirect(url_for("admin.panel"))

@admin_bp.route("/cambiar_rol/<int:user_id>", methods=["POST"])
@login_required
def cambiar_rol(user_id):
    """Cambiar el rol de un usuario temporalmente"""
    is_base_super_admin = current_user.rol == "super admin"
    is_active_admin = current_user.rol_activo in ["super admin", "administrador"]

    # Super admin base puede cambiar su propio rol aunque su rol activo sea otro.
    if not is_active_admin and not is_base_super_admin:
        return jsonify({"success": False, "error": "No tienes permiso"}), 403

    # Si super admin base está actuando como rol no administrativo, solo puede cambiarse a sí mismo.
    if is_base_super_admin and not is_active_admin and user_id != current_user.id:
        return jsonify({"success": False, "error": "Con tu rol activo actual solo puedes cambiar tu propio rol"}), 403
    
    data = request.get_json()
    nuevo_rol = data.get('rol')
    duracion = data.get('duracion')  # 'semana', 'mes', 'permanente'
    
    user = Users.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": "Usuario no encontrado"}), 404
    
    # Validar rol
    roles_validos = ["super admin", "administrador", "gestor", "instructor"]
    if nuevo_rol not in roles_validos:
        return jsonify({"success": False, "error": "Rol no válido"}), 400
    
    # Si es permanente o si el usuario actual no es super admin, no permitir crear super admin
    if nuevo_rol == "super admin" and not is_base_super_admin:
        return jsonify({"success": False, "error": "No tienes permiso para asignar rol de super admin"}), 403
    
    hoy = datetime.now().date()
    
    if duracion == 'permanente':
        # Establecer rol permanente
        user.rol = nuevo_rol
        user.temp_rol = None
        user.temp_rol_start = None
        user.temp_rol_end = None
        mensaje = f"Rol cambiado a {nuevo_rol} permanentemente"
    elif duracion == 'semana':
        # Rol temporal por una semana
        user.temp_rol = nuevo_rol
        user.temp_rol_start = hoy
        user.temp_rol_end = hoy + timedelta(days=7)
        mensaje = f"Rol cambiado a {nuevo_rol} por una semana"
    elif duracion == 'mes':
        # Rol temporal por un mes
        user.temp_rol = nuevo_rol
        user.temp_rol_start = hoy
        user.temp_rol_end = hoy + timedelta(days=30)
        mensaje = f"Rol cambiado a {nuevo_rol} por un mes"
    else:
        return jsonify({"success": False, "error": "Duración no válida"}), 400
    
    try:
        db.session.commit()
        return jsonify({"success": True, "message": mensaje})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/registrar", methods=["GET", "POST"])
@login_required
def registrar():
    # Super admin, administrador y gestor pueden ver la pantalla.
    if current_user.rol_activo not in ["super admin", "administrador", "gestor"]:
        flash("No tienes permiso para registrar usuarios", "danger")
        return redirect(url_for("main.home"))
    
    # Gestores solo pueden ver, no registrar
    if request.method == "POST" and current_user.rol_activo == "gestor":
        flash("Los gestores no pueden registrar usuarios", "danger")
        return redirect(url_for("admin.registrar"))
    
    if request.method == "POST":
        nombre = request.form.get("nombre")
        correo = request.form.get("correo")
        rol = request.form.get("rol")
        perfil_profesional = request.form.get("perfil_profesional", "").strip()
        
        # Generar contraseña base aleatoria (no se envía por correo)
        password = generar_password_aleatoria(8)
        
        # Validate role based on current user permissions
        if current_user.rol_activo == "super admin":
            # Super admin can create super admin, administrador, gestor, instructor
            if rol not in ["super admin", "administrador", "gestor", "instructor"]:
                flash("Rol no válido", "danger")
                return redirect(url_for("admin.registrar"))
        elif current_user.rol_activo == "administrador":
            # Administrador can create administrador, gestor, instructor
            if rol not in ["administrador", "gestor", "instructor"]:
                flash("Rol no válido. Solo se pueden registrar administradores, gestores o instructores", "danger")
                return redirect(url_for("admin.registrar"))
        else:
            # Gestor cannot create any users
            flash("No tienes permiso para registrar usuarios", "danger")
            return redirect(url_for("admin.panel"))
        
        # Check if user already exists
        existing_user = Users.query.filter_by(nombre=nombre).first()
        if existing_user:
            flash("El nombre de usuario ya existe", "danger")
            return redirect(url_for("admin.registrar"))
        
        existing_email = Users.query.filter_by(correo=correo).first()
        if existing_email:
            flash("El correo electrónico ya está registrado", "danger")
            return redirect(url_for("admin.registrar"))
        
        # Create new user with only required fields
        new_user = Users(
            nombre=nombre,
            correo=correo,
            telefono="",  # Empty as per requirement
            direccion="",  # Empty as per requirement
            password=password,  # Se hasheará automáticamente gracias al setter
            rol=rol,
            must_change_password=rol in ["administrador", "gestor", "instructor"],
            perfil_profesional=perfil_profesional
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()

            try:
                token = new_user.generate_recovery_token()
                db.session.commit()
                reset_url = construir_reset_url(new_user.id, token)
                enviar_link_activacion(correo, nombre, reset_url)
                flash(f"Usuario {nombre} registrado exitosamente como {rol}. Se envió enlace de activación al correo {correo}", "success")
            except RuntimeError as e:
                flash(f"Usuario {nombre} registrado exitosamente como {rol}. {e}", "warning")
            
            return redirect(url_for("admin.panel"))
        except Exception:
            db.session.rollback()
            flash("Error al registrar el usuario", "danger")
            return redirect(url_for("admin.registrar"))
    
    return render_template("admin/registrar.html", read_only=(current_user.rol_activo == "gestor"))

@admin_bp.route("/eliminar/<int:user_id>", methods=["POST"])
@login_required
def eliminar(user_id):
    # Only super admin can delete users
    if current_user.rol_activo not in ["super admin", "administrador"]:
        flash("No tienes permiso para eliminar usuarios", "danger")
        return redirect(url_for("main.home"))
    
    # Gestores solo pueden ver, no eliminar
    if current_user.rol_activo == "gestor":
        flash("Los gestores no pueden eliminar usuarios", "danger")
        return redirect(url_for("admin.panel"))
    
    # Prevent self-deletion
    if user_id == current_user.id:
        flash("No puedes eliminarte a ti mismo", "danger")
        return redirect(url_for("admin.panel"))
    
    user_to_delete = Users.query.get_or_404(user_id)
    
    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f"Usuario {user_to_delete.nombre} eliminado exitosamente", "success")
    except Exception:
        db.session.rollback()
        flash("Error al eliminar el usuario", "danger")
    
    return redirect(url_for("admin.panel"))


@admin_bp.route("/password_changes_by_week")
@login_required
def password_changes_by_week():
    if current_user.rol != "super admin":
        return jsonify({"error": "No autorizado"}), 403

    from app.models.users import PasswordHistory
    from calendar import monthrange
    import math

    year = request.args.get('year', type=int, default=datetime.now().year)
    month_0 = request.args.get('month', type=int, default=datetime.now().month - 1)
    month_1 = month_0 + 1  # convertir a 1-based

    days_in_month = monthrange(year, month_1)[1]
    start_dt = datetime(year, month_1, 1)
    end_dt = datetime(year, month_1, days_in_month, 23, 59, 59)

    records = (
        db.session.query(PasswordHistory, Users)
        .join(Users, Users.id == PasswordHistory.user_id)
        .filter(PasswordHistory.created_at >= start_dt,
                PasswordHistory.created_at <= end_dt)
        .order_by(PasswordHistory.created_at.desc())
        .all()
    )

    weeks = {}
    for ph, user in records:
        week_num = math.ceil(ph.created_at.day / 7)
        week_key = f"Semana {week_num}"
        if week_key not in weeks:
            weeks[week_key] = []
        weeks[week_key].append({
            "nombre": user.nombre,
            "rol": user.rol,
            "fecha": ph.created_at.strftime("%d/%m/%Y %H:%M")
        })

    return jsonify({"weeks": weeks, "total": len(records)})