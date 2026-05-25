from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .models import User, Group, TeacherProfile, StudentProfile, BulkImport

UserModel = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    groups_info = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'phone', 'is_active', 'avatar', 'groups_info',
            'date_joined', 'last_login', 'created_at', 'updated_at'
        ]
        read_only_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']
    
    def get_groups_info(self, obj):
        if obj.role == 'student':
            return [
                {'id': g.id, 'name': g.group_name} 
                for g in obj.student_groups.all()
            ]
        return []


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания пользователя"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'phone', 'avatar'
        ]
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        
        # Создаем профиль в зависимости от роли
        if validated_data.get('role') == 'teacher':
            TeacherProfile.objects.create(
                user=user,
                department='Общая',
                position='Преподаватель'
            )
        elif validated_data.get('role') == 'student':
            StudentProfile.objects.create(user=user)
        
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления пользователя"""
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'avatar', 'is_active', 'password'
        ]
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        
        if password:
            instance.set_password(password)
            instance.save()
        
        return instance


class GroupSerializer(serializers.ModelSerializer):
    """Сериализатор группы"""
    students_count = serializers.IntegerField(read_only=True, source='student_count')
    
    class Meta:
        model = Group
        fields = [
            'id', 'group_name', 'department', 'semester', 'year',
            'is_active', 'description', 'students_count', 'created_at'
        ]


class GroupDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор группы со студентами"""
    students = UserSerializer(many=True, read_only=True)
    students_count = serializers.IntegerField(read_only=True, source='student_count')
    courses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id', 'group_name', 'department', 'semester', 'year',
            'is_active', 'description', 'students', 'students_count', 'courses_count',
            'created_at'
        ]
    
    def get_courses_count(self, obj):
        return obj.courses.count()


class TeacherProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля преподавателя"""
    user = UserSerializer(read_only=True)
    subjects_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'user', 'department', 'position', 'bio',
            'academic_degree', 'work_experience', 'is_verified', 'subjects_count'
        ]
    
    def get_subjects_count(self, obj):
        return obj.user.subjects.count()


class TeacherProfileCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания профиля преподавателя"""
    
    class Meta:
        model = TeacherProfile
        fields = ['department', 'position', 'bio', 'academic_degree', 'work_experience']


class StudentProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля студента"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user', 'student_id_number', 'date_of_birth',
            'address', 'emergency_contact', 'notes'
        ]


class StudentProfileCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания профиля студента"""
    
    class Meta:
        model = StudentProfile
        fields = ['student_id_number', 'date_of_birth', 'address', 'emergency_contact', 'notes']


class BulkImportSerializer(serializers.ModelSerializer):
    """Сериализатор для массового импорта"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = BulkImport
        fields = [
            'id', 'file', 'import_type', 'status', 'status_display',
            'total_rows', 'successful_rows', 'failed_rows', 'error_log',
            'created_by', 'created_by_username', 'created_at', 'processed_at'
        ]
        read_only_fields = ['status', 'total_rows', 'successful_rows', 'failed_rows', 'error_log', 'processed_at']


class BulkImportCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания задачи импорта"""
    
    class Meta:
        model = BulkImport
        fields = ['file', 'import_type']


class AuthResponseSerializer(serializers.Serializer):
    """Ответ для аутентификации"""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer(read_only=True)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Кастомный сериализатор для аутентификации с ролью"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Добавляем роль в токен
        token['role'] = user.role
        token['user_id'] = user.id
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Добавляем данные пользователя и роль
        data['user'] = UserSerializer(self.user).data
        data['role'] = self.user.role
        
        return data