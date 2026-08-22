Standart Reserve — План разработки (v2.0)

CI/CD + Docker-first стратегия
1. ОБЩАЯ СТРАТЕГИЯ
1.1. Принципы разработки
Принцип	Описание
Docker-first	Всё разрабатывается и запускается в контейнерах
CI/CD с первого дня	Каждый PR → сборка → тесты → деплой на dev-стенд
Vertical Slices	Каждый этап — законченная функция (сквозная)
Working MVP	После каждого этапа система должна быть работоспособна в контейнерах
Agent-Ready	Каждый промпт — самодостаточный блок для передачи в Cursor/Grok
1.2. Инфраструктура
yaml
# docker-compose.yml (базовая структура)
services:
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: standart_reserve
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/standart_reserve
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host 0.0.0.0

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
1.3. CI/CD Pipeline (GitHub Actions / GitLab CI)
yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run backend tests
        run: |
          cd backend
          docker build -t backend-test .
          docker run backend-test pytest

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run frontend tests
        run: |
          cd frontend
          npm ci
          npm run test

  deploy-dev:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to dev
        run: |
          docker-compose -f docker-compose.dev.yml up -d --build

2. ЭТАПЫ РАЗРАБОТКИ
ЭТАП 0: ИНИЦИАЛИЗАЦИЯ ПРОЕКТА И DOCKER-ИНФРАСТРУКТУРА (1 день)
Цель: Создать структуру проекта, настроить Docker-контейнеры, подготовить CI/CD.

Промпт для агента:
text
Ты — DevOps-инженер и разработчик. Создай инфраструктуру проекта Standart Reserve с полной контейнеризацией и CI/CD.

## Структура проекта
standart-reserve/
├── .github/
│ └── workflows/
│ └── ci.yml # CI/CD pipeline
├── backend/
│ ├── app/
│ │ ├── init.py
│ │ ├── main.py # FastAPI приложение
│ │ ├── core/
│ │ │ ├── init.py
│ │ │ ├── config.py # Настройки (pydantic-settings)
│ │ │ └── database.py # Подключение к БД
│ │ ├── api/
│ │ │ └── v1/
│ │ │ └── init.py
│ │ ├── models/
│ │ │ └── init.py
│ │ └── schemas/
│ │ └── init.py
│ ├── tests/
│ │ └── init.py
│ ├── Dockerfile
│ ├── docker-compose.yml
│ ├── requirements.txt
│ ├── pyproject.toml
│ └── .env.example
├── frontend/
│ ├── src/
│ │ ├── main.tsx
│ │ ├── App.tsx
│ │ ├── vite-env.d.ts
│ │ ├── api/
│ │ ├── components/
│ │ ├── pages/
│ │ ├── stores/
│ │ └── types/
│ ├── Dockerfile
│ ├── nginx.conf
│ ├── package.json
│ ├── vite.config.ts
│ └── .env.example
├── nginx/
│ └── nginx.conf # Reverse proxy
├── docker-compose.yml # Полный стек
├── docker-compose.dev.yml # Dev-стек с горячей перезагрузкой
├── docker-compose.test.yml # Test-стек
├── .env.example # Общие переменные
└── README.md

text

## Требования

### 1. Backend Dockerfile
- Базовый образ: python:3.12-slim
- Установка зависимостей из requirements.txt
- Копирование исходного кода
- Запуск через uvicorn
- Healthcheck: /health
- Работает на порту 8000

### 2. Frontend Dockerfile
- Многостадийная сборка:
  - Стадия 1: node:20-alpine (сборка)
  - Стадия 2: nginx:alpine (раздача)
- Сборка через Vite
- Раздача через Nginx
- Работает на порту 80 (внутри контейнера)

### 3. docker-compose.yml
- postgres:15 (с volume для данных)
- backend (сборка из ./backend)
- frontend (сборка из ./frontend)
- nginx (reverse proxy, порт 80)
- Все сервисы в одной сети

### 4. docker-compose.dev.yml
- postgres
- backend с горячей перезагрузкой (volume + --reload)
- frontend с hot-reload (npm run dev)
- Порты: 5432, 8000, 5173

### 5. CI/CD (.github/workflows/ci.yml)
- Триггеры: push на main/develop, pull_request
- Stage 1: Lint (flake8/black)
- Stage 2: Test Backend (pytest в контейнере)
- Stage 3: Test Frontend (npm test)
- Stage 4: Build (сборка образов)
- Stage 5: Deploy Dev (автоматически при push в develop)

### 6. Backend app/main.py
- FastAPI приложение с CORS
- Эндпоинт /health → {"status": "ok"}
- Swagger на /docs
- Подключение к БД через SQLAlchemy (проверка при старте)

## Критерии приемки

- [ ] `docker-compose up -d` — все контейнеры запускаются без ошибок
- [ ] `curl http://localhost/health` → {"status": "ok"}
- [ ] `curl http://localhost/docs` → Swagger UI открывается
- [ ] `docker-compose down` — контейнеры останавливаются чисто
- [ ] `docker-compose -f docker-compose.dev.yml up` — backend перезагружается при изменении кода
- [ ] `docker-compose -f docker-compose.dev.yml up` — frontend перезагружается при изменении кода
- [ ] В CI: успешный прогон линтера и тестов (хотя бы заглушек)
- [ ] В CI: сборка образов проходит без ошибок
- [ ] `.env.example` создан со всеми переменными

## Способ проверки

1. Клонировать репозиторий
2. Скопировать .env.example в .env
3. Выполнить `docker-compose up -d`
4. Открыть http://localhost/docs
5. Выполнить `docker-compose down`
6. Проверить CI (GitHub Actions) — зеленая галочка

ЭТАП 1: МОДЕЛИ ДАННЫХ И МИГРАЦИИ (1 день)
Цель: Создать все модели SQLAlchemy, настроить Alembic, выполнить миграции.

Промпт для агента:
text
Ты — разработчик Python и SQLAlchemy. Реализуй модели данных и миграции для проекта Standart Reserve по спецификации DATA_MODEL.md.

## Задача

Создать все модели SQLAlchemy и настроить Alembic для миграций.

## Требования

### 1. Файлы моделей (app/models/)

Создать файлы:
- `app/models/__init__.py` — экспорт всех моделей
- `app/models/base.py` — базовый класс с created_at/updated_at
- `app/models/product.py` — Product (code, name, category, plant_id...)
- `app/models/object.py` — Object (code, name, city, type...)
- `app/models/user.py` — User (id, username, email, password_hash...)
- `app/models/session.py` — Session (id, user_id, token...)
- `app/models/password_reset.py` — PasswordResetToken
- `app/models/request.py` — Request (id, request_type, status...)
- `app/models/request_item.py` — RequestItem
- `app/models/request_item_history.py` — RequestItemHistory
- `app/models/normative.py` — Normative
- `app/models/available_balance.py` — AvailableBalance
- `app/models/event.py` — Event

