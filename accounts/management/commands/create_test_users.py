from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Создание тестовых пользователей'

    def handle(self, *args, **kwargs):
        # Создаем админа
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123', role='admin')
            self.stdout.write(self.style.SUCCESS('Администратор создан: admin / admin123'))
        else:
            self.stdout.write('Администратор уже существует')

        # Создаем преподавателя
        if not User.objects.filter(username='teacher').exists():
            User.objects.create_user('teacher', 'teacher@example.com', 'teacher123', role='teacher')
            self.stdout.write(self.style.SUCCESS('Преподаватель создан: teacher / teacher123'))
        else:
            self.stdout.write('Преподаватель уже существует')

        # Создаем студента
        if not User.objects.filter(username='student').exists():
            User.objects.create_user('student', 'student@example.com', 'student123', role='student')
            self.stdout.write(self.style.SUCCESS('Студент создан: student / student123'))
        else:
            self.stdout.write('Студент уже существует')

        self.stdout.write(self.style.SUCCESS('\nВсе тестовые пользователи готовы!'))