from django.db import models
from django.utils import timezone
from accounts.models import User
from courses.models import Course, Subject


class Task(models.Model):
    """Задание"""
    CATEGORY_CHOICES = (
        ('homework', 'Домашняя работа'),
        ('project', 'Проект'),
        ('lab', 'Лабораторная'),
        ('test', 'Тест'),
        ('exam', 'Экзамен'),
        ('quiz', 'Квик-тест'),
    )
    
    title = models.CharField(max_length=200, verbose_name="Название задания")
    description = models.TextField(verbose_name="Описание задания")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='tasks')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'})
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='homework')
    max_points = models.PositiveIntegerField(default=100, verbose_name="Максимальные баллы")
    deadline = models.DateTimeField(verbose_name="Дедлайн")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    allow_late_submission = models.BooleanField(default=False, verbose_name="Разрешить позднюю сдачу")
    late_penalty_percent = models.PositiveIntegerField(default=0, verbose_name="Штраф за опоздание (%)")
    attachment = models.FileField(upload_to='task_attachments/', blank=True, null=True, verbose_name="Материалы")
    instructions_url = models.URLField(blank=True, verbose_name="Ссылка на инструкцию")
    
    class Meta:
        db_table = 'tasks'
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'
        ordering = ['-deadline']
    
    def __str__(self):
        return f"{self.title} ({self.course})"
    
    @property
    def time_remaining(self):
        """Время до дедлайна в секундах"""
        now = timezone.now()
        delta = self.deadline - now
        return max(0, int(delta.total_seconds()))
    
    @property
    def is_urgent(self):
        """Задача срочная (менее часа до дедлайна)"""
        return 0 < self.time_remaining < 3600


class TaskAssignment(models.Model):
    """Назначение задания студенту (для модифицированного распределения)"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='assignments')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    variant_number = models.PositiveIntegerField(verbose_name="Номер варианта")
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'task_assignments'
        unique_together = ('task', 'student')
        verbose_name = 'Назначение задания'
        verbose_name_plural = 'Назначения заданий'
    
    def __str__(self):
        return f"{self.task.title} - {self.student.username} (Вариант {self.variant_number})"


class Submission(models.Model):
    """Работа студента"""
    STATUS_CHOICES = (
        ('pending', 'Ожидает проверки'),
        ('graded', 'Проверено'),
        ('revision', 'На доработке'),
        ('rejected', 'Отклонена'),
    )
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    task_assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='submissions/%Y/%m/%d/', verbose_name="Файл работы")
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_late = models.BooleanField(default=False, verbose_name="Позже дедлайна")
    
    # Поля оценки
    score = models.PositiveIntegerField(null=True, blank=True, verbose_name="Баллы")
    max_score = models.PositiveIntegerField(null=True, blank=True, verbose_name="Максимум баллов")
    
    # Поля фидбека
    feedback = models.TextField(blank=True, verbose_name="Комментарий преподавателя")
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'teacher'}, related_name='graded_submissions')
    graded_at = models.DateTimeField(null=True, blank=True)
    
    # История версий
    version = models.PositiveIntegerField(default=1, verbose_name="Версия")
    
    class Meta:
        db_table = 'submissions'
        unique_together = ('task', 'student')
        verbose_name = 'Работа студента'
        verbose_name_plural = 'Работы студентов'
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.task.title}"
    
    def save(self, *args, **kwargs):
        # Автоматическое определение late submission
        if self.submitted_at and self.task.deadline:
            self.is_late = self.submitted_at > self.task.deadline
        super().save(*args, **kwargs)


class Feedback(models.Model):
    """Дополнительный фидбек (комментарии)"""
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='feedbacks')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField(verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True)
    is_internal = models.BooleanField(default=False, verbose_name="Внутренний комментарий")
    is_resolved = models.BooleanField(default=False, verbose_name="Решено")
    
    class Meta:
        db_table = 'feedbacks'
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Комментарий к работе {self.submission.id}"


class TaskBatch(models.Model):
    """Пакет задач (для массового создания)"""
    name = models.CharField(max_length=200, verbose_name="Название пакета")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='task_batches')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'})
    tasks_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'task_batches'
        verbose_name = 'Пакет задач'
        verbose_name_plural = 'Пакеты задач'
    
    def __str__(self):
        return self.name


class SubmissionAnalytics(models.Model):
    """Аналитика по сдаче работ"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='submission_analytics')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='analytics')
    total_assigned = models.PositiveIntegerField(default=0)
    total_submitted = models.PositiveIntegerField(default=0)
    total_graded = models.PositiveIntegerField(default=0)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    median_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    min_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    late_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'submission_analytics'
        verbose_name = 'Аналитика сдачи'
        verbose_name_plural = 'Аналитика сдачи'
    
    def __str__(self):
        task_name = f" ({self.task.title})" if self.task else ""
        return f"Аналитика: {self.course}{task_name}"
