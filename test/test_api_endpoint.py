from app import create_app, db
from app.models.users import Users
from app.models.competency import CalendarAssignment
import json

app = create_app()

with app.app_context():
    with app.test_client() as client:
        # Get a user to test with
        user = Users.query.first()
        if user:
            print(f"Testing with user: {user.nombre} (rol: {user.rol_activo})")
            
            # Directly test the logic without authentication
            # Get assignments for April 2026
            month = 3
            year = 2026
            
            query = CalendarAssignment.query.filter_by(month=month, year=year)
            assignments = query.all()
            
            print(f"\nTotal assignments found in DB: {len(assignments)}")
            
            # Build the response dict as the endpoint would
            assignments_dict = {}
            for assign in assignments:
                key = f"{assign.day_number}-{assign.hour}"
                from app.models.training import TrainingProgram
                program = TrainingProgram.query.get(assign.training_program_id)
                program_name = program.program_name if program else "Unknown"
                ficha_number = program.ficha_number if program else ""
                assignments_dict[key] = {
                    'instructor': assign.instructor_name,
                    'subject': assign.subject,
                    'program': program_name,
                    'ficha': ficha_number,
                    'program_id': assign.training_program_id,
                    'competencia': assign.competencia or '',
                    'resultado': assign.resultado or ''
                }
            
            print(f"Response dict keys count: {len(assignments_dict)}")
            print("\nFirst 10 entries:")
            for i, (key, value) in enumerate(list(assignments_dict.items())[:10]):
                print(f"  {key}: {value}")
        else:
            print("No users found in database")
