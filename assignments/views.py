from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Count, Q, Min, Max
from django.utils import timezone
from datetime import timedelta

from .models import Task, TaskAssignment, Submission, Feedback, TaskBatch, SubmissionAnalytics
from accounts.models import User
from courses.models import Course, CourseSlot
from .serializers import (
    TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer,
    TaskWithAssignmentsSerializer, TaskAssignmentSerializer,
    SubmissionSerializer, SubmissionCreateSerializer, SubmissionGradingSerializer,
    FeedbackSerializer, TaskBatchSerializer, SubmissionAnalyticsSerializer
)


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet для управления заданиями"""
    queryset = Task.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer
        elif self.action == 'list':
            return TaskWithAssignmentsSerializer
        return TaskSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Task.objects.select_related(
            'course', 'course__subject', 'course__group', 'created_by'
        ).all()
        
        # Студенты видят только задания своих курсов
        if user.role == 'student':
            course_ids = user.enrolled_courses.values_list('id', flat=True)
            queryset = queryset.filter(course_id__in=course_ids)
        # Преподаватели видят только задания своих курсов
        elif user.role == 'teacher':
            course_ids = user.subjects.values('courses__id').distinct()
            if course_ids.exists():
                queryset = queryset.filter(course_id__in=course_ids)
            else:
                # Если у преподавателя нет курсов, возвращаем пустой queryset
                queryset = queryset.none()
        
        # Фильтры
        course_id = self.request.query_params.get('course_id')
        category = self.request.query_params.get('category')
        is_active = self.request.query_params.get('is_active')
        
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if category:
            queryset = queryset.filter(category=category)
        if is_active is not None:
            now = timezone.now()
            if is_active.lower() == 'true':
                queryset = queryset.filter(deadline__gt=now, is_active=True)
            else:
                queryset = queryset.filter(Q(deadline__lte=now) | Q(is_active=False))
        
        return queryset.order_by('-deadline')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def assign_to_group(self, request, pk=None):
        """Назначить задание группе с использованием Modulo Assign"""
        task = self.get_object()
        group_id = request.data.get('group_id')
        
        if not group_id:
            return Response(
                {'error': 'group_id требуется'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response(
                {'error': 'Группа не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Получаем студентов группы, отсортированных по ID
        students = list(group.students.filter(role='student').order_by('id'))
        
        if not students:
            return Response(
                {'error': 'В группе нет студентов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем все задачи этого курса для расчета варианта
        course_tasks = Task.objects.filter(course=task.course)
        tasks_count = course_tasks.count() or 1
        
        # Modulo Assign: student_index % tasks_count
        assignments = []
        for index, student in enumerate(students):
            variant_number = (index % tasks_count) + 1
            
            # Проверяем, есть ли уже назначение
            assignment, created = TaskAssignment.objects.get_or_create(
                task=task,
                student=student,
                defaults={'variant_number': variant_number}
            )
            
            if created:
                assignments.append({
                    'student': student.username,
                    'student_name': student.full_name,
                    'variant_number': variant_number
                })
        
        return Response({
            'message': f'Задание назначено {len(assignments)} студентам',
            'assignments': assignments
        })
    
    @action(detail=True, methods=['post'])
    def assign_to_students(self, request, pk=None):
        """Назначить задание конкретным студентам"""
        task = self.get_object()
        student_ids = request.data.get('student_ids', [])
        
        if not student_ids:
            return Response(
                {'error': 'student_ids требуется'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        students = User.objects.filter(id__in=student_ids, role='student')
        tasks_count = Task.objects.filter(course=task.course).count() or 1
        
        assignments = []
        for index, student in enumerate(students):
            variant_number = (index % tasks_count) + 1
            
            assignment, created = TaskAssignment.objects.get_or_create(
                task=task,
                student=student,
                defaults={'variant_number': variant_number}
            )
            
            if created:
                assignments.append({
                    'student': student.username,
                    'variant_number': variant_number
                })
        
        return Response({
            'message': f'Задание назначено {len(assignments)} студентам',
            'assignments': assignments
        })
    
    @action(detail=True, methods=['get'])
    def my_assignment(self, request, pk=None):
        """Получить своё назначение (для студента)"""
        if request.user.role != 'student':
            return Response(
                {'error': 'Доступно только студентам'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            assignment = TaskAssignment.objects.get(
                task=pk,
                student=request.user
            )
            return Response(TaskAssignmentSerializer(assignment).data)
        except TaskAssignment.DoesNotExist:
            return Response(
                {'error': 'Вы не назначены на это задание'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def auto_fill_slots(self, request):
        """
        Автоматическое заполнение пустых слотов задачами из шаблонов
        
        POST /api/tasks/auto-fill-slots/
        {
            "course_id": 1,
            "template_task_ids": [1, 2, 3],
            "fill_all": true  // Заполнить все пустые слоты
        }
        """
        if not request.user.is_teacher:
            return Response(
                {'error': 'Доступно только преподавателям'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        course_id = request.data.get('course_id')
        template_task_ids = request.data.get('template_task_ids', [])
        fill_all = request.data.get('fill_all', False)
        
        if not course_id:
            return Response(
                {'error': 'course_id требуется'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Курс не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Получаем пустые слоты для курса
        empty_slots = list(CourseSlot.objects.filter(
            course=course,
            is_filled=False,
            is_active=True
        ).order_by('deadline'))
        
        if not empty_slots:
            return Response({
                'message': 'Нет пустых слотов',
                'filled_count': 0
            })
        
        # Получаем задачи-шаблоны
        if template_task_ids:
            template_tasks = Task.objects.filter(
                id__in=template_task_ids,
                created_by=request.user
            )
        else:
            # Если шаблоны не указаны, используем все задачи преподавателя для этого курса
            template_tasks = Task.objects.filter(
                course=course,
                created_by=request.user
            )
        
        if not template_tasks.exists():
            return Response({
                'error': 'Нет доступных шаблонов задач',
                'filled_count': 0
            })
        
        template_tasks_list = list(template_tasks)
        filled_count = 0
        
        for slot in empty_slots:
            # Берем шаблон по кругу
            template = template_tasks_list[filled_count % len(template_tasks_list)]
            
            # Создаем новую задачу на основе шаблона с дедлайном слота
            task = Task.objects.create(
                title=f"{template.title}",
                description=template.description,
                course=course,
                created_by=request.user,
                category=template.category,
                max_points=template.max_points,
                deadline=slot.deadline,
                is_active=True,
                allow_late_submission=template.allow_late_submission,
                late_penalty_percent=template.late_penalty_percent,
                attachment=template.attachment,
                instructions_url=template.instructions_url
            )
            
            # Маркуем слот как заполненный
            slot.is_filled = True
            slot.save()
            
            # Назначаем задачу студентам курса
            students = list(course.students.filter(role='student'))
            for idx, student in enumerate(students):
                TaskAssignment.objects.get_or_create(
                    task=task,
                    student=student,
                    defaults={'variant_number': (idx % 5) + 1}
                )
            
            filled_count += 1
        
        return Response({
            'message': f'Заполнено {filled_count} слотов',
            'filled_count': filled_count,
            'remaining_slots': len(empty_slots) - filled_count
        })
        """Массовое создание задач"""
        if not request.user.is_teacher:
            return Response(
                {'error': 'Доступно только преподавателям'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tasks_data = request.data.get('tasks', [])
        created = []
        errors = []
        
        for task_data in tasks_data:
            try:
                task = Task.objects.create(
                    **task_data,
                    created_by=request.user
                )
                created.append(task.title)
            except Exception as e:
                errors.append(f"{task_data.get('title', 'Unknown')}: {str(e)}")
        
        return Response({
            'created': created,
            'errors': errors,
            'total_created': len(created)
        })


class SubmissionViewSet(viewsets.ModelViewSet):
    """ViewSet для управления работами студентов"""
    queryset = Submission.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # Отключаем пагинацию для списка
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SubmissionCreateSerializer
        elif self.action in ['grade', 'partial_update']:
            return SubmissionGradingSerializer
        return SubmissionSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Submission.objects.select_related(
            'task', 'task_assignment', 'student', 'graded_by'
        ).all()
        
        if user.role == 'student':
            queryset = queryset.filter(student=user)
        elif user.role == 'teacher':
            # Преподаватели видят работы по своим курсам
            course_ids = user.subjects.values('courses__id')
            task_ids = Task.objects.filter(course_id__in=course_ids).values('id')
            queryset = queryset.filter(task_id__in=task_ids)
        
        # Фильтры
        task_id = self.request.query_params.get('task_id')
        status = self.request.query_params.get('status')
        is_late = self.request.query_params.get('is_late')
        
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        if status:
            queryset = queryset.filter(status=status)
        if is_late is not None:
            queryset = queryset.filter(is_late=is_late.lower() == 'true')
        
        return queryset.order_by('-submitted_at')
    
    def perform_create(self, serializer):
        # Проверка дедлайна происходит в save() модели
        pass
    
    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        """Оценить работу (для преподавателя)"""
        submission = self.get_object()
        serializer = SubmissionGradingSerializer(
            submission, data=request.data, partial=True
        )
        
        if serializer.is_valid():
            submission.score = serializer.validated_data.get('score', submission.score)
            submission.feedback = serializer.validated_data.get('feedback', submission.feedback)
            submission.status = serializer.validated_data.get('status', 'graded')
            submission.graded_by = request.user
            submission.graded_at = timezone.now()
            submission.save()
            
            return Response(SubmissionSerializer(submission).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_task(self, request):
        """Получить работы по задаче"""
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'task_id требуется'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submissions = Submission.objects.filter(task_id=task_id)
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Получить работы, ожидающие проверки"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Доступно только преподавателям'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        submissions = Submission.objects.filter(status='pending')
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def urgent(self, request):
        """Получить срочные работы (сданы менее чем за 1 час до дедлайна)"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Доступно только преподавателям'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        submissions = Submission.objects.filter(
            task__deadline__gt=timezone.now() - timezone.timedelta(hours=1)
        )
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def request_revision(self, request, pk=None):
        """Запросить доработку работы"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Доступно только преподавателям'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        submission = self.get_object()
        submission.status = 'revision'
        submission.feedback = request.data.get('feedback', submission.feedback)
        submission.save()
        
        return Response({
            'message': 'Работа отправлена на доработку',
            'submission': SubmissionSerializer(submission).data
        })
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Скачать файл работы"""
        submission = self.get_object()
        
        # Проверка прав
        if request.user.role == 'student' and submission.student != request.user:
            return Response(
                {'error': 'Доступ запрещён'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role == 'teacher':
            course_id = request.user.subjects.values('courses__id')
            task_ids = Task.objects.filter(course_id__in=course_id).values('id')
            if not submission.task_id in task_ids:
                return Response(
                    {'error': 'Доступ запрещён'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return Response({
            'file_url': submission.file.url,
            'file_name': submission.file.name
        })


class FeedbackViewSet(viewsets.ModelViewSet):
    """ViewSet для комментариев"""
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Feedback.objects.all().select_related('submission', 'author')
        submission_id = self.request.query_params.get('submission_id')
        
        if submission_id:
            queryset = queryset.filter(submission_id=submission_id)
        
        # Студенты видят только публичные комментарии к своим работам
        if self.request.user.role == 'student':
            queryset = queryset.filter(
                is_internal=False,
                submission__student=self.request.user
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Отметить комментарий как решённый"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Доступно только преподавателям'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        feedback = self.get_object()
        feedback.is_resolved = True
        feedback.save()
        
        return Response({'message': 'Комментарий отмечен как решённый'})


class TaskBatchViewSet(viewsets.ModelViewSet):
    """ViewSet для управления пакетами задач"""
    queryset = TaskBatch.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TaskBatchCreateSerializer
        return TaskBatchSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = TaskBatch.objects.all().select_related('course', 'created_by')
        
        if user.role == 'teacher':
            queryset = queryset.filter(
                Q(created_by=user) | Q(course__subject__teacher=user)
            )
        elif user.role == 'student':
            queryset = queryset.filter(course__students=user)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_tasks(self, request, pk=None):
        """Добавить задачи в пакет"""
        batch = self.get_object()
        tasks_data = request.data.get('tasks', [])
        
        created = 0
        for task_data in tasks_data:
            Task.objects.create(
                **task_data,
                course=batch.course,
                created_by=batch.created_by
            )
            created += 1
        
        batch.tasks_count = batch.tasks.all().count()
        batch.save()
        
        return Response({
            'message': f'Создано {created} задач',
            'total_tasks': batch.tasks_count
        })


class SubmissionAnalyticsViewSet(viewsets.ModelViewSet):
    """ViewSet для аналитики сдачи работ"""
    queryset = SubmissionAnalytics.objects.all()
    serializer_class = SubmissionAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = SubmissionAnalytics.objects.all()
        
        if user.role == 'teacher':
            course_ids = user.subjects.values('courses__id')
            queryset = queryset.filter(course_id__in=course_ids)
        elif user.role == 'student':
            queryset = queryset.filter(course__students=user)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Общая аналитика по всем submission"""
        from assignments.models import Task, Submission
        
        tasks = Task.objects.all()
        submissions = Submission.objects.all()
        
        analytics = {
            'total_courses': tasks.values('course').distinct().count(),
            'total_tasks': tasks.count(),
            'total_submissions': submissions.count(),
            'pending': submissions.filter(status='pending').count(),
            'graded': submissions.filter(score__isnull=False).count(),
            'late': submissions.filter(is_late=True).count(),
            'average_score': submissions.filter(score__isnull=False).aggregate(Avg('score'))['score__avg'] or 0,
            'min_score': submissions.filter(score__isnull=False).aggregate(min=Min('score'))['min'] or 0,
            'max_score': submissions.filter(score__isnull=False).aggregate(max=Max('score'))['max'] or 0,
        }
        
        return Response(analytics)

    @action(detail=False, methods=['get'])
    def course_overview(self, request):
        """Обзор аналитики по курсу"""
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response(
                {'error': 'course_id требуется'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from assignments.models import Task, Submission
        
        tasks = Task.objects.filter(course_id=course_id)
        submissions = Submission.objects.filter(task__in=tasks)
        
        analytics = {
            'total_tasks': tasks.count(),
            'total_submissions': submissions.count(),
            'pending': submissions.filter(status='pending').count(),
            'graded': submissions.filter(score__isnull=False).count(),
            'late': submissions.filter(is_late=True).count(),
            'average_score': submissions.filter(score__isnull=False).aggregate(Avg('score'))['score__avg'] or 0,
            'min_score': submissions.filter(score__isnull=False).aggregate(min=Min('score'))['min'] or 0,
            'max_score': submissions.filter(score__isnull=False).aggregate(max=Max('score'))['max'] or 0,
        }
        
        return Response(analytics)
