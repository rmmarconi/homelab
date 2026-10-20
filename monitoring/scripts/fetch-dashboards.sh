#!/usr/bin/env bash
# Baixa os dashboards da comunidade (grafana.com) e ajusta o datasource para "prometheus".
# Os dashboards próprios (logs, NetFlow, WAN) já estão versionados em grafana/dashboards/unifi.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v jq >/dev/null || { echo "instale o jq"; exit 1; }

declare -A DASH=(
  [11310]=unifi [11311]=unifi [11312]=unifi [11313]=unifi [11314]=unifi [11315]=unifi [23027]=unifi
  [1860]=sistema [10347]=proxmox
)

for id in "${!DASH[@]}"; do
  dir="grafana/dashboards/${DASH[$id]}"
  mkdir -p "$dir"
  tmp=$(mktemp)
  curl -sfL "https://grafana.com/api/dashboards/$id/revisions/latest/download" -o "$tmp"
  name=$(jq -r .title "$tmp" | tr ' /:' '___')
  jq 'del(.__inputs,.__requires,.id)' "$tmp" \
    | sed -E 's/\$\{DS_[A-Z_0-9]+\}/prometheus/g' > "$dir/$id-$name.json"
  rm -f "$tmp"
  echo "ok  $id  $name"
done
