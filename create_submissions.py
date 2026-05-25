import os
import django
from datetime import timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from assignments.models import Task, Submission, TaskAssignment
from accounts.models import User
from django.utils import timezone

print('🚀 Создание работ студентов...')

# Получаем студентов и задачи
students = list(User.objects.filter(role='student'))
tasks = list(Task.objects.all())

print(f'Студентов: {len(students)}')
print(f'Задач: {len(tasks)}')

# Удаляем существующие работы (для чистоты эксперимента)
Submission.objects.all().delete()
print('✅ Удалены старые работы')

submissions_created = 0
graded_count = 0
pending_count = 0

for task in tasks[:20]:  # Первые 20 задач
    # Получаем назначения для этой задачи
    assignments = TaskAssignment.objects.filter(task=task)
    
    for assignment in assignments:
        student = assignment.student
        
        # 80% студентов сдали работу
        if random.random() < 0.8:
            # Определяем, опоздал ли студент
            is_late = random.random() < 0.2
            
            # Время отправки
            if is_late:
                submitted_at = task.deadline + timedelta(hours=random.randint(1, 48))
            else:
                submitted_at = task.deadline - timedelta(hours=random.randint(1, 72))
            
            # Статус
            status = 'graded' if random.random() < 0.6 else 'pending'
            
            # Оценка
            score = random.randint(60, 100) if status == 'graded' else None
            
            # Создаем работу
            submission = Submission.objects.create(
                task=task,
                student=student,
                task_assignment=assignment,
                file=f'submissions/{timezone.now().strftime("%Y/%m/%d")}/{student.username}_{task.id}.pdf',
                status=status,
                is_late=is_late,
                score=score,
                max_score=task.max_points,
                feedback='' if status == 'pending' else ('Отличная работа! 🎉' if score and score >= 85 else 'Хорошо, но есть над чем работать.' if score else 'Нужно доработать.'),
                graded_by=task.created_by if status == 'graded' else None,
                version=1
            )
            
            submissions_created += 1
            if status == 'graded':
                graded_count += 1
            else:
                pending_count += 1

print(f'\n📊 Статистика:')
print(f'   ✅ Создано работ: {submissions_created}')
print(f'   ✅ Проверено: {graded_count}')
print(f'   ✅ Ожидают проверки: {pending_count}')

# Итоговая статистика
print(f'\n📈 Общая статистика базы:')
print(f'   • Студентов: {User.objects.filter(role="student").count()}')
print(f'   • Задач: {Task.objects.count()}')
print(f'   • Назначений: {TaskAssignment.objects.count()}')
print(f'   • Работ: {Submission.objects.count()}')

print('\n🎉 Готово! Студенты могут отправлять работы.')
