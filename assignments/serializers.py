from rest_framework import serializers
from .models import Task, TaskAssignment, Submission, Feedback, TaskBatch, SubmissionAnalytics
from accounts.serializers import UserSerializer


class TaskSerializer(serializers.ModelSerializer):
    """Сериализатор задания"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    course_name = serializers.CharField(source='course.subject.name', read_only=True)
    group_name = serializers.CharField(source='course.group.group_name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    time_remaining = serializers.IntegerField(read_only=True)
    is_urgent = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'course', 'course_name', 'group_name',
            'created_by', 'created_by_name', 'category', 'max_points',
            'deadline', 'created_at', 'updated_at', 'is_active', 'allow_late_submission',
            'late_penalty_percent', 'attachment', 'instructions_url', 'time_remaining', 'is_urgent'
        ]


class TaskCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания задания"""
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'course', 'category', 'max_points', 'deadline',
            'allow_late_submission', 'late_penalty_percent', 'attachment', 'instructions_url'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TaskUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления задания"""
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'category', 'max_points', 'deadline',
            'is_active', 'allow_late_submission', 'late_penalty_percent', 'attachment', 'instructions_url'
        ]


class TaskAssignmentSerializer(serializers.ModelSerializer):
    """Сериализатор назначения задания"""
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_full_name = serializers.CharField(source='student.full_name', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = TaskAssignment
        fields = [
            'id', 'task', 'task_title', 'student', 'student_username', 'student_full_name',
            'variant_number', 'assigned_at'
        ]


class SubmissionSerializer(serializers.ModelSerializer):
    """Сериализатор работы студента"""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_username = serializers.CharField(source='student.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    task_deadline = serializers.DateTimeField(source='task.deadline', read_only=True)
    graded_by_name = serializers.CharField(source='graded_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Submission
        fields = [
            'id', 'task', 'task_title', 'task_deadline', 'student', 'student_name', 'student_username',
            'file', 'submitted_at', 'status', 'status_display', 'is_late', 'score', 'max_score',
            'feedback', 'graded_by', 'graded_by_name', 'graded_at', 'version'
        ]
        read_only_fields = ['student', 'submitted_at', 'is_late']


class SubmissionCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания работы"""
    
    class Meta:
        model = Submission
        fields = ['task', 'file']
    
    def create(self, validated_data):
        request = self.context['request']
        task = validated_data['task']
        
        # Находим назначение задания студенту
        try:
            task_assignment = TaskAssignment.objects.get(
                task=task,
                student=request.user
            )
        except TaskAssignment.DoesNotExist:
            raise serializers.ValidationError("Вы не назначены на это задание")
        
        # Проверяем, есть ли уже сдача
        existing = Submission.objects.filter(task=task, student=request.user).first()
        if existing:
            # Обновляем существующую версию
            existing.version += 1
            existing.file = validated_data['file']
            existing.status = 'pending'
            existing.save()
            return existing
        
        submission = Submission.objects.create(
            task=task,
            student=request.user,
            task_assignment=task_assignment,
            **validated_data
        )
        return submission


class SubmissionGradingSerializer(serializers.ModelSerializer):
    """Сериализатор для оценки работы"""
    
    class Meta:
        model = Submission
        fields = ['score', 'feedback', 'status']
    
    def validate(self, data):
        task = self.instance.task
        score = data.get('score')
        
        if score and score > task.max_points:
            raise serializers.ValidationError({
                "score": f"Оценка не может превышать {task.max_points} баллов"
            })
        
        if score and data.get('status') == 'pending':
            data['status'] = 'graded'
        
        return data


class FeedbackSerializer(serializers.ModelSerializer):
    """Сериализатор комментариев"""
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)
    
    class Meta:
        model = Feedback
        fields = [
            'id', 'submission', 'author', 'author_name', 'author_role', 'comment',
            'created_at', 'is_internal', 'is_resolved'
        ]


class TaskWithAssignmentsSerializer(serializers.ModelSerializer):
    """Задание с информацией о назначениях"""
    assignments_count = serializers.SerializerMethodField()
    submissions_count = serializers.SerializerMethodField()
    graded_count = serializers.SerializerMethodField()
    average_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'category', 'max_points',
            'deadline', 'is_active', 'assignments_count', 'submissions_count',
            'graded_count', 'average_score'
        ]
    
    def get_assignments_count(self, obj):
        return obj.assignments.count()
    
    def get_submissions_count(self, obj):
        return obj.submissions.count()
    
    def get_graded_count(self, obj):
        return obj.submissions.filter(score__isnull=False).count()
    
    def get_average_score(self, obj):
        submissions = obj.submissions.filter(score__isnull=False)
        if not submissions.exists():
            return 0
        return submissions.aggregate(avg=serializers.DecimalField(max_digits=5, decimal_places=2)).get('avg') or 0


class TaskBatchSerializer(serializers.ModelSerializer):
    """Сериализатор пакета задач"""
    course_name = serializers.CharField(source='course.subject.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = TaskBatch
        fields = [
            'id', 'name', 'course', 'course_name', 'created_by', 'created_by_name',
            'tasks_count', 'created_at', 'description'
        ]


class TaskBatchCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания пакета задач"""
    
    class Meta:
        model = TaskBatch
        fields = ['name', 'course', 'description']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class SubmissionAnalyticsSerializer(serializers.ModelSerializer):
    """Сериализатор аналитики сдачи"""
    course_name = serializers.CharField(source='course.subject.name', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = SubmissionAnalytics
        fields = [
            'id', 'course', 'course_name', 'task', 'task_title',
            'total_assigned', 'total_submitted', 'total_graded',
            'average_score', 'median_score', 'min_score', 'max_score',
            'late_rate', 'last_updated'
        ]