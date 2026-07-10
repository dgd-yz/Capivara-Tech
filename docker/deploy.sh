#!/usr/bin/env bash
#
# Deploy do Capivara Tech na VPS (chamado pelo GitHub Actions via SSH).
# Padrão igual ao Baby Tracker: git checkout do commit exato -> backup do
# Postgres -> docker compose up --build -> espera healthcheck -> limpa imagens.
#
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/capivara-tech}"
COMPOSE="docker compose -f docker-compose.prod.yml"

cd "$APP_DIR"

# carrega POSTGRES_* do .env para o pg_dump
set -a
# shellcheck disable=SC1091
[ -f "$APP_DIR/.env" ] && . "$APP_DIR/.env"
set +a

diagnose_failure() {
  echo "::::::::::::: DEPLOY FALHOU :::::::::::::"
  $COMPOSE ps || true
  echo "----- logs web -----"
  $COMPOSE logs --tail=100 web || true
  echo "----- health web -----"
  docker inspect --format '{{json .State.Health}}' "$($COMPOSE ps -q web)" 2>/dev/null || true
}
trap diagnose_failure ERR

echo "==> Buscando código (${DEPLOY_SHA:-origin/main})..."
git fetch --all --prune
git checkout -f "${DEPLOY_SHA:-origin/main}"

echo "==> Backup do Postgres (mantém 14 dias)..."
mkdir -p backups
if $COMPOSE ps db 2>/dev/null | grep -q db; then
  TS="$(date +%Y%m%d-%H%M%S)"
  if $COMPOSE exec -T db pg_dump -U "${POSTGRES_USER:-capivara}" "${POSTGRES_DB:-capivara}" | gzip > "backups/db-${TS}.sql.gz"; then
    echo "backup salvo em backups/db-${TS}.sql.gz"
  else
    echo "aviso: backup não realizado (primeiro deploy?)"
    rm -f "backups/db-${TS}.sql.gz"
  fi
  find backups -name 'db-*.sql.gz' -mtime +14 -delete || true
fi

echo "==> Subindo containers (build)..."
$COMPOSE up -d --build --remove-orphans

echo "==> Aguardando healthcheck do web..."
status="starting"
for _ in $(seq 1 36); do
  status="$(docker inspect --format '{{.State.Health.Status}}' "$($COMPOSE ps -q web)" 2>/dev/null || echo starting)"
  [ "$status" = "healthy" ] && break
  sleep 5
done
if [ "$status" != "healthy" ]; then
  echo "web não ficou healthy (status: $status)"
  exit 1
fi

echo "==> Limpando imagens antigas..."
docker image prune -f || true

echo "==> Deploy concluído com sucesso."
