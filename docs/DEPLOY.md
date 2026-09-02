# Деплой Standart Reserve на production

Автоматический деплой: **push в `main` → зелёный CI → обновление сервера**.

Репозиторий у разработчика. Сервер у DevOps. Секреты живут только на сервере, в GitHub их нет.

```
Разработчик                         DevOps (один раз)
─────────────                       ─────────────────
1. Пушит workflow в main            4. Ставит Docker + раннер
2. Создаёт environment production      одним скриптом
3. Даёт URL репо и token            5. При необходимости правит
                                       домен в /opt/standart-reserve/.env

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

1. Скопируйте на сервер файл deploy/install-runner.sh из репозитория.
2. Выполните:

sudo bash install-runner.sh \
  --url https://github.com/ORG/REPO \
  --token ВСТАВЬТЕ_ТОКЕН \
  --domain app.company.ru

3. Если домена нет — уберите --domain (будет localhost + self-signed TLS).
4. Откройте входящие 80 и 443. Исходящий HTTPS до github.com и Docker Hub
   должен уже работать, отдельных портов для раннера открывать не нужно.
5. Напишите, когда в GitHub → Settings → Actions → Runners статус Idle.

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

### 1.8. Что разработчику больше не нужно

- SSH на сервер
- `git pull` на сервере
- Секреты в GitHub Secrets
- Собирать и пушить Docker-образы в registry

---

## Часть 2. DevOps (сервер, один раз)

Нужны: Ubuntu 22.04+ (или Debian), root/sudo, исходящий HTTPS. Входящие порты: **80** и **443**. Репозиторий клонировать не обязательно.

### 2.1. Что пришлёт разработчик

- файл `install-runner.sh`
- `--url` репозитория
- `--token`
- домен (если есть)

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
3. Создаёт `/opt/standart-reserve/.env` со сгенерированным паролем БД (существующий `.env` не трогает).
4. Скачивает GitHub Actions runner, регистрирует метку `standart-reserve-prod`, включает systemd.

Повторная регистрация (новый токен):

```bash
sudo bash install-runner.sh --url ... --token ... --replace
```

Только проверка:

```bash
sudo bash install-runner.sh --check
```

### 2.3. После скрипта — если есть боевой домен

```bash
sudo nano /opt/standart-reserve/.env
```

Проверьте:

| Переменная | Что поставить |
|------------|----------------|
| `DOMAIN` | Публичное имя хоста |
| `BACKEND_CORS_ORIGINS` | `["https://ваш-домен"]` без `*` |
| `POSTGRES_PASSWORD` / `DATABASE_URL` | Уже сгенерированы, должны совпадать |
| `CERTS_DIR` | Оставьте `/opt/standart-reserve/certs` |
| `SECRET_KEY` | Можно пустым: ключ создастся при первом старте |

Доверенный TLS: положите Let's Encrypt в `/opt/standart-reserve/certs/fullchain.pem` и `privkey.pem`. Если файлов нет, Nginx сделает self-signed.

Откройте 80/443, затем напишите разработчику, что раннер **Idle**.

Код приложения и `git pull` не нужны: первый workflow сам выкатит стек (`docker-compose.prod.yml`).

### 2.4. Файрвол

| Направление | Куда | Зачем |
|-------------|------|--------|
| Входящий | 80, 443 | Приложение |
| Исходящий | 443 → github.com, objects.githubusercontent.com | Связь раннера |
| Исходящий | 443 → Docker Hub / registry | Образы postgres, nginx, python, node |

Входящий доступ со стороны GitHub **не открывать**.

---

## Как устроен выкат

1. Push в `main` запускает **CI/CD** на GitHub-hosted runner (линтеры, тесты, сборка образов).
2. При успехе `workflow_run` запускает **Deploy production** на сервере.
3. Runner забирает тот же коммит, подключает `/opt/standart-reserve/.env`, выполняет:

   `docker compose -f docker-compose.prod.yml up -d --build --remove-orphans`

4. Alembic-миграции идут при старте backend (`RUN_MIGRATIONS=1`).
5. Проверка: `http://127.0.0.1/health`.
6. Volume PostgreSQL (`postgres_data`) и бэкапы не сбрасываются. TLS лежит в `CERTS_DIR`, а не в рабочей папке Actions.

Ручной выкат: **Actions → Deploy production → Run workflow**.

---

## Эксплуатация

| Задача | Команда / место |
|--------|------------------|
| Статус раннера | GitHub → Settings → Actions → Runners |
| Служба раннера | `sudo systemctl status actions.runner.*.service` |
| Логи раннера | `journalctl -u 'actions.runner.*' -f` |
| Контейнеры | `docker compose -f docker-compose.prod.yml -p standart-reserve-prod ps` |
| Логи приложения | `docker compose -f docker-compose.prod.yml logs -f` |
| Health | `curl -fsS http://127.0.0.1/health` |
| Бэкап БД | sidecar `backup` раз в сутки; дампы в volume `postgres_backups` |
| Снять раннер | `sudo bash install-runner.sh --uninstall` (`.env` и БД остаются) |

Compose-проект называется `standart-reserve-prod` (поле `name` в `docker-compose.prod.yml`). Команды `docker compose` запускайте из каталога, где есть актуальный compose-файл, либо из воркспейса последнего деплоя (`_work/...` у пользователя `github-runner`). Для логов удобнее:

```bash
docker ps --filter name=standart-reserve-prod
docker logs -f standart-reserve-prod-backend-1
```

### Откат

В GitHub: Revert merge в `main` и пуш — после зелёного CI выедет предыдущее состояние. Либо **Run workflow** на нужном коммите, если запускаете вручную с выбранного ref.

Базу откатывать отдельно: восстановить дамп из `postgres_backups`.

---

## Если деплой не стартовал

1. CI на этом коммите красный — прод специально не трогаем.
2. Раннер Offline — DevOps: `sudo bash install-runner.sh --check` и `systemctl status actions.runner.*.service`.
3. Job висит в очереди — нет раннера с меткой `standart-reserve-prod`.
4. Нет `/opt/standart-reserve/.env` — DevOps не отработал скрипт или стёр файл.
5. Environment `production` ждёт ревьюера — подтвердите в Actions.
6. Org запрещает self-hosted runners.

---

## Безопасность

- Self-hosted runner только на **private** репозитории.
- Не вешайте этот же раннер на другие репо и не ставьте метку без префикса проекта.
- `.env` не коммитить (`chmod 640`, владелец `github-runner`).
- `workflow_dispatch` и `workflow_run` после CI на `main`. Pull request с раннера не гоняется.
