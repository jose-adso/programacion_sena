from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.models.competency import CompetencyRecord, CalendarAssignment
from app.models.training import TrainingProgram
from app.models.users import Users, GestorEquipo
from app import db
from datetime import datetime

main_bp = Blueprint("main", __name__)


def _filter_query_by_professional_profile(query, professional_profile):
    """Filtra asignaciones por instructores cuyo perfil profesional coincida."""
    if not professional_profile:
        return query

    instructor_names = [
        user.nombre
        for user in Users.query.filter(
            Users.perfil_profesional.isnot(None),
            Users.perfil_profesional != ''
        ).filter(Users.perfil_profesional.ilike(f"%{professional_profile}%")).all()
    ]

    if not instructor_names:
        return query.filter(CalendarAssignment.id == -1)

    return query.filter(CalendarAssignment.instructor_name.in_(instructor_names))


@main_bp.route("/update_user_asignatura", methods=["POST"])
@login_required
def update_user_asignatura():
    """Actualizar la asignatura de un usuario (instructor/gestor)"""
    # Gestores solo pueden ver, no modificar
    if current_user.rol_activo == "gestor":
        return jsonify({"success": False, "error": "Los gestores no pueden modificar asignaturas"}), 403
    
    if current_user.rol_activo not in ["super admin", "administrador"]:
        return jsonify({"success": False, "error": "No autorizado"}), 403
    
    data = request.get_json()
    user_name = data.get('user_name')
    asignatura = data.get('asignatura')
    
    user = Users.query.filter_by(nombre=user_name).first()
    if not user:
        return jsonify({"success": False, "error": "Usuario no encontrado"}), 404
    
    user.asignatura = asignatura
    
    try:
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@main_bp.route("/update_my_professional_profile", methods=["POST"])
@login_required
def update_my_professional_profile():
    """Permite al instructor o gestor actualizar su propio perfil profesional."""
    if current_user.rol_activo not in ("instructor", "gestor"):
        return jsonify({"success": False, "error": "No tienes permiso para modificar el perfil profesional"}), 403

    data = request.get_json() or {}
    profile = (data.get("perfil_profesional") or "").strip()

    if current_user.perfil_profesional and current_user.perfil_profesional.strip():
        return jsonify({"success": False, "error": "El perfil profesional ya fue registrado y solo se puede guardar una vez"}), 400

    if not profile:
        return jsonify({"success": False, "error": "Debe ingresar un perfil profesional"}), 400

    if len(profile) > 200:
        return jsonify({"success": False, "error": "El perfil profesional no puede superar 200 caracteres"}), 400

    current_user.perfil_profesional = profile

    try:
        db.session.commit()
        return jsonify({"success": True, "perfil_profesional": current_user.perfil_profesional})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@main_bp.route("/")
def index():
    return render_template(
        "home.html",
        username=current_user.nombre if current_user.is_authenticated else "Invitado",
        current_user_rol=current_user.rol_activo if current_user.is_authenticated else None,
        current_user_asignatura=current_user.asignatura if current_user.is_authenticated else None
    )


