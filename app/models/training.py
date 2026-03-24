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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<TrainingProgram {self.ficha_number}: {self.program_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'ficha_number': self.ficha_number,
            'program_name': self.program_name,
            'classroom': self.classroom,
            'location_municipality': self.location_municipality,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }