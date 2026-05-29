from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import (
    CustomTokenObtainPairView, UserViewSet, GroupViewSet,
    TeacherProfileViewSet, StudentProfileViewSet, BulkImportViewSet
)
from courses.views import (
    SubjectViewSet, CourseViewSet, ScheduleViewSet,
    DeadlineTemplateViewSet, CourseAnalyticsViewSet, CourseSlotViewSet
)
from assignments.views import (
    TaskViewSet, SubmissionViewSet, FeedbackViewSet,
    TaskBatchViewSet, SubmissionAnalyticsViewSet
)

def health_check(request):
    return JsonResponse({'status': 'ok'})

router = DefaultRouter()

# Accounts
router.register(r'users', UserViewSet, basename='user')
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'teacher-profiles', TeacherProfileViewSet, basename='teacher-profile')
router.register(r'student-profiles', StudentProfileViewSet, basename='student-profile')
router.register(r'bulk-imports', BulkImportViewSet, basename='bulk-import')

# Courses
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'schedule', ScheduleViewSet, basename='schedule')
router.register(r'deadline-templates', DeadlineTemplateViewSet, basename='deadline-template')
router.register(r'course-analytics', CourseAnalyticsViewSet, basename='course-analytics')
router.register(r'course-slots', CourseSlotViewSet, basename='course-slot')

# Assignments
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'submissions', SubmissionViewSet, basename='submission')
router.register(r'feedbacks', FeedbackViewSet, basename='feedback')
router.register(r'task-batches', TaskBatchViewSet, basename='task-batch')
router.register(r'submission-analytics', SubmissionAnalyticsViewSet, basename='submission-analytics')

urlpatterns = [
    # Health check for Render
    path('', health_check, name='health_check'),
    
    # API Schema (Swagger/OpenAPI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # JWT Auth
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API routes
    path('api/', include(router.urls)),
    
    # Admin
    path('admin/', admin.site.urls),
]
