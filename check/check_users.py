from app import create_app, db
from app.models.users import Users

app = create_app()
with app.app_context():
    users = Users.query.all()
    print(f"Total users: {len(users)}")
    for u in users[:10]:  # Show first 10
        print(f"ID: {u.id}, Nombre: {u.nombre}, Rol: {u.rol}, Rol activo: {getattr(u, 'rol_activo', 'N/A')}")
    
    # Check for instructors specifically
    instructors = Users.query.filter(Users.rol == 'instructor').all()
    print(f"\nInstructors: {len(instructors)}")
    for i in instructors[:5]:
        print(f"  {i.nombre} - Asignatura: {getattr(i, 'asignatura', 'N/A')}")
        
    # Check for gestores
    gestores = Users.query.filter(Users.rol == 'gestor').all()
    print(f"\nGestores: {len(gestores)}")
    for g in gestores[:5]:
        print(f"  {g.nombre}")