from app import db
from datetime import datetime

class TrainingProgram(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ficha_number = db.Column(db.String(20), unique=True, nullable=False)
    program_name = db.Column(db.String(100), nullable=False)
    classroom = db.Column(db.String(50))
    location_municipality = db.Column(db.String(100))  # AMB LUGAR O MUNICIPIO
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    scheduled_days = db.Column(db.String(100), nullable=True)  # Ej: lunes,martes,miercoles
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TrainingProgram {self.ficha_number}: {self.program_name}>'

    def get_scheduled_days(self):
        if not self.scheduled_days:
            return []
        return [day for day in self.scheduled_days.split(',') if day]

    def set_scheduled_days(self, days):
        self.scheduled_days = ','.join(days) if days else None

    def to_dict(self):
        return {
            'id': self.id,
            'ficha_number': self.ficha_number,
            'program_name': self.program_name,
            'classroom': self.classroom,
            'location_municipality': self.location_municipality,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'scheduled_days': self.get_scheduled_days(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }