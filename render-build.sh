#!/usr/bin/env bash
set -o errexit

echo "=== Render Build Script ==="

# Проверяем переменные окружения
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo 'yes' || echo 'no')"

# Устанавливаем зависимости
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Применяем миграции только если есть DATABASE_URL
if [ -n "$DATABASE_URL" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput
else
    echo "WARNING: DATABASE_URL not set, skipping migrations"
fi

# Собираем статические файлы
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "=== Build complete ==="
