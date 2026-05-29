#!/usr/bin/env bash
set -o errexit

# Устанавливаем зависимости
pip install --upgrade pip
pip install -r requirements.txt

# Применяем миграции Django
python manage.py migrate --noinput

# Собираем статические файлы
python manage.py collectstatic --noinput