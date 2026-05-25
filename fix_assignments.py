import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from assignments.models import TaskAssignment, Task
from accounts.models import User, Group
from courses.models import Course

print('🔧 Исправление назначений задач...')

# Получаем всех студентов
students = list(User.objects.filter(role='student'))
print(f'Всего студентов: {len(students)}')

# Получаем все задачи
tasks = list(Task.objects.all())
print(f'Всего задач: {len(tasks)}')

# Проверяем существующие назначения
existing_assignments = TaskAssignment.objects.all()
print(f'Существующие назначения: {existing_assignments.count()}')

# Создаем назначения для ВСЕХ студентов на ВСЕ задачи (для демонстрации)
created_count = 0
for student in students:
    for task in tasks:
        variant = (student.id % 5) + 1
        assignment, created = TaskAssignment.objects.get_or_create(
            task=task,
            student=student,
            defaults={'variant_number': variant}
        )
        if created:
            created_count += 1

print(f'✅ Создано новых назначений: {created_count}')

# Проверка после создания
total_assignments = TaskAssignment.objects.count()
print(f'✅ Итого назначений: {total_assignments}')

# Проверка первого студента
student = User.objects.filter(role='student').first()
if student:
    assignments = student.taskassignment_set.count()
    print(f'📋 Назначений у первого студента ({student.username}): {assignments}')

print('\n✅ Назначения созданы успешно!')