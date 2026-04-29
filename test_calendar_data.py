from app import create_app, db
from app.models.competency import CalendarAssignment

app = create_app()
with app.app_context():
    # Check specific assignments for April 2026 (month=3)
    april_data = CalendarAssignment.query.filter_by(month=3, year=2026).all()
    
    print(f"Total April 2026 assignments: {len(april_data)}")
    print("\nSample of assignments by day_number:")
    
    # Group by day
    by_day = {}
    for a in april_data:
        if a.day_number not in by_day:
            by_day[a.day_number] = []
        by_day[a.day_number].append(a)
    
    # Show first 5 days
    for day in sorted(by_day.keys())[:5]:
        assignments = by_day[day]
        print(f"\n  Day {day}: {len(assignments)} assignments")
        for a in assignments[:2]:
            print(f"    - Hour: {a.hour}, Subject: {a.subject}, Instructor: {a.instructor_name}")
