from django.db import models
from django.utils import timezone
from accounts.models import User, Group
from datetime import timedelta


class Subject(models.Model):
    """Дисциплина/Предмет"""
    name = models.CharField(max_length=200, verbose_name="Название предмета")
    code = models.CharField(max_length=20, unique=True, verbose_name="Код предмета")
    description = models.TextField(blank=True, verbose_name="Описание")
    credit_hours = models.PositiveIntegerField(default=3, verbose_name="Кредиты")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'}, related_name='subjects')
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    semester = models.PositiveIntegerField(verbose_name="Семестр изучения")
    year = models.PositiveIntegerField(verbose_name="Учебный год")
    
    class Meta:
        db_table = 'subjects'
        verbose_name = 'Дисциплина'
        verbose_name_plural = 'Дисциплины'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Course(models.Model):
    """Курс (связь предмета и группы)"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='courses')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='courses')
    semester = models.PositiveIntegerField(verbose_name="Семестр")
    year = models.PositiveIntegerField(verbose_name="Учебный год")
    students = models.ManyToManyField(User, related_name='enrolled_courses', blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    description = models.TextField(blank=True, verbose_name="Описание курса")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'courses'
        unique_together = ('subject', 'group', 'semester', 'year')
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-year', '-semester', 'subject__code']
    
    def __str__(self):
        return f"{self.subject.name} - {self.group.group_name}"
    
    @property
    def student_count(self):
        return self.students.count()
    
    @property
    def average_score(self):
        """Средний балл по курсу"""
        from assignments.models import Submission
        submissions = Submission.objects.filter(
            task__course=self,
            score__isnull=False
        )
        if not submissions.exists():
            return 0
        return submissions.aggregate(avg=models.Avg('score'))['avg__avg'] or 0


class Schedule(models.Model):
    """Расписание занятий"""
    DAYS_CHOICES = (
        (1, 'Понедельник'),
        (2, 'Вторник'),
        (3, 'Среда'),
        (4, 'Четверг'),
        (5, 'Пятница'),
        (6, 'Суббота'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='schedule')
    day_of_week = models.PositiveIntegerField(choices=DAYS_CHOICES, verbose_name="День недели")
    start_time = models.TimeField(verbose_name="Время начала")
    end_time = models.TimeField(verbose_name="Время конца")
    classroom = models.CharField(max_length=20, verbose_name="Аудитория")
    week_start = models.DateField(null=True, blank=True, verbose_name="Начало недели")
    week_end = models.DateField(null=True, blank=True, verbose_name="Конец недели")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'schedule'
        verbose_name = 'Занятие'
        verbose_name_plural = 'Расписание'
        ordering = ['course', 'day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.course} - {self.get_day_of_week_display()} {self.start_time}"
    
    def get_deadline_time(self):
        """Получить время дедлайна (за 10 минут до начала)"""
        from datetime import timedelta
        deadline = timezone.datetime.combine(timezone.now().date(), self.start_time) - timezone.timedelta(minutes=10)
        return deadline


class DeadlineTemplate(models.Model):
    """Шаблон дедлайнов для автоматической генерации"""
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='deadline_template')
    default_deadline_offset = models.PositiveIntegerField(default=10, verbose_name="Отступ дедлайна (минуты)")
    allow_weekend_submission = models.BooleanField(default=False, verbose_name="Принимать работы в выходные")
    late_penalty_percent = models.PositiveIntegerField(default=10, verbose_name="Штраф за опоздание (%)")
    max_late_days = models.PositiveIntegerField(default=3, verbose_name="Макс. дней для поздней сдачи")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        db_table = 'deadline_templates'
        verbose_name = 'Шаблон дедлайнов'
        verbose_name_plural = 'Шаблоны дедлайнов'
    
    def __str__(self):
        return f"Шаблон для {self.course}"


class CourseAnalytics(models.Model):
    """Аналитика по курсу (кэшированные данные)"""
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='analytics')
    total_submissions = models.PositiveIntegerField(default=0)
    graded_submissions = models.PositiveIntegerField(default=0)
    late_submissions = models.PositiveIntegerField(default=0)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fail_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'course_analytics'
        verbose_name = 'Аналитика курса'
        verbose_name_plural = 'Аналитика курсов'
    
    def __str__(self):
        return f"Аналитика: {self.course}"
    
    def update_stats(self):
        """Обновить статистику"""
        from assignments.models import Submission, Task
        
        tasks = Task.objects.filter(course=self.course)
        submissions = Submission.objects.filter(task__in=tasks)
        
        self.total_submissions = submissions.count()
        self.graded_submissions = submissions.filter(score__isnull=False).count()
        self.late_submissions = submissions.filter(is_late=True).count()
        
        if submissions.filter(score__isnull=False).exists():
            avg = submissions.filter(score__isnull=False).aggregate(a=models.Avg('score'))['a']
            self.average_score = avg if avg else 0
            
            # Fail rate (оценка ниже 60)
            failed = submissions.filter(score__lt=60).count()
            graded = self.graded_submissions
            self.fail_rate = (failed / graded * 100) if graded > 0 else 0
        
        # Completion rate
        if tasks.exists():
            self.completion_rate = (self.total_submissions / tasks.count() * 100) if tasks.count() > 0 else 0
        
        self.save()


class CourseSlot(models.Model):
    """Слот для задания в курсе (генерируется автоматически)"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='slots')
    slot_number = models.PositiveIntegerField(verbose_name="Номер слота")
    deadline = models.DateTimeField(verbose_name="Дедлайн")
    is_filled = models.BooleanField(default=False, verbose_name="Заполнен")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'course_slots'
        verbose_name = 'Слот задания'
        verbose_name_plural = 'Слоты заданий'
        ordering = ['course', 'deadline']
    
    def __str__(self):
        return f"Слот {self.slot_number} - {self.course} ({self.deadline})"
    
    @classmethod
    def generate_for_course(cls, course, start_date, end_date, total_slots, days_of_week=[1, 2, 3, 4, 5]):
        """
        Автоматическая генерация слотов для курса
        
        Args:
            course: Курс
            start_date: Дата начала (datetime.date)
            end_date: Дата окончания (datetime.date)
            total_slots: Количество слотов
            days_of_week: Дни недели для генерации [1=Пн, 2=Вт, ...]
        
        Returns:
            tuple: (созданные слоты, ошибки конфликтов)
        """
        from assignments.models import Task
        
        created_slots = []
        conflicts = []
        
        current_date = start_date
        slot_number = 1
        slots_created = 0
        
        while current_date <= end_date and slots_created < total_slots:
            # Проверяем день недели
            if current_date.weekday() + 1 in days_of_week:
                # Проверяем конфликты
                has_conflict = cls.check_conflict(course, current_date)
                
                if not has_conflict:
                    # Получаем время начала занятий для этого дня
                    schedule_entry = Schedule.objects.filter(
                        course=course,
                        day_of_week=current_date.weekday() + 1,
                        is_active=True
                    ).first()
                    
                    if schedule_entry:
                        deadline = timezone.datetime.combine(
                            current_date,
                            schedule_entry.start_time
                        )
                        
                        slot = cls.objects.create(
                            course=course,
                            slot_number=slot_number,
                            deadline=deadline,
                            is_filled=False,
                            is_active=True
                        )
                        created_slots.append(slot)
                        slots_created += 1
                        slot_number += 1
                
                else:
                    conflicts.append({
                        'date': current_date,
                        'reason': has_conflict
                    })
            
            current_date += timedelta(days=1)
        
        return created_slots, conflicts
    
    @classmethod
    def check_conflict(cls, course, date):
        """
        Проверка конфликта для даты
        
        Returns:
            str или None: Причина конфликта или None если свободно
        """
        # Проверяем, есть ли уже слот в эту дату
        existing_slot = cls.objects.filter(
            course=course,
            deadline__year=date.year,
            deadline__month=date.month,
            deadline__day=date.day
        ).exists()
        
        if existing_slot:
            return "Уже есть слот в эту дату"
        
        # Проверяем, есть ли занятие в расписании
        day_of_week = date.weekday() + 1
        schedule_exists = Schedule.objects.filter(
            course=course,
            day_of_week=day_of_week,
            is_active=True
        ).exists()
        
        if not schedule_exists:
            return "Нет занятия в расписании в этот день"
        
        # Проверяем конфликты с другими курсами для этой группы
        group_courses = Course.objects.filter(
            group=course.group,
            is_active=True
        ).exclude(id=course.id)
        
        for other_course in group_courses:
            other_schedule = Schedule.objects.filter(
                course=other_course,
                day_of_week=day_of_week,
                is_active=True
            ).first()
            
            if other_schedule:
                # Проверяем пересечение времени
                return f"Группа занята другим предметом: {other_course.subject.name}"
        
        # Проверяем конфликты с преподавателем
        teacher_courses = Course.objects.filter(
            subject__teacher=course.subject.teacher,
            is_active=True
        ).exclude(id=course.id)
        
        for teacher_course in teacher_courses:
            teacher_schedule = Schedule.objects.filter(
                course=teacher_course,
                day_of_week=day_of_week,
                is_active=True
            ).first()
            
            if teacher_schedule:
                return f"Преподаватель занят с другой группой: {teacher_course.group.group_name}"
        
        return None
