# Standart Reserve

Система управления нормативными запасами и разовыми перемещениями.

## Стек

- **Backend:** FastAPI (Python 3.12) + SQLAlchemy + PostgreSQL 15
- **Frontend:** React 18 + TypeScript + Vite + Ant Design
- **Инфраструктура:** Docker Compose, Nginx, GitHub Actions

## Быстрый старт (dev)

```bash
cp .env.example .env
make dev
```

После запуска:

| Сервис | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend health | http://localhost:8000/health |
| Swagger UI | http://localhost:8000/docs |
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

Удаление контейнеров и volume:

```bash
make clean
```

## Продакшн-стек

```bash
cp .env.example .env
make up
```

Приложение доступно на http://localhost (Nginx reverse proxy).

- Health: http://localhost/health
- Swagger: http://localhost/docs

## Команды Makefile

| Команда | Описание |
|---------|----------|
| `make dev` | Dev-стек с hot-reload (порты 5173, 8000, 5432) |
| `make up` | Продакшн-стек (порт 80) |
| `make down` | Остановить контейнеры |
| `make logs` | Логи dev-стека |
| `make test` | Тесты backend и frontend |
| `make lint` | Линтеры backend и frontend |
| `make clean` | Остановить контейнеры и удалить volume |

## Структура проекта

```
standart-reserve/
├── .github/workflows/ci.yml
├── backend/                 # FastAPI
├── frontend/                # React + Vite
├── nginx/nginx.conf         # Reverse proxy
├── docker-compose.yml       # Production
├── docker-compose.dev.yml   # Development
├── docker-compose.test.yml  # Tests
├── Makefile
└── docs/                    # Спецификации
```

## Переменные окружения

Скопируйте `.env.example` в `.env` и при необходимости измените значения.

Основные переменные:

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `SECRET_KEY`
- `BACKEND_CORS_ORIGINS`
- `VITE_API_URL`

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):

1. `lint-backend` — ruff + black
2. `lint-frontend` — ESLint
3. `test-backend` / `test-frontend`
4. `build` — сборка Docker-образов
5. `deploy-dev` — автоматически при push в `develop`

## Документация

- [Видение продукта](docs/PROJECT_VISION.MD)
- [Модель данных](docs/DATA_MODEL.MD)
- [API](docs/API_SPECIFICATION.MD)
- [Фронтенд](docs/FRONTEND_SPEC.MD)
- [План разработки](docs/MVP_ROADMAP.MD)
