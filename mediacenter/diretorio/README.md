# Diretório no mediacenter (2026-10-27)

Piloto do projeto Diretório em `https://diretorio.rafaelmarconi.com.br`. O código vem de
`~/rmediacenter/diretorio-deploy/diretorio-src.tar.gz` (Mac); o instalador do projeto
(`infra/homelab/server-install.sh`) espera o Caddy em contêiner do rmediacenter, mas este
mediacenter usa nginx nativo — por isso a variante `server-install-nginx.sh` daqui.

```
Internet → roteador (80/443 → 10.1.1.100) → nginx (TLS Let's Encrypt, webroot)
             ├─ /                                → 127.0.0.1:3010 (diretorio-web)
             └─ /media/diretorio-public/public/* → 127.0.0.1:9010 (MinIO, só GET: imagens e mapa)
Docker (Debian: docker.io, docker-compose, docker-buildx), compose "diretorio" em /opt/diretorio:
  web · worker · Postgres 16 + PostGIS · MinIO · Mailpit (http://10.1.1.100:8025, só LAN)
```

Diferenças em relação ao instalador original:

- web e MinIO publicam só em `127.0.0.1` (`compose.nginx.yml`); a rede "proxy" do compose é a
  `diretorio-proxy`, sem ninguém mais nela.
- MinIO: as imagens `minio/minio` e `minio/mc` não existem mais no Docker Hub/quay.io (a MinIO
  parou de publicar a edição comunitária). O override usa `cgr.dev/chainguard/minio` e
  `minio-client` (compiladas do código-fonte), fixadas por digest no `server-install-nginx.sh`.
- O nginx **sobrescreve** `X-Forwarded-For` com `$remote_addr` (o app confia no primeiro valor,
  `TRUSTED_IP_HEADER=x-forwarded-for`), então não dá para forjar o IP nos limites de taxa.
- `/api/metrics` responde 404 por fora; o Prometheus pode usar `127.0.0.1:3010` com `OPS_TOKEN`.
- Backup do app às 03:10 em `/opt/diretorio/backups` (14 dias); o `mediacenter-backup` das 03:30
  leva o dump mais recente, o `storage-*.tgz` e os arquivos de segredos (`.env`, `app.env`) para o UNAS.
- AdGuard: regravação `diretorio.rafaelmarconi.com.br → 10.1.1.100` para a rede interna.

## Instalar ou atualizar

```bash
ssh rmmarconi@10.1.1.100 'rm -rf ~/diretorio-install && mkdir -p ~/diretorio-install'
scp diretorio-src.tar.gz server-install-nginx.sh rmmarconi@10.1.1.100:diretorio-install/
ssh rmmarconi@10.1.1.100 'cd ~/diretorio-install && tar xzf diretorio-src.tar.gz && sudo bash server-install-nginx.sh ~/diretorio-install/diretorio'
```

Idempotente: mantém segredos e dados. Log em `/var/log/diretorio-install.log`.

## Operação

```bash
cd /opt/diretorio && sudo docker compose ps          # COMPOSE_FILE no .env já inclui o override
sudo docker compose logs -f web worker
sudo /opt/diretorio/admin.sh pessoa@email.com          # papel ADMIN para conta já confirmada
```

Modo piloto (`APP_ENV=staging`): e-mails ficam no Mailpit local, sem Turnstile, fora dos
buscadores. Para abrir ao público: e-mail real e Turnstile em `app.env` e `APP_ENV=production`
(ver `docs/LAUNCH_CHECKLIST.md` do projeto).
