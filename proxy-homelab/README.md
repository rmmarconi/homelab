# *.homelab.rafaelmarconi.com.br

Nomes para os serviços que antes eram acessados por IP. Tudo passa pelo nginx do
mediacenter (10.1.1.100) com o certificado wildcard e só responde para a LAN
(`allow 10.1.0.0/16`).

| Nome | Destino |
|---|---|
| `homelab.rafaelmarconi.com.br` | painel de serviços (mesmo conteúdo de painel.rafaelmarconi.com.br) |
| `proxmox.` | https://10.1.1.254:8006 |
| `unifi.` | https://10.1.0.1 (Protect em `/protect`) |
| `unas.` | https://10.1.1.253 |
| `adguard.` / `adguard2.` | http://10.1.1.3 / http://10.1.1.4 |
| `grafana.` / `prometheus.` | http://10.1.1.15:3000 / :9090 |
| `ha.` | http://10.1.1.11 (sem X-Forwarded-For: o HA recusaria) |
| `openclaw.` / `financas.` | https://10.1.1.20 / http://10.1.1.20:8080 |
| `mailpit.` | http://10.1.1.100:8025 |

Peças:

- DNS: rewrites `homelab.rafaelmarconi.com.br` e `*.homelab.rafaelmarconi.com.br` → 10.1.1.100
  no AdGuard (`dns-adguard/adguard-config.json`). Fora de casa o nome cai no wildcard
  público e o nginx nega.
- Certificado: `certbot certonly --dns-cloudflare --cert-name homelab.rafaelmarconi.com.br
  -d homelab.rafaelmarconi.com.br -d '*.homelab.rafaelmarconi.com.br'` (renova sozinho).
- `homelab-tls.conf` → `/etc/nginx/snippets/homelab-tls.conf`;
  `nginx-homelab.conf` → `/etc/nginx/sites-available/homelab.rafaelmarconi.com.br`.

Serviço novo: copie um server block, ajuste `server_name`/`proxy_pass`, `nginx -t &&
systemctl reload nginx`, e troque a URL em `painel/www/services.json`.
