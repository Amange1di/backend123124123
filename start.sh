#!/usr/bin/env bash

echo "=== Starting Django Application ==="

# Проверяем переменные окружения
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'yes' || echo 'no')"
echo "DATABASE_URL length: ${#DATABASE_URL}"
echo "RENDER_POSTGRES set: $([ -n "$RENDER_POSTGRES" ] && echo 'yes' || echo 'no')"
echo "PORT: ${PORT:-8000}"

# Проверяем Python и зависимости
echo "=== Checking Python environment ==="
python --version
echo "Checking if gunicorn is installed..."
which gunicorn || pip show gunicorn

# Проверяем, может ли Django загрузиться
echo "=== Checking Django configuration ==="
python manage.py check --deploy || echo "WARNING: Django check found issues, continuing..."

# Применяем миграции
echo "=== Applying migrations ==="
if [ -n "$DATABASE_URL" ]; then
    echo "Running migrations with DATABASE_URL..."
    echo "First 30 chars of DATABASE_URL: ${DATABASE_URL:0:30}..."
    echo "Database type appears to be: ${DATABASE_URL%%://*}"
    
    # Пробуем проверить подключение к БД
    echo "Testing database connection..."
    python -c "
import os
import sys
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
from django.db import connection
cursor = connection.cursor()
print('Database connection successful!')
" || {
        echo "ERROR: Cannot connect to database!"
        exit 1
    }
    
    if ! python manage.py migrate --noinput --verbosity=2; then
        echo "ERROR: Migrations failed!"
        exit 1
    fi
    echo "Migrations completed successfully"
elif [ -n "$RENDER_POSTGRES" ]; then
    echo "Running migrations with RENDER_POSTGRES..."
    if ! python manage.py migrate --noinput --verbosity=2; then
        echo "ERROR: Migrations failed!"
        exit 1
    fi
else
    echo "WARNING: DATABASE_URL not set, using SQLite (NOT recommended for production)"
    if ! python manage.py migrate --noinput; then
        echo "ERROR: Migrations failed!"
        exit 1
    fi
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
echo "Will bind to 0.0.0.0:${PORT:-8000}"
exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --timeout 60 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile -
