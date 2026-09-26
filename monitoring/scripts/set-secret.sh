#!/usr/bin/env bash
# Grava um valor no .env sem mostrar na tela nem deixar no histórico do shell.
# Uso: ./scripts/set-secret.sh UP_UNIFI_DEFAULT_PASS
set -euo pipefail
cd "$(dirname "$0")/.."
var="${1:?informe o nome da variável, ex.: PIHOLE_PASSWORD}"
[ -f .env ] || { cp .env.example .env; chmod 600 .env; }
read -rsp "Valor para $var: " val; echo
[ -n "$val" ] || { echo "vazio, nada alterado"; exit 1; }
tmp=$(mktemp)
grep -v "^${var}=" .env > "$tmp" || true
printf '%s=%s\n' "$var" "$val" >> "$tmp"
cat "$tmp" > .env && rm -f "$tmp" && chmod 600 .env
echo "$var gravada. Recrie o serviço: docker compose up -d --force-recreate <serviço>"
