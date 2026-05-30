from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Group, TeacherProfile
from assignments.models import Task
from courses.models import Course, Schedule, Subject


User = get_user_model()


class Command(BaseCommand):
    help = "Seed a small initial dataset if the database is empty."

    def handle(self, *args, **options):
        if User.objects.exists() or Group.objects.exists() or Subject.objects.exists():
            self.stdout.write(self.style.SUCCESS("Seed skipped: database already has data."))
            return

        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123",
            role="admin",
        )

        teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@example.com",
            password="teacher123",
            role="teacher",
            first_name="Teacher",
            last_name="One",
        )
        TeacherProfile.objects.create(
            user=teacher,
            department="Informatics",
            position="Lecturer",
        )

        group = Group.objects.create(
            group_name="POVT-1-24",
            department="Informatics",
            semester=1,
            year=2024,
        )

        students = []
        for i in range(1, 6):
            student = User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@example.com",
                password="student123",
                role="student",
                first_name=f"Student{i}",
            )
            group.students.add(student)
            students.append(student)

        subject = Subject.objects.create(
            code="CS101",
            name="Python Backend",
            description="Introductory Django course",
            credit_hours=4,
            teacher=teacher,
            semester=1,
            year=2024,
        )

        course = Course.objects.create(
            subject=subject,
            group=group,
            semester=1,
            year=2024,
        )
        course.students.set(students)

        Schedule.objects.create(
            course=course,
            day_of_week=1,
            start_time="08:00:00",
            end_time="09:30:00",
            classroom="301",
        )

        Task.objects.create(
            title="First Django REST API task",
            description="Create a simple REST API for tasks.",
            course=course,
            created_by=teacher,
            category="homework",
            max_points=100,
            deadline=timezone.now() + timedelta(days=7),
            is_active=True,
        )

        self.stdout.write(self.style.SUCCESS("Initial demo data created successfully."))
        self.stdout.write(f"Admin: {admin.username} / admin123")
        self.stdout.write(f"Teacher: {teacher.username} / teacher123")