### 2. Отношения (SQLAlchemy relationships)

- Product.parent_code → Product
- Product.children_code → Product
- Product.plant_id → Object
- User.sessions → Session (cascade delete)
- User.password_reset_tokens → PasswordResetToken (cascade delete)
- Request.initiator → User
- Request.items → RequestItem (cascade delete)
- Request.normatives → Normative
- RequestItem.product → Product
- RequestItem.warehouse → Object
- RequestItemHistory.request_item → RequestItem (cascade delete)
- RequestItemHistory.changed_by → User
- Normative.request → Request
- Normative.product → Product
- Normative.warehouse → Object
- AvailableBalance.warehouse → Object
- AvailableBalance.product → Product
- Event.request → Request

### 3. Настройка Alembic

- Инициализировать Alembic: `alembic init migrations`
- Настроить alembic.ini (url из .env)
- Создать первую миграцию (создание всех таблиц)
- Создать вторую миграцию (индексы из DATA_MODEL.md)
- Создать третью миграцию (триггеры expire_normatives и т.д.)

### 4. Триггеры и функции (Python или SQL)

Реализовать через SQLAlchemy или сырой SQL:
- Функция expire_normatives() — ежедневное истечение сроков
- Триггер request_created_event — создание события при создании запроса
- Триггер create_normative_on_approve — создание норматива при утверждении
- Функция convert_to_tons() и convert_to_units() — пересчет единиц

### 5. Тестовые данные

Создать скрипт `scripts/seed_data.py` для заполнения тестовыми данными:
- 3 завода (Москва, Екатеринбург, Новосибирск)
- 5 складов (Ростов, Владивосток, Казань, Краснодар, СПб)
- 10 продуктов (разных категорий A/B/C)
- 5 пользователей (по одной на каждую роль)

## Критерии приемки

- [ ] Alembic migration успешно создает все таблицы в БД
- [ ] Alembic migration успешно создает все индексы
- [ ] Все Foreign Key отношения работают (ON DELETE CASCADE)
- [ ] Триггеры созданы и работают (можно проверить через psql)
- [ ] `python scripts/seed_data.py` заполняет БД тестовыми данными
- [ ] `docker-compose exec backend python -c "from app.models import *; print('ok')"` не выдает ошибок импорта
- [ ] SQLAlchemy может выполнить SELECT * FROM products

## Способ проверки

1. `docker-compose up -d postgres`
2. `docker-compose run --rm backend alembic upgrade head`
3. `docker-compose exec postgres psql -U postgres -d standart_reserve -c "\dt"` → список таблиц
4. `docker-compose run --rm backend python scripts/seed_data.py`
5. `docker-compose exec postgres psql -U postgres -d standart_reserve -c "SELECT * FROM products;"` → видим данные
6. Проверить триггеры: `docker-compose exec postgres psql -U postgres -d standart_reserve -c "\d+ normatives"` → триггеры видны


ЭТАП 2: БЭКЕНД — АУТЕНТИФИКАЦИЯ И ПОЛЬЗОВАТЕЛИ (2 дня)
Цель: Реализовать JWT-аутентификацию, регистрацию, управление пользователями и RBAC.

Промпт для агента:
text
Ты — разработчик FastAPI. Реализуй аутентификацию и управление пользователями для проекта Standart Reserve.

## Контекст

- Backend: FastAPI
- DB: PostgreSQL (SQLAlchemy async)
- Auth: JWT (access + refresh токены)
- Password: bcrypt (passlib)

## Задача

Реализовать модуль аутентификации с полным функционалом.

## Требования

### 1. Настройка безопасности

