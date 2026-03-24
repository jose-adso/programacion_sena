from app import create_app, db
from app.models.users import Users
import os
import secrets

app = create_app()

with app.app_context():
    db.create_all()
    admin_email = 'jhoset40@gmail.com'
    
    # Solo crear el usuario admin si no existe
    admin_user = Users.query.filter_by(nombre='joserojas').first()
    if not admin_user:
        admin_password = os.getenv('ADMIN_PASSWORD')
        if not admin_password:
            admin_password = secrets.token_urlsafe(16)
            print(f"\n🔐 Contraseña admin generada: {admin_password}")
            print(f"   Guárdala en la variable ADMIN_PASSWORD\n")
        
        admin_user = Users(
            nombre='joserojas',
            correo=admin_email,
            telefono='',
            direccion='',
            rol='super admin'
        )
        admin_user.password = admin_password
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Usuario admin 'joserojas' creado.")
    elif admin_user.correo != admin_email:
        admin_user.correo = admin_email
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8010)))
