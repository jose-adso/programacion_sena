import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "38.242.137.70"),
    port=os.getenv("DB_PORT", "5432"),
    database=os.getenv("DB_NAME", "postgres"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "zJmO99T7siPFYb5BnMy9Ixrhn0UJZZo6hoHJjSmtSCa15T12hMJJ7bJ3Rdx0Nv5B")
)

cur = conn.cursor()
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_super_admin_base BOOLEAN DEFAULT FALSE")
conn.commit()
cur.close()
conn.close()
print("Columna is_super_admin_base agregada.")