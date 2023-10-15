# Usar una imagen base de Python
FROM python:3.11-slim

# Establecer una variable de entorno para asegurarse de que la salida de Python se envía directamente al terminal
ENV PYTHONUNBUFFERED=1

# Copiar el archivo requirements.txt y instalar las dependencias
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Crear y cambiar al directorio de trabajo
WORKDIR /app

# Copiar el código fuente al directorio de trabajo
COPY src/ /app/

# Ejecutar uvicorn para iniciar la aplicación FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
