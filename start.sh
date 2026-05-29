#!/usr/bin/env bash
set -e

echo "=== Starting Django Application ==="

# Применяем миграции (не прерываем если БД не настроена)
echo "=== Applying migrations ==="
if [ -n "$DATABASE_URL" ]; then
    python manage.py migrate --noinput || {
        echo "ERROR: Migrations failed!"
        exit 1
    }
else
    echo "WARNING: DATABASE_URL not set, skipping migrations"
fi

# Создаём тестовых пользователей (опционально, не прерываем при ошибке)
echo "=== Creating test users ==="
if [ -n "$DATABASE_URL" ]; then
    python manage.py create_test_users || echo "Warning: create_test_users command failed, continuing..."
fi

# Запускаем Gunicorn
echo "=== Starting Gunicorn ==="
exec gunicorn backend.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