@main_bp.route("/home")
@login_required
def home():
    import logging
    logger = logging.getLogger(__name__)
    
    # DEBUG: Log del usuario actual y su rol
    logger.info(f"DEBUG: Usuario actual: {current_user.nombre}, Rol: {current_user.rol}, Asignatura: {current_user.asignatura}")
    
    # Obtener lista de instructores únicos desde CompetencyRecord
    instructors = db.session.query(CompetencyRecord.instructor_name).distinct().all()
    instructors = [i[0] for i in instructors]
    
    logger.info(f"DEBUG: Instructores en CompetencyRecord: {instructors}")
    
    # Obtener usuarios con rol de gestor e instructor (excluir super admin y administrador)
    user_instructors = Users.query.filter(Users.rol.in_(['gestor', 'instructor'])).all()
    
    # Obtener lista de programas de formación (fichas)
    programs = TrainingProgram.query.all()
    
    # Obtener instructores sin asignaciones en la semana actual
    from datetime import timedelta
    today = datetime.now().date()
    # Calcular inicio de semana (lunes)
    start_of_week = today - timedelta(days=today.weekday())
    # Calcular fin de semana (domingo)
    end_of_week = start_of_week + timedelta(days=6)
    
    # Obtener instructores con asignaciones en la semana actual
    assignments_this_week = CalendarAssignment.query.filter(
        CalendarAssignment.year == today.year
    ).all()
    
    # Filtrar asignaciones de la semana actual
    instructors_with_assignments = set()
    for assign in assignments_this_week:
        try:
            assign_date = datetime(assign.year, assign.month + 1, assign.day_number).date()
            if start_of_week <= assign_date <= end_of_week:
                instructors_with_assignments.add(assign.instructor_name)
        except:
            pass
    
    # Crear lista de instructores sin asignaciones esta semana
    available_instructors = []
    for user in user_instructors:
        if user.nombre not in instructors_with_assignments:
            available_instructors.append(user)
    
    # También agregar instructores desde CompetencyRecord que no tengan asignaciones
    for inst in instructors:
        if inst not in instructors_with_assignments:
            # Verificar si ya está en la lista
            if not any(u.nombre == inst for u in available_instructors):
                available_instructors.append(type('obj', (object,), {'nombre': inst, 'rol': 'Instructor'})())
    
    # Solo instructores usan el filtro por asignatura propia.
    is_instructor = current_user.rol_activo == 'instructor'
    current_asignatura = current_user.asignatura if is_instructor else ''

    # Equipo de trabajo del gestor (solo aplica si el usuario es gestor)
    equipo_ids = []
    all_instructors = []
    if current_user.rol_activo == 'gestor':
        equipo = GestorEquipo.query.filter_by(gestor_id=current_user.id).all()
        equipo_ids = [e.instructor_id for e in equipo]
        all_instructors = [
            {"id": u.id, "nombre": u.nombre, "perfil_profesional": u.perfil_profesional or ""}
            for u in Users.query.filter_by(rol='instructor').order_by(Users.nombre).all()
        ]
        # Filtrar user_instructors y available_instructors al equipo del gestor
        equipo_nombres = {
            u.nombre for u in Users.query.filter(Users.id.in_(equipo_ids)).all()
        }
        user_instructors = [u for u in user_instructors if u.nombre in equipo_nombres]
        available_instructors = [u for u in available_instructors if getattr(u, 'nombre', None) in equipo_nombres]
        instructors = [i for i in instructors if i in equipo_nombres]

    return render_template("home.html", 
        username=current_user.nombre, 
        instructors=instructors, 
        programs=programs, 
        user_instructors=user_instructors, 
        available_instructors=available_instructors,
        current_user_rol=current_user.rol_activo,
        current_user_asignatura=current_asignatura,
        equipo_ids=equipo_ids,
        all_instructors=all_instructors)


@main_bp.route("/gestor/equipo", methods=["GET"])
@login_required
def get_gestor_equipo():
    if current_user.rol_activo != 'gestor':
        return jsonify({"error": "No autorizado"}), 403
    equipo = GestorEquipo.query.filter_by(gestor_id=current_user.id).all()
    return jsonify({"equipo": [e.instructor_id for e in equipo]})


@main_bp.route("/gestor/equipo", methods=["POST"])
@login_required
def save_gestor_equipo():
    if current_user.rol_activo != 'gestor':
        return jsonify({"error": "No autorizado"}), 403
    data = request.get_json()
    instructor_ids = data.get("instructor_ids", [])

    # Validar que todos los IDs pertenezcan a instructores reales
    valid_ids = {
        u.id for u in Users.query.filter(
            Users.id.in_(instructor_ids),
            Users.rol == 'instructor'
        ).all()
    }

    GestorEquipo.query.filter_by(gestor_id=current_user.id).delete()
    for iid in valid_ids:
        db.session.add(GestorEquipo(gestor_id=current_user.id, instructor_id=iid))
    db.session.commit()
    return jsonify({"success": True, "count": len(valid_ids)})


