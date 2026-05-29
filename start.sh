#!/usr/bin/env bash
set -e

echo "=== Applying migrations ==="
python manage.py migrate --noinput

echo "=== Creating test users ==="
python create_test_users.py || true

echo "=== Starting server ==="
gunicorn backend.wsgi:application --log-file - --bind 0.0.0.0:$PORT
