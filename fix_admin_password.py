from app import create_app, db
from app.models.users import Users

app = create_app()

with app.app_context():
    user = Users.query.filter_by(nombre='joserojas').first()
    if user:
        # Reseteamos la contraseña
        user.password = 'jhoset40@'
        db.session.commit()
        print(f"✅ Contraseña reseteada para {user.nombre}")
        print(f"Usuario: {user.nombre}")
        print(f"Correo: {user.correo}")
        print(f"Rol: {user.rol}")
        
        # Verificar que funciona
        if user.check_password('jhoset40@'):
            print("✅ La contraseña es correcta")
        else:
            print("❌ La contraseña NO es correcta")
    else:
        print("❌ Usuario no encontrado")
