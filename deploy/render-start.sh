#!/bin/sh
# Partida no Render: aplica as migrações, sobe o núcleo leve ao fundo e entrega a porta pública à API.
set -e

alembic upgrade head

nucleo-servidor &

# O Render define PORT (padrão 10000); localmente cai para 8000.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
