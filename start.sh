#!/usr/bin/env bash
set -e

echo "=== Starting Django Application ==="

# Проверяем наличие DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "Warning: DATABASE_URL not set. Using default SQLite."
fi

# Применяем миграции
echo "=== Applying migrations ==="
python manage.py migrate --noinput

# Создаём тестовых пользователей (опционально)
echo "=== Creating test users ==="
python create_test_users.py || echo "Warning: create_test_users.py failed, continuing..."

# Запускаем Gunicorn
echo "=== Starting Gunicorn ==="
exec gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120