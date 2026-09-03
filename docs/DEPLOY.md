# Деплой Standart Reserve на production

Автоматический деплой: **push в `main` → зелёный CI → обновление сервера**.

Репозиторий у разработчика. Сервер у DevOps. Секреты живут только на сервере, в GitHub их нет.

На проде **нет Nginx в compose**. Вход: внешний **Traefik** (сеть `traefik`), TLS и порты 80/443 — на стороне Traefik. Стек приложения: postgres, backend, frontend, backup.

```
Разработчик                         DevOps (один раз)
─────────────                       ─────────────────
1. Пушит workflow в main            4. Ставит раннер скриптом
2. Создаёт environment production   5. Traefik уже должен работать
3. Даёт URL репо и token            6. В .env: боевой DOMAIN (и CORS)

Дальше: git push origin main → GitHub Actions → docker compose на сервере
```

---

## Часть 1. Разработчик (GitHub)

Нужны права **admin** на репозиторий. Репозиторий должен быть **private**: self-hosted runner выполняет код, который приходит из GitHub.

### 1.1. Файлы в репозитории

Уже должны быть в `main`:

| Файл | Зачем |
|------|--------|
| `.github/workflows/ci.yml` | Линтеры, тесты, сборка |
| `.github/workflows/deploy.yml` | Деплой на сервер после зелёного CI |
| `docker-compose.prod.yml` | Прод-стек (Traefik labels, без Nginx) |
| `deploy/install-runner.sh` | Скрипт, который вы отдаёте DevOps |

Если этого ещё нет в `main` — замержите и пушьте. Пока `deploy.yml` нет в ветке по умолчанию, автодеплой не стартует.

### 1.2. Settings → Actions → General

- **Actions permissions:** Allow all actions and reusable workflows.
- Если репозиторий в организации: в org Settings разрешите **self-hosted runners** для этого репо.

### 1.3. Environment `production`

1. **Settings → Environments → New environment**
2. Имя **точно:** `production` (так указано в `deploy.yml`)
3. По желанию включите защиту: Required reviewers, Wait timer, Deployment branches = `main`.

Секреты в Environment **не нужны**. Пароль БД и `SECRET_KEY` лежат в `/opt/standart-reserve/.env` на сервере.

### 1.4. Токен для раннера (живёт около 1 часа)

1. **Settings → Actions → Runners → New self-hosted runner**
2. OS: Linux. Architecture: x64 (или ARM64, если сервер на ARM).
3. Из инструкции на экране возьмите только:
   - URL репозитория: `https://github.com/<org-or-user>/<repo>`
   - `--token` (строка вида `AXXXXXXXXXXXXXXXXXXXXXXXXXX`)
4. **Не запускайте `config.sh` сами.** Токен и URL отправьте DevOps вместе с файлом `deploy/install-runner.sh`.

Если DevOps не успел за час — выпустите новый токен тем же путём (старый никуда передавать не нужно).

Метка раннера, которую проставит скрипт: **`standart-reserve-prod`**. Её нельзя менять — workflow ищет именно её.

### 1.5. Сообщение DevOps (скопируйте)

```
Нужно один раз поставить GitHub Actions runner на прод-сервер Standart Reserve.

Стек ходит в уже существующий Traefik (Docker-сеть traefik). Nginx в приложении больше нет.
Порты 80/443 это приложение не публикует.

1. Скопируйте на сервер файл deploy/install-runner.sh из репозитория.
2. Выполните:

sudo bash install-runner.sh \
  --url https://github.com/ORG/REPO \
  --token ВСТАВЬТЕ_ТОКЕН \
  --domain app.company.ru

3. Проверьте: sudo bash install-runner.sh --check
   Должны быть OK: Docker, .env, DOMAIN, сеть traefik, служба раннера.
4. Если сеть Traefik называется иначе — TRAEFIK_NETWORK в /opt/standart-reserve/.env.
5. Пароль Postgres в .env не меняйте, если база уже есть.
6. Напишите, когда в GitHub → Settings → Actions → Runners статус Idle.

Токен живёт ~1 час. Если протух — пришлите новый, команда та же с --replace.
```

Подставьте свой URL, токен и домен.

### 1.6. Проверка, что раннер на связи

**Settings → Actions → Runners:** имя вида `<hostname>-prod`, метки `self-hosted`, `standart-reserve-prod`, статус **Idle**.

