from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Add the new column if it doesn't exist
    try:
        db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_super_admin_base BOOLEAN DEFAULT FALSE"))
        db.session.commit()
        print("✅ Columna is_super_admin_base agregada.")
    except Exception as e:
        print(f"Error agregando columna: {e}")
        db.session.rollback()