# Инструкция по деплою Django Backend на Render

## Способ 1: Деплой через файл render.yaml (рекомендуется)

1. **Создайте новый репозиторий на GitHub** (если ещё не создан):
   ```bash
   cd C:\Users\user\Desktop\12\backend
   git init
   git add .
   git commit -m "Initial commit for Render deployment"
   # Добавьте удалённый репозиторий на GitHub и сделайте push
   ```

2. **На Render.com**:
   - Нажмите "New" → "Other" → "Blueprint" (или "Deploy from Git repo")
   - Выберите "Deploy using Blueprint"
   - Загрузите файл `render.yaml` из папки `backend`
   - Render автоматически создаст сервис с правильными настройками

3. **Настройте переменные окружения в Render Dashboard**:
   - Зайдите в созданный сервис
   - Перейдите во вкладку "Environment"
   - Добавьте/измените следующие переменные:
     - `SECRET_KEY`: сгенерируйте новый (см. ниже)
     - `DEBUG`: `false`
     - `ALLOWED_HOSTS`: `ваш-домен.onrender.com`
     - `CORS_ALLOWED_ORIGINS`: `https://ваш-frontend.vercel.app`
     - `CSRF_TRUSTED_ORIGINS`: `https://ваш-frontend.vercel.app`
     - `DATABASE_URL`: будет автоматически создана Render (PostgreSQL)

4. **Сгенерируйте SECRET_KEY**:
   ```bash
   python generate_secret_key.py
   ```
   Скопируйте результат и вставьте в переменную `SECRET_KEY` в Render Dashboard.

## Способ 2: Ручная настройка в UI Render (если Blueprint не работает)

При создании **Static Site** (или **Web Service**) вручную укажите:

### Поля для заполнения:

| Поле | Значение |
|------|----------|
| **Name** | `lms-backend` |
| **Region** | Выберите ближайший к вам (например, Frankfurt) |
| **Branch** | `main` |
| **Root Directory** | *(оставьте пустым)* |
| **Build Command** | `pip install --upgrade pip && pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| **Start Command** | `bash start.sh` |

### Environment Variables (добавьте через кнопку "Add Environment Variable"):

```
SECRET_KEY=ваш-сгенерированный-ключ
DEBUG=false
ALLOWED_HOSTS=*
CORS_ALLOWED_ORIGINS=https://ваш-frontend.vercel.app
CSRF_TRUSTED_ORIGINS=https://ваш-frontend.vercel.app
PYTHON_VERSION=3.11
```

> **Важно:** `DATABASE_URL` создается автоматически Render при подключении PostgreSQL (добавьте базу данных через вкладку "Databases").

## Дополнительные шаги после деплоя

1. **Добавьте PostgreSQL базу данных**:
   - В Dashboard сервиса нажмите "Add Database" → "PostgreSQL"
   - Скопируйте `DATABASE_URL` из переменных окружения

2. **Запустите миграции вручную** (если не сработали автоматически):
   ```bash
   render shell
   python manage.py migrate
   ```

3. **Создайте суперпользователя**:
   ```bash
   render shell
   python manage.py createsuperuser
   ```

4. **Проверьте лог деплоя**:
   - Вкладка "Logs" покажет процесс сборки и возможные ошибки

## Исправление распространённых ошибок

### Ошибка: "No module named 'backend'"
- Убедитесь, что `PYTHONPATH` включает корень проекта (Render делает это автоматически)

### Ошибка: "DATABASE_URL not found"
- Добавьте PostgreSQL через вкладку "Databases" в сервисе

### Ошибка: "Permission denied" для скриптов
- Закоммитьте файлы с правами исполнения:
  ```bash
  git update-index --chmod=+x start.sh render-build.sh
  git commit -m "Fix file permissions"
  ```

## Проверка работы

После деплоя:
1. Откройте `https://ваш-домен.onrender.com/api/`
2. Проверьте авторизацию через `https://ваш-домен.onrender.com/api/token/`
3. Убедитесь, что CORS работает (откройте консоль браузера при запросе с фронтенда)

---

**Файл `render.yaml` уже создан в `backend/render.yaml` и содержит все необходимые настройки.**
