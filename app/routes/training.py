from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.training import TrainingProgram
from app import db
from datetime import datetime

training_bp = Blueprint("training", __name__)

WEEK_DAYS = [
    ("lunes", "Lunes"),
    ("martes", "Martes"),
    ("miercoles", "Miercoles"),
    ("jueves", "Jueves"),
    ("viernes", "Viernes"),
    ("sabado", "Sabado"),
    ("domingo", "Domingo"),
]


def normalize_scheduled_days(selected_days):
    day_order = {value: index for index, (value, _) in enumerate(WEEK_DAYS)}
    unique_days = []
    for day in selected_days:
        if day in day_order and day not in unique_days:
            unique_days.append(day)
    return sorted(unique_days, key=lambda day: day_order[day])

@training_bp.route("/programs")
@login_required
def programs():
    # Super admin, administrador y gestor pueden ver programas.
    if current_user.rol_activo not in ["super admin", "administrador", "gestor"]:
        flash("No tienes permiso para acceder a la gestión de programas de formación", "danger")
        return redirect(url_for("main.home"))
    
    programs = TrainingProgram.query.all()
    return render_template("training/programs.html", programs=programs)

@training_bp.route("/programs/add", methods=["GET", "POST"])
@login_required
def add_program():
    # Super admin, administrador y gestor pueden ver la pantalla.
    if current_user.rol_activo not in ["super admin", "administrador", "gestor"]:
        flash("No tienes permiso para agregar programas de formación", "danger")
        return redirect(url_for("main.home"))
    
    # Gestores solo pueden ver, no modificar
    if request.method == "POST" and current_user.rol_activo == "gestor":
        flash("Los gestores no pueden agregar programas", "danger")
        return redirect(url_for("training.programs"))
    
    if request.method == "POST":
        ficha_number = request.form.get("ficha_number")
        program_name = request.form.get("program_name")
        classroom = request.form.get("classroom")
        location_municipality = request.form.get("location_municipality")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        scheduled_days = normalize_scheduled_days(request.form.getlist("scheduled_days"))
        
        # Validaciones básicas
        if not ficha_number or not program_name or not start_date or not end_date:
            flash("Todos los campos marcados como obligatorios deben ser completados", "danger")
            return redirect(url_for("training.add_program"))

        if not scheduled_days:
            flash("Debes seleccionar al menos un dia de formacion", "danger")
            return redirect(url_for("training.add_program"))
        
        # Verificar si la ficha ya existe
        existing_ficha = TrainingProgram.query.filter_by(ficha_number=ficha_number).first()
        if existing_ficha:
            flash("Ya existe un programa con ese número de ficha", "danger")
            return redirect(url_for("training.add_program"))
        
        try:
            # Convertir strings de fecha a objetos date
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            new_program = TrainingProgram(
                ficha_number=ficha_number,
                program_name=program_name,
                classroom=classroom if classroom else None,
                location_municipality=location_municipality if location_municipality else None,
                start_date=start_date_obj,
                end_date=end_date_obj
            )
            new_program.set_scheduled_days(scheduled_days)
            
            db.session.add(new_program)
            db.session.commit()
            flash(f"Programa de formación '{program_name}' agregado exitosamente", "success")
            return redirect(url_for("training.programs"))
        except ValueError as e:
            flash("Formato de fecha inválido. Use YYYY-MM-DD", "danger")
            return redirect(url_for("training.add_program"))
        except Exception as e:
            db.session.rollback()
            flash("Error al agregar el programa de formación", "danger")
            return redirect(url_for("training.add_program"))
    
    return render_template(
        "training/add_program.html",
        read_only=(current_user.rol_activo == "gestor"),
        week_days=WEEK_DAYS,
    )

