# Standart Reserve

Система управления нормативными запасами и разовыми перемещениями: от коммерческого запроса до исполнения на складе.

## Требования

| Инструмент | Версия |
|------------|--------|
| Docker Engine | 24+ |
| Docker Compose | v2 (`docker compose`) или v1 (`docker-compose`) |
| Python | 3.12 (только для запуска backend без Docker) |
| Node.js | 20 (только для запуска frontend без Docker) |

Порты по умолчанию: **80** и **443** (продакшн), **5173 / 8000 / 5432** (разработка).

## Быстрый старт (локально, dev)

```bash
cp .env.example .env
make dev
```

После запуска:

| Сервис | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend health | http://localhost:8000/health |
| Swagger UI (только DEBUG=true) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

Если порты заняты, измените их в `.env`:

```
BACKEND_PORT=8000
FRONTEND_PORT=5173
POSTGRES_HOST_PORT=5432
```

Горячая перезагрузка включена для backend (`--reload`) и frontend (Vite HMR).

Остановка:

```bash
make down
```

## Продакшн (локально или на сервере)

```bash
cp .env.example .env
# Обязательно задайте POSTGRES_PASSWORD, DATABASE_URL и BACKEND_CORS_ORIGINS.
# SECRET_KEY можно оставить пустым — ключ сгенерируется при первом запуске.
make up
# или:
docker-compose -f docker-compose.prod.yml up -d
```

Приложение доступно по HTTPS. Самоподписанный сертификат создаётся автоматически в `certs/`, если файлов ещё нет.

| Проверка | Команда |
|----------|---------|
| Контейнеры | `docker-compose -f docker-compose.prod.yml ps` |
| Health | `curl -fk https://localhost/health` |
| Главная | `curl -Ik https://localhost` → 200 |

Для домена с доверенным сертификатом:

1. Пропишите `DOMAIN=your-domain.com` и CORS: `BACKEND_CORS_ORIGINS=["https://your-domain.com"]`.
2. Положите Let's Encrypt файлы в `certs/fullchain.pem` и `certs/privkey.pem`.
3. Откройте 80/443 и выполните `curl -I https://your-domain.com`.

HTTP (порт 80) перенаправляет на HTTPS, кроме `/health`.

### Деплой на сервер

Боевой выкат: **push в `main`** → зелёный CI → self-hosted runner на сервере. Пошагово для разработчика и DevOps: **[docs/DEPLOY.md](docs/DEPLOY.md)**.

Кратко: разработчик создаёт токен раннера в GitHub, DevOps один раз запускает `deploy/install-runner.sh`. Секреты остаются в `/opt/standart-reserve/.env` на сервере.

Миграции Alembic применяются автоматически при старте backend (`RUN_MIGRATIONS=1`).

Бэкапы PostgreSQL (`pg_dump`, gzip) пишет sidecar `backup` раз в сутки (настраивается `BACKUP_INTERVAL_SECONDS`). Ручной снимок:

```bash
make backup
```

Дампы лежат в volume `postgres_backups`, хранение — `BACKUP_KEEP_DAYS` дней.

## Команды Makefile

| Команда | Описание |
|---------|----------|
| `make dev` | Dev-стек с hot-reload (порты 5173, 8000, 5432) |
| `make up` / `make prod` | Продакшн-стек с HTTPS (порты 80, 443) |
| `make down` | Остановить контейнеры |
| `make logs` | Логи dev-стека |
| `make logs-prod` | Логи продакшн-стека |
| `make test` | Тесты backend и frontend |
| `make lint` | Линтеры backend и frontend |
| `make migrate` | Применить миграции Alembic (dev) |
| `make backup` | Разовый `pg_dump` |
| `make clean` | Остановить контейнеры и удалить volume |

## Структура проекта

```
standart-reserve/
├── .github/workflows/ci.yml
├── .github/workflows/deploy.yml
├── deploy/                  # Установка self-hosted runner
├── backend/                 # FastAPI
├── frontend/                # React + Vite
├── nginx/                   # Reverse proxy (HTTP→HTTPS)
├── scripts/                 # pg_dump backup loop
├── certs/                   # TLS (не коммитится)
├── docker-compose.yml       # Упрощённый HTTP-стек
├── docker-compose.prod.yml  # Продакшн (HTTPS, limits, backups; проект standart-reserve-prod)
├── docker-compose.dev.yml   # Development
├── docker-compose.test.yml  # Tests
├── Makefile
└── docs/                    # Спецификации
```

## Переменные окружения

Файл `.env` не коммитится. Скопируйте `.env.example` и измените секреты.

| Переменная | Назначение |
|------------|------------|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Учётные данные PostgreSQL |
| `DATABASE_URL` | Строка подключения backend |
| `SECRET_KEY` | JWT; пустое значение → автогенерация при первом запуске |
| `DEBUG` | `false` на продакшне (Swagger отключён) |
| `LOG_LEVEL` | `INFO` на продакшне; логи пишутся в stdout |
| `BACKEND_CORS_ORIGINS` | Список доверенных origin, без `*` |
| `DOMAIN` | Имя хоста для TLS |
| `VITE_API_URL` | Базовый путь API (`/api/v1`) |

## Безопасность (продакшн)

- `DEBUG=false`, Swagger/OpenAPI отключены
- CORS только из `BACKEND_CORS_ORIGINS` (wildcard запрещён)
- HTTPS через Nginx, HSTS и базовые security-заголовки
- Healthcheck и лимиты CPU/RAM у всех сервисов
- Образы с тегами версий (`postgres:15-alpine`, `nginx:1.27-alpine`, `python:3.12-slim`, `node:20-alpine`)

## CI/CD

GitHub Actions:

1. `lint-backend` — ruff + black (`.github/workflows/ci.yml`)
2. `lint-frontend` — ESLint
3. `test-backend` / `test-frontend`
4. `build` — сборка Docker-образов
5. `deploy-dev` — при push в `develop` (GitHub-hosted)
6. `deploy-prod` — после успешного CI на `main`, self-hosted runner (`.github/workflows/deploy.yml`)

Настройка прод-деплоя: [docs/DEPLOY.md](docs/DEPLOY.md).

## Документация

- [Видение продукта](docs/PROJECT_VISION.MD)
- [Модель данных](docs/DATA_MODEL.MD)
- [API](docs/API_SPECIFICATION.MD)
- [Фронтенд](docs/FRONTEND_SPEC.MD)
- [План разработки](docs/MVP_ROADMAP.MD)
- [Деплой на production](docs/DEPLOY.md)

## Контакты

- Система: Standart Reserve
- Эксплуатация / доступы: отдел логистики
- Email: logistics@company.ru
