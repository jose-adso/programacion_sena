from app import db
from datetime import datetime

class CompetencyRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    training_program_id = db.Column(db.Integer, db.ForeignKey('training_program.id'), nullable=False)
    competencia = db.Column(db.String(200), nullable=False)
    resultado = db.Column(db.Text, nullable=True)  # Resultado esperado o logrado
    instructor_name = db.Column(db.String(100), nullable=False)
    horario = db.Column(db.Text, nullable=True)  # JSON o string para horarios semanales
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación con TrainingProgram
    training_program = db.relationship('TrainingProgram', backref=db.backref('competency_records', lazy=True))

    def __repr__(self):
        return f'<CompetencyRecord {self.id}: {self.competencia}>'


class CalendarAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    training_program_id = db.Column(db.Integer, db.ForeignKey('training_program.id'), nullable=False)
    instructor_name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)  # Ej: TIC
    competencia = db.Column(db.String(200), nullable=True)  # Competencia asociada
    resultado = db.Column(db.Text, nullable=True)  # Resultado de aprendizaje
    day = db.Column(db.String(20), nullable=False)  # Lunes, Martes, etc.
    day_number = db.Column(db.Integer, nullable=False)  # Número del día del mes (1-31)
    month = db.Column(db.Integer, nullable=False)  # Mes (0-11)
    year = db.Column(db.Integer, nullable=False)  # Año
    hour = db.Column(db.Integer, nullable=False)  # Hora en formato 24h
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación con TrainingProgram
    training_program = db.relationship('TrainingProgram', backref=db.backref('calendar_assignments', lazy=True))

    def __repr__(self):
        return f'<CalendarAssignment {self.subject} {self.day} {self.hour}:00 - {self.instructor_name}>'
