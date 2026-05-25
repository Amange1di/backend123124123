import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Создаём пользователей
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser('admin', 'admin@test.com', 'admin123', role='admin')
    print(f'Created admin user: {admin.username} (ID: {admin.id})')

if not User.objects.filter(username='teacher').exists():
    teacher = User.objects.create_user('teacher', 'teacher@test.com', 'teacher123', role='teacher')
    print(f'Created teacher user: {teacher.username} (ID: {teacher.id})')

if not User.objects.filter(username='student').exists():
    student = User.objects.create_user('student', 'student@test.com', 'student123', role='student')
    print(f'Created student user: {student.username} (ID: {student.id})')

print('\nAll users created successfully!')
print('Login credentials:')
print('  admin/admin123')
print('  teacher/teacher123')
print('  student/student123')
