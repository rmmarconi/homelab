#!/usr/bin/env bash
# Instala ou atualiza o Diretório no mediacenter (Linux + Docker), atrás do nginx nativo.
# Variante do infra/homelab/server-install.sh do projeto: o mediacenter não tem Caddy;
# web e MinIO publicam só em 127.0.0.1 e o nginx faz TLS (Let's Encrypt, webroot).
#
#   sudo bash server-install-nginx.sh <pasta-com-o-código>
#
# Idempotente: rodar de novo atualiza o código, aplica migrations e recria web/worker sem
# trocar segredos nem apagar dados. Variáveis opcionais:
#   DOMAIN=diretorio.rafaelmarconi.com.br   SKIP_TILES=1   TILES_MAXZOOM=14   WEB_PORT=3010   MINIO_PORT=9010
set -euo pipefail

DOMAIN="${DOMAIN:-diretorio.rafaelmarconi.com.br}"
BASE=/opt/diretorio
SRC_IN="${1:?uso: sudo bash server-install.sh <pasta-com-o-código>}"
TILES_MAXZOOM="${TILES_MAXZOOM:-14}"
SITE_NAME="${SITE_NAME:-Diretório}"

c_ok=$'\e[32m'; c_warn=$'\e[33m'; c_err=$'\e[31m'; c_off=$'\e[0m'
step() { printf '\n\e[1m==> %s\e[0m\n' "$*"; }
ok() { printf '%s✔%s %s\n' "$c_ok" "$c_off" "$*"; }
warn() { printf '%s!%s %s\n' "$c_warn" "$c_off" "$*"; }
die() { printf '%s✘ %s%s\n' "$c_err" "$*" "$c_off" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "rode com sudo"
exec > >(tee -a /var/log/diretorio-install.log) 2>&1
echo "---- $(date -Is) instalação do Diretório ----"
SRC_IN="$(cd "$SRC_IN" && pwd)"
[[ -f "$SRC_IN/Dockerfile" && -f "$SRC_IN/infra/homelab/compose.yml" ]] || die "pasta de código inválida: $SRC_IN"

# ----------------------------------------------------------------------------- 1. pré-requisitos
step "Verificando o servidor"
command -v docker >/dev/null || die "Docker não encontrado"
docker compose version >/dev/null 2>&1 || die "plugin 'docker compose' (v2) não encontrado"
docker buildx version >/dev/null 2>&1 || die "docker buildx não encontrado (pacote docker-buildx-plugin)"
command -v openssl >/dev/null || die "openssl não encontrado"
command -v curl >/dev/null || die "curl não encontrado"
arch="$(uname -m)"
case "$arch" in x86_64 | amd64) pm_arch=x86_64 ;; aarch64 | arm64) pm_arch=arm64 ;; *) die "arquitetura não suportada: $arch" ;; esac
mem_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
(( mem_mb >= 3000 )) || warn "só ${mem_mb} MB de RAM: o build do Next.js precisa de ~3 GB (pode ficar lento ou falhar)"
docker_root="$(docker info -f '{{.DockerRootDir}}')"
free_gb=$(df -BG --output=avail "$docker_root" | tail -1 | tr -dc 0-9)
(( free_gb >= 12 )) || die "pouco espaço em $docker_root (${free_gb} GB livres; precisa de ~12 GB com o mapa)"
ok "Docker, compose, buildx; ${mem_mb} MB RAM; ${free_gb} GB livres em $docker_root; $arch"

# ----------------------------------------------------------------------------- 2. nginx
step "Conferindo o nginx"
command -v nginx >/dev/null || die "nginx não encontrado"
command -v certbot >/dev/null || die "certbot não encontrado"
WEB_PORT="${WEB_PORT:-3010}"
MINIO_PORT="${MINIO_PORT:-9010}"
MINIO_IMAGE="${MINIO_IMAGE:-cgr.dev/chainguard/minio@sha256:a1d2b3516a41296510f7fb49184c18b88287fa8f35cf3ce5c047289053b94964}"
MC_IMAGE="${MC_IMAGE:-cgr.dev/chainguard/minio-client@sha256:778b2dac231584d5d5749ab663f9f61979d60dd5c00abf682af888db6a9f46e4}"
# Rede "proxy" do compose do projeto; aqui ninguém mais entra nela (o nginx usa as portas locais)
CADDY_NETWORK=diretorio-proxy
docker network inspect "$CADDY_NETWORK" >/dev/null 2>&1 || docker network create "$CADDY_NETWORK" >/dev/null
ok "nginx e certbot · web → 127.0.0.1:$WEB_PORT · minio → 127.0.0.1:$MINIO_PORT"

