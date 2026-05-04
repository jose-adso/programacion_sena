"""
Script para agregar 50 fichas a la base de datos
con fechas de inicio y terminación con diferencia de 6 o 9 meses
"""
import sqlite3
import os
from datetime import datetime, timedelta
import random

# Ruta de la base de datos
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'site_new.db')

# Lista de programas de formación
program_names = [
    "Análisis y Desarrollo de Software",
    "Gestión Administrativa",
    "Contabilidad y Finanzas",
    "Diseño e Integración de Multimedia",
    "Soporte y Mantenimiento de Equipos de Cómputo",
    "Logística Empresarial",
    "Mercadeo y Ventas",
    "Gestión de Recursos Humanos",
    "Producción Industrial",
    "Mantenimiento Electromecánico"
]

# Aula y municipio por defecto
default_classroom = "Aula 101"
default_municipality = "Bogotá D.C."

def agregar_meses(fecha, meses):
    """Agrega meses a una fecha"""
    mes = fecha.month - 1 + meses
    año = fecha.year + mes // 12
    mes = mes % 12 + 1
    dia = min(fecha.day, [31, 29 if año % 4 == 0 and (año % 100 != 0 or año % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1])
    return fecha.replace(year=año, month=mes, day=dia)

def insertar_fichas():
    """Inserta 50 fichas en la base de datos"""
    
    if not os.path.exists(db_path):
        print(f"Error: No se encontró la base de datos en {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar si la tabla existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='training_program'")
    if not cursor.fetchone():
        print("Error: La tabla training_program no existe")
        conn.close()
        return
    
    # Obtener el último número de ficha para continuar la secuencia
    cursor.execute("SELECT MAX(CAST(ficha_number AS INTEGER)) FROM training_program")
    last_ficha = cursor.fetchone()[0]
    if last_ficha is None:
        start_ficha = 2500001
    else:
        start_ficha = last_ficha + 1
    
    print(f"Iniciando desde ficha número: {start_ficha}")
    
    # Fecha de inicio base (comenzando desde enero 2025)
    base_date = datetime(2025, 1, 1).date()
    
    fichas_insertadas = 0
    
    for i in range(50):
        # Número de ficha
        ficha_number = str(start_ficha + i)
        
        # Programa de formación (rotativo)
        program_name = program_names[i % len(program_names)]
        
        # Fecha de inicio escalonada (cada 15 días)
        dias_inicio = i * 15
        start_date = (base_date + timedelta(days=dias_inicio)).strftime('%Y-%m-%d')
        
        # Duración: 6 o 9 meses aleatoriamente
        meses_duracion = random.choice([6, 9])
        end_date_obj = agregar_meses(datetime.strptime(start_date, '%Y-%m-%d'), meses_duracion)
        end_date = end_date_obj.strftime('%Y-%m-%d')
        
        # Insertar la ficha
        try:
            cursor.execute("""
                INSERT INTO training_program 
                (ficha_number, program_name, classroom, location_municipality, start_date, end_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ficha_number,
                program_name,
                default_classroom,
                default_municipality,
                start_date,
                end_date,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            fichas_insertadas += 1
            print(f"Ficha {ficha_number}: {program_name}")
            print(f"  Inicio: {start_date} - Fin: {end_date} ({meses_duracion} meses)")
        except sqlite3.Error as e:
            print(f"Error al insertar ficha {ficha_number}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n¡Se insertaron {fichas_insertadas} fichas exitosamente!")

if __name__ == "__main__":
    insertar_fichas()
