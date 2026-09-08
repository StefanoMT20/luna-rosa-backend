#!/bin/sh
set -e

echo "==> Esperando a PostgreSQL en ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" >/dev/null 2>&1; do
  echo "    PostgreSQL no responde todavia, reintentando en 2s..."
  sleep 2
done
echo "==> PostgreSQL listo."

echo "==> Aplicando migraciones..."
python manage.py migrate --noinput

echo "==> Provisionando usuario dueña..."
python manage.py create_owner

echo "==> Recolectando archivos estaticos..."
python manage.py collectstatic --noinput

echo "==> Arrancando Gunicorn en 0.0.0.0:8000"
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-4}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
