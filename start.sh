#!/usr/bin/env bash
set -e

echo "=== Starting Django Application ==="

# Применяем миграции
echo "=== Applying migrations ==="
python manage.py migrate --noinput || {
    echo "ERROR: Migrations failed!"
    exit 1
}

# Создаём тестовых пользователей (опционально, не прерываем при ошибке)
echo "=== Creating test users ==="
python create_test_users.py || echo "Warning: create_test_users.py failed, continuing..."

# Запускаем Gunicorn
echo "=== Starting Gunicorn ==="
exec gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
