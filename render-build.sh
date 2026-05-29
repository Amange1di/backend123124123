#!/usr/bin/env bash
# exit on error
set -o errexit

# Устанавливаем зависимости через pip
pip install --upgrade pip
pip install -r requirements.txt

# Применяем миграции Django
python manage.py migrate --noinput
