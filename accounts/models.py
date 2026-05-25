from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Аватар")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username


class Group(models.Model):
    """Группа студентов"""
    group_name = models.CharField(max_length=50, unique=True, verbose_name="Название группы")
    department = models.CharField(max_length=100, verbose_name="Кафедра")
    semester = models.PositiveIntegerField(verbose_name="Семестр")
    year = models.PositiveIntegerField(verbose_name="Год поступления")
    students = models.ManyToManyField('User', related_name='student_groups', blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'groups'
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
        ordering = ['group_name']
    
    def __str__(self):
        return self.group_name
    
    @property
    def student_count(self):
        return self.students.count()


class TeacherProfile(models.Model):
    """Профиль преподавателя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'}, related_name='teacher_profile')
    department = models.CharField(max_length=100, verbose_name="Кафедра")
    position = models.CharField(max_length=100, verbose_name="Должность")
    bio = models.TextField(blank=True, verbose_name="Биография")
    academic_degree = models.CharField(max_length=100, blank=True, verbose_name="Учёная степень")
    work_experience = models.PositiveIntegerField(blank=True, null=True, verbose_name="Стаж работы (лет)")
    is_verified = models.BooleanField(default=True, verbose_name="Проверен")
    
    class Meta:
        db_table = 'teacher_profiles'
        verbose_name = 'Профиль преподавателя'
        verbose_name_plural = 'Профили преподавателей'
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username


class StudentProfile(models.Model):
    """Профиль студента - для расширенной информации"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'}, related_name='student_profile')
    student_id_number = models.CharField(max_length=20, blank=True, verbose_name="Номер зачётной книжки")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Дата рождения")
    address = models.TextField(blank=True, verbose_name="Адрес")
    emergency_contact = models.CharField(max_length=50, blank=True, verbose_name="Контакт для экстренных случаев")
    notes = models.TextField(blank=True, verbose_name="Примечания")
    
    class Meta:
        db_table = 'student_profiles'
        verbose_name = 'Профиль студента'
        verbose_name_plural = 'Профили студентов'
    
    def __str__(self):
        return f"Профиль {self.user.username}"


class BulkImport(models.Model):
    """Массовый импорт пользователей из Excel"""
    STATUS_CHOICES = (
        ('pending', 'В очереди'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершён'),
        ('failed', 'Ошибка'),
    )
    
    file = models.FileField(upload_to='imports/%Y/%m/%d/', verbose_name="Файл импорта")
    import_type = models.CharField(max_length=20, choices=(
        ('students', 'Студенты'),
        ('teachers', 'Преподаватели'),
        ('groups', 'Группы'),
    ), verbose_name="Тип импорта")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_rows = models.PositiveIntegerField(default=0, verbose_name="Всего строк")
    successful_rows = models.PositiveIntegerField(default=0, verbose_name="Успешных")
    failed_rows = models.PositiveIntegerField(default=0, verbose_name="Ошибок")
    error_log = models.TextField(blank=True, verbose_name="Журнал ошибок")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, limit_choices_to={'role': 'admin'})
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'bulk_imports'
        verbose_name = 'Импорт данных'
        verbose_name_plural = 'Импорт данных'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.import_type} - {self.status} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"
