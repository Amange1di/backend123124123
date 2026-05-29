#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("=== Creating test users ===")

# Создаем админа
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123',
        role='admin'
    )
    print('✓ Администратор создан: admin / admin123')
else:
    print('ℹ Администратор уже существует')

# Создаем преподавателя
if not User.objects.filter(username='teacher').exists():
    User.objects.create_user(
        username='teacher',
        email='teacher@example.com',
        password='teacher123',
        role='teacher'
    )
    print('✓ Преподаватель создан: teacher / teacher123')
else:
    print('ℹ Преподаватель уже существует')

# Создаем студента
if not User.objects.filter(username='student').exists():
    User.objects.create_user(
        username='student',
        email='student@example.com',
        password='student123',
        role='student'
    )
    print('✓ Студент создан: student / student123')
else:
    print('ℹ Студент уже существует')

print('\n=== Все тестовые пользователи созданы! ===')