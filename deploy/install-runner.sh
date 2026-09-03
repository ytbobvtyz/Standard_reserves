#!/usr/bin/env bash
# One-shot setup of a GitHub Actions self-hosted runner for Standart Reserve.
# Standalone: copy this file to the server. Does not need a git clone.
set -euo pipefail

# sudo/cron often have a short PATH; binaries live in /usr/bin.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

APP_DIR=/opt/standart-reserve
RUNNER_DIR=/opt/actions-runner
RUNNER_USER=github-runner
RUNNER_LABELS=standart-reserve-prod
RUNNER_NAME="$(hostname)-prod"
REPO_URL=""
TOKEN=""
DOMAIN="localhost"
REPLACE=0
CHECK_ONLY=0
UNINSTALL=0
INSTALL_DOCKER=1
RUNNER_VERSION="${RUNNER_VERSION:-}"

usage() {
  cat <<'EOF'
Установка GitHub Actions Self-Hosted Runner для Standart Reserve.

Обязательные аргументы (кроме --check / --uninstall):
  --url URL          Репозиторий, например https://github.com/org/standart-reserve
  --token TOKEN      Registration token от разработчика (живёт ~1 час)

Опционально:
  --domain NAME      Публичный домен для Traefik Host() и CORS. По умолчанию: localhost
  --name NAME        Имя раннера. По умолчанию: <hostname>-prod
  --labels LIST      Метки через запятую. По умолчанию: standart-reserve-prod
  --replace          Перерегистрировать уже установленный раннер
  --no-docker        Не ставить Docker, если его нет
  --check            Только проверить сервер (docker, .env, сеть Traefik, служба раннера)
  --uninstall        Снять службу раннера (контейнеры и .env не трогает)
  -h, --help         Справка

Пример:
  sudo bash install-runner.sh \
    --url https://github.com/org/standart-reserve \
    --token AAAA \
    --domain app.company.ru
EOF
}

log() { printf '[standart-reserve] %s\n' "$*"; }
err() { printf '[standart-reserve] ОШИБКА: %s\n' "$*" >&2; exit 1; }

# True if a binary is on PATH or in a standard directory.
# Do not pass Debian package names here (e.g. ca-certificates has no such command).
have_cmd() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    return 0
  fi
  [ -x "/usr/bin/${name}" ] || [ -x "/bin/${name}" ] || [ -x "/usr/sbin/${name}" ] || [ -x "/sbin/${name}" ]
}

pkg_installed() {
  have_cmd dpkg && dpkg -s "$1" >/dev/null 2>&1
}

need_root() {
  if [ "$(id -u)" -ne 0 ]; then
    err "Запустите скрипт от root: sudo bash $0 ..."
  fi
}

env_value() {
  local key="$1"
  local file="${2:-$APP_DIR/.env}"
  [ -f "$file" ] || return 0
  grep -E "^${key}=" "$file" | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true
}

traefik_network_name() {
  local name
  name="$(env_value TRAEFIK_NETWORK)"
  echo "${name:-traefik}"
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --url) REPO_URL="${2:-}"; shift 2 ;;
      --token) TOKEN="${2:-}"; shift 2 ;;
      --domain) DOMAIN="${2:-}"; shift 2 ;;
      --name) RUNNER_NAME="${2:-}"; shift 2 ;;
      --labels) RUNNER_LABELS="${2:-}"; shift 2 ;;
      --replace) REPLACE=1; shift ;;
      --no-docker) INSTALL_DOCKER=0; shift ;;
      --check) CHECK_ONLY=1; shift ;;
      --uninstall) UNINSTALL=1; shift ;;
      -h|--help) usage; exit 0 ;;
      *) err "Неизвестный аргумент: $1 (см. --help)" ;;
    esac
  done
}

runner_arch() {
  case "$(uname -m)" in
    x86_64) echo x64 ;;
    aarch64|arm64) echo arm64 ;;
    *) err "Неподдерживаемая архитектура: $(uname -m). Нужны x86_64 или arm64." ;;
  esac
}

