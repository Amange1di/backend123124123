from rest_framework import serializers
from .models import Subject, Course, Schedule, DeadlineTemplate, CourseAnalytics, CourseSlot
from accounts.models import User, Group


class UserSimpleSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор пользователя"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email', 'avatar']


class SubjectSerializer(serializers.ModelSerializer):
    """Сериализатор предмета"""
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    teacher_username = serializers.CharField(source='teacher.username', read_only=True)
    teacher_info = UserSimpleSerializer(source='teacher', read_only=True)
    courses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'description', 'credit_hours',
            'teacher', 'teacher_name', 'teacher_username', 'teacher_info',
            'is_active', 'semester', 'year', 'courses_count'
        ]
    
    def get_courses_count(self, obj):
        return obj.courses.count()


class SubjectCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания предмета"""
    
    class Meta:
        model = Subject
        fields = ['name', 'code', 'description', 'credit_hours', 'teacher', 'semester', 'year']


class GroupSimpleSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор группы"""
    student_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Group
        fields = ['id', 'group_name', 'department', 'semester', 'year', 'is_active', 'student_count']


class CourseSerializer(serializers.ModelSerializer):
    """Сериализатор курса"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    group_name = serializers.CharField(source='group.group_name', read_only=True)
    teacher_name = serializers.CharField(source='subject.teacher.get_full_name', read_only=True)
    subject_info = SubjectSerializer(source='subject', read_only=True)
    group_info = GroupSimpleSerializer(source='group', read_only=True)
    students_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 'subject', 'subject_name', 'subject_code', 'group', 'group_name',
            'subject_info', 'group_info', 'teacher_name',
            'semester', 'year', 'is_active', 'students_count', 'description'
        ]


class CourseCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания курса"""
    
    class Meta:
        model = Course
        fields = ['subject', 'group', 'semester', 'year', 'description']
    
    def validate(self, data):
        # Проверка на существование курса
        existing = Course.objects.filter(
            subject=data['subject'],
            group=data['group'],
            semester=data['semester'],
            year=data['year']
        )
        if existing.exists():
            raise serializers.ValidationError({"non_field_errors": "Курс уже существует"})
        return data


class CourseDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор курса"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    group_name = serializers.CharField(source='group.group_name', read_only=True)
    teacher_name = serializers.CharField(source='subject.teacher.get_full_name', read_only=True)
    subject_info = SubjectSerializer(source='subject', read_only=True)
    group_info = GroupSimpleSerializer(source='group', read_only=True)
    students_count = serializers.SerializerMethodField()
    schedule = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()
    analytics = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'subject', 'subject_name', 'subject_code', 'group', 'group_name',
            'subject_info', 'group_info', 'teacher_name', 'description', 'is_active',
            'students_count', 'schedule', 'tasks_count', 'analytics'
        ]
    
    def get_students_count(self, obj):
        return obj.students.count()
    
    def get_schedule(self, obj):
        return ScheduleSerializer(obj.schedule.all(), many=True).data
    
    def get_tasks_count(self, obj):
        return obj.tasks.count()
    
    def get_analytics(self, obj):
        try:
            analytics = obj.analytics
            return {
                'total_submissions': analytics.total_submissions,
                'average_score': float(analytics.average_score),
                'fail_rate': float(analytics.fail_rate),
                'completion_rate': float(analytics.completion_rate)
            }
        except CourseAnalytics.DoesNotExist:
            return None


class ScheduleSerializer(serializers.ModelSerializer):
    """Сериализатор расписания"""
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    course_name = serializers.CharField(source='course.subject.name', read_only=True)
    group_name = serializers.CharField(source='course.group.group_name', read_only=True)
    deadline_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'course', 'course_name', 'group_name', 'day_of_week', 'day_display',
            'start_time', 'end_time', 'classroom', 'deadline_time', 'is_active', 'created_at'
        ]
    
    def get_deadline_time(self, obj):
        return obj.get_deadline_time()


class ScheduleCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания расписания"""
    
    class Meta:
        model = Schedule
        fields = ['course', 'day_of_week', 'start_time', 'end_time', 'classroom', 'week_start', 'week_end']


class DeadlineTemplateSerializer(serializers.ModelSerializer):
    """Сериализатор шаблона дедлайнов"""
    course_name = serializers.CharField(source='course.subject.name', read_only=True)
    group_name = serializers.CharField(source='course.group.group_name', read_only=True)
    
    class Meta:
        model = DeadlineTemplate
        fields = [
            'id', 'course', 'course_name', 'group_name',
            'default_deadline_offset', 'allow_weekend_submission',
            'late_penalty_percent', 'max_late_days', 'is_active'
        ]


class DeadlineTemplateCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания шаблона дедлайнов"""
    
    class Meta:
        model = DeadlineTemplate
        fields = ['course', 'default_deadline_offset', 'allow_weekend_submission', 'late_penalty_percent', 'max_late_days']


class CourseAnalyticsSerializer(serializers.ModelSerializer):
    """Сериализатор аналитики курса"""
    course_name = serializers.CharField(source='course.subject.name', read_only=True)
    group_name = serializers.CharField(source='course.group.group_name', read_only=True)
    
    class Meta:
        model = CourseAnalytics
        fields = [
            'id', 'course', 'course_name', 'group_name',
            'total_submissions', 'graded_submissions', 'late_submissions',
            'average_score', 'fail_rate', 'completion_rate', 'last_updated'
        ]


class CourseSlotSerializer(serializers.ModelSerializer):
    """Сериализатор слота курса"""
    course_name = serializers.CharField(source='course.subject.name', read_only=True)
    group_name = serializers.CharField(source='course.group.group_name', read_only=True)
    is_conflict = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseSlot
        fields = [
            'id', 'course', 'course_name', 'group_name', 'slot_number',
            'deadline', 'is_filled', 'is_active', 'generated_at', 'is_conflict'
        ]
    
    def get_is_conflict(self, obj):
        # Проверяем, есть ли задача в этом слоте
        from assignments.models import Task
        task = Task.objects.filter(course=obj.course, deadline__date=obj.deadline.date()).first()
        return obj.is_filled and not task


class CourseSlotGenerateSerializer(serializers.Serializer):
    """Сериализатор для генерации слотов"""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    total_slots = serializers.IntegerField(min_value=1, max_value=100)
    days_of_week = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=6),
        required=False,
        default=[1, 2, 3, 4, 5]  # Пн-Пт по умолчанию
    )