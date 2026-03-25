from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import CheckConstraint
import secrets

from app import db
from datetime import datetime, timedelta


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(64), unique=True, nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(200))
    _password_hash = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), default="gestor")
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    perfil_profesional = db.Column(db.String(200))
    asignatura = db.Column(db.String(100))  # Asignatura o materia que dicta el instructor
    
    # Campos para rol temporal
    temp_rol = db.Column(db.String(20), nullable=True)  # Rol temporal
    temp_rol_start = db.Column(db.Date, nullable=True)  # Fecha de inicio del rol temporal
    temp_rol_end = db.Column(db.Date, nullable=True)    # Fecha de fin del rol temporal
    
    # Campos para recuperación de contraseña
    recovery_token = db.Column(db.String(64), nullable=True)  # Token de recuperación
    recovery_token_expires = db.Column(db.DateTime, nullable=True)  # Fecha de expiración del token
    
    __table_args__ = (
        CheckConstraint(rol.in_(['super admin', 'administrador', 'gestor', 'instructor']), name='valid_rol'),
    )
    
    @property
    def rol_activo(self):
        """Devuelve el rol activo (temporal si está vigente, sino el normal)"""
        if self.temp_rol and self.temp_rol_start and self.temp_rol_end:
            hoy = datetime.now().date()
            if self.temp_rol_start <= hoy <= self.temp_rol_end:
                return self.temp_rol
        return self.rol
    
    @property
    def tiene_rol_temporal(self):
        """Verifica si tiene un rol temporal vigente"""
        if self.temp_rol and self.temp_rol_start and self.temp_rol_end:
            hoy = datetime.now().date()
            return self.temp_rol_start <= hoy <= self.temp_rol_end
        return False
    
    @property
    def password(self):
        """Getter que devuelve un valor protegido para evitar exposición accidental"""
        return "[PROTEGIDO]"

    @password.setter
    def password(self, password):
        """Setter que hashea la contraseña y la almacena en _password_hash usando scrypt"""
        # Usar el método por defecto de Werkzeug que es scrypt (más seguro)
        self._password_hash = generate_password_hash(password, method='scrypt', salt_length=32)

    def check_password(self, password: str) -> bool:
        """Verifica la contraseña contra el hash almacenado"""
        return check_password_hash(self._password_hash, password)

    def has_used_password(self, password: str) -> bool:
        """Indica si la contraseña ya fue usada por el usuario (actual o histórica)."""
        if self._password_hash and check_password_hash(self._password_hash, password):
            return True

        if not self.id:
            return False

        history_records = PasswordHistory.query.filter_by(user_id=self.id).all()
        return any(check_password_hash(record.password_hash, password) for record in history_records)

    def update_password(self, password: str) -> bool:
        """Actualiza contraseña guardando el hash anterior en historial; retorna False si se repite."""
        if self.has_used_password(password):
            return False

        if self.id and self._password_hash:
            db.session.add(PasswordHistory(user_id=self.id, password_hash=self._password_hash))

        self.password = password
        return True
    
    def generate_recovery_token(self):
        """Genera un token de recuperación de contraseña"""
        # Generar token seguro
        token = secrets.token_hex(32)
        self.recovery_token = token
        # El token expira en 1 hora
        self.recovery_token_expires = datetime.now() + timedelta(hours=1)
        return token
    
    def verify_recovery_token(self, token: str) -> bool:
        """Verifica si el token de recuperación es válido"""
        if not self.recovery_token or not self.recovery_token_expires:
            return False
        
        # Verificar si el token ha expirado
        if datetime.now() > self.recovery_token_expires:
            # Limpiar token expirado
            self.recovery_token = None
            self.recovery_token_expires = None
            return False
        
        return self.recovery_token == token
    
    def clear_recovery_token(self):
        """Limpia el token de recuperación después de usarlo"""
        self.recovery_token = None
        self.recovery_token_expires = None

    def __repr__(self):
        return f"<Users {self.nombre}>"


class PasswordHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('Users', backref=db.backref('password_history', lazy=True, cascade='all, delete-orphan'))


class GestorEquipo(db.Model):
    """Relación entre un gestor y los instructores que conforman su equipo de trabajo."""
    __tablename__ = 'gestor_equipo'

    gestor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    gestor = db.relationship('Users', foreign_keys=[gestor_id],
                             backref=db.backref('equipo_miembros', lazy=True, cascade='all, delete-orphan'))
    instructor = db.relationship('Users', foreign_keys=[instructor_id])
