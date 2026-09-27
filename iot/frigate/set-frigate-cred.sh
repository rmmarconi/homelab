#!/bin/sh
# Roda na VM iot. Pede usuário e senha ONVIF/RTSP das câmeras e troca os
# marcadores __RTSP_USER__/__RTSP_PASS__ em config/config.yml (sem mostrar a senha).
# Uso: sudo ./frigate/set-frigate-cred.sh   (a partir de /opt/iot)
set -eu
CFG="$(dirname "$0")/config/config.yml"
printf "Usuário ONVIF das câmeras [admin]: "; read -r U; U=${U:-admin}
printf "Senha ONVIF das câmeras (não aparece): "; stty -echo; read -r P; stty echo; echo
[ -n "$P" ] || { echo "senha vazia, nada alterado"; exit 1; }
esc() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }
sed -i -e "s|__RTSP_USER__|$(esc "$U")|g" -e "s|__RTSP_PASS__|$(esc "$P")|g" "$CFG"
chmod 600 "$CFG"
echo "marcadores restantes: $(grep -c __RTSP_ "$CFG" || true)"
docker compose -f "$(dirname "$0")/../docker-compose.yml" restart frigate