# ----------------------------------------------------------------------------- 3. arquivos
step "Copiando código e configuração para $BASE"
install -d -m 750 "$BASE" "$BASE/backups"
rm -rf "$BASE/src.new"
cp -a "$SRC_IN" "$BASE/src.new"
rm -rf "$BASE/src" && mv "$BASE/src.new" "$BASE/src"
install -m 644 "$BASE/src/infra/homelab/compose.yml" "$BASE/compose.yml"
install -m 755 "$BASE/src/infra/homelab/backup.sh" "$BASE/backup.sh"
install -m 755 "$BASE/src/infra/homelab/admin.sh" "$BASE/admin.sh"
cat > "$BASE/compose.nginx.yml" <<EOF
# Gerado pelo server-install-nginx.sh: portas só em 127.0.0.1 para o nginx do host.
# A MinIO parou de publicar as imagens comunitárias (minio/minio e minio/mc sumiram do Docker
# Hub e do quay.io); a da Chainguard é compilada do código-fonte e traz minio, mc e sh.
services:
  web:
    ports: ["127.0.0.1:${WEB_PORT}:3000"]
  minio:
    image: $MINIO_IMAGE
    ports: ["127.0.0.1:${MINIO_PORT}:9000"]
    environment:
      MC_CONFIG_DIR: /tmp/.mc   # o healthcheck usa "mc ready local"
  minio-init:
    image: $MINIO_IMAGE
    environment:
      MC_CONFIG_DIR: /tmp/.mc
EOF
ok "código em $BASE/src"

rand_hex() { openssl rand -hex "$1"; }
if [[ ! -f "$BASE/.env" ]]; then
  umask 077
  cat > "$BASE/.env" <<EOF
# Gerado em $(date -Is). Segredos: guarde uma cópia no seu cofre.
POSTGRES_PASSWORD=$(rand_hex 24)
MINIO_ROOT_USER=diretorio-root
MINIO_ROOT_PASSWORD=$(rand_hex 24)
S3_APP_KEY=diretorio-app
S3_APP_SECRET=$(rand_hex 24)
MIGRATOR_PASSWORD=$(rand_hex 24)
APP_DB_PASSWORD=$(rand_hex 24)
BACKUP_DB_PASSWORD=$(rand_hex 24)
CADDY_NETWORK=$CADDY_NETWORK
APP_TAG=local
# Caixa do Mailpit só no IP da LAN (o roteador só encaminha 80/443)
MAILPIT_UI_PORT=$(hostname -I | awk '{print $1}'):8025
# admin.sh/backup.sh do projeto chamam "docker compose" nesta pasta: inclui o override
COMPOSE_FILE=compose.yml:compose.nginx.yml
EOF
  umask 022
  ok "segredos de infraestrutura gerados (.env)"
else
  sed -i "s/^CADDY_NETWORK=.*/CADDY_NETWORK=$CADDY_NETWORK/" "$BASE/.env"
  ok ".env existente mantido"
fi
set -a; . "$BASE/.env"; set +a

URL="https://$DOMAIN"
MEDIA="$URL/media/diretorio-public"
PMTILES_URL="$MEDIA/public/tiles/brasil.pmtiles"
if [[ ! -f "$BASE/app.env" ]]; then
  umask 077
  cat > "$BASE/app.env" <<EOF
