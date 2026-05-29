#!/usr/bin/env bash
set -e

cd /opt/render/project/src/backend

echo "=== Starting Django Application ==="

# Применяем миграции
echo "=== Applying migrations ==="
python manage.py migrate --noinput || {
    echo "ERROR: Migrations failed!"
    exit 1
}

# Создаём тестовых пользователей (опционально, не прерываем при ошибке)
echo "=== Creating test users ==="
python manage.py create_test_users || echo "Warning: create_test_users command failed, continuing..."

# Запускаем Gunicorn
echo "=== Starting Gunicorn ==="
exec gunicorn backend.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
