# Shlink — short.x7velo.com (mediacenter, 10.1.1.100)

Encurtador de links com estatísticas, nativo (sem Docker): Shlink 5.1.7 em `/opt/shlink`,
PHP 8.4-FPM com pool próprio (usuário `shlink`), MariaDB local (banco `shlink`), nginx.

| Item | Onde |
|---|---|
| Links curtos | https://short.x7velo.com (DNS na Cloudflare, proxied) |
| Painel web | https://shlink.media.rafaelmarconi.com.br (shlink-web-client 4.8.1, `/var/www/shlink-web-client`) |
| Configuração | variáveis `env[]` em `etc/php/8.4/fpm/pool.d/shlink.conf` |
| CLI | `sudo shlink <comando>` (mesmo ambiente do pool) |
| Segredos (fora do git) | `/etc/shlink/db_password`, `/etc/shlink/admin-api-key` (root 600) |
| Tarefas | `etc/cron.d/shlink`: visit:locate de hora em hora, GeoLite2 aos domingos |
| Certificado | Let's Encrypt `short.x7velo.com` (webroot, renovação automática) |

O nginx usa o IP real do visitante (`snippets/cloudflare-realip.conf`, `CF-Connecting-IP`) e
descarta cabeçalhos de proxy forjáveis antes do PHP. As faixas da Cloudflare mudam raramente;
regenerar com o laço em `cloudflare-realip.conf`.

Geolocalização: `sudo shlink-set-geolite` (pede a license key da MaxMind sem ecoar).
