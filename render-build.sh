#!/usr/bin/env bash
set -o errexit

echo "=== Render Build Script ==="

# Устанавливаем зависимости
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Применяем миграции
echo "Running migrations..."
python manage.py migrate --noinput

# Собираем статические файлы
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "=== Build complete ==="
