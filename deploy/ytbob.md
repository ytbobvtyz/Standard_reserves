# Деплой Standart Reserve на сервер musicme.ru (домен ytbob.ru)

Порты **80 и 443 не публикуются** контейнерами Standart Reserve. Их занимает Nginx в контейнере `frontend` проекта `muzzzic-prod`. Этот Nginx получает отдельный `server` для `ytbob.ru` и проксирует на контейнеры в той же Docker-сети.

`docker-compose.prod.yml` на этом хосте не использовать: он ждёт сеть Traefik.

## 0. Что уже есть в репозитории

| Файл | Назначение |
|------|------------|
| `docker-compose.ytbob.yml` | postgres, backend, frontend, backup. Без `ports`. Сеть musicme — `external` |
| `nginx/ytbob.http.conf` | Порт 80: ACME и редирект на HTTPS. До сертификата |
| `nginx/ytbob.conf` | Порт 80 + 443. После появления сертификата, вместо http-файла |
| `.env.ytbob.example` | Шаблон `.env`, CORS `https://ytbob.ru` |

Имена, которые резолвит Nginx: `standart-reserve-frontend`, `standart-reserve-backend`.

Живые проверки приложения: `GET /health` и `GET /api/v1/status`. Отдельного маршрута `/api/v1/health` в backend нет; Nginx отдаёт его как прокси на `/health`.

## 1. DNS

Узнать адрес, на котором уже отвечает musicme:

```bash
dig +short musicme.ru A
```

У регистратора домена `ytbob.ru` создать запись:

| Тип | Имя | Значение |
|-----|-----|----------|
| A | `@` | тот же IPv4, что у `musicme.ru` |

`www` не нужен: в конфиге только `ytbob.ru`.

Подождать, пока с самого сервера имя смотрит на этот IP:

```bash
dig +short ytbob.ru A
```

Пока A-запись не совпадает с IP сервера, Let's Encrypt сертификат не выдаст.

