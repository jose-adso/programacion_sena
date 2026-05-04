from app import create_app, db
import json

app = create_app()
with app.app_context():
    with app.test_client() as client:
        # Simulate a request to get_calendar_data for current month and year
        # We need to be logged in, so we'll use a test user or skip authentication for now?
        # Instead, let's just check the query directly.
        from app.models.competency import CalendarAssignment
        from datetime import datetime
        
        now = datetime.now()
        month = now.month - 1  # JavaScript months are 0-indexed
        year = now.year
        
        print(f"Checking for month={month}, year={year}")
        
        assignments = CalendarAssignment.query.filter_by(month=month, year=year).all()
        print(f"Found {len(assignments)} assignments for this month")
        
        if assignments:
            # Show first few
            for a in assignments[:5]:
                print(f"  Day: {a.day_number}, Hour: {a.hour}, Instructor: {a.instructor_name}, Subject: {a.subject}")
        else:
            print("No assignments found for current month.")
            
        # Also check if there are any assignments at all
        total = CalendarAssignment.query.count()
        print(f"Total assignments in DB: {total}")