# Configuração da aplicação (ver .env.example no código). Gerado em $(date -Is).
# staging = piloto: sem Turnstile, e-mails na caixa local (Mailpit), fora dos buscadores.
APP_ENV=staging
APP_URL=$URL
NEXT_PUBLIC_SITE_NAME=$SITE_NAME
LOG_LEVEL=info
DATABASE_URL=postgres://diretorio_app:${APP_DB_PASSWORD}@db:5432/diretorio
MIGRATION_DATABASE_URL=postgres://diretorio_migrator:${MIGRATOR_PASSWORD}@db:5432/diretorio
DATABASE_POOL_MAX=10
ENCRYPTION_KEY=$(openssl rand -base64 32)
LOCATION_NOISE_SECRET=$(rand_hex 32)
HASH_SECRET=$(rand_hex 32)
TRUSTED_IP_HEADER=x-forwarded-for
JOBS_MODE=queue
EMAIL_PROVIDER=smtp
EMAIL_FROM=$SITE_NAME <nao-responda@$DOMAIN>
SMTP_URL=smtp://mailpit:1025
STORAGE_DRIVER=s3
S3_ENDPOINT=http://minio:9000
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=$S3_APP_KEY
S3_SECRET_ACCESS_KEY=$S3_APP_SECRET
S3_BUCKET_PUBLIC=diretorio-public
S3_BUCKET_PRIVATE=diretorio-private
S3_FORCE_PATH_STYLE=true
PUBLIC_ASSETS_URL=$MEDIA
NEXT_PUBLIC_PMTILES_URL=$PMTILES_URL
NOMINATIM_URL=https://nominatim.openstreetmap.org
GEOCODER_USER_AGENT=diretorio/1.0 (+$URL)
OPS_TOKEN=$(openssl rand -base64 32 | tr -d '/+=')
EOF
  umask 022
  ok "configuração da aplicação gerada (app.env)"
else
  ok "app.env existente mantido"
fi

cd "$BASE"
dc() { docker compose --project-directory "$BASE" -f "$BASE/compose.yml" -f "$BASE/compose.nginx.yml" "$@"; }

# ----------------------------------------------------------------------------- 4. imagem
step "Construindo a imagem (5–15 min na primeira vez)"
APP_VERSION="$(date -u +%Y%m%d%H%M)"
DOCKER_BUILDKIT=1 docker build \
  --build-arg APP_VERSION="$APP_VERSION" \
  --build-arg NEXT_PUBLIC_SITE_NAME="$SITE_NAME" \
  --build-arg NEXT_PUBLIC_PMTILES_URL="$(grep '^NEXT_PUBLIC_PMTILES_URL=' app.env | cut -d= -f2-)" \
  -t diretorio:local -t "diretorio:$APP_VERSION" "$BASE/src"
ok "imagem diretorio:$APP_VERSION"

# ----------------------------------------------------------------------------- 5. banco e storage
step "Subindo Postgres/PostGIS, MinIO e Mailpit"
dc up -d db minio mailpit
for _ in $(seq 1 60); do
  [[ "$(docker inspect -f '{{.State.Health.Status}}' diretorio-db 2>/dev/null)" == healthy ]] && break
  sleep 2
done
[[ "$(docker inspect -f '{{.State.Health.Status}}' diretorio-db)" == healthy ]] || die "Postgres não ficou saudável"
dc --profile ops run --rm minio-init
ok "banco e storage no ar"

if [[ "$(dc exec -T db psql -U postgres -d diretorio -tAc "select count(*) from pg_roles where rolname='diretorio_app'")" != "1" ]]; then
  dc exec -T db psql -q -U postgres -d diretorio -v ON_ERROR_STOP=1 -v db=diretorio \
    -v migrator_password="$MIGRATOR_PASSWORD" -v app_password="$APP_DB_PASSWORD" \
    -v backup_password="$BACKUP_DB_PASSWORD" < "$BASE/src/infra/postgres/roles.sql"
  ok "papéis de banco com menor privilégio criados"
else
  ok "papéis de banco já existem"
fi

step "Aplicando migrations e dados de referência (UFs, municípios, categorias)"
dc --profile ops run --rm migrate
ok "banco atualizado"

