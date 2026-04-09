import psycopg2
import os

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "38.242.137.70"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "zJmO99T7siPFYb5BnMy9Ixrhn0UJZZo6hoHJjSmtSCa15T12hMJJ7bJ3Rdx0Nv5B")
    )

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("✅ Conexión exitosa")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        print(cursor.fetchone())
        cursor.close()
        conn.close()
    except Exception as e:
        print("❌ Error:", e)
