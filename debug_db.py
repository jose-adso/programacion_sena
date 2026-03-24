import sqlite3
conn = sqlite3.connect('instance/site_new.db')
cursor = conn.cursor()
cursor.execute('SELECT id, nombre, correo, rol FROM users ORDER BY id DESC LIMIT 5')
rows = cursor.fetchall()
print('=== ULTIMOS 5 USUARIOS ===')
for row in rows:
    print(f'ID: {row[0]}, Nombre: {row[1]}, Correo: {row[2]}, Rol: {row[3]}')
conn.close()
