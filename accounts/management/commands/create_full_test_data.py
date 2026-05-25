from django.core.management.base import BaseCommand
from accounts.models import User, Group, TeacherProfile
from courses.models import Subject, Course, Schedule
from assignments.models import Task, TaskAssignment, Submission, Feedback
from django.utils import timezone
from datetime import timedelta
import random


class Command(BaseCommand):
    help = 'Создание полных тестовых данных для демонстрации'

    def handle(self, *args, **kwargs):
        self.stdout.write('🚀 Начинаем создание тестовых данных...\n')

        # === 1. СОЗДАНИЕ АДМИНА ===
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@uni.ru',
                password='admin123',
                role='admin',
                first_name='Администратор',
                last_name='Системы'
            )
            self.stdout.write(self.style.SUCCESS('✅ Админ: admin / admin123'))
        else:
            admin = User.objects.get(username='admin')

        # === 2. СОЗДАНИЕ ПРЕПОДАВАТЕЛЕЙ ===
        teachers_data = [
            ('teacher1', 'Иван', 'Иванов', 'Информатика', 'Доцент'),
            ('teacher2', 'Петр', 'Петров', 'Математика', 'Профессор'),
            ('teacher3', 'Анна', 'Сидорова', 'Программирование', 'Доцент'),
        ]

        teachers = {}
        for username, first_name, last_name, dept, position in teachers_data:
            if not User.objects.filter(username=username).exists():
                teacher = User.objects.create_user(
                    username=username,
                    email=f'{username}@uni.ru',
                    password='teacher123',
                    role='teacher',
                    first_name=first_name,
                    last_name=last_name
                )
                TeacherProfile.objects.create(
                    user=teacher,
                    department=dept,
                    position=position
                )
                self.stdout.write(self.style.SUCCESS(f'✅ Преподаватель: {username} / teacher123'))
            else:
                teacher = User.objects.get(username=username)
            teachers[username] = teacher

        # === 3. СОЗДАНИЕ ГРУПП ===
        groups_data = [
            ('ПОВТ-1-24', 'Информатика', 1, 2024),
            ('ПОВТ-2-24', 'Информатика', 2, 2024),
            ('ПМ-1-24', 'Математика', 1, 2024),
        ]

        groups = {}
        for group_name, dept, semester, year in groups_data:
            group, created = Group.objects.get_or_create(
                group_name=group_name,
                defaults={
                    'department': dept,
                    'semester': semester,
                    'year': year
                }
            )
            groups[group_name] = group
            status = 'создана' if created else 'найдена'
            self.stdout.write(self.style.SUCCESS(f'✅ Группа {group_name} {status}'))

        # === 4. СОЗДАНИЕ СТУДЕНТОВ ===
        students_per_group = 8
        all_students = []

        for group_name, group in groups.items():
            for i in range(1, students_per_group + 1):
                username = f'std_{group_name.replace("-", "_")}_{i}'
                if not User.objects.filter(username=username).exists():
                    student = User.objects.create_user(
                        username=username,
                        email=f'{username}@uni.ru',
                        password='student123',
                        role='student',
                        first_name=f'Студент{i}',
                        last_name=f'{group_name.split("-")[0]}ский'
                    )
                    group.students.add(student)
                    all_students.append(student)
                else:
                    all_students.append(User.objects.get(username=username))

        self.stdout.write(self.style.SUCCESS(f'✅ Создано {len(all_students)} студентов\n'))

        # === 5. СОЗДАНИЕ ПРЕДМЕТОВ ===
        subjects_data = [
            ('Python Backend', 'Разработка REST API на Django', 4, 'teacher1', 1, 2024),
            ('JavaScript', 'Современный JS и React', 4, 'teacher2', 1, 2024),
            ('Базы данных', 'Проектирование и работа с БД', 3, 'teacher1', 2, 2024),
            ('Алгоритмы', 'Структуры данных и алгоритмы', 4, 'teacher3', 1, 2024),
            ('Web Development', 'Full-stack разработка', 5, 'teacher3', 2, 2024),
        ]

        subjects = {}
        for name, description, credits, teacher_username, semester, year in subjects_data:
            teacher = teachers.get(teacher_username, teachers['teacher1'])
            subject, created = Subject.objects.get_or_create(
                code=name[:4].upper(),
                defaults={
                    'name': name,
                    'description': description,
                    'credit_hours': credits,
                    'teacher': teacher,
                    'semester': semester,
                    'year': year
                }
            )
            subjects[name] = subject
            status = 'создан' if created else 'найден'
            self.stdout.write(self.style.SUCCESS(f'✅ Предмет "{name}" {status}'))

        self.stdout.write('\n')

        # === 6. СОЗДАНИЕ КУРСОВ ===
        courses = []
        course_tasks = {
            'Python Backend': [
                ('Введение в Django', 'Создайте простой Django проект с базовой моделью', 'homework', 50),
                ('REST API Basics', 'Создайте REST API для CRUD операций', 'homework', 100),
                ('Advanced Serializers', 'Реализуйте вложенные сериализаторы', 'lab', 80),
                ('Authentication', 'Добавьте JWT аутентификацию', 'project', 150),
                ('Testing API', 'Напишите тесты для вашего API', 'lab', 70),
            ],
            'JavaScript': [
                ('ES6+ Features', 'Используйте современные возможности JS', 'homework', 60),
                ('React Components', 'Создайте компоненты React приложения', 'lab', 100),
                ('State Management', 'Реализуйте управление состоянием', 'project', 120),
                ('Hooks Deep Dive', 'Используйте хуки в реальном проекте', 'homework', 80),
            ],
            'Базы данных': [
                ('SQL Basics', 'Напишите сложные SQL запросы', 'homework', 50),
                ('Database Design', 'Спроектируйте БД для интернет-магазина', 'project', 100),
                ('Indexing', 'Оптимизируйте запросы с помощью индексов', 'lab', 70),
                ('NoSQL Introduction', 'Работа с MongoDB', 'homework', 60),
            ],
            'Алгоритмы': [
                ('Sorting Algorithms', 'Реализуйте сортировки', 'homework', 50),
                ('Graph Algorithms', 'Алгоритмы на графах', 'lab', 100),
                ('Dynamic Programming', 'Задачи динамического программирования', 'project', 120),
                ('Tree Structures', 'Работа с деревьями', 'homework', 70),
            ],
            'Web Development': [
                ('Full-stack App', 'Создайте полное веб-приложение', 'project', 200),
                ('Deployment', 'Разверните приложение на сервере', 'lab', 80),
                ('Performance', 'Оптимизируйте производительность', 'homework', 60),
            ],
        }

        for subject_name, subject in subjects.items():
            for group_name, group in list(groups.items())[:2]:  # Первые 2 группы
                teacher = subject.teacher
                course, created = Course.objects.get_or_create(
                    subject=subject,
                    group=group,
                    defaults={
                        'semester': 1,
                        'year': 2024,
                    }
                )
                course.students.set(group.students.all())
                courses.append(course)
                
                # Создаем задачи для курса
                if subject_name in course_tasks:
                    base_deadline = timezone.now() + timedelta(days=7)
                    for task_num, (title, desc, category, points) in enumerate(course_tasks[subject_name], 1):
                        deadline = base_deadline + timedelta(days=task_num * 7)
                        task = Task.objects.create(
                            title=f'{title} ({group_name})',
                            description=desc,
                            course=course,
                            created_by=teacher,
                            category=category,
                            max_points=points,
                            deadline=deadline,
                            is_active=True
                        )
                        self.stdout.write(f'   📝 Создана задача: {task.title}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Создано {len(courses)} курсов\n'))

        # === 7. СОЗДАНИЕ РАСПИСАНИЯ ===
        day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница']
        times = [('08:00', '09:30'), ('10:00', '11:30'), ('12:00', '13:30'), ('14:00', '15:30')]
        classrooms = ['301', '302', '401', '402', 'LAB-1', 'LAB-2']

        schedules_created = 0
        for course in courses[:4]:  # Первые 4 курса
            for day in range(1, 4):  # Пн-Ср
                start, end = times[day - 1]
                Schedule.objects.create(
                    course=course,
                    day_of_week=day,
                    start_time=start,
                    end_time=end,
                    classroom=random.choice(classrooms)
                )
                schedules_created += 1

        self.stdout.write(self.style.SUCCESS(f'✅ Создано {schedules_created} занятий в расписании\n'))

        # === 8. СОЗДАНИЕ НАЗНАЧЕНИЙ ЗАДАЧ (TaskAssignment) ===
        assignments_created = 0
        for task in Task.objects.all()[:20]:  # Первые 20 задач
            students = list(task.course.students.filter(role='student'))
            for idx, student in enumerate(students):
                variant = (idx % 5) + 1
                TaskAssignment.objects.get_or_create(
                    task=task,
                    student=student,
                    defaults={'variant_number': variant}
                )
                assignments_created += 1

        self.stdout.write(self.style.SUCCESS(f'✅ Создано {assignments_created} назначений задач\n'))

        # === 9. СОЗДАНИЕ РАБОТ СТУДЕНТОВ (Submission) ===
        submissions_created = 0
        graded_count = 0
        pending_count = 0

        for task in Task.objects.all()[:15]:  # Первые 15 задач
            assignments = TaskAssignment.objects.filter(task=task)
            
            for assignment in assignments:
                # 70% студентов сдали работу
                if random.random() < 0.7:
                    # Проверяем, нет ли уже подачи
                    if Submission.objects.filter(task=task, student=assignment.student).exists():
                        continue
                        
                    is_late = random.random() < 0.2  # 20% опоздали
                    submitted_at = task.deadline - timedelta(hours=random.randint(1, 48))
                    if is_late:
                        submitted_at = task.deadline + timedelta(hours=random.randint(1, 24))
                    
                    status = 'graded' if random.random() < 0.6 else 'pending'
                    score = random.randint(60, 100) if status == 'graded' else None
                    
                    submission = Submission.objects.create(
                        task=task,
                        student=assignment.student,
                        task_assignment=assignment,
                        file=f'submissions/{timezone.now().strftime("%Y/%m/%d")}/{assignment.student.username}_{task.id}.pdf',
                        status=status,
                        is_late=is_late,
                        score=score,
                        max_score=task.max_points,
                        feedback='' if status == 'pending' else ('Отличная работа!' if score and score >= 80 else 'Хорошо, но есть над чем работать'),
                        graded_by=task.created_by if status == 'graded' else None,
                        version=1
                    )
                    submissions_created += 1
                    
                    if status == 'graded':
                        graded_count += 1
                    else:
                        pending_count += 1

        self.stdout.write(self.style.SUCCESS(f'\n📊 Статистика работ:'))
        self.stdout.write(self.style.SUCCESS(f'   ✅ Всего работ: {submissions_created}'))
        self.stdout.write(self.style.SUCCESS(f'   ✅ Проверено: {graded_count}'))
        self.stdout.write(self.style.SUCCESS(f'   ✅ Ожидают проверки: {pending_count}'))

        # === 10. СОЗДАНИЕ КОММЕНТАРИЕВ (Feedback) ===
        feedbacks_created = 0
        for submission in Submission.objects.filter(status='graded').order_by('?')[:10]:
            Feedback.objects.create(
                submission=submission,
                author=submission.graded_by,
                comment='Обратите внимание на оформление кода',
                is_internal=False
            )
            feedbacks_created += 1

        self.stdout.write(self.style.SUCCESS(f'✅ Создано {feedbacks_created} комментариев\n'))

        # === ИТОГ ===
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('🎉 ВСЕ ТЕСТОВЫЕ ДАННЫЕ СОЗДАНЫ!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('\n📋 УЧЕТНЫЕ ЗАПИСИ:'))
        self.stdout.write(self.style.SUCCESS('   👤 Админ: admin / admin123'))
        self.stdout.write(self.style.SUCCESS('   👨‍🏫 Преподаватели: teacher1-3 / teacher123'))
        self.stdout.write(self.style.SUCCESS('   👨‍🎓 Студенты: std_* / student123'))
        self.stdout.write(self.style.SUCCESS('\n📊 СТАТИСТИКА:'))
        self.stdout.write(self.style.SUCCESS(f'   • Групп: {Group.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   • Студентов: {User.objects.filter(role="student").count()}'))
        self.stdout.write(self.style.SUCCESS(f'   • Преподавателей: {User.objects.filter(role="teacher").count()}'))
        self.stdout.write(self.style.SUCCESS(f'   • Предметов: {Subject.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   • Курсов: {Course.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   • Задач: {Task.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   • Работ: {Submission.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   • Расписание: {Schedule.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('\n🚀 Запустите сервер и наслаждайтесь!\n'))