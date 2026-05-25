import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

users = User.objects.all()
print(f'Всего пользователей: {users.count()}\n')

for u in users:
    print(f'ID: {u.id}, Логин: {u.username}, Email: {u.email}, Роль: {u.role}, Активен: {u.is_active}')