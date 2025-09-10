# Dockerfile
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Paquetes del sistema para compilar dependencias y esperar DB
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requisitos primero (mejor cache)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY src /app/src
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Variables por defecto dentro del contenedor
ENV DJANGO_SETTINGS_MODULE=backend.settings \
    PYTHONPATH=/app/src

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
