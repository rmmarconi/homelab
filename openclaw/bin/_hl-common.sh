# Funções comuns dos comandos hl-* (somente leitura, comandos fixos).
KEY="$HOME/.ssh/openclaw_homelab"
SSH_OPTS="-i $KEY -o BatchMode=yes -o ConnectTimeout=8 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
PVE="root@10.1.1.254"; MON="rmmarconi@10.1.1.15"; MEDIA="rmmarconi@10.1.1.100"
BLOG="-p 65002 u819599816@82.25.72.87"; BLOG_DIR='~/domains/rafaelmarconi.com.br/public_html'
PROM="http://10.1.1.15:9090"; LOKI="http://10.1.1.15:3100"; HA="http://10.1.1.11"
HA_TOKEN_FILE="$HOME/.config/homelab/ha_token"
rsh() { local host="$1"; shift; ssh $SSH_OPTS $host "$@"; }
sec() { printf '\n## %s\n' "$*"; }
ha_get() {
  [ -r "$HA_TOKEN_FILE" ] || { echo "sem token do Home Assistant em $HA_TOKEN_FILE"; return 1; }
  printf 'header = "Authorization: Bearer %s"\n' "$(tr -d '\n\r ' < "$HA_TOKEN_FILE")" \
    | curl -s -m 20 -K - "$HA$1"
}
