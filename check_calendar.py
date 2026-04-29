from app import create_app, db
from app.models.competency import CalendarAssignment

app = create_app()
with app.app_context():
    # Count assignments
    count = CalendarAssignment.query.count()
    print(f"Total CalendarAssignment records: {count}")
    
    if count > 0:
        # Show first few
        assignments = CalendarAssignment.query.limit(5).all()
        for a in assignments:
            print(f"ID: {a.id}, Day: {a.day_number}, Hour: {a.hour}, Instructor: {a.instructor_name}, Subject: {a.subject}, ProgramID: {a.training_program_id}")
    else:
        print("No assignments found in the database.")
        
    # Also check if there are any training programs
    from app.models.training import TrainingProgram
    prog_count = TrainingProgram.query.count()
    print(f"Total TrainingProgram records: {prog_count}")
    if prog_count > 0:
        prog = TrainingProgram.query.first()
        print(f"First program: {prog.ficha_number} - {prog.program_name}")