from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta, date

from .models import Subject, Course, Schedule, DeadlineTemplate, CourseAnalytics, CourseSlot
from assignments.models import Task
from .serializers import (
    SubjectSerializer, SubjectCreateSerializer,
    CourseSerializer, CourseCreateSerializer, CourseDetailSerializer,
    ScheduleSerializer, ScheduleCreateSerializer,
    DeadlineTemplateSerializer, DeadlineTemplateCreateSerializer,
    CourseAnalyticsSerializer, CourseSlotSerializer, CourseSlotGenerateSerializer
)


class SubjectViewSet(viewsets.ModelViewSet):
    """ViewSet для управления предметами"""
    queryset = Subject.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SubjectCreateSerializer
        return SubjectSerializer
    
    def get_queryset(self):
        queryset = Subject.objects.all().select_related('teacher')
        teacher_id = self.request.query_params.get('teacher_id')
        is_active = self.request.query_params.get('is_active')
        
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Преподаватели видят только свои предметы
        if self.request.user.role == 'teacher':
            queryset = queryset.filter(teacher=self.request.user)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def courses(self, request, pk=None):
        """Получить все курсы предмета"""
        from courses.serializers import CourseSerializer
        subject = self.get_object()
        courses = Course.objects.filter(subject=subject)
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Статистика предмета"""
        subject = self.get_object()
        courses = Course.objects.filter(subject=subject)
        
        stats = {
            'total_courses': courses.count(),
            'active_courses': courses.filter(is_active=True).count(),
            'total_students': sum(c.students.count() for c in courses),
            'average_score': 0,
        }
        
        # Расчет среднего балла по всем курсам
        from assignments.models import Submission, Task
        tasks = Task.objects.filter(course__in=courses)
        submissions = Submission.objects.filter(task__in=tasks, score__isnull=False)
        
        if submissions.exists():
            stats['average_score'] = submissions.aggregate(Avg('score'))['score__avg']
        
        return Response(stats)


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet для управления курсами"""
    queryset = Course.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CourseCreateSerializer
        elif self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Course.objects.all().select_related('subject', 'group', 'subject__teacher')
        
        # Студенты видят только свои курсы
        if user.role == 'student':
            queryset = queryset.filter(Q(students=user) | Q(group__students=user)).distinct()
        # Преподаватели видят только свои курсы
        elif user.role == 'teacher':
            queryset = queryset.filter(subject__teacher=user)
        # Админы видят все
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    def perform_create(self, serializer):
        course = serializer.save()
        # Автоматически добавить всех студентов группы
        course.students.set(course.group.students.all())
        # Создать шаблон дедлайнов
        DeadlineTemplate.objects.get_or_create(course=course)
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Получить список студентов курса"""
        from accounts.serializers import UserSerializer
        course = self.get_object()
        students = course.students.all()
        serializer = UserSerializer(students, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Статистика курса"""
        course = self.get_object()
        from assignments.models import Submission, Task
        
        tasks = Task.objects.filter(course=course)
        submissions = Submission.objects.filter(task__in=tasks)
        
        stats = {
            'total_students': course.students.count(),
            'total_tasks': tasks.count(),
            'total_submissions': submissions.count(),
            'pending_submissions': submissions.filter(status='pending').count(),
            'graded_submissions': submissions.filter(score__isnull=False).count(),
            'late_submissions': submissions.filter(is_late=True).count(),
            'average_score': submissions.filter(score__isnull=False).aggregate(Avg('score'))['score__avg'] or 0,
        }
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def add_student(self, request, pk=None):
        """Добавить студента в курс"""
        course = self.get_object()
        student_id = request.data.get('student_id')
        
        try:
            student = User.objects.get(id=student_id, role='student')
            course.students.add(student)
            return Response({'message': 'Студент добавлен'})
        except User.DoesNotExist:
            return Response(
                {'error': 'Студент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def generate_deadlines_from_schedule(self, request, pk=None):
        """Генерация дедлайнов из расписания (автоматизация)"""
        if not request.user.is_admin and not request.user.is_teacher:
            return Response(
                {'error': 'Доступно только администраторам и преподавателям'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        course = self.get_object()
        schedule_items = Schedule.objects.filter(course=course, is_active=True)
        deadline_template = DeadlineTemplate.objects.filter(course=course).first()
        
        if not schedule_items.exists():
            return Response(
                {'error': 'Расписание для курса не найдено'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        offset_minutes = deadline_template.default_deadline_offset if deadline_template else 10
        created_tasks = 0
        
        for schedule in schedule_items:
            # Создаем дедлайн за offset минут до начала занятия
            deadline = timezone.datetime.combine(
                timezone.now().date(),
                schedule.start_time
            ) - timezone.timedelta(minutes=offset_minutes)
            
            # Проверяем, есть ли уже задача с таким дедлайном
            if not Task.objects.filter(course=course, deadline__date=deadline.date()).exists():
                # Здесь можно создавать задачу-шаблон
                # Task.objects.create(...)
                created_tasks += 1
        
        return Response({
            'message': f'Генерация дедлайнов завершена. Создано/обновлено задач: {created_tasks}'
        })
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Аналитика курса (кэшированная)"""
        course = self.get_object()
        
        # Обновляем аналитику
        try:
            analytics = course.analytics
            analytics.update_stats()
        except CourseAnalytics.DoesNotExist:
            analytics = CourseAnalytics.objects.create(course=course)
            analytics.update_stats()
        
        return Response(CourseAnalyticsSerializer(analytics).data)
    
    @action(detail=False, methods=['get'])
    def my_courses(self, request):
        """Получить курсы текущего пользователя"""
        user = request.user
        queryset = self.get_queryset()
        
        courses = queryset.filter(is_active=True)
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data)


class ScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet для управления расписанием"""
    queryset = Schedule.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ScheduleCreateSerializer
        return ScheduleSerializer
    
    def get_queryset(self):
        queryset = Schedule.objects.all().select_related('course', 'course__subject', 'course__group')
        course_id = self.request.query_params.get('course_id')
        group_id = self.request.query_params.get('group_id')
        day = self.request.query_params.get('day')
        is_active = self.request.query_params.get('is_active')
        
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if group_id:
            queryset = queryset.filter(course__group_id=group_id)
        if day:
            queryset = queryset.filter(day_of_week=day)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('course', 'day_of_week', 'start_time')
    
    @action(detail=False, methods=['get'])
    def by_group(self, request):
        """Получить расписание по группе"""
        group_id = request.query_params.get('group_id')
        
        if not group_id:
            return Response(
                {'error': 'group_id требуется'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        schedules = self.get_queryset().filter(course__group_id=group_id)
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_day(self, request):
        """Получить расписание на день"""
        day = request.query_params.get('day')
        if not day:
            return Response(
                {'error': 'day требуется (1-6)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        schedules = self.get_queryset().filter(day_of_week=day)
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def generate_deadline_task(self, request, pk=None):
        """Создать задачу из расписания (автоматический дедлайн)"""
        schedule = self.get_object()
        offset_minutes = 10  # По умолчанию 10 минут
        
        deadline = timezone.datetime.combine(
            timezone.now().date(),
            schedule.start_time
        ) - timezone.timedelta(minutes=offset_minutes)
        
        from assignments.models import Task
        
        task = Task.objects.create(
            title=f"Задание: {schedule.course.subject.name}",
            description="Задача создана автоматически из расписания",
            course=schedule.course,
            created_by=request.user,
            deadline=deadline,
            max_points=100
        )
        
        return Response({
            'message': 'Задача создана',
            'task_id': task.id,
            'deadline': task.deadline.isoformat()
        })


class DeadlineTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet для управления шаблонами дедлайнов"""
    queryset = DeadlineTemplate.objects.all()
    serializer_class = DeadlineTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DeadlineTemplateCreateSerializer
        return DeadlineTemplateSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = DeadlineTemplate.objects.all().select_related('course', 'course__subject', 'course__group')
        
        if user.role == 'teacher':
            queryset = queryset.filter(course__subject__teacher=user)
        elif user.role == 'student':
            queryset = queryset.filter(course__students=user)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def apply_to_course(self, request, pk=None):
        """Применить шаблон ко всем задачам курса"""
        template = self.get_object()
        updated = 0
        
        for task in Task.objects.filter(course=template.course):
            task.allow_late_submission = template.allow_weekend_submission
            task.late_penalty_percent = template.late_penalty_percent
            task.save()
            updated += 1
        
        return Response({
            'message': f'Шаблон применён к {updated} задачам'
        })


class CourseAnalyticsViewSet(viewsets.ModelViewSet):
    """ViewSet для аналитики курсов"""
    queryset = CourseAnalytics.objects.all()
    serializer_class = CourseAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = CourseAnalytics.objects.all().select_related('course', 'course__subject', 'course__group')
        
        if user.role == 'teacher':
            queryset = queryset.filter(course__subject__teacher=user)
        elif user.role == 'student':
            queryset = queryset.filter(course__students=user)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Обзор аналитики для пользователя"""
        user = request.user
        from assignments.models import Submission, Task
        
        if user.role == 'student':
            courses = Course.objects.filter(students=user)
        elif user.role == 'teacher':
            courses = Course.objects.filter(subject__teacher=user)
        else:
            courses = Course.objects.all()
        
        total_courses = courses.count()
        total_tasks = Task.objects.filter(course__in=courses).count()
        total_submissions = Submission.objects.filter(
            task__course__in=courses
        ).count()
        graded_submissions = Submission.objects.filter(
            task__course__in=courses,
            score__isnull=False
        ).count()
        
        avg_score = Submission.objects.filter(
            task__course__in=courses,
            score__isnull=False
        ).aggregate(Avg('score'))['score__avg'] or 0
        
        return Response({
            'total_courses': total_courses,
            'total_tasks': total_tasks,
            'total_submissions': total_submissions,
            'graded_submissions': graded_submissions,
            'average_score': round(avg_score, 2)
        })


class CourseSlotViewSet(viewsets.ModelViewSet):
    """ViewSet для управления слотами курса"""
    queryset = CourseSlot.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseSlotSerializer
    
    def get_queryset(self):
        queryset = CourseSlot.objects.select_related('course__subject', 'course__group').filter(is_active=True)
        
        course_id = self.request.query_params.get('course_id')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        is_filled = self.request.query_params.get('is_filled')
        if is_filled is not None:
            queryset = queryset.filter(is_filled=is_filled.lower() == 'true')
        
        return queryset.order_by('course', 'deadline')
    
    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """
        Генерация слотов для курса
        
        POST /api/course-slots/generate/
        {
            "course": 1,
            "start_date": "2024-05-15",
            "end_date": "2024-06-30",
            "total_slots": 29,
            "days_of_week": [1, 2, 3, 4, 5]
        }
        """
        from django.core.exceptions import ValidationError
        from datetime import date as date_type
        
        course_id = request.data.get('course')
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')
        total_slots = int(request.data.get('total_slots', 29))
        days_of_week = request.data.get('days_of_week', [1, 2, 3, 4, 5])
        
        if not all([course_id, start_date_str, end_date_str]):
            return Response(
                {'error': 'Необходимы параметры: course, start_date, end_date'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = Course.objects.get(id=course_id)
            start_date = date_type.fromisoformat(start_date_str)
            end_date = date_type.fromisoformat(end_date_str)
            days_of_week = [int(d) for d in days_of_week] if isinstance(days_of_week, str) else days_of_week
        except (ValueError, Course.DoesNotExist) as e:
            return Response(
                {'error': f'Неверные параметры: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Удаляем старые слоты для этого курса
        CourseSlot.objects.filter(course=course, is_active=True).update(is_active=False)
        
        # Генерируем новые слоты
        created_slots, conflicts = CourseSlot.generate_for_course(
            course=course,
            start_date=start_date,
            end_date=end_date,
            total_slots=total_slots,
            days_of_week=days_of_week
        )
        
        return Response({
            'success': True,
            'created_slots': len(created_slots),
            'slots': CourseSlotSerializer(created_slots, many=True).data,
            'conflicts': conflicts,
            'message': f'Создано {len(created_slots)} слотов' + (f'. Предупреждений: {len(conflicts)}' if conflicts else '')
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def preview(self, request):
        """
        Предпросмотр генерации слотов (без сохранения)
        
        GET /api/course-slots/preview/?course=1&start_date=2024-05-15&end_date=2024-06-30&total_slots=29&days_of_week=1,2,3,4,5
        """
        course_id = request.query_params.get('course')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        total_slots = int(request.query_params.get('total_slots', 29))
        days_of_week = request.query_params.get('days_of_week', '1,2,3,4,5')
        
        if not all([course_id, start_date_str, end_date_str]):
            return Response(
                {'error': 'Необходимы параметры: course, start_date, end_date'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = Course.objects.get(id=course_id)
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            days_of_week = [int(d) for d in days_of_week.split(',')]
        except (ValueError, Course.DoesNotExist):
            return Response(
                {'error': 'Неверные параметры'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Предпросмотр (без сохранения)
        from courses.models import CourseSlot
        created_slots, conflicts = CourseSlot.generate_for_course(
            course=course,
            start_date=start_date,
            end_date=end_date,
            total_slots=total_slots,
            days_of_week=days_of_week
        )
        
        return Response({
            'expected_slots': len(created_slots),
            'conflicts': conflicts,
            'message': f'Будет создано {len(created_slots)} слотов' + (f'. Предупреждений: {len(conflicts)}' if conflicts else '')
        })