@main_bp.route("/get_calendar_data")
@login_required
def get_calendar_data():
    """Obtener datos del calendario con filtros opcionales"""
    month = int(request.args.get('month', 0))
    year = int(request.args.get('year', 2026))
    
    # Filtros opcionales
    program_id = request.args.get('program_id', type=int)  # Filtrar por ficha
    instructor_name = request.args.get('instructor_name')  # Filtrar por instructor
    professional_profile = (request.args.get('professional_profile') or '').strip()  # Filtrar por perfil profesional
    
    # Gestor ve solo su equipo de trabajo (solo lectura).
    is_admin = current_user.rol_activo in ['super admin', 'administrador', 'gestor']
    
    # Instructor solo puede ver sus propias asignaciones.
    if current_user.rol_activo == 'instructor':
        instructor_name = current_user.nombre
    
    # Obtener todas las asignaciones del mes con filtros
    query = CalendarAssignment.query.filter_by(month=month, year=year)
    
    if program_id:
        query = query.filter_by(training_program_id=program_id)
    
    if instructor_name:
        query = query.filter_by(instructor_name=instructor_name)
    elif current_user.rol_activo == 'gestor':
        # Filtrar solo instructores del equipo del gestor
        equipo = GestorEquipo.query.filter_by(gestor_id=current_user.id).all()
        equipo_ids = [e.instructor_id for e in equipo]
        if equipo_ids:
            equipo_nombres = [
                u.nombre for u in Users.query.filter(Users.id.in_(equipo_ids)).all()
            ]
            query = query.filter(CalendarAssignment.instructor_name.in_(equipo_nombres))
        else:
            query = query.filter(CalendarAssignment.id == -1)

    if professional_profile and current_user.rol_activo in ['super admin', 'administrador']:
        query = _filter_query_by_professional_profile(query, professional_profile)
    
    assignments = query.all()
    
    assignments_dict = {}
    for assign in assignments:
        key = f"{assign.day_number}-{assign.hour}"
        program = TrainingProgram.query.get(assign.training_program_id)
        program_name = program.program_name if program else "Unknown"
        ficha_number = program.ficha_number if program else ""
        assignments_dict[key] = {
            'instructor': assign.instructor_name,
            'subject': assign.subject,
            'program': program_name,
            'ficha': ficha_number,
            'program_id': assign.training_program_id,
            'competencia': assign.competencia or '',
            'resultado': assign.resultado or ''
        }
    
    return jsonify(assignments_dict)