### 1.7. Первый деплой и дальше

Обычный путь: **push / merge в `main`**. Сначала проходит workflow **CI/CD**. Если он зелёный, стартует **Deploy production** на сервере.

Первый раз после добавления `deploy.yml` автозапуск может не сработать (GitHub читает `workflow_run` с ветки по умолчанию). Тогда:

**Actions → Deploy production → Run workflow** (ветка `main`).

Дальше каждый push в `main` деплоит сам, если CI успешен. Ручной запуск оставляйте для повторного выката того же коммита.

`--remove-orphans` снимет старый контейнер **nginx**, если он ещё был в проекте `standart-reserve-prod`. Том Postgres не трогается.

### 1.8. Что разработчику больше не нужно

- SSH на сервер
- `git pull` на сервере
- Секреты в GitHub Secrets
- Собирать и пушить Docker-образы в registry
- Класть TLS-сертификаты в репозиторий или в `certs/` приложения

---

## Часть 2. DevOps (сервер, один раз)

Нужны: Ubuntu 22.04+ (или Debian), root/sudo, исходящий HTTPS, **уже работающий Traefik** с Docker-сетью (обычно `traefik`). Репозиторий клонировать не обязательно.

Скрипт **не** ставит Traefik и **не** открывает 80/443 — это зона Traefik.

### 2.1. Что пришлёт разработчик

- файл `install-runner.sh`
- `--url` репозитория
- `--token`
- публичный домен (тот же, что в Traefik Host)

### 2.2. Одна команда

```bash
sudo bash install-runner.sh \
  --url https://github.com/ORG/REPO \
  --token AAAA \
  --domain app.company.ru
```

Скрипт сам:

1. Ставит Docker Engine и Compose v2, если их ещё нет.
2. Создаёт пользователя `github-runner` (группа `docker`).
3. Создаёт `/opt/standart-reserve/.env` со сгенерированным паролем БД (**существующий `.env` не трогает**).
4. Скачивает GitHub Actions runner, регистрирует метку `standart-reserve-prod`, включает systemd.

Повторная регистрация (новый токен):

```bash
sudo bash install-runner.sh --url ... --token ... --replace
```

Только проверка:

```bash
sudo bash install-runner.sh --check
```

### 2.3. После скрипта

```bash
sudo nano /opt/standart-reserve/.env
```

| Переменная | Что поставить |
|------------|----------------|
| `DOMAIN` | Тот же хост, что в Traefik (`Host(...)`) |
| `BACKEND_CORS_ORIGINS` | `["https://ваш-домен"]` без `*` |
| `TRAEFIK_NETWORK` | Имя Docker-сети Traefik, по умолчанию `traefik` |
| `POSTGRES_PASSWORD` / `DATABASE_URL` | Если том БД уже есть — **не менять**, должны совпадать с инициализацией тома |
| `SECRET_KEY` | Можно пустым: ключ создастся при первом старте |

TLS класть в приложение не нужно: сертификаты у Traefik.

Проверьте сеть до первого деплоя:

```bash
docker network inspect traefik
```

Напишите разработчику, что раннер **Idle**. Код приложения и `git pull` не нужны: первый workflow сам выкатит стек.

### 2.4. Файрвол

| Направление | Куда | Зачем |
|-------------|------|--------|
| Входящий 80/443 | Traefik на хосте | Приложение порты не публикует |
| Исходящий | 443 → github.com, objects.githubusercontent.com | Связь раннера |
| Исходящий | 443 → Docker Hub / registry | Образы postgres, python, node |

Входящий доступ со стороны GitHub **не открывать**.

---

## Как устроен выкат

1. Push в `main` запускает **CI/CD** на GitHub-hosted runner (линтеры, тесты, сборка образов).
2. При успехе `workflow_run` запускает **Deploy production** на сервере.
3. Runner забирает тот же коммит, подключает `/opt/standart-reserve/.env`, проверяет сеть Traefik, выполняет:

   `docker compose -f docker-compose.prod.yml up -d --build --remove-orphans`

4. Alembic-миграции идут при старте backend (`RUN_MIGRATIONS=1`).
5. Проверка: `curl` внутри контейнера backend на `/health`, затем `/health` через Traefik по `DOMAIN`.
6. Volume PostgreSQL (`postgres_data`) и бэкапы не сбрасываются.

