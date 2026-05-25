import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from assignments.models import TaskAssignment, Task, Submission
from accounts.models import User

print(f'Задач: {Task.objects.count()}')
print(f'Назначений задач: {TaskAssignment.objects.count()}')
print(f'Работ: {Submission.objects.count()}')
print(f'Студентов: {User.objects.filter(role="student").count()}')

# Проверка первого студента
student = User.objects.filter(role='student').first()
if student:
    print(f'\nПервый студент: {student.username}')
    assignments = TaskAssignment.objects.filter(student=student)
    print(f'Назначений у этого студента: {assignments.count()}')
    
    submissions = Submission.objects.filter(student=student)
    print(f'Работ у этого студента: {submissions.count()}')