```python
# app/core/security.py
- hash_password(password: str) -> str (bcrypt)
- verify_password(password: str, hash: str) -> bool
- create_access_token(data: dict, expires_delta: timedelta) -> str
- create_refresh_token(data: dict) -> str
- get_current_user(token: str) -> User (зависимость для эндпоинтов)
- require_roles(roles: List[str]) -> зависимость для RBAC
2. Эндпоинты (app/api/v1/endpoints/auth.py)
Эндпоинт	Метод	Описание	Права
/auth/register	POST	Регистрация пользователя	admin (MVP — можно всем)
/auth/login	POST	Вход, получение токенов	public
/auth/logout	POST	Выход (revoke refresh token)	auth
/auth/refresh	POST	Обновление access токена	public (с refresh_token)
/auth/profile	GET	Текущий пользователь	auth
/auth/change-password	POST	Смена пароля	auth
3. Модели Session
Хранит refresh_token (для logout и refresh)

user_id → Users.id (CASCADE)

expires_at → 7 дней

revoked_at → null, если активна

4. RBAC (Роли)
commercial — создает запросы, видит свои

pp — согласование ПП, видит все запросы

economist — согласование экономиста, видит все запросы

logistics — дашборд, заказы, разовые перемещения

guest — только чтение

5. Тесты
python
# tests/test_auth.py
- test_login_success()
- test_login_wrong_password()
- test_login_inactive_user()
- test_refresh_token()
- test_logout()
- test_profile_without_token_401()
- test_profile_with_token_200()
- test_rbac_commercial_cannot_see_all_requests()
- test_rbac_pp_can_see_all_requests()
6. Middleware
CORS настроен для фронтенда (localhost:5173, 80)

Обработка 401 → автоматический logout на фронтенде

Критерии приемки
□ POST /auth/login → возвращает { access_token, refresh_token, user }
□ POST /auth/login с неверным паролем → 401
□ GET /auth/profile с токеном → данные пользователя
□ GET /auth/profile без токена → 401
□ POST /auth/refresh с валидным refresh_token → новый access_token
□ POST /auth/logout делает refresh_token недействительным
□ GET /admin/dashboard с ролью guest → 403 (или 404, если нет эндпоинта)
□ Все тесты проходят: docker-compose run --rm backend pytest
□ Swagger (/docs) показывает все эндпоинты с авторизацией
Способ проверки
docker-compose up -d

Создать пользователя: POST /auth/register

Войти: POST /auth/login

Сохранить токен, проверить GET /auth/profile

Попробовать без токена → 401

Обновить токен через /auth/refresh

Выйти через /auth/logout

Попробовать обновить токен → 401

Запустить тесты: docker-compose run --rm backend pytest -v



### ЭТАП 3: БЭКЕНД — СПРАВОЧНИКИ И CRUD ЗАПРОСОВ (2 дня)

**Цель:** Реализовать CRUD для справочников (products, objects) и запросов (requests).

#### Промпт для агента:
Ты — разработчик FastAPI. Реализуй справочники и CRUD запросов для проекта Standart Reserve.

Контекст
Модели: Product, Object, Request, RequestItem уже созданы

Аутентификация: работает

RBAC: работает

Задача
Реализовать эндпоинты для справочников и управления запросами.

Требования
1. Справочники (app/api/v1/endpoints/references.py)
Эндпоинт	Метод	Описание	Права
/references/products	GET	Список продуктов (пагинация, фильтры)	auth
/references/products/{code}	GET	Продукт по коду	auth
/references/objects	GET	Список объектов (пагинация, фильтры)	auth
/references/objects/{code}	GET	Объект по коду	auth
/references/users	GET	Список пользователей	admin/auth
Фильтры для продуктов:

search (по code или name, ILIKE)

category (A/B/C)

is_active (true/false)

Фильтры для объектов:

type (plant/warehouse)

city

is_active

2. Запросы (app/api/v1/endpoints/requests.py)
Эндпоинт	Метод	Описание	Права
/requests	POST	Создать запрос	commercial, logistics (one_time)
/requests	GET	Список запросов	auth (с фильтрацией по роли)
/requests/{id}	GET	Детали запроса	auth (проверка прав)
/requests/{id}	PUT	Обновить черновик	initiator (только draft)
/requests/{id}	DELETE	Удалить черновик	initiator (только draft)
/requests/{id}/submit	POST	Отправить на согласование	initiator (только draft)
Фильтры для запросов:

type (normative/one_time)

status (draft/pp_approved/economy_check/...)

client_name (ILIKE)

initiator_id (только для админов)

from_date / to_date (created_at)

Права на чтение:

Commercial: видит только свои запросы

PP/Economist/Logistics: видит все запросы

Guest: видит только активные нормативы (через другой эндпоинт)

3. Валидация (Pydantic)
python
# app/schemas/request.py
class RequestCreate(BaseModel):
    request_type: Literal['normative', 'one_time']
    client_name: str
    expiry_date: Optional[date] = None  # только для normative
    items: List[RequestItemCreate]
    comment: Optional[str] = None

class RequestItemCreate(BaseModel):
    product_code: int
    warehouse_code: int
    quantity_requested: Decimal
    unit: Literal['шт', 'т']
4. Бизнес-логика
Создание:

Проверка: если request_type == 'normative' → expiry_date обязателен

Проверка: expiry_date ≤ NOW() + 6 месяцев, иначе 400 INVALID_EXPIRY_DATE

Проверка: product_code, warehouse_code существуют

Проверка: unit соответствует product (шт или т)

Инициатор: текущий пользователь

Статус: draft

Обновление:

Только для статуса draft

Только инициатор

Можно изменить: client_name, expiry_date, items, comment

Удаление:

Только для статуса draft

Только инициатор

Soft delete (deleted_at)

Отправка:

Только для статуса draft

Только инициатор

Статус → pp_approved

5. Тесты
python
# tests/test_requests.py
- test_create_request_normative_success()
- test_create_request_one_time_success()
- test_create_request_without_expiry_date_fails()
- test_update_draft_success()
- test_update_not_draft_fails()
- test_delete_draft_success()
- test_submit_draft_to_pp()
- test_commercial_sees_only_own_requests()
- test_pp_sees_all_requests()
Критерии приемки
□ GET /references/products → список продуктов с пагинацией
□ GET /references/products?search=подшипник → фильтрация работает
□ POST /requests → запрос создан с правильным статусом (draft)
□ GET /requests/my → только запросы текущего пользователя (для commercial)
□ GET /requests (PP) → видит все запросы
□ PUT /requests/{id} → обновляет только в статусе draft
□ DELETE /requests/{id} → удаляет только в статусе draft
□ POST /requests/{id}/submit → статус стал pp_approved
□ Все тесты проходят
Способ проверки
docker-compose up -d

POST /auth/login → получить токен коммерческого менеджера

POST /requests → создать запрос с 2-3 позициями

GET /requests/my → видим созданный запрос

PUT /requests/{id} → меняем клиента

POST /requests/{id}/submit → статус стал pp_approved

DELETE /requests/{id} → ошибка (нельзя удалить не draft)

GET /requests (admin/pp) → видим все запросы

Тесты: docker-compose run --rm backend pytest tests/test_requests.py -v

text

---

### ЭТАП 4: БЭКЕНД — СОГЛАСОВАНИЕ (2 дня)

**Цель:** Реализовать процесс согласования для ПП и экономиста с тремя действиями.

#### Промпт для агента:
Ты — разработчик FastAPI. Реализуй процесс согласования запросов для проекта Standart Reserve.

Контекст
Модели: Request, RequestItem, RequestItemHistory, Normative

Статусы: draft → pp_approved → economy_check → active/approved

Задача
Реализовать эндпоинты согласования с действиями: approve, edit, reject.

Требования
1. Эндпоинты (app/api/v1/endpoints/approvals.py)
Эндпоинт	Метод	Описание	Права
/approvals/pp/pending	GET	Список для ПП (status=pp_approved)	pp
/approvals/pp/{id}/action	POST	Действие ПП	pp
/approvals/economy/pending	GET	Список для экономиста (status=economy_check)	economist
/approvals/economy/{id}/action	POST	Действие экономиста	economist
2. Действия
approve:

ПП: status → economy_check

Экономист (нормативный): status → active + создание Normative

Экономист (разовый): status → approved

edit:

Изменяет quantity_approved в request_items

Сохраняет комментарий в comment_pp или comment_economy

ПП: status → economy_check (после редактирования)

Экономист: status → economy_rework (возврат инициатору)

reject:

status → rejected

Сохраняет комментарий в comment_pp или comment_economy

3. RequestItemHistory
При каждом edit создается запись в request_item_history:

request_item_id

field_name: 'quantity_approved'

old_value, new_value

changed_by: текущий пользователь

comment: из действия

4. Создание Normative (триггер или логика)
При approved от экономиста (нормативный):

Создать запись в normatives для каждой позиции

Использовать quantity_approved (или quantity_requested, если не указан)

category взять из products

client_name, expiry_date из requests

5. Логика для экономиста (тарифы — не MVP)
В MVP экономист видит только:

Список позиций с объемами

Может принять решение без отображения тарифов (задел на будущее)

6. Тесты
python
# tests/test_approvals.py
- test_pp_approve_normative()
- test_pp_approve_one_time()
- test_pp_edit()
- test_pp_reject()
- test_economist_approve_normative_creates_normative()
- test_economist_approve_one_time()
- test_economist_edit_returns_to_rework()
- test_economist_reject()
- test_non_pp_cannot_approve()
- test_cannot_approve_wrong_status()
Критерии приемки
□ GET /approvals/pp/pending → список со статусом pp_approved
□ POST /approvals/pp/{id}/action approve → статус economy_check
□ POST /approvals/pp/{id}/action edit → quantity_approved изменен, комментарий сохранен
□ POST /approvals/pp/{id}/action reject → статус rejected
□ GET /approvals/economy/pending → список со статусом economy_check
□ POST /approvals/economy/{id}/action approve → статус active (норматив создан)
□ POST /approvals/economy/{id}/action approve (разовый) → статус approved
□ POST /approvals/economy/{id}/action edit → статус economy_rework
□ request_item_history содержит запись при edit
□ normatives содержит запись при утверждении
□ Все тесты проходят
Способ проверки
Создать запрос (коммерция) → draft

POST /requests/{id}/submit → pp_approved

Войти как ПП → GET /approvals/pp/pending → видим запрос

POST /approvals/pp/{id}/action approve → economy_check

Войти как экономист → GET /approvals/economy/pending → видим запрос

POST /approvals/economy/{id}/action approve → active

Проверить normatives: SELECT * FROM normatives WHERE request_id = '{id}'

Проверить историю: SELECT * FROM request_item_history WHERE request_item_id = ...

Проверить rejected: POST ... reject → статус rejected

Тесты: docker-compose run --rm backend pytest tests/test_approvals.py -v

text

---

### ЭТАП 5: БЭКЕНД — ЛОГИСТИКА (2 дня)

**Цель:** Реализовать дашборд логиста, дефицит, формирование заказов, Excel-экспорт.

#### Промпт для агента:
Ты — разработчик FastAPI. Реализуй логистический модуль для проекта Standart Reserve.

Контекст
Модели: Normative, AvailableBalance, Product, Object, Request

Фильтры: все запасы / только с нормативами / только дефицит

Единицы: шт/т (пересчет через weight_kg)

Задача
Реализовать дашборд логиста для нормативов и разовых перемещений.

Требования
1. Нормативы (app/api/v1/endpoints/logistics_normative.py)
Эндпоинт	Метод	Описание	Права
/logistics/normative/dashboard	GET	Дашборд с дефицитом	все авторизованные
/logistics/normative/{warehouse_code}/generate-orders	POST	Сформировать заказы	logistics
/logistics/normative/export	GET	Выгрузка в Excel	logistics
2. Логика дашборда
sql
-- Дашборд (дефицит)
SELECT 
    n.warehouse_code,
    o.name AS warehouse_name,
    n.product_code,
    p.name AS product_name,
    n.quantity AS normative_quantity,
    COALESCE(ab.quantity, 0) AS fact_quantity,
    (n.quantity - COALESCE(ab.quantity, 0)) AS deficit,
    n.unit,
    n.client_name,
    n.expiry_date,
    p.category,
    p.weight_kg
FROM normatives n
JOIN objects o ON n.warehouse_code = o.code
JOIN products p ON n.product_code = p.code
LEFT JOIN available_balances ab ON n.warehouse_code = ab.warehouse_code AND n.product_code = ab.product_code
WHERE n.deleted_at IS NULL
  AND n.expiry_date >= CURRENT_DATE
Фильтры (query params):

warehouse_code — фильтр по складу

filter_mode — 'all' | 'with_normatives' | 'deficit_only'

unit — 'шт' | 'т' (пересчет через weight_kg)

Пересчет единиц:

Если unit = 'т': quantity = quantity * weight_kg / 1000

Если unit = 'шт': quantity = quantity (без изменений)

3. Формирование заказов
POST /logistics/normative/{warehouse_code}/generate-orders

Логика:

Получить все позиции с дефицитом для склада

Сгруппировать по заводам (plant_id из products)

Для каждого завода создать заказ со списком позиций

Вернуть структуру:

json
{
    "orders": [
        {
            "plant_code": 1001,
            "plant_name": "Завод Московский",
            "items": [
                {
                    "product_code": 10001,
                    "product_name": "Подшипник 6204ZZ",
                    "deficit": 400,
                    "unit": "шт"
                }
            ]
        }
    ]
}
4. Экспорт Excel
GET /logistics/normative/export

Формат: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

Структура:
| Склад | Артикул | Название | Норматив | Факт | Дефицит | Ед | Клиент |

5. Разовые перемещения (app/api/v1/endpoints/logistics_one_time.py)
Эндпоинт	Метод	Описание	Права
/logistics/one-time/list	GET	Список разовых запросов	все авторизованные
/logistics/one-time/{id}/execute	POST	Отметить исполненным	logistics
/logistics/one-time/initiators	GET	Список заявителей	все авторизованные
/logistics/one-time/clients	GET	Список клиентов	все авторизованные
Фильтры:

warehouse_code

client_name (ILIKE)

initiator_id

from_date / to_date (created_at)

status (approved/executed/rejected)

Исполнение:

json
{
    "order_number": "РН-2026-08-18-001",
    "comment": "Отгрузка произведена"
}
→ статус executed, executed_at, executed_by

6. Тесты
python
# tests/test_logistics.py
- test_dashboard_returns_deficit()
- test_dashboard_filter_deficit_only()
- test_dashboard_unit_conversion()
- test_generate_orders_returns_correct_structure()
- test_export_excel_returns_file()
- test_one_time_list_filters()
- test_one_time_execute()
- test_one_time_cannot_execute_wrong_status()
Критерии приемки
□ GET /logistics/normative/dashboard → список с дефицитом
□ Фильтр deficit_only → только позиции с дефицитом > 0
□ Переключение unit=т → значения пересчитаны через weight_kg
□ POST /logistics/normative/{warehouse_code}/generate-orders → структура с заказами
□ GET /logistics/normative/export → Excel-файл
□ GET /logistics/one-time/list → список с пагинацией
□ Фильтры работают (склад, клиент, заявитель, дата)
□ POST /logistics/one-time/{id}/execute → статус executed
□ Все тесты проходят
Способ проверки
Создать нормативный запрос → утвердить (активен)

Загрузить остатки (POST /inventory/upload или ручной INSERT)

GET /logistics/normative/dashboard → видим дефицит

GET /logistics/normative/dashboard?unit=т → значения в тоннах

GET /logistics/normative/dashboard?filter_mode=deficit_only → только дефицит

POST /logistics/normative/{warehouse_code}/generate-orders → заказы сформированы

GET /logistics/normative/export → скачивается Excel

Создать разовый запрос → утвердить (approved)

GET /logistics/one-time/list → видим в списке

POST /logistics/one-time/{id}/execute → статус executed

Тесты: docker-compose run --rm backend pytest tests/test_logistics.py -v

text

---

### ЭТАП 6: ФРОНТЕНД — БАЗОВАЯ ИНФРАСТРУКТУРА И СТРАНИЦЫ (2 дня)

**Цель:** Создать фронтенд-приложение с роутингом, аутентификацией и базовыми страницами.

#### Промпт для агента:
Ты — разработчик React и TypeScript. Создай фронтенд-приложение для проекта Standart Reserve.

Контекст
Бэкенд: FastAPI (http://localhost:8000/api/v1)

Аутентификация: JWT (Bearer token)

Стейт: Pinia

UI: Ant Design или MUI

Задача
Создать фронтенд с роутингом, аутентификацией, базовыми страницами и API-клиентом.

Требования
1. Структура проекта (src/)
text
src/
├── api/
│   ├── client.ts           # axios instance + interceptors
│   ├── auth.ts             # auth endpoints
│   ├── requests.ts         # request endpoints
│   ├── references.ts       # reference endpoints
│   └── types.ts            # TypeScript types
├── components/
│   ├── common/
│   │   ├── Layout.tsx      # глобальный лейаут (меню + header)
│   │   ├── ProtectedRoute.tsx
│   │   ├── StatusBadge.tsx
│   │   └── LoadingOverlay.tsx
│   └── requests/
│       ├── RequestCard.tsx
│       └── RequestForm.tsx
├── pages/
│   ├── LoginPage.tsx
│   ├── DashboardPage.tsx
│   ├── RequestsPage.tsx
│   ├── CreateRequestPage.tsx
│   ├── RequestDetailPage.tsx
│   ├── ApprovalsPage.tsx
│   ├── NormativesPage.tsx
│   └── ...
├── stores/
│   ├── auth.ts             # Pinia auth store
│   ├── requests.ts         # Pinia requests store
│   └── ui.ts               # UI state (theme, loading)
├── hooks/
│   ├── useAuth.ts
│   └── useRequests.ts
├── router/
│   └── index.tsx           # React Router routes
├── styles/
│   └── global.css
├── App.tsx
└── main.tsx
2. API-клиент (axios)
Базовый URL: /api/v1 (прокси на бэкенд)

Интерцептор: добавляет Authorization: Bearer <token>

Интерцептор: обработка 401 → logout

Интерцептор: обработка ошибок (показ toast)

3. AuthStore (Pinia)
typescript
interface AuthStore {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    
    login(username: string, password: string): Promise<void>;
    logout(): Promise<void>;
    refreshToken(): Promise<void>;
    fetchProfile(): Promise<void>;
}
4. Роутинг
Путь	Компонент	Защита
/login	LoginPage	public
/	редирект на /dashboard	auth
/dashboard	DashboardPage	auth
/requests/my	RequestsPage	auth
/requests/create	CreateRequestPage	auth (commercial/logistics)
/requests/:id	RequestDetailPage	auth
/approvals/pp	ApprovalsPage	auth (pp)
/approvals/economy	ApprovalsPage	auth (economist)
/logistics/dashboard	LogisticsDashboardPage	auth (все роли, управление — logistics)
/logistics/one-time	OneTimeRequestsPage	auth (все роли, управление — logistics)
/normatives	NormativesPage	auth
/references/products	ReferencesPage	auth
/references/objects	ReferencesPage	auth
5. Базовые страницы (MVP)
LoginPage:

Форма: username, password

Кнопка "Войти"

Обработка ошибок

DashboardPage:

Карточки-виджеты (кол-во активных, в работе, ожидают...)

Последние 10 запросов (таблица)

Ссылки на переход

RequestsPage:

Список запросов с пагинацией

Фильтры: статус, тип, клиент

Кнопка "Создать запрос"

CreateRequestPage:

Форма создания запроса

Выбор типа (нормативный/разовый)

Динамическое добавление позиций (артикул, склад, кол-во)

Кнопки: Сохранить, Отправить

RequestDetailPage:

Отображение всей информации

История изменений

Кнопки действий (зависят от роли/статуса)

6. dev-окружение
Vite с HMR

Прокси на бэкенд: http://localhost:8000

.env: VITE_API_URL

Критерии приемки
□ npm run dev → приложение открывается на http://localhost:5173
□ Страница /login отображается
□ Вход работает → редирект на /dashboard
□ Без токена → редирект на /login
□ Меню отображается для авторизованного пользователя
□ API-клиент работает (запросы к /auth/profile)
□ Обработка 401 → автоматический logout
□ Создание запроса → данные отправляются на бэк
□ Список запросов загружается и отображается
Способ проверки
docker-compose up -d (backend + frontend)

Открыть http://localhost

Попробовать войти с тестовым пользователем

После входа → видим дашборд

Перейти в "Мои запросы" → загружается список

Создать запрос → заполнить форму → отправить

Проверить в админке БД: SELECT * FROM requests ORDER BY created_at DESC

Открыть карточку запроса → видим детали

Если нет токена → редирект на /login

text

---

### ЭТАП 7: ФРОНТЕНД — СОГЛАСОВАНИЕ И ЛОГИСТИКА (2 дня)

**Цель:** Реализовать страницы согласования и логистики на фронтенде.

#### Промпт для агента:
Ты — разработчик React и TypeScript. Реализуй страницы согласования и логистики для проекта Standart Reserve.

Контекст
Бэкенд: все эндпоинты готовы

Роли: pp, economist, logistics

UI: Ant Design / MUI

Задача
Реализовать страницы для согласования и логистики.

Требования
1. Страница согласования (/approvals/pp и /approvals/economy)
Список:

Таблица с запросами в статусе pp_approved (для ПП) или economy_check (для экономиста)

Колонки: ID, клиент, тип, кол-во позиций, дата

Фильтры: тип, клиент

Кнопка "Открыть" → модальное окно

Модальное окно согласования:

Информация о запросе (клиент, тип, дата)

Таблица позиций с editable quantity_approved (поле ввода)

Поле для комментария

Три кнопки: "Утвердить", "Редактировать (с комментарием)", "Отказать"

Состояния:

Загрузка (spinner)

Успешно (toast)

Ошибка (toast)

2. Страница логистики — нормативы (/logistics/dashboard)
Фильтры:

Переключатель единиц: шт / тонны

Переключатель фильтра: Все запасы / Только с нормативами / Требуют пополнения

Поиск по артикулу/названию

Выбор склада

Дашборд:

Группировка по складам (аккордеон)

Для каждого склада: таблица с позициями

Колонки: артикул, название, норматив, факт, дефицит, единица, клиент

Индикатор: красный если дефицит > 0

Кнопка "Сформировать заказы":

Открывает модалку с предпросмотром заказов

Список заказов по заводам

Кнопка "Подтвердить" → отправка на бэк

Кнопка "Скачать Excel" → выгрузка

3. Страница логистики — разовые (/logistics/one-time)
Фильтры:

Склад (select)

Клиент (input + автокомплит)

Заявитель (select из списка)

Дата с... по...

Статус (select)

Таблица:

Колонки: ID, клиент, склад, заявитель, дата, статус, позиции

Кнопка "Исполнить" (для статуса approved)

Модальное окно "Исполнить":

Поле: Номер разнарядки (обязательное)

Поле: Комментарий (опционально)

Кнопка "Подтвердить"

4. Общие компоненты
StatusBadge:

tsx
<StatusBadge status="active" /> // зеленый
<StatusBadge status="draft" />  // серый
<StatusBadge status="rejected" /> // красный
DeficitIndicator:

tsx
<DeficitIndicator deficit={400} /> // красный если > 0
<DeficitIndicator deficit={0} />  // зеленый если 0
UnitToggle:

tsx
<UnitToggle value="шт" onChange={setUnit} />
FilterToggle:

tsx
<FilterToggle value="all" onChange={setFilter} />
5. API-клиент (новые эндпоинты)
typescript
// src/api/approvals.ts
export const approvalsApi = {
    getPPPending: (params) => api.get('/approvals/pp/pending', { params }),
    ppAction: (id, data) => api.post(`/approvals/pp/${id}/action`, data),
    getEconomyPending: (params) => api.get('/approvals/economy/pending', { params }),
    economyAction: (id, data) => api.post(`/approvals/economy/${id}/action`, data),
};

// src/api/logistics.ts
export const logisticsApi = {
    getDashboard: (params) => api.get('/logistics/normative/dashboard', { params }),
    generateOrders: (warehouseCode) => api.post(`/logistics/normative/${warehouseCode}/generate-orders`),
    exportOrders: (params) => api.get('/logistics/normative/export', { params, responseType: 'blob' }),
    getOneTimeList: (params) => api.get('/logistics/one-time/list', { params }),
    executeOneTime: (id, data) => api.post(`/logistics/one-time/${id}/execute`, data),
    getInitiators: () => api.get('/logistics/one-time/initiators'),
    getClients: () => api.get('/logistics/one-time/clients'),
};
Критерии приемки
□ Страница /approvals/pp → список запросов для ПП
□ Модалка согласования открывается по клику
□ Можно изменить quantity_approved
□ Кнопки: Утвердить → статус меняется
□ Кнопки: Редактировать → возврат на доработку
□ Кнопки: Отказать → статус rejected
□ Страница /logistics/dashboard → показывает дефицит
□ Переключатель шт/т меняет единицы
□ Переключатель фильтра работает
□ Кнопка "Сформировать заказы" → предпросмотр
□ Скачать Excel → файл скачивается
□ Страница /logistics/one-time → список разовых
□ Фильтры работают
□ Кнопка "Исполнить" → модалка с order_number и comment
□ После исполнения статус меняется на executed
Способ проверки
Создать запрос (коммерция) → отправить

Войти как ПП → /approvals/pp → видим запрос

Открыть → изменить объем → "Утвердить"

Войти как экономист → /approvals/economy → видим запрос

Открыть → "Утвердить" → статус active

Войти как логист → /logistics/dashboard → видим дефицит

Переключить единицы → данные обновились

Сформировать заказы → предпросмотр → подтвердить

Скачать Excel → файл скачался

Создать разовый запрос → утвердить (ПП + экономист)

Войти как логист → /logistics/one-time → видим запрос

Фильтр по складу → список обновился

"Исполнить" → заполнить номер → подтвердить

Статус изменился на executed

text

---

### ЭТАП 7.1: УПРАВЛЕНИЕ ПРОДУКТАМИ (CRUD + EXCEL-ЗАГРУЗКА)

**Цель:** Дать ролям ПП, экономист и логист возможность вести номенклатуру: скачивать Excel-шаблон, загружать продукты пакетом, редактировать карточку и удалять артикул с проверкой связей.

#### Новые поля в `products`

| Поле | Тип | Описание |
|------|-----|----------|
| `gtin` | VARCHAR(13) | Штрихкод GTIN-13 (если заполнен — ровно 13 цифр; **не уникален**) |
| `mark_control` | BOOLEAN DEFAULT false | Признак «Честный знак» |
| `last_modified_by` | UUID → users.id | Кто последний изменил карточку |
| `last_modified_at` | TIMESTAMPTZ DEFAULT NOW() | Когда последний раз изменили |

Изменения пишутся в `audit_log` (entity_type=`product`).

#### Эндпоинты

| Метод | Эндпоинт | Описание | Права |
|-------|----------|----------|-------|
| GET | `/references/products/template` | Скачать Excel-шаблон | pp, economist, logistics |
| POST | `/references/products/upload` | Загрузить продукты из Excel | pp, economist, logistics |
| GET | `/references/products/{code}/edit` | Карточка для редактирования | pp, economist, logistics |
| PUT | `/references/products/{code}` | Обновить продукт | pp, economist, logistics |
| DELETE | `/references/products/{code}` | Удалить продукт (soft delete) | pp, economist, logistics |

Просмотр списка и карточки (`GET /references/products`, `GET /references/products/{code}`) остаётся доступным всем авторизованным ролям.

#### Права доступа

| Роль | Просмотр | Загрузка Excel | Редактирование | Удаление |
|------|----------|----------------|----------------|----------|
| commercial | ✅ | ❌ | ❌ | ❌ |
| pp | ✅ | ✅ | ✅ | ✅ |
| economist | ✅ | ✅ | ✅ | ✅ |
| logistics | ✅ | ✅ | ✅ | ✅ |
| guest | ✅ | ❌ | ❌ | ❌ |

#### Excel-шаблон

Формат: `.xlsx` (допускается `.xls`). Первая строка — заголовки.

| Колонка | Формат | Пример |
|---------|--------|--------|
| code | integer, обязательный | 10020 |
| name | текст, обязательный | Подшипник 6205ZZ |
| status | «Активный» → is_active=true; пусто → false | Активный |
| children_code | integer или пусто; не обязан существовать в БД | 10021 |
| parent_code | integer или пусто; не обязан существовать в БД | 10001 |
| category | A / B / C, обязательный | A |
| mark_control | «да» / «нет» | нет |
| gtin | 13 цифр или пусто; может повторяться у разных артикулов | 4601234567890 |
| plant_id | код завода (нужен для новых) | 1001 |
| weight_kg | вес > 0 (нужен для новых) | 0.250 |

Логика загрузки: совпадение по `code` — обновление, иначе создание. Обязательные поля: `code`, `name`, `category`. GTIN не проверяется на уникальность. `parent_code` / `children_code` записываются как есть, даже если таких артикулов ещё нет. Итог: «Загружено X, ошибок Y».

Удаление блокируется, если есть связанные `normatives`, `request_items` или `available_balances`.

#### Критерии приемки

- [ ] Документация согласована (roadmap, data model, API, frontend)
- [ ] Поля gtin, mark_control, last_modified_by, last_modified_at в модели и миграции
- [ ] GET `/references/products/template` отдаёт Excel с шапкой
- [ ] POST `/references/products/upload` создаёт новые и обновляет существующие
- [ ] Отчёт: «Загружено X, ошибок Y»
- [ ] GET/PUT/DELETE `/references/products/{code}` работают с RBAC
- [ ] Удаление с связями возвращает ошибку
- [ ] GTIN: 13 цифр если заполнен, дубликаты разрешены
- [ ] parent_code / children_code: сохраняются без проверки существования в БД
- [ ] Фронт: шаблон, Drag-and-Drop загрузка, модалка редактирования, удаление с подтверждением
- [ ] Кнопки управления только у pp / economist / logistics
- [ ] Тесты проходят

---

### ЭТАП 7.2: УПРАВЛЕНИЕ ОБЪЕКТАМИ (СКЛАДЫ И ЗАВОДЫ)

**Цель:** Дать роли логист возможность вести справочник объектов (`objects`): создавать склады и заводы, редактировать карточку и удалять объект с проверкой связей. Просмотр остаётся доступным всем авторизованным ролям.

Принцип тот же, что у управления продуктами (этап 7.1), но проще: нет родительских связей, Excel-загрузки и GTIN.

#### Новые поля в `objects`

| Поле | Тип | Описание |
|------|-----|----------|
| `last_modified_by` | UUID → users.id | Кто последний изменил карточку |
| `last_modified_at` | TIMESTAMPTZ DEFAULT NOW() | Когда последний раз изменили |

Изменения пишутся в `audit_log` (entity_type=`object`). При создании нового склада/завода `is_active = true` по умолчанию. Seed заполняет `last_modified_by` / `last_modified_at` у существующих объектов.

#### Эндпоинты

| Метод | Эндпоинт | Описание | Права |
|-------|----------|----------|-------|
| POST | `/references/objects` | Создать объект | logistics |
| GET | `/references/objects/{code}/edit` | Карточка для редактирования | logistics |
| PUT | `/references/objects/{code}` | Обновить объект | logistics |
| DELETE | `/references/objects/{code}` | Удалить объект (soft delete) | logistics |

Просмотр списка и карточки (`GET /references/objects`, `GET /references/objects/{code}`) остаётся доступным всем авторизованным ролям.

#### Поля объекта

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `code` | INTEGER | ✅ | Код объекта (PK, вводит пользователь, не редактируется) |
| `name` | TEXT | ✅ | Наименование |
| `city` | TEXT | ✅ | Город |
| `region` | TEXT | ❌ | Регион |
| `address` | TEXT | ❌ | Адрес |
| `type` | VARCHAR(20) | ✅ | `plant` или `warehouse` |
| `is_active` | BOOLEAN | ✅ | Активен (по умолчанию true) |
| `last_modified_by` | UUID | ❌ | Кто последний изменил → `users(id)` |
| `last_modified_at` | TIMESTAMP | ❌ | Дата последнего изменения |

#### Права доступа

| Роль | Просмотр | Создание | Редактирование | Удаление |
|------|----------|----------|----------------|----------|
| commercial | ✅ | ❌ | ❌ | ❌ |
| pp | ✅ | ❌ | ❌ | ❌ |
| economist | ✅ | ❌ | ❌ | ❌ |
| logistics | ✅ | ✅ | ✅ | ✅ |
| guest | ✅ | ❌ | ❌ | ❌ |

#### Валидация и удаление

- `code` — целое число > 0; при создании проверяется уникальность
- `name`, `city` — не пустые
- `type` — только `plant` или `warehouse`
- `code` при обновлении не меняется
- `last_modified_by` / `last_modified_at` заполняются автоматически

Удаление (soft delete, `deleted_at`) блокируется с **409 Conflict**, если объект используется в:

- `products.plant_id` / `second_plant_id` / `third_plant_id`
- `request_items.warehouse_code`
- `normatives.warehouse_code`
- `available_balances.warehouse_code`

#### Критерии приемки

- [ ] Документация согласована (roadmap, data model, API, frontend)
- [ ] Поля last_modified_by, last_modified_at в модели и миграции
- [ ] POST `/references/objects` создаёт объект (is_active=true по умолчанию)
- [ ] GET `/references/objects/{code}/edit` возвращает объект
- [ ] PUT `/references/objects/{code}` обновляет объект, code не меняется
- [ ] DELETE `/references/objects/{code}` — soft delete, связи → 409
- [ ] last_modified_by и last_modified_at заполняются
- [ ] Кнопки управления только у logistics
- [ ] Фронт: модалки создания и редактирования, удаление с подтверждением
- [ ] Seed: существующие объекты с last_modified_by / last_modified_at
- [ ] Тесты проходят (`tests/test_objects_crud.py`)

---

### ЭТАП 7.3: ЗАГРУЗКА ОСТАТКОВ ИЗ ERP И ДАШБОРД ЛОГИСТА

**Цель:** Загружать остатки из Excel ERP (`available` / `plan`) и показывать их на дашборде логиста вместо поля «Факт».

#### Изменения в `available_balances`

| Поле | Тип | Описание |
|------|-----|----------|
| `available` | DECIMAL(12,2) | Доступно (факт − заказы клиентов); бывшее `quantity` |
| `plan` | DECIMAL(12,2) | Запланировано (`available` + разнарядки) |

Дефицит: норматив − `plan`.

#### Эндпоинт

| Метод | Эндпоинт | Описание | Права |
|-------|----------|----------|-------|
| POST | `/logistics/normative/upload` | Загрузить остатки из Excel | logistics |

Колонки Excel (1-based): 1 `product_code`, 3 `erp_plant_code`, 5 `erp_warehouse_code`, 19 `available`, 20 `plan`. Upsert по складу и артикулу.

Дашборд (`GET /logistics/normative/dashboard`) возвращает `available` и `plan` вместо `fact_quantity`. Кнопка «Загрузить актуальные остатки» — только у логиста.

При загрузке: для складов из файла старые `available_balances` удаляются, затем вставляются строки файла. Обновляется `sync_metadata` (`GET /logistics/normative/sync-info`).

---

### ЭТАП 7.4: УДАЛЕНИЕ ЗАПРОСА И ИЗМЕНЕНИЕ СРОКА НОРМАТИВА

**Цель:** Разрешить инициатору удалять запрос до финального согласования; дать возможность уменьшить срок активного норматива.

#### Удаление (`DELETE /requests/{id}`)

Только инициатор. Soft delete. Разрешённые статусы: `draft`, `pp_approved`, `economy_check`, `rejected`, `expired`. Запрещено: `active`, `approved`, `executed` (400 «Невозможно удалить запрос после финального согласования»). Связанные `normatives` тоже soft-delete.

#### Изменение срока

- Черновик: `PUT /requests/{id}` — максимум 6 месяцев от `created_at`.
- Согласование: `expiry_date` в теле `approve` (не отдельный `edit`). У экономиста для норматива — только уменьшение, не раньше сегодня.
- Активный норматив: `PATCH /requests/{id}/expiry-date` — только уменьшение, ≥ сегодня. Гость не может. Обновляются связанные `normatives`.

Фронт: кнопка «Удалить» на карточке (до согласования); кнопка «Изменить дату» для `active`; поле даты в модалке экономиста.

---

### ЭТАП 7.5: СОГЛАСОВАНИЕ APPROVE/REJECT (БЕЗ REWORK)

**Цель:** Зафиксировать фактический процесс согласования.

- API: `action` ∈ {`approve`, `reject`}. `edit` → 422.
- Статусы `pp_rework` / `economy_rework` не используются (сняты с CHECK в миграции `0012`).
- Корректировка объёма — поля `items` в `approve`.
- ПП pending: статус `pp_approved` (после `submit` из `draft`).
- Фронт: кнопки «Утвердить» и «Отказать»; меню согласования только у соответствующей роли.

---

### ЭТАП 8: CI/CD, ТЕСТИРОВАНИЕ И ЗАВЕРШЕНИЕ (1 день)

**Цель:** Настроить полноценный CI/CD пайплайн, написать сквозные тесты, подготовить к деплою.

#### Промпт для агента:
Ты — DevOps и разработчик. Заверши проект Standart Reserve: настрой CI/CD, напиши сквозные тесты и подготовь к деплою.

Контекст
Проект полностью разработан

Контейнеры работают

CI/CD частично настроен

Задача
Довести CI/CD до полной готовности, написать сквозные тесты, подготовить документацию по деплою.

Требования
1. CI/CD Pipeline (полный)
yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Lint backend
        run: |
          cd backend
          pip install ruff
          ruff check .
      - name: Lint frontend
        run: |
          cd frontend
          npm ci
          npm run lint

  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - name: Run backend tests
        run: |
          cd backend
          docker build -t backend-test .
          docker run --network host -e DATABASE_URL=postgresql://postgres:test@localhost:5432/test backend-test pytest

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run frontend tests
        run: |
          cd frontend
          npm ci
          npm run test

  build:
    needs: [lint, test-backend, test-frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build backend image
        run: |
          cd backend
          docker build -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/backend:latest .
      - name: Build frontend image
        run: |
          cd frontend
          docker build -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/frontend:latest .

  deploy-dev:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to dev
        run: |
          docker-compose -f docker-compose.dev.yml up -d --build
      - name: Health check
        run: |
          curl --retry 10 --retry-delay 5 http://localhost/health || exit 1

  deploy-prod:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Deploy to production
        run: |
          # Копирование на прод-сервер и запуск
          echo "Deploy to production server..."
2. Сквозные тесты (E2E)
Создать tests/e2e/test_full_flow.py (Playwright или pytest + requests):

python
# tests/e2e/test_full_flow.py
import requests

BASE_URL = "http://localhost/api/v1"

def test_full_normative_flow():
    # 1. Создать пользователей
    # 2. Войти как commercial → создать запрос
    # 3. Войти как PP → утвердить
    # 4. Войти как экономист → утвердить
    # 5. Войти как логист → проверить дефицит
    # 6. Сформировать заказ
    # 7. Проверить, что норматив создан
    pass

def test_full_one_time_flow():
    # 1. Создать разовый запрос
    # 2. PP утвердить
    # 3. Экономист утвердить
    # 4. Логист исполнить
    pass
3. Документация по деплою
Создать DEPLOY.md:

markdown
# Deploy Guide

## Требования
- Docker 24+
- Docker Compose 2+
- Сервер с Ubuntu 22.04+

## Установка

1. Клонировать репозиторий
2. Скопировать .env.example → .env
3. Изменить переменные окружения
4. Запустить: `docker-compose up -d`

## Обновление

1. `git pull`
2. `docker-compose down`
3. `docker-compose up -d --build`

## Мониторинг

- Healthcheck: http://localhost/health
- Логи: `docker-compose logs -f`

## Бэкап

- `docker-compose exec postgres pg_dump -U postgres standart_reserve > backup.sql`
4. Скрипты для облегчения разработки
Создать Makefile:

makefile
.PHONY: help up down logs test seed

help:
	@echo "Available commands:"
	@echo "  up       Start all services"
	@echo "  down     Stop all services"
	@echo "  logs     Show logs"
	@echo "  test     Run all tests"
	@echo "  seed     Seed test data"

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	docker-compose run --rm backend pytest
	docker-compose run --rm frontend npm test

seed:
	docker-compose run --rm backend python scripts/seed_data.py
5. README.md (обновленный)
Добавить:

Скриншоты дашборда

Инструкция по локальной разработке

Ссылка на Swagger (/docs)

Критерии приемки
□ CI/CD проходит без ошибок (зеленая галочка)
□ Сквозные тесты проходят
□ make up → все запускается
□ make test → все тесты проходят
□ make seed → тестовые данные загружены
□ DEPLOY.md написан и понятен
□ README.md обновлен
Способ проверки
Запушить в develop → CI прогоняет тесты → деплой на dev

Запушить в main → CI прогоняет тесты → деплой на prod

Открыть dev-стенд и проверить руками

Выполнить сквозной тест: commercial → PP → economist → logistics

Проверить что все работает

Сделать make down и make up → все поднимается

text

---

## 3. ИТОГОВАЯ СВОДКА

| Этап | Название | Дней | Ключевой результат |
|------|----------|------|---------------------|
| 0 | Docker + CI/CD | 1 | Полная контейнеризация, готовый CI/CD |
| 1 | Модели + миграции | 1 | Все таблицы БД, триггеры, тестовые данные |
| 2 | Аутентификация | 2 | JWT, RBAC, сессии, тесты |
| 3 | Справочники + CRUD | 2 | Продукты, объекты, создание запросов |
| 4 | Согласование | 2 | ПП + Экономист, 3 действия, нормативы |
| 5 | Логистика | 2 | Дашборд, дефицит, заказы, Excel, разовые |
| 6 | Фронтенд — база | 2 | Роутинг, auth, базовые страницы |
| 7 | Фронтенд — согласование | 2 | Согласование + логистика на фронте |
| 7.1 | Управление продуктами | 1 | CRUD номенклатуры, Excel-загрузка, GTIN |
| 7.2 | Управление объектами | 1 | CRUD складов и заводов, RBAC logistics |
| 7.3 | Остатки ERP + дашборд | 1 | Excel-загрузка available/plan, overwrite, sync-info |
| 7.4 | Удаление запроса и срок | 0.5 | Delete до согласования, уменьшение expiry |
| 7.5 | Согласование approve/reject | 0.5 | Без rework/edit, меню по ролям |
| 8 | CI/CD + тесты | 1 | Полный пайплайн, E2E тесты, деплой |
| **Итого** | | **18 дней** | **Полноценный MVP с CI/CD** |

---

## 4. КРИТЕРИИ ГОТОВНОСТИ MVP

- [ ] Все контейнеры собираются без ошибок (`docker-compose build`)
- [ ] Все контейнеры запускаются (`docker-compose up -d`)
- [ ] Healthcheck проходит (`curl http://localhost/health` → 200)
- [ ] Swagger доступен (`http://localhost/docs`)
- [ ] Фронтенд доступен (`http://localhost/`)
- [ ] Можно войти (login → dashboard)
- [ ] Можно создать запрос (commercial)
- [ ] Можно согласовать (PP → approve → economist → approve)
- [ ] Появляется норматив (проверить в БД)
- [ ] Логист видит дефицит
- [ ] Логист формирует заказы
- [ ] Логист выгружает Excel
- [ ] CI/CD проходит (зеленый билд)
- [ ] Сквозной тест проходит без ошибок

---

**Версия:** 2.1
**Дата:** 22.08.2026
**Статус:** Утверждена