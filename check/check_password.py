from app import create_app, db
from app.models.users import Users

app = create_app()
with app.app_context():
    user = Users.query.filter_by(nombre='joserojas').first()
    if user:
        print(f"User: {user.nombre}")
        print(f"Password hash: {user._password_hash[:50]}...")
        
        # Try common passwords
        from werkzeug.security import check_password_hash
        
        test_passwords = ['password123', 'Password123!', 'Sena2024!', 'Admin123!', '123456', 'joserojas123']
        
        for pwd in test_passwords:
            if check_password_hash(user._password_hash, pwd):
                print(f"✓ Password is: {pwd}")
                break
        else:
            print("✗ None of the test passwords matched")
            
            # Check if password is empty or default
            if user._password_hash == '':
                print("Password hash is empty")