@main_bp.route("/get_assignments_by_week")
@login_required
def get_assignments_by_week():
    """Obtener datos del calendario agrupados por semana"""
    import logging
    logger = logging.getLogger(__name__)
    
    month = int(request.args.get('month', 0))
    year = int(request.args.get('year', 2026))
    week = int(request.args.get('week', 0))  # Semana 0-4
    
    # DEBUG: Log de los parámetros recibidos
    logger.info(f"DEBUG get_assignments_by_week: usuario={current_user.nombre}, rol={current_user.rol_activo}, month={month}, year={year}, week={week}")
    
    # Filtros opcionales
    program_id = request.args.get('program_id', type=int)
    instructor_name = request.args.get('instructor_name')
    professional_profile = (request.args.get('professional_profile') or '').strip()
    
    logger.info(f"DEBUG get_assignments_by_week: program_id={program_id}, instructor_name={instructor_name}")
    
    # Gestor ve solo su equipo de trabajo (solo lectura).
    is_admin = current_user.rol_activo in ['super admin', 'administrador', 'gestor']
    
    # Instructor solo puede ver sus propias asignaciones.
    if current_user.rol_activo == 'instructor':
        instructor_name = current_user.nombre
        filter_subject = current_user.asignatura or None
        logger.info(f"DEBUG: Filtrando automáticamente por instructor: {instructor_name}, Asignatura: {filter_subject}")
    else:
        filter_subject = None
    
    # Calcular días de la semana
    first_day = datetime(year, month + 1, 1)
    start_day_of_week = first_day.weekday()  # 0 = Lunes, 6 = Domingo
    
    # Encontrar el primer lunes del mes
    first_monday = 1 if start_day_of_week == 0 else 8 - start_day_of_week
    
    # Calcular el rango de días para la semana seleccionada
    week_start = first_monday + (week * 7)
    week_end = week_start + 6
    
    # Obtener todas las asignaciones del mes con filtros
    query = CalendarAssignment.query.filter_by(month=month, year=year)
    
    if program_id:
        query = query.filter_by(training_program_id=program_id)
    
    if instructor_name:
        query = query.filter_by(instructor_name=instructor_name)
    elif current_user.rol_activo == 'gestor':
        equipo = GestorEquipo.query.filter_by(gestor_id=current_user.id).all()
        equipo_ids = [e.instructor_id for e in equipo]
        if equipo_ids:
            equipo_nombres = [
                u.nombre for u in Users.query.filter(Users.id.in_(equipo_ids)).all()
            ]
            query = query.filter(CalendarAssignment.instructor_name.in_(equipo_nombres))
        else:
            query = query.filter(CalendarAssignment.id == -1)

    if professional_profile and current_user.rol_activo in ['super admin', 'administrador']:
        query = _filter_query_by_professional_profile(query, professional_profile)
    
    # Filtrar por subject si el usuario tiene una asignatura asignada
    if filter_subject:
        query = query.filter_by(subject=filter_subject)
    
    assignments = query.all()
    
    logger.info(f"DEBUG: Total de asignaciones encontradas: {len(assignments)}")
    
    assignments_by_week = {}
    for assign in assignments:
        if week_start <= assign.day_number <= week_end:
            key = f"{assign.day_number}-{assign.hour}"
            program = TrainingProgram.query.get(assign.training_program_id)
            program_name = program.program_name if program else "Unknown"
            ficha_number = program.ficha_number if program else ""
            assignments_by_week[key] = {
                'id': assign.id,
                'instructor': assign.instructor_name,
                'subject': assign.subject,
                'program': program_name,
                'ficha': ficha_number,
                'program_id': assign.training_program_id,
                'day': assign.day,
                'hour': assign.hour,
                'competencia': assign.competencia or '',
                'resultado': assign.resultado or ''
            }
    
    # Información de la semana
    week_info = {
        'week_number': week,
        'start_day': max(1, week_start),
        'end_day': min(week_end, 31)
    }
    
    return jsonify({'assignments': assignments_by_week, 'week_info': week_info})


