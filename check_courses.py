import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()
from courses.models import Course
print('Все курсы в базе:')
for c in Course.objects.all()[:15]:
    print(f'  {c.subject.name} - {c.group.group_name}')
print(f'\nВсего курсов: {Course.objects.count()}')
