from app import create_app, db
from app.models.users import Users
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    user = Users.query.filter_by(nombre='joserojas').first()
    if user:
        # Set password to TestPassword123!
        new_password = 'TestPassword123!'
        user._password_hash = generate_password_hash(new_password)
        db.session.commit()
        print(f"Password reset for {user.nombre}")
        print(f"New password: {new_password}")
    else:
        print("User not found")