ensure_docker() {
  if have_cmd docker; then
    return 0
  fi
  if [ "$INSTALL_DOCKER" -ne 1 ]; then
    err "Docker не найден. Установите Docker Engine 24+ и Docker Compose v2 либо запустите без --no-docker."
  fi
  log "Устанавливаю Docker Engine..."
  if ! have_cmd curl; then
    if have_cmd apt-get; then
      apt-get update -y
      apt-get install -y --no-install-recommends curl ca-certificates
    else
      err "Нужен curl (или Ubuntu/Debian с apt)."
    fi
  fi
  curl -fsSL https://get.docker.com | sh
  have_cmd docker || err "Docker не установился. Поставьте его вручную и повторите."
}

enable_docker() {
  systemctl enable --now docker >/dev/null 2>&1 || true
  docker info >/dev/null 2>&1 || err "Служба Docker не отвечает. Проверьте: systemctl status docker"
  docker compose version >/dev/null 2>&1 || err "Нет Docker Compose v2. Ожидается команда: docker compose version"
}

ensure_packages() {
  local pkgs=()
  have_cmd curl || pkgs+=(curl)
  have_cmd tar || pkgs+=(tar)
  have_cmd gzip || pkgs+=(gzip)
  have_cmd git || pkgs+=(git)
  if ! pkg_installed ca-certificates && [ ! -d /etc/ssl/certs ]; then
    pkgs+=(ca-certificates)
  fi
  if [ "${#pkgs[@]}" -eq 0 ]; then
    return 0
  fi
  if ! have_cmd apt-get; then
    err "Нет apt-get, не могу поставить: ${pkgs[*]}. Установите их и повторите."
  fi
  log "Устанавливаю пакеты: ${pkgs[*]}"
  apt-get update -y
  apt-get install -y --no-install-recommends "${pkgs[@]}"
}

ensure_user() {
  if ! id "$RUNNER_USER" >/dev/null 2>&1; then
    log "Создаю пользователя ${RUNNER_USER}"
    useradd --system --create-home --home-dir /home/"$RUNNER_USER" --shell /bin/bash "$RUNNER_USER"
  fi
  getent group docker >/dev/null 2>&1 || groupadd docker
  usermod -aG docker "$RUNNER_USER"
}

write_env_if_missing() {
  mkdir -p "$APP_DIR"
  if [ -f "$APP_DIR/.env" ]; then
    log "Файл ${APP_DIR}/.env уже есть — не перезаписываю"
    return 0
  fi
  local password=""
  while [ "${#password}" -lt 24 ]; do
    password="${password}$(dd if=/dev/urandom bs=32 count=1 2>/dev/null | base64 | tr -dc 'A-Za-z0-9')"
  done
  password="${password:0:24}"
  [ "${#password}" -eq 24 ] || err "Не удалось сгенерировать пароль БД"

  local cors
  if [ "$DOMAIN" = "localhost" ]; then
    cors='["https://localhost","https://127.0.0.1"]'
  else
    cors="[\"https://${DOMAIN}\"]"
  fi

  cat > "$APP_DIR/.env" <<EOF
POSTGRES_DB=standart_reserve
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${password}
DATABASE_URL=postgresql://postgres:${password}@postgres:5432/standart_reserve
SECRET_KEY=
DEBUG=false
LOG_LEVEL=INFO
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
DOMAIN=${DOMAIN}
BACKEND_CORS_ORIGINS=${cors}
VITE_API_URL=/api/v1
BACKUP_INTERVAL_SECONDS=86400
BACKUP_KEEP_DAYS=14
TRAEFIK_NETWORK=traefik
EOF
  chmod 640 "$APP_DIR/.env"
  log "Создан ${APP_DIR}/.env (пароль БД сгенерирован)"
  if [ "$DOMAIN" = "localhost" ]; then
    log "Домен не задан. Для Traefik обязателен боевой DOMAIN в ${APP_DIR}/.env"
  fi
}

fix_permissions() {
  chown -R "$RUNNER_USER":"$RUNNER_USER" "$APP_DIR"
  chmod 750 "$APP_DIR"
  chmod 640 "$APP_DIR/.env"
}

