from django.contrib.auth import get_user_model

User = get_user_model()

# Создаем админа
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123', role='admin')
    print('Администратор создан: admin / admin123')

# Создаем преподавателя
if not User.objects.filter(username='teacher').exists():
    User.objects.create_user('teacher', 'teacher@example.com', 'teacher123', role='teacher')
    print('Преподаватель создан: teacher / teacher123')

# Создаем студента
if not User.objects.filter(username='student').exists():
    User.objects.create_user('student', 'student@example.com', 'student123', role='student')
    print('Студент создан: student / student123')

print('\nВсе тестовые пользователи созданы!')
