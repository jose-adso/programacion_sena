from app import create_app, db
from app.models.users import Users
from app.models.competency import CalendarAssignment
import json

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

with app.app_context():
    # Get the admin user (assuming it exists)
    admin = Users.query.filter_by(rol='super admin').first()
    if not admin:
        # If not, create one (as in run.py)
        import os, secrets
        admin_email = os.environ.get('SUPER_ADMIN_EMAIL', 'superadmin@example.com')
        admin_name = os.environ.get('SUPER_ADMIN_NAME', 'superadmin')
        admin_password = os.environ.get('ADMIN_PASSWORD', secrets.token_urlsafe(16))
        admin = Users(
            nombre=admin_name,
            correo=admin_email,
            telefono='',
            direccion='',
            rol='super admin'
        )
        admin.password = admin_password
        db.session.add(admin)
        db.session.commit()
        print(f"Created admin user: {admin.nombre}")
    else:
        print(f"Using existing admin user: {admin.nombre}")

    # Now we need to simulate a login. We can use Flask-Login's login_user in a test request context.
    from flask_login import login_user
    with app.test_request_context():
        login_user(admin)
        # Now we can make a test request to the endpoint
        with app.test_client() as client:
            # We need to set the cookie for the session
            # Since we used login_user in a test_request_context, the session is available.
            # But let's just use the client and simulate login via POST? 
            # Instead, let's use the test client with the context we already have.
            # We'll make a GET request to the endpoint.
            response = client.get('/get_calendar_data?month=3&year=2026')  # April is month 3 (0-indexed)
            print(f"Status code: {response.status_code}")
            print(f"Response data: {response.get_data(as_text=True)}")
            try:
                data = json.loads(response.get_data(as_text=True))
                print(f"Parsed JSON: {data}")
                print(f"Number of keys in data: {len(data)}")
                if len(data) > 0:
                    # Show first few keys
                    for i, (key, val) in enumerate(data.items()):
                        if i < 5:
                            print(f"  {key}: {val}")
                        else:
                            break
                else:
                    print("No data returned.")
            except Exception as e:
                print(f"Error parsing JSON: {e}")