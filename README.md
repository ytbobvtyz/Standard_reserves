# Standart Reserve

Система управления нормативными запасами и разовыми перемещениями: от коммерческого запроса до исполнения на складе.

## Требования

| Инструмент | Версия |
|------------|--------|
| Docker Engine | 24+ |
| Docker Compose | v2 (`docker compose`) или v1 (`docker-compose`) |
| Python | 3.12 (только для запуска backend без Docker) |
| Node.js | 20 (только для запуска frontend без Docker) |

Порты по умолчанию: **5173 / 8000 / 5432** (разработка). На production порты 80/443 слушает внешний Traefik, стек приложения их не публикует.

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

## Продакшн (сервер)

Ingress — внешний Traefik. Стек: postgres, backend, frontend, backup. Nginx в `docker-compose.prod.yml` нет.

На сервере:

1. Traefik уже работает, Docker-сеть обычно называется `traefik`.
2. В `.env` заданы `DOMAIN` (тот же Host, что у Traefik), `BACKEND_CORS_ORIGINS`, пароль БД.
3. Выкат: **push в `main`** → зелёный CI → self-hosted runner. Инструкция: **[docs/DEPLOY.md](docs/DEPLOY.md)**.

Локально `make up` поднимет тот же compose. Если сети Traefik нет, Makefile создаст пустую сеть `traefik` — без самого Traefik сайт на 80/443 не откроется. Для разработки используйте `make dev`.

| Проверка | Команда |
|----------|---------|
| Контейнеры | `docker compose -f docker-compose.prod.yml ps` |
| Health (контейнер) | `docker compose -f docker-compose.prod.yml exec backend curl -fsS http://localhost:8000/health` |
| Health (через Traefik) | `curl -fsS https://your-domain.com/health` |

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
| `make up` / `make prod` | Прод-compose (нужна сеть Traefik; порты 80/443 не публикуются) |
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
├── nginx/                   # Reverse proxy для локального docker-compose.yml
├── scripts/                 # pg_dump backup loop
├── docker-compose.yml       # Упрощённый HTTP-стек с Nginx
├── docker-compose.prod.yml  # Прод: Traefik labels, без Nginx (проект standart-reserve-prod)
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
| `DOMAIN` | Публичный хост; Traefik маршрутизирует `Host(DOMAIN)` |
| `TRAEFIK_NETWORK` | Внешняя Docker-сеть Traefik (по умолчанию `traefik`) |
| `VITE_API_URL` | Базовый путь API (`/api/v1`) |

## Безопасность (продакшн)

- `DEBUG=false`, Swagger/OpenAPI отключены
- CORS только из `BACKEND_CORS_ORIGINS` (wildcard запрещён)
- HTTPS и сертификаты — на внешнем Traefik
- Healthcheck и лимиты CPU/RAM у всех сервисов
- Образы с тегами версий (`postgres:15-alpine`, `python:3.12-slim`, `node:20-alpine`)

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