## 2. Посмотреть musicme, ничего не останавливая

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
docker network ls | grep muzzzic
docker volume ls | grep -E 'certbot|letsencrypt'
```

Дальше `FRONTEND` — имя контейнера, у которого в портах есть `0.0.0.0:80` и `0.0.0.0:443` (контейнер frontend musicme).

```bash
docker inspect "$FRONTEND" --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
docker inspect "$FRONTEND" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{"\n"}}{{end}}'
docker exec "$FRONTEND" nginx -T 2>/dev/null | grep -E 'include |server_name |listen |certbot|letsencrypt|root '
```

Зафиксировать три факта:

1. Имя сети из `docker network ls | grep muzzzic` — это значение `MUZZZIC_NETWORK`. Часто `muzzzic-prod_default`, но подставлять нужно фактическое.
2. Куда в контейнере смонтирован webroot certbot. В конфиге ожидается `/var/www/certbot`. Если mount другой, поправить `root` в обоих nginx-файлах под этот путь.
3. Есть ли `include /etc/nginx/conf.d/*.conf;` внутри `http {}`. Если да, файл можно положить в `conf.d`. Если конфиг musicme — один файл без include, в `http {}` добавить одну строку `include /etc/nginx/conf.d/ytbob.conf;` и каталог смонтировать. Блоки `server` для `musicme.ru` не менять.

Проверка, что каталог certbot пишется туда же, откуда Nginx его читает: volume `certbot_www` проекта `muzzzic-prod` и mount webroot в `FRONTEND` — один и тот же volume.

## 3. HTTP-vhost, не трогая musicme.ru

Скопировать репозиторий на сервер, например в `/opt/standart-reserve`.

Подключить **только** `nginx/ytbob.http.conf`. Пример, если Nginx включает `conf.d` и этот каталог — bind-mount с хоста (`CONF_D` — хостовый путь, не путь внутри контейнера):

```bash
cp /opt/standart-reserve/nginx/ytbob.http.conf "$CONF_D/ytbob.conf"
docker exec "$FRONTEND" nginx -t
docker exec "$FRONTEND" nginx -s reload
```

Если `conf.d` внутрь контейнера не смонтирован, добавить в `docker-compose` musicme у сервиса `frontend` volume (путь поправить под сервер):

```yaml
- /opt/standart-reserve/nginx/ytbob.http.conf:/etc/nginx/conf.d/ytbob.conf:ro
```

После правки compose musicme — `docker compose -f docker-compose.prod.yml up -d` в каталоге musicme **только если** `nginx -t` проходит. Пока сертификата нет, монтировать `nginx/ytbob.conf` (с `listen 443 ssl`) нельзя: Nginx не стартует, и musicme.ru ляжет. Пока активен http-файл, `nginx -t` сертификат ytbob не требует.

Проверка:

```bash
curl -fsS -o /dev/null -w 'musicme %{http_code}\n' https://musicme.ru
curl -sI http://ytbob.ru/ | head -n 5
```

`musicme.ru` — прежний код ответа. `http://ytbob.ru/` — `301` на `https://ytbob.ru/...` (HTTPS заработает на шаге 6).

## 4. Сертификат Let's Encrypt

Тем же certbot, которым выпущен musicme.ru. Webroot — каталог volume `certbot_www` (на хосте это mountpoint volume, либо путь `-w` внутри контейнера certbot).

Хостовый certbot, если он уже обслуживает musicme:

```bash
WEBROOT="$(docker volume inspect muzzzic-prod_certbot_www --format '{{.Mountpoint}}')"
certbot certonly --webroot -w "$WEBROOT" -d ytbob.ru \
  --email "$(awk -F= '/^email/{print $2; exit}' /etc/letsencrypt/renewal/*.conf)" \
  --agree-tos --no-eff-email --keep-until-expiring
```

Имя volume сверить с `docker volume ls | grep certbot`. Если certbot сам в Docker и пишет в `/var/www/certbot`:

```bash
docker run --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v muzzzic-prod_certbot_www:/var/www/certbot \
  certbot/certbot certonly --webroot -w /var/www/certbot -d ytbob.ru \
  --agree-tos --no-eff-email --keep-until-expiring \
  -m admin@example.com
```

Почту взять из уже выпущенного сертификата musicme (`certbot certificates`), не выдумывать новую без нужды.

Успех:

```bash
ls /etc/letsencrypt/live/ytbob.ru/fullchain.pem /etc/letsencrypt/live/ytbob.ru/privkey.pem
```

Контейнер `FRONTEND` должен видеть те же файлы через уже существующий mount `/etc/letsencrypt`.

### Автообновление

`certbot certonly --webroot` записывает renew-конфиг. Уже включённый timer/cron certbot подхватит `ytbob.ru` вместе с musicme. HTTP-location `/.well-known/acme-challenge/` в vhost ytbob остаётся постоянно.

Nginx читает сертификат до reload. Хук:

```bash
cat >/etc/letsencrypt/renewal-hooks/deploy/reload-musicme-nginx.sh <<'EOF'
#!/bin/sh
docker exec FRONTEND_CONTAINER_NAME nginx -s reload
EOF
chmod 755 /etc/letsencrypt/renewal-hooks/deploy/reload-musicme-nginx.sh
```

Подставить реальное имя контейнера. Проверка без выпуска нового сертификата:

```bash
certbot renew --dry-run
```

## 5. Стек Standart Reserve

```bash
cd /opt/standart-reserve
cp .env.ytbob.example .env
chmod 600 .env
```

В `.env`:

- длинный `POSTGRES_PASSWORD`, тот же пароль внутри `DATABASE_URL`;
- `BACKEND_CORS_ORIGINS=["https://ytbob.ru"]` — без `*`;
- `MUZZZIC_NETWORK` — имя из шага 2.

```bash
docker network inspect "$MUZZZIC_NETWORK" >/dev/null
docker compose -f docker-compose.ytbob.yml up -d --build
docker compose -f docker-compose.ytbob.yml ps
docker ps --filter name=standart-reserve --format '{{.Names}} {{.Ports}}'
```

Колонка `PORTS` у `standart-reserve-frontend` и `standart-reserve-backend` пустая. `0.0.0.0:80` и `:443` по-прежнему только у frontend musicme.

Postgres в сеть musicme не входит. Backup пишет в volume `standart-reserve-prod_postgres_backups` раз в сутки.

## 6. Включить HTTPS-vhost

Заменить http-файл полным конфигом (тот же путь, который Nginx уже include-ит):

```bash
cp /opt/standart-reserve/nginx/ytbob.conf "$CONF_D/ytbob.conf"
docker exec "$FRONTEND" nginx -t && docker exec "$FRONTEND" nginx -s reload
```

`nginx/ytbob.http.conf` в этот момент не должен лежать рядом под другим именем в `conf.d`: два `server_name ytbob.ru` на порту 80 конфликтуют.

Если на шаге 3 в compose musicme был примонтирован именно `ytbob.http.conf`, сменить source на `nginx/ytbob.conf` и пересоздавать контейнер только после успешного `nginx -t` во временной проверке. Безопаснее держать bind на фиксированный путь `ytbob.conf` и подменять файл на хосте, затем `nginx -s reload`.

## 7. Приёмка

```bash
curl -fsS https://ytbob.ru/api/v1/health
curl -fsS https://ytbob.ru/health
curl -fsS https://ytbob.ru/api/v1/status
curl -fsS -o /dev/null -w 'ytbob %{http_code}\n' https://ytbob.ru/
curl -fsS -o /dev/null -w 'musicme %{http_code}\n' https://musicme.ru/
docker ps --filter name=standart-reserve --format '{{.Names}} {{.Ports}}'
```

Ожидание: health/status — `{"status":"ok"...}`, главная ytbob — `200`, musicme — как до деплоя, у контейнеров Standart Reserve нет `0.0.0.0:80` и `:443`.

CORS: в `.env` строка `BACKEND_CORS_ORIGINS=["https://ytbob.ru"]`. Браузерный запрос с `Origin: https://ytbob.ru` на `/api/` получает `access-control-allow-origin: https://ytbob.ru`. Фронт и API на одном хосте, для обычной навигации по сайту заголовок не обязателен; критерий закрывает эта настройка.