@training_bp.route("/programs/edit/<int:program_id>", methods=["GET", "POST"])
@login_required
def edit_program(program_id):
    # Super admin, administrador y gestor pueden ver la pantalla.
    if current_user.rol_activo not in ["super admin", "administrador", "gestor"]:
        flash("No tienes permiso para editar programas de formación", "danger")
        return redirect(url_for("main.home"))
    
    # Gestores solo pueden ver, no modificar
    if request.method == "POST" and current_user.rol_activo == "gestor":
        flash("Los gestores no pueden editar programas", "danger")
        return redirect(url_for("training.programs"))
    
    program = TrainingProgram.query.get_or_404(program_id)
    
    if request.method == "POST":
        ficha_number = request.form.get("ficha_number")
        program_name = request.form.get("program_name")
        classroom = request.form.get("classroom")
        location_municipality = request.form.get("location_municipality")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        scheduled_days = normalize_scheduled_days(request.form.getlist("scheduled_days"))
        
        # Validaciones básicas
        if not ficha_number or not program_name or not start_date or not end_date:
            flash("Todos los campos marcados como obligatorios deben ser completados", "danger")
            return redirect(url_for("training.edit_program", program_id=program_id))

        if not scheduled_days:
            flash("Debes seleccionar al menos un dia de formacion", "danger")
            return redirect(url_for("training.edit_program", program_id=program_id))
        
        # Verificar si la ficha ya existe en otro programa
        existing_ficha = TrainingProgram.query.filter_by(ficha_number=ficha_number).first()
        if existing_ficha and existing_ficha.id != program_id:
            flash("Ya existe otro programa con ese número de ficha", "danger")
            return redirect(url_for("training.edit_program", program_id=program_id))
        
        try:
            # Convertir strings de fecha a objetos date
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            program.ficha_number = ficha_number
            program.program_name = program_name
            program.classroom = classroom if classroom else None
            program.location_municipality = location_municipality if location_municipality else None
            program.start_date = start_date_obj
            program.end_date = end_date_obj
            program.set_scheduled_days(scheduled_days)
            program.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash(f"Programa de formación '{program_name}' actualizado exitosamente", "success")
            return redirect(url_for("training.programs"))
        except ValueError as e:
            flash("Formato de fecha inválido. Use YYYY-MM-DD", "danger")
            return redirect(url_for("training.edit_program", program_id=program_id))
        except Exception as e:
            db.session.rollback()
            flash("Error al actualizar el programa de formación", "danger")
            return redirect(url_for("training.edit_program", program_id=program_id))
    
    # Para GET request, mostrar el formulario con los datos actuales
    return render_template(
        "training/edit_program.html",
        program=program,
        read_only=(current_user.rol_activo == "gestor"),
        week_days=WEEK_DAYS,
    )

@training_bp.route("/programs/delete/<int:program_id>", methods=["POST"])
@login_required
def delete_program(program_id):
    # Only super admin can delete training programs
    if current_user.rol_activo not in ["super admin", "administrador"]:
        flash("No tienes permiso para eliminar programas de formación", "danger")
        return redirect(url_for("main.home"))
    
    # Gestores solo pueden ver, no eliminar
    if current_user.rol_activo == "gestor":
        flash("Los gestores no pueden eliminar programas", "danger")
        return redirect(url_for("training.programs"))
    
    program = TrainingProgram.query.get_or_404(program_id)
    
    try:
        # Eliminar primero los registros relacionados en otras tablas
        from app.models.competency import CompetencyRecord, CalendarAssignment
        
        # Eliminar CalendarAssignments relacionados
        CalendarAssignment.query.filter_by(training_program_id=program_id).delete()
        
        # Eliminar CompetencyRecords relacionados
        CompetencyRecord.query.filter_by(training_program_id=program_id).delete()
        
        # Ahora eliminar el programa
        db.session.delete(program)
        db.session.commit()
        flash(f"Programa de formación '{program.program_name}' eliminado exitosamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el programa de formación: {str(e)}", "danger")
    
    return redirect(url_for("training.programs"))