latest_runner_version() {
  if [ -n "$RUNNER_VERSION" ]; then
    echo "$RUNNER_VERSION"
    return 0
  fi
  local version
  version="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest \
    | sed -n 's/.*"tag_name": "v\([^"]*\)".*/\1/p' \
    | head -1)"
  [ -n "$version" ] || err "Не удалось узнать версию actions/runner. Задайте RUNNER_VERSION=2.328.0"
  echo "$version"
}

install_runner_binaries() {
  local version arch tarball url
  version="$(latest_runner_version)"
  arch="$(runner_arch)"
  tarball="actions-runner-linux-${arch}-${version}.tar.gz"
  url="https://github.com/actions/runner/releases/download/v${version}/${tarball}"

  mkdir -p "$RUNNER_DIR"
  if [ -x "$RUNNER_DIR/config.sh" ] && [ "$REPLACE" -ne 1 ] && [ -f "$RUNNER_DIR/.runner" ]; then
    log "Раннер уже настроен в ${RUNNER_DIR}. Для перерегистрации добавьте --replace"
    return 0
  fi

  log "Скачиваю GitHub Actions runner v${version} (${arch})"
  local tmp
  tmp="$(mktemp -d)"
  curl -fsSL -o "${tmp}/${tarball}" "$url"
  if [ ! -x "$RUNNER_DIR/config.sh" ]; then
    tar -xzf "${tmp}/${tarball}" -C "$RUNNER_DIR"
  fi
  rm -rf "$tmp"
  if [ -x "$RUNNER_DIR/bin/installdependencies.sh" ]; then
    log "Ставлю системные зависимости раннера"
    (cd "$RUNNER_DIR" && ./bin/installdependencies.sh)
  fi
  chown -R "$RUNNER_USER":"$RUNNER_USER" "$RUNNER_DIR"
}

stop_runner_service() {
  if [ -x "$RUNNER_DIR/svc.sh" ]; then
    (cd "$RUNNER_DIR" && ./svc.sh stop >/dev/null 2>&1 || true)
    (cd "$RUNNER_DIR" && ./svc.sh uninstall >/dev/null 2>&1 || true)
  fi
}

configure_runner() {
  [ -n "$REPO_URL" ] || err "Нужен --url"
  [ -n "$TOKEN" ] || err "Нужен --token (Settings → Actions → Runners → New self-hosted runner)"

  if [ -f "$RUNNER_DIR/.runner" ] && [ "$REPLACE" -ne 1 ]; then
    log "Конфиг раннера уже есть. Пропускаю регистрацию (нужен --replace, чтобы перезаписать)"
    return 0
  fi

  stop_runner_service
  log "Регистрирую раннер ${RUNNER_NAME} с меткой ${RUNNER_LABELS}"
  sudo -u "$RUNNER_USER" bash -lc "
    cd '$RUNNER_DIR'
    ./config.sh --unattended --replace \
      --url '$REPO_URL' \
      --token '$TOKEN' \
      --name '$RUNNER_NAME' \
      --labels '$RUNNER_LABELS' \
      --work _work
  "
}

install_service() {
  local svc
  svc="$(service_name)"
  if [ -n "$svc" ] && [ -f "/etc/systemd/system/${svc}" ]; then
    log "Служба раннера уже есть (${svc}) — перезапускаю"
    (cd "$RUNNER_DIR" && ./svc.sh start)
    return 0
  fi
  log "Включаю systemd-службу раннера"
  (cd "$RUNNER_DIR" && ./svc.sh install "$RUNNER_USER")
  svc="$(service_name)"
  if [ -n "$svc" ]; then
    mkdir -p "/etc/systemd/system/${svc}.d"
    printf '[Service]\nSupplementaryGroups=docker\n' > "/etc/systemd/system/${svc}.d/docker.conf"
    systemctl daemon-reload
  fi
  (cd "$RUNNER_DIR" && ./svc.sh start)
}

service_name() {
  local f
  for f in /etc/systemd/system/actions.runner.*.service; do
    [ -e "$f" ] || return 0
    basename "$f"
    return 0
  done
}

print_check() {
  local ok=0
  echo
  log "Проверка сервера"
  if docker info >/dev/null 2>&1; then
    log "  Docker: OK ($(docker --version | tr -d '\n'))"
  else
    log "  Docker: НЕТ"; ok=1
  fi
  if docker compose version >/dev/null 2>&1; then
    log "  Compose: OK"
  else
    log "  Compose: НЕТ"; ok=1
  fi
  if [ -f "$APP_DIR/.env" ]; then
    if grep -Eq '^POSTGRES_PASSWORD=(change-me-strong-password)?$' "$APP_DIR/.env"; then
      log "  .env: есть, но пароль БД не задан"; ok=1
    else
      log "  .env: OK (${APP_DIR}/.env)"
    fi
    local domain
    domain="$(env_value DOMAIN)"
    if [ -z "$domain" ] || [ "$domain" = "localhost" ]; then
      log "  DOMAIN: не задан (Traefik не пропишет Host)"; ok=1
    else
      log "  DOMAIN: ${domain}"
    fi
  else
    log "  .env: НЕТ (${APP_DIR}/.env)"; ok=1
  fi
  local traefik_net
  traefik_net="$(traefik_network_name)"
  if docker network inspect "$traefik_net" >/dev/null 2>&1; then
    log "  Сеть Traefik (${traefik_net}): OK"
  else
    log "  Сеть Traefik (${traefik_net}): НЕТ — compose не поднимется"; ok=1
  fi
  if id "$RUNNER_USER" >/dev/null 2>&1 && id -nG "$RUNNER_USER" | grep -qw docker; then
    log "  Пользователь ${RUNNER_USER} в группе docker: OK"
  else
    log "  Пользователь ${RUNNER_USER} в группе docker: НЕТ"; ok=1
  fi
  if have_cmd git; then
    log "  git: OK"
  else
    log "  git: НЕТ (нужен для checkout)"; ok=1
  fi
  local svc
  svc="$(service_name)"
  if [ -n "$svc" ] && systemctl is-active --quiet "$svc"; then
    log "  Служба раннера: active (${svc})"
  else
    log "  Служба раннера: не запущена"; ok=1
  fi
  echo
  return "$ok"
}

uninstall_runner() {
  need_root
  log "Снимаю раннер (контейнеры и ${APP_DIR} не удаляю)"
  stop_runner_service
  if [ -x "$RUNNER_DIR/config.sh" ] && [ -f "$RUNNER_DIR/.runner" ]; then
    log "Чтобы удалить раннер из GitHub, разработчик: Settings → Actions → Runners → Remove"
  fi
  log "Готово"
}

print_next_steps() {
  cat <<EOF

Готово. Раннер установлен.

Что осталось DevOps (если ещё не сделано):
  1. Traefik уже должен работать. Сеть по умолчанию: traefik
       docker network inspect traefik
     Если имя сети другое — пропишите TRAEFIK_NETWORK в ${APP_DIR}/.env
  2. В ${APP_DIR}/.env задайте боевой DOMAIN и CORS:
       sudo nano ${APP_DIR}/.env
     Поля: DOMAIN, BACKEND_CORS_ORIGINS
     Существующий пароль БД не меняйте, если том postgres уже есть.
  3. Порты 80/443 открывает Traefik, не этот стек. Лишние порты для приложения не нужны.
  4. Сообщите разработчику: раннер в GitHub должен быть Idle
     (Settings → Actions → Runners).

Проверка:
  sudo bash $0 --check

Первый деплой делает разработчик: push в main или Actions → Deploy production → Run workflow.
Nginx из старого compose будет снят как orphan — это ожидаемо. Том postgres_data не удаляется.
EOF
}

main() {
  parse_args "$@"
  if [ "$CHECK_ONLY" -eq 1 ]; then
    print_check
    exit $?
  fi
  need_root
  if [ "$UNINSTALL" -eq 1 ]; then
    uninstall_runner
    exit 0
  fi
  [ -n "$REPO_URL" ] || err "Нужен --url (см. --help)"
  [ -n "$TOKEN" ] || err "Нужен --token (см. --help)"

  ensure_packages
  ensure_docker
  enable_docker
  ensure_user
  write_env_if_missing
  fix_permissions
  install_runner_binaries
  configure_runner
  install_service
  print_check || true
  print_next_steps
}

main "$@"
