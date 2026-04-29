from app import create_app, db
from app.models.users import Users
import os
import secrets

app = create_app()

with app.app_context():
    db.create_all()
    admin_email = os.environ.get('SUPER_ADMIN_EMAIL', 'superadmin@example.com')
    admin_name = os.environ.get('SUPER_ADMIN_NAME', 'superadmin')
    
    # Solo crear el usuario admin si no existe
    admin_user = Users.query.filter_by(nombre=admin_name).first()
    if not admin_user:
        admin_password = os.environ.get('ADMIN_PASSWORD', secrets.token_urlsafe(16))
        admin_user = Users(
            nombre=admin_name,
            correo=admin_email,
            telefono='',
            direccion='',
            rol='super admin'
        )
        admin_user.password = admin_password
        db.session.add(admin_user)
        db.session.commit()
        print(f"✅ Usuario admin '{admin_name}' creado.")
    else:
        # Actualizar contraseña si es necesario
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if admin_password and not admin_user.check_password(admin_password):
            admin_user.password = admin_password
            db.session.commit()
            print(f"✅ Contraseña del admin actualizada.")
    if admin_user.correo != admin_email:
        admin_user.correo = admin_email
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8010)))
