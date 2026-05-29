#!/usr/bin/env bash

echo "=== Starting Django Application ==="

# Проверяем переменные окружения
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'yes' || echo 'no')"
echo "DATABASE_URL length: ${#DATABASE_URL}"
echo "RENDER_POSTGRES set: $([ -n "$RENDER_POSTGRES" ] && echo 'yes' || echo 'no')"

# Применяем миграции
echo "=== Applying migrations ==="
if [ -n "$DATABASE_URL" ]; then
    echo "Running migrations with DATABASE_URL..."
    echo "First 20 chars of DATABASE_URL: ${DATABASE_URL:0:20}..."
    if ! python manage.py migrate --noinput --verbosity=2; then
        echo "ERROR: Migrations failed!"
        exit 1
    fi
elif [ -n "$RENDER_POSTGRES" ]; then
    echo "Running migrations with RENDER_POSTGRES..."
    if ! python manage.py migrate --noinput --verbosity=2; then
        echo "ERROR: Migrations failed!"
        exit 1
    fi
else
    echo "WARNING: DATABASE_URL not set, using SQLite (NOT recommended for production)"
    python manage.py migrate --noinput || {
        echo "ERROR: Migrations failed!"
        exit 1
    }
fi

# Создаём тестовых пользователей (опционально, не прерываем при ошибке)
echo "=== Creating test users ==="
if [ -n "$DATABASE_URL" ] || [ -n "$RENDER_POSTGRES" ]; then
    if ! python manage.py create_test_users; then
        echo "Warning: create_test_users command failed, continuing..."
    fi
fi

# Запускаем Gunicorn
echo "=== Starting Gunicorn ==="
exec gunicorn backend.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
