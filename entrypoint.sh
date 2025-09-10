#!/usr/bin/env bash
set -e

echo "Esperando a Postgres en $POSTGRES_HOST:$POSTGRES_PORT ..."
until nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 1
done
echo "Postgres listo."

# Migraciones
python /app/src/manage.py migrate --noinput

# Crear carpetas media necesarias
mkdir -p /app/src/media/uploads /app/src/media/outputs

# (Opcional) cargar data inicial o crear superusuario por variables, etc.

# Iniciar servidor de desarrollo
python /app/src/manage.py runserver 0.0.0.0:8000
