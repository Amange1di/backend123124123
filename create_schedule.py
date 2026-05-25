import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from courses.models import Course, Schedule
from datetime import time

print('🔧 Создание расписания для курсов...')

# Удаление старых расписаний
Schedule.objects.all().delete()
print('✅ Удалены старые расписания')

# Время пар
class_times = [
    (time(8, 0), time(9, 30), '301'),   # 1 пара
    (time(10, 0), time(11, 30), '302'), # 2 пара
    (time(12, 0), time(13, 30), '401'), # 3 пара
    (time(14, 0), time(15, 30), '402'), # 4 пара
]

# Дни недели: 1=Пн, 2=Вт, 3=Ср, 4=Чт, 5=Пт
days = [1, 2, 3, 4, 5]

courses = Course.objects.all()
print(f'Найдено курсов: {courses.count()}')

created_count = 0

for course in courses:
    # Создаем расписание для каждого курса (Пн-Пт, 1-2 пара)
    for day in days[:3]:  # Пн, Вт, Ср
        start_time, end_time, classroom = class_times[day - 1]
        
        schedule, created = Schedule.objects.get_or_create(
            course=course,
            day_of_week=day,
            start_time=start_time,
            end_time=end_time,
            defaults={'classroom': classroom, 'is_active': True}
        )
        
        if created:
            created_count += 1
            day_names = {1: 'Пн', 2: 'Вт', 3: 'Ср', 4: 'Чт', 5: 'Пт'}
            print(f'  ✅ {course.subject.name} — {course.group.group_name}: {day_names[day]} {start_time}-{end_time}')

print(f'\n✅ Создано занятий в расписании: {created_count}')
print(f'📊 Всего занятий: {Schedule.objects.count()}')