Маршруты Traefik (labels в `docker-compose.prod.yml`):

| Правило | Куда |
|---------|------|
| `Host(DOMAIN) && PathPrefix(/api)` | backend:8000 |
| `Host(DOMAIN) && PathPrefix(/health)` | backend:8000 |
| `Host(DOMAIN)` | frontend:80 |

Ручной выкат: **Actions → Deploy production → Run workflow**.

---

## Эксплуатация

| Задача | Команда / место |
|--------|------------------|
| Статус раннера | GitHub → Settings → Actions → Runners |
| Служба раннера | `sudo systemctl status actions.runner.*.service` |
| Логи раннера | `journalctl -u 'actions.runner.*' -f` |
| Контейнеры | `docker ps --filter name=standart-reserve-prod` |
| Логи приложения | `docker logs -f standart-reserve-prod-backend-1` |
| Health (из контейнера) | `docker compose -f docker-compose.prod.yml exec backend curl -fsS http://localhost:8000/health` |
| Health (через Traefik) | `curl -fsS https://DOMAIN/health` |
| Бэкап БД | sidecar `backup` раз в сутки; дампы в volume `postgres_backups` |
| Снять раннер | `sudo bash install-runner.sh --uninstall` (`.env` и БД остаются) |

Compose-проект называется `standart-reserve-prod` (поле `name` в `docker-compose.prod.yml`).

### Откат

В GitHub: Revert merge в `main` и пуш — после зелёного CI выедет предыдущее состояние. Либо **Run workflow** на нужном коммите, если запускаете вручную с выбранного ref.

Базу откатывать отдельно: восстановить дамп из `postgres_backups`.

---

## Если деплой не стартовал

1. CI на этом коммите красный — прод специально не трогаем.
2. Раннер Offline — DevOps: `sudo bash install-runner.sh --check` и `systemctl status actions.runner.*.service`.
3. Job висит в очереди — нет раннера с меткой `standart-reserve-prod`.
4. Нет `/opt/standart-reserve/.env` — DevOps не отработал скрипт или стёр файл.
5. `DOMAIN=localhost` или пустой — Traefik не привяжет Host.
6. Нет Docker-сети `traefik` (или `TRAEFIK_NETWORK`) — Traefik не поднят / другое имя сети.
7. Контейнер healthy, а `/health` с хоста 502 — контейнер не в сети Traefik или правило Host не совпадает с доменом.
8. Environment `production` ждёт ревьюера — подтвердите в Actions.
9. Org запрещает self-hosted runners.

### Backend unhealthy: `password authentication failed for user "postgres"`

Образ собрался, Postgres **healthy**, но backend не может войти. Образ Postgres запоминает пароль **только при первом создании тома** `postgres_data`. Позже смена `POSTGRES_PASSWORD` в `.env` **не меняет** пароль в уже существующей базе.

Типичная причина: `install-runner.sh` создал новый `/opt/standart-reserve/.env` со случайным паролем, а том остался от старого запуска с другим паролем.

**Данные не удалять** (`docker compose down -v` и `docker volume rm` запрещены).

DevOps:

1. Взять пароль из **старого** `.env` (каталог, откуда стек поднимали до раннера).
2. Прописать его в оба поля `/opt/standart-reserve/.env`:
   - `POSTGRES_PASSWORD=...`
   - `DATABASE_URL=postgresql://postgres:ЭТОТ_ЖЕ_ПАРОЛЬ@postgres:5432/standart_reserve`
3. Если в пароле есть `$`, `#`, пробел — лучше сменить его в самой БД осознанно, чем ломать URL. Символ `$` Compose раньше мог «съесть» при подстановке `${...}`.
4. Перезапустить только backend (или снова Run workflow **Deploy production**):

```bash
# пароль в чат не копировать
sudo grep -E '^(POSTGRES_PASSWORD|DATABASE_URL)=' /opt/standart-reserve/.env
```

После правки `.env` повторный деплой из GitHub подхватит файл сам.

---

## Безопасность

- Self-hosted runner только на **private** репозитории.
- Не вешайте этот же раннер на другие репо и не ставьте метку без префикса проекта.
- `.env` не коммитить (`chmod 640`, владелец `github-runner`).
- `workflow_dispatch` и `workflow_run` после CI на `main`. Pull request с раннера не гоняется.
- TLS и HSTS настраивает Traefik, не этот репозиторий.