# ----------------------------------------------------------------------------- 6. aplicação
step "Subindo a aplicação"
dc up -d --force-recreate web worker
for _ in $(seq 1 60); do
  [[ "$(docker inspect -f '{{.State.Health.Status}}' diretorio-web 2>/dev/null)" == healthy ]] && break
  sleep 3
done
if [[ "$(docker inspect -f '{{.State.Health.Status}}' diretorio-web)" != healthy ]]; then
  docker logs --tail 60 diretorio-web >&2
  die "a aplicação não ficou saudável (logs acima)"
fi
ok "diretorio-web saudável"

# ----------------------------------------------------------------------------- 7. nginx
step "Publicando $DOMAIN no nginx"
if [[ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
  # DNS-01 pela Cloudflare, como o media.: o domínio tem dois A (dois links WAN) e só um
  # encaminha a porta 80, então o HTTP-01 falha quando o Let's Encrypt escolhe o outro.
  cf_ini=/etc/letsencrypt/dns-credentials.ini
  if [[ -f "$cf_ini" ]]; then
    auth=(--dns-cloudflare --dns-cloudflare-credentials "$cf_ini" --dns-cloudflare-propagation-seconds 30)
  else
    auth=(--webroot -w /var/www/html)   # default_server da porta 80 serve /.well-known
  fi
  certbot certonly "${auth[@]}" -d "$DOMAIN" --non-interactive --agree-tos \
    --register-unsafely-without-email --deploy-hook 'systemctl reload nginx' \
    || die "certificado não emitido para $DOMAIN (veja /var/log/letsencrypt/letsencrypt.log)"
fi
vhost="/etc/nginx/sites-available/$DOMAIN"
[[ -f "$vhost" ]] && cp -p "$vhost" "/root/nginx-$DOMAIN.bak-$(date +%Y%m%d%H%M%S)"
cat > "$vhost" <<EOF
# Diretório — gerado por server-install-nginx.sh (rode o instalador de novo em vez de editar).
# A porta 80 cai no default_server do mediacenter.conf (ACME + redirect para HTTPS).
map \$http_upgrade \$diretorio_connection { default upgrade; '' close; }

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    client_max_body_size 9m;
    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;

    # Imagens e mapa (MinIO, bucket público): só leitura; Range passa direto (PMTiles)
    location /media/diretorio-public/public/ {
        limit_except GET { deny all; }
        proxy_pass http://127.0.0.1:$MINIO_PORT/diretorio-public/public/;
        proxy_set_header Host 127.0.0.1:$MINIO_PORT;
        proxy_hide_header Set-Cookie;
        proxy_hide_header x-amz-request-id;
        proxy_hide_header x-amz-id-2;
        proxy_buffering off;
        add_header Cache-Control "public, max-age=86400" always;
        add_header X-Content-Type-Options nosniff always;
    }
    location /media/ { return 404; }

    # Métricas só pela rede interna (Bearer OPS_TOKEN direto em 127.0.0.1:$WEB_PORT)
    location = /api/metrics { return 404; }

    location / {
        proxy_pass http://127.0.0.1:$WEB_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        # Sobrescreve (não acrescenta): o app confia no primeiro valor deste cabeçalho
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$diretorio_connection;
        proxy_read_timeout 60s;
    }
}
EOF
ln -sf "$vhost" "/etc/nginx/sites-enabled/$DOMAIN"
if ! nginx -t 2>/tmp/nginx-t.log; then
  rm -f "/etc/nginx/sites-enabled/$DOMAIN"
  cat /tmp/nginx-t.log >&2
  die "configuração do nginx inválida — site desativado"
fi
systemctl reload nginx
ok "nginx recarregado"

# ----------------------------------------------------------------------------- 8. backups
step "Agendando backup diário"
cat > /etc/cron.d/diretorio-backup <<EOF
# Backup diário do Diretório (banco + imagens), 14 dias em $BASE/backups; o mediacenter-backup (03:30) leva para o UNAS
10 3 * * * root $BASE/backup.sh >> /var/log/diretorio-backup.log 2>&1
EOF
chmod 644 /etc/cron.d/diretorio-backup
ok "cron 03:10 → $BASE/backups (o mediacenter-backup das 03:30 copia para o UNAS)"

# ----------------------------------------------------------------------------- 9. mapa
tiles_present() {
  curl -s -o /dev/null -w '%{http_code}' -r 0-15 \
    "$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' diretorio-minio | awk '{print $1}'):9000/diretorio-public/public/tiles/brasil.pmtiles" \
    | grep -q '^20[06]$'
}
if [[ "${SKIP_TILES:-0}" == "1" ]]; then
  warn "mapa: pulado (SKIP_TILES=1)"
elif tiles_present; then
  ok "mapa do Brasil já publicado"
else
  step "Baixando o mapa do Brasil (Protomaps/OpenStreetMap, zoom até $TILES_MAXZOOM) — pode levar 10–40 min"
  work="$BASE/tiles-work"; install -d "$work"
  tag="$(curl -fsSIL -o /dev/null -w '%{url_effective}' https://github.com/protomaps/go-pmtiles/releases/latest | sed 's#.*/tag/##')"
  [[ "$tag" == v* ]] || die "não consegui descobrir a versão do go-pmtiles"
  curl -fsSL "https://github.com/protomaps/go-pmtiles/releases/download/$tag/go-pmtiles_${tag#v}_Linux_${pm_arch}.tar.gz" \
    | tar -xz -C "$work" pmtiles
  build=""
  for d in $(seq 0 14); do
    day="$(date -u -d "-$d day" +%Y%m%d)"
    if curl -fsI "https://build.protomaps.com/$day.pmtiles" >/dev/null 2>&1; then build="$day"; break; fi
  done
  [[ -n "$build" ]] || die "nenhum build recente do Protomaps encontrado"
  "$work/pmtiles" extract "https://build.protomaps.com/$build.pmtiles" "$work/brasil.pmtiles" \
    --bbox=-74.1,-33.8,-28.6,5.4 --maxzoom="$TILES_MAXZOOM"
  docker run --rm --network diretorio_internal -v "$work:/t:ro" \
    -e MC_HOST_local="http://$MINIO_ROOT_USER:$MINIO_ROOT_PASSWORD@minio:9000" -e MC_CONFIG_DIR=/tmp/.mc \
    "$MC_IMAGE" cp /t/brasil.pmtiles local/diretorio-public/public/tiles/brasil.pmtiles
  rm -rf "$work"
  ok "mapa publicado (build $build)"
fi

# ----------------------------------------------------------------------------- 10. verificação
step "Verificando"
public_ip="$(curl -fsS -m 5 https://api.ipify.org 2>/dev/null || true)"
dns_ip="$(getent ahostsv4 "$DOMAIN" 2>/dev/null | awk 'NR==1{print $1}')"
if [[ -z "$dns_ip" ]]; then
  warn "DNS: $DOMAIN ainda não resolve. Crie um registro A apontando para ${public_ip:-seu IP público}."
elif [[ -n "$public_ip" && "$dns_ip" != "$public_ip" ]]; then
  warn "DNS: $DOMAIN → $dns_ip, mas a saída desta rede é $public_ip (ok se for o outro link WAN)."
else
  ok "DNS: $DOMAIN → $dns_ip"
fi
code="$(curl -sk -o /dev/null -w '%{http_code}' --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/api/ready" || true)"
[[ "$code" == 200 ]] && ok "https://$DOMAIN/api/ready responde 200 pelo nginx" || warn "pelo nginx respondeu $code"

lan_ip="$(hostname -I | awk '{print $1}')"
cat <<EOF

${c_ok}Pronto.${c_off}  https://$DOMAIN

Primeira pessoa administradora:
  1. Cadastre-se em https://$DOMAIN/cadastrar
  2. Abra a caixa de e-mails local http://$lan_ip:8025 e clique no link de confirmação
  3. sudo $BASE/admin.sh seu@email.com
  4. Entre de novo: o painel exige configurar a verificação em duas etapas (app autenticador)

Arquivos: $BASE/.env e $BASE/app.env (segredos — guarde cópia no cofre) · backups em $BASE/backups
Atualizar: rode o instalador de novo com o código novo.
EOF
