#!/bin/sh
set -e

# Release tasks só para o papel "web" (o worker seta DJANGO_RELEASE=false).
if [ "${DJANGO_RELEASE:-true}" = "true" ]; then
  echo "==> Aplicando migrations..."
  python3 manage.py migrate --noinput
  echo "==> Coletando arquivos estáticos..."
  python3 manage.py collectstatic --noinput
fi

exec "$@"
