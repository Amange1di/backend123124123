from django.core.management.base import BaseCommand
from accounts.models import User, Group, TeacherProfile
from courses.models import Subject, Course, Schedule
from assignments.models import Task
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Создание тестовых данных'

    def handle(self, *args, **kwargs):
        # Создаем админа
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@uni.ru',
                password='admin123',
                role='admin'
            )
            self.stdout.write(self.style.SUCCESS('Создан админ: admin / admin123'))
        else:
            admin = User.objects.get(username='admin')

        # Создаем преподавателя
        if not User.objects.filter(username='teacher1').exists():
            teacher = User.objects.create_user(
                username='teacher1',
                email='teacher1@uni.ru',
                password='teacher123',
                role='teacher',
                first_name='Иван',
                last_name='Иванов'
            )
            TeacherProfile.objects.create(
                user=teacher,
                department='Информатика',
                position='Доцент'
            )
            self.stdout.write(self.style.SUCCESS('Создан преподаватель: teacher1 / teacher123'))
        else:
            teacher = User.objects.get(username='teacher1')

        # Создаем группу
        group, _ = Group.objects.get_or_create(
            group_name='ПОВТ-1-24',
            defaults={
                'department': 'Информатика',
                'semester': 1,
                'year': 2024
            }
        )

        # Создаем студентов
        for i in range(1, 11):
            username = f'student{i}'
            if not User.objects.filter(username=username).exists():
                student = User.objects.create_user(
                    username=username,
                    email=f'student{i}@uni.ru',
                    password='student123',
                    role='student',
                    first_name=f'Студент{i}'
                )
                group.students.add(student)
        
        self.stdout.write(self.style.SUCCESS('Создано 10 студентов'))

        # Создаем предмет
        subject, _ = Subject.objects.get_or_create(
            code='CS101',
            defaults={
                'name': 'Python Backend',
                'description': 'Курс по разработке на Python/Django',
                'credit_hours': 4,
                'teacher': teacher
            }
        )

        # Создаем курс
        course, _ = Course.objects.get_or_create(
            subject=subject,
            group=group,
            semester=1,
            year=2024
        )
        course.students.set(group.students.all())

        self.stdout.write(self.style.SUCCESS('Создан курс: Python Backend - ПОВТ-1-24'))

        # Создаем расписание
        Schedule.objects.get_or_create(
            course=course,
            day_of_week=1,  # Понедельник
            start_time='08:00:00',
            end_time='09:30:00',
            classroom='301'
        )

        # Создаем задачу
        Task.objects.get_or_create(
            title='Первое задание: Django REST API',
            course=course,
            defaults={
                'description': 'Создайте REST API для управления задачами.',
                'created_by': teacher,
                'category': 'homework',
                'max_points': 100,
                'deadline': timezone.now() + timedelta(days=7)
            }
        )

        self.stdout.write(self.style.SUCCESS('Создана тестовая задача'))
        self.stdout.write(self.style.SUCCESS('\nТестовые данные созданы успешно!'))