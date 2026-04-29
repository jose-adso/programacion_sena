from app import create_app, db
from app.models.users import Users

app = create_app()
with app.app_context():
    # Look for joserojas user
    user = Users.query.filter_by(nombre='joserojas').first()
    
    if user:
        print(f"User found: {user.nombre} ({user.correo})")
        print(f"Rol: {user.rol}")
        print(f"Rol activo: {user.rol_activo}")
        print(f"ID: {user.id}")
    else:
        print("User 'joserojas' not found")
        print("\nAll users:")
        users = Users.query.all()
        for u in users[:10]:
            print(f"  - {u.nombre} ({u.correo})")
