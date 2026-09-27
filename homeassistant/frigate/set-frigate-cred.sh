#!/bin/sh
# Roda no Proxmox (root). Pede usuário e senha RTSP/ONVIF das câmeras e grava no
# config.yml do Frigate dentro da VM do HA (105), sem mostrar a senha.
set -eu
CFG=/mnt/data/supervisor/app_configs/ccab4aaf_frigate/config.yml
printf "Usuário ONVIF das câmeras [admin]: "; read -r U; U=${U:-admin}
printf "Senha ONVIF das câmeras: "; stty -echo; read -r P; stty echo; echo
[ -n "$P" ] || { echo "senha vazia, nada alterado"; exit 1; }
# escapa \ & | para o sed
esc() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }
printf '%s\n%s\n' "$(esc "$U")" "$(esc "$P")" | qm guest exec 105 --timeout 60 --pass-stdin 1 -- sh -c \
  "read -r U; read -r P; sed -i -e \"s|__RTSP_USER__|\$U|g\" -e \"s|__RTSP_PASS__|\$P|g\" $CFG; grep -c __RTSP_ $CFG || true" \
  | sed -n 's/.*"out-data" : "\([0-9]*\).*/marcadores restantes: \1/p'
echo "ok - agora reinicie o Frigate (o Claude faz isso)"
