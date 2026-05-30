#!/usr/bin/env bash

echo "=== Starting Django Application ==="

# Проверяем переменные окружения
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'yes' || echo 'no')"
echo "PORT: ${PORT:-8000}"

# Применяем миграции
echo "=== Applying migrations ==="
if [ -n "$DATABASE_URL" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput || {
        echo "ERROR: Migrations failed!"
        exit 1
    }
    echo "Migrations completed successfully"
else
    echo "WARNING: DATABASE_URL not set, using SQLite"
    python manage.py migrate --noinput || {
        echo "ERROR: Migrations failed!"
        exit 1
    }
fi

# Создаём тестовых пользователей (опционально)
echo "=== Creating test users ==="
python manage.py create_test_users || echo "Warning: create_test_users failed, continuing..."

# Запускаем Gunicorn
echo "=== Starting Gunicorn on port ${PORT:-8000} ==="
exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --timeout 60 \
    --keep-alive 5