@main_bp.route("/get_current_assignments")
@login_required
def get_current_assignments():
    """Obtener las asignaciones actuales del mes con filtros para mostrar en el panel lateral"""
    month = int(request.args.get('month', 0))
    year = int(request.args.get('year', 2026))
    
    # Filtros opcionales
    program_id = request.args.get('program_id', type=int)
    instructor_name = request.args.get('instructor_name')
    professional_profile = (request.args.get('professional_profile') or '').strip()
    
    # Gestor ve solo su equipo de trabajo (solo lectura).
    is_admin = current_user.rol_activo in ['super admin', 'administrador', 'gestor']
    
    # Instructor solo puede ver sus propias asignaciones.
    if current_user.rol_activo == 'instructor':
        instructor_name = current_user.nombre
    
    # Obtener todas las asignaciones del mes con filtros
    query = CalendarAssignment.query.filter_by(month=month, year=year)
    
    if program_id:
        query = query.filter_by(training_program_id=program_id)
    
    if instructor_name:
        query = query.filter_by(instructor_name=instructor_name)
    elif current_user.rol_activo == 'gestor':
        equipo = GestorEquipo.query.filter_by(gestor_id=current_user.id).all()
        equipo_ids = [e.instructor_id for e in equipo]
        if equipo_ids:
            equipo_nombres = [
                u.nombre for u in Users.query.filter(Users.id.in_(equipo_ids)).all()
            ]
            query = query.filter(CalendarAssignment.instructor_name.in_(equipo_nombres))
        else:
            query = query.filter(CalendarAssignment.id == -1)

    if professional_profile and current_user.rol_activo in ['super admin', 'administrador']:
        query = _filter_query_by_professional_profile(query, professional_profile)
    
    assignments = query.all()
    
    # Agrupar por instructor
    instructors_dict = {}
    for assign in assignments:
        instructor = assign.instructor_name
        if instructor not in instructors_dict:
            instructors_dict[instructor] = []
        
        program = TrainingProgram.query.get(assign.training_program_id)
        program_name = program.program_name if program else "Unknown"
        ficha_number = program.ficha_number if program else ""
        classroom = (program.classroom or "") if program else ""
        location_municipality = (program.location_municipality or "") if program else ""
        
        instructors_dict[instructor].append({
            'subject': assign.subject,
            'day': assign.day,
            'day_number': assign.day_number,
            'hour': assign.hour,
            'ficha': ficha_number,
            'program': program_name,
            'classroom': classroom,
            'location_municipality': location_municipality
        })
    
    return jsonify(instructors_dict)


@main_bp.route("/save_assignment", methods=["POST"])
@login_required
def save_assignment():
    """Guardar una asignación de instructor"""
    # Gestores solo pueden ver, no modificar
    if current_user.rol_activo == "gestor":
        return jsonify({"success": False, "error": "Los gestores no pueden crear asignaciones"}), 403
    
    if current_user.rol_activo not in ["super admin", "administrador"]:
        return jsonify({"success": False, "error": "No autorizado"}), 403
    
    data = request.get_json()
    program_id = data.get('program_id')
    instructor = data.get('instructor')
    subject = data.get('subject')
    day = data.get('day')
    day_number = data.get('day_number')
    month = data.get('month')
    year = data.get('year')
    hour = data.get('hour')

    try:
        program_id = int(program_id)
        day_number = int(day_number)
        month = int(month)
        year = int(year)
        hour = int(hour)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Datos de fecha u horario inválidos"}), 400
    
    # Obtener el programa (ficha) para validar las fechas
    program = TrainingProgram.query.get(program_id)
    if not program:
        return jsonify({"success": False, "error": "Programa no encontrado"}), 404
    
    # El frontend usa meses 0-11; Python datetime usa meses 1-12.
    try:
        assignment_date = datetime(year, month + 1, day_number).date()
    except ValueError as e:
        return jsonify({"success": False, "error": f"Fecha inválida: {str(e)}"}), 400
    
    # Validar que la fecha de asignación esté dentro del rango de la ficha
    if program.start_date and program.end_date:
        if assignment_date < program.start_date:
            return jsonify({
                "success": False, 
                "error": f"La fecha de asignación ({assignment_date.strftime('%d/%m/%Y')}) no puede ser anterior a la fecha de inicio de la ficha ({program.start_date.strftime('%d/%m/%Y')})"
            }), 400
        if assignment_date > program.end_date:
            return jsonify({
                "success": False, 
                "error": f"La fecha de asignación ({assignment_date.strftime('%d/%m/%Y')}) no puede ser posterior a la fecha de fin de la ficha ({program.end_date.strftime('%d/%m/%Y')})"
            }), 400
    
    # Verificar si ya existe una asignación para ese día y hora
    existing = CalendarAssignment.query.filter_by(
        training_program_id=program_id,
        day_number=day_number,
        month=month,
        year=year,
        hour=hour
    ).first()
    
    if existing:
        # Actualizar existente
        existing.instructor_name = instructor
        existing.subject = subject
    else:
        # Crear nueva asignación
        new_assignment = CalendarAssignment(
            training_program_id=program_id,
            instructor_name=instructor,
            subject=subject,
            day=day,
            day_number=day_number,
            month=month,
            year=year,
            hour=hour
        )
        db.session.add(new_assignment)
    
    try:
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@main_bp.route("/remove_calendar_assignment", methods=["POST"])
@login_required
def remove_calendar_assignment():
    """Eliminar una asignación del calendario"""
    # Gestores solo pueden ver, no modificar
    if current_user.rol_activo == "gestor":
        return jsonify({"success": False, "error": "Los gestores no pueden eliminar asignaciones"}), 403
    
    if current_user.rol_activo not in ["super admin", "administrador"]:
        return jsonify({"success": False, "error": "No autorizado"}), 403
    
    data = request.get_json()
    program_id = data.get('program_id')
    day_number = data.get('day_number')
    month = data.get('month')
    year = data.get('year')
    hour = data.get('hour')
    
    assignment = CalendarAssignment.query.filter_by(
        training_program_id=program_id,
        day_number=day_number,
        month=month,
        year=year,
        hour=hour
    ).first()
    
    if assignment:
        db.session.delete(assignment)
        try:
            db.session.commit()
            return jsonify({"success": True})
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
    
    return jsonify({"success": True})


@main_bp.route("/update_assignment_competency", methods=["POST"])
@login_required
def update_assignment_competency():
    """Actualizar competencia y resultado de aprendizaje de una asignación"""
    # Gestores solo pueden ver, no modificar
    if current_user.rol_activo == "gestor":
        return jsonify({"success": False, "error": "Los gestores no pueden modificar competencias"}), 403
    
    if current_user.rol_activo not in ["super admin", "administrador"]:
        return jsonify({"success": False, "error": "No autorizado"}), 403
    
    data = request.get_json()
    assignment_id = data.get('assignment_id')
    competencia = data.get('competencia')
    resultado = data.get('resultado')
    
    assignment = CalendarAssignment.query.get(assignment_id)
    
    if not assignment:
        return jsonify({"success": False, "error": "Asignación no encontrada"}), 404
    
    assignment.competencia = competencia
    assignment.resultado = resultado
    assignment.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@main_bp.route("/save_weekly_competency", methods=["POST"])
@login_required
def save_weekly_competency():
    """Guardar competencia y resultado de aprendizaje para toda una semana (lunes a viernes)"""
    # Gestores solo pueden ver, no modificar
    if current_user.rol_activo == "gestor":
        return jsonify({"success": False, "error": "Los gestores no pueden guardar competencias"}), 403
    
    if current_user.rol_activo not in ["super admin", "administrador"]:
        return jsonify({"success": False, "error": "No autorizado"}), 403
    
    data = request.get_json()
    program_id = data.get('program_id')
    instructor_name = data.get('instructor')
    subject = data.get('subject')
    competencia = data.get('competencia')
    resultado = data.get('resultado')
    week_start = data.get('week_start')  # Día de inicio de la semana (número)
    week_end = data.get('week_end')      # Día de fin de la semana (número)
    month = data.get('month')
    year = data.get('year')
    
    if not all([program_id, instructor_name, subject, competencia, week_start, week_end, month, year]):
        return jsonify({"success": False, "error": "Faltan datos obligatorios"}), 400
    
    # Días de la semana que queremos actualizar (Lunes a Viernes)
    days_to_update = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    
    # Obtener todas las asignaciones que coincidan con los filtros
    assignments = CalendarAssignment.query.filter_by(
        training_program_id=program_id,
        instructor_name=instructor_name,
        subject=subject,
        month=month,
        year=year
    ).filter(
        CalendarAssignment.day_number >= week_start,
        CalendarAssignment.day_number <= week_end,
        CalendarAssignment.day.in_(days_to_update)
    ).all()
    
    updated_count = 0
    for assign in assignments:
        assign.competencia = competencia
        assign.resultado = resultado
        assign.updated_at = datetime.utcnow()
        updated_count += 1
    
    try:
        db.session.commit()
        return jsonify({"success": True, "updated_count": updated_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@main_bp.route("/get_month_weeks")
@login_required
def get_month_weeks():
    """Obtener todas las semanas de un mes con sus fechas (lunes a viernes)"""
    month = int(request.args.get('month', 0))
    year = int(request.args.get('year', 2026))
    
    from calendar import monthrange
    
    # Días del mes
    days_in_month = monthrange(year, month + 1)[1]
    
    # Calcular el primer día del mes
    first_day = datetime(year, month + 1, 1)
    start_day_of_week = first_day.weekday()  # 0 = Lunes, 6 = Domingo
    
    # Encontrar el primer lunes
    # Si el mes empieza en lunes (0): primer lunes = día 1
    # Si empieza en otro día: primer lunes = 8 - start_day_of_week
    first_monday = 1 if start_day_of_week == 0 else 8 - start_day_of_week
    
    # Generar semanas (lunes a viernes)
    weeks = []
    days_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    
    current_monday = first_monday
    week_num = 1
    
    while current_monday <= days_in_month:
        week_days = []
        for i, day_name in enumerate(days_es):
            day_num = current_monday + i
            if day_num <= days_in_month:
                week_days.append({
                    'day': day_name,
                    'day_number': day_num
                })
        
        if week_days:  # Solo agregar si hay días válidos
            # Crear texto descriptivo
            if len(week_days) == 5:
                label = f"Semana {week_num}: {week_days[0]['day']} {week_days[0]['day_number']} - {week_days[-1]['day']} {week_days[-1]['day_number']}"
            else:
                label = f"Semana {week_num}: {week_days[0]['day']} {week_days[0]['day_number']} - {week_days[-1]['day']} {week_days[-1]['day_number']}"
            
            weeks.append({
                'week_number': week_num - 1,  # 0-indexed para consistencia
                'label': label,
                'start': week_days[0]['day_number'],
                'end': week_days[-1]['day_number'],
                'days': week_days
            })
        
        current_monday += 7
        week_num += 1
    
    return jsonify({'weeks': weeks})


@main_bp.route("/get_week_dates")
@login_required
def get_week_dates():
    """Obtener las fechas de una semana específica (lunes a viernes)"""
    month = int(request.args.get('month', 0))
    year = int(request.args.get('year', 2026))
    week = int(request.args.get('week', 0))
    
    # Calcular el primer día del mes
    first_day = datetime(year, month + 1, 1)
    start_day_of_week = first_day.weekday()  # 0 = Lunes, 6 = Domingo
    
    # Calcular el inicio de la semana seleccionada (basado en semanas calendario)
    # week 0 = primera semana completa o parcial del mes
    # Encontrar el primer lunes del mes
    days_to_add = (7 - start_day_of_week) % 7
    first_monday = 1 + days_to_add if start_day_of_week > 0 else 1
    
    # Calcular el lunes de la semana seleccionada
    week_monday = first_monday + (week * 7)
    
    # Calcular los 5 días (lunes a viernes)
    week_days = []
    days_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    
    for i, day_name in enumerate(days_es):
        day_num = week_monday + i
        # Verificar que el día sea válido para el mes
        if month in [0, 2, 4, 6, 7, 9, 11]:  # 31 días
            max_day = 31
        elif month in [3, 5, 8, 10]:  # 30 días
            max_day = 30
        else:  # Febrero
            max_day = 28
        
        if 1 <= day_num <= max_day:
            week_days.append({
                'day': day_name,
                'day_number': day_num
            })
    
    # Calcular rango de la semana para filtrar
    week_start = week_days[0]['day_number'] if week_days else 1
    week_end = week_days[-1]['day_number'] if week_days else 5
    
    return jsonify({
        'week_days': week_days,
        'week_start': week_start,
        'week_end': week_end
    })
