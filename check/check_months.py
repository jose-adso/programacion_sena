from app import create_app, db
from app.models.competency import CalendarAssignment

app = create_app()
with app.app_context():
    # Get all unique month/year combinations
    assignments = CalendarAssignment.query.all()
    
    months_years = {}
    for a in assignments:
        key = f"Month: {a.month}, Year: {a.year}"
        if key not in months_years:
            months_years[key] = 0
        months_years[key] += 1
    
    print("Months/Years with assignments:")
    for key in sorted(months_years.keys()):
        print(f"  {key} - {months_years[key]} assignments")
    
    # Check for April 2026 (month 3)
    april_2026 = CalendarAssignment.query.filter_by(month=3, year=2026).all()
    print(f"\nAssignments for April 2026 (month=3, year=2026): {len(april_2026)}")
    if april_2026:
        for a in april_2026[:3]:
            print(f"  Day: {a.day_number}, Hour: {a.hour}, Subject: {a.subject}")
