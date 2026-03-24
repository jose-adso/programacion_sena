# Usar imagen oficial de Python
FROM python:3.11-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8010

# Copiar requirements.txt primero para aprovechar caché de Docker
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación
COPY . .

# Crear directorio instance si no existe
RUN mkdir -p instance

# Exponer el puerto
EXPOSE 8010

# Comando para ejecutar la aplicación
CMD ["python", "run.py"]
