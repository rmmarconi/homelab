# Painel do homelab (2026-11-12)

`https://painel.rafaelmarconi.com.br`: página única com um cartão (logo + link + status) para cada
serviço, dividida por categoria: virtualização, rede e armazenamento, DNS, monitoramento, casa, mídia,
IA e automação, sites e apps. Busca com `/` (Enter abre o primeiro resultado).

- Estático, servido pelo nginx do mediacenter (`nginx-painel.conf` →
  `/etc/nginx/sites-available/painel.rafaelmarconi.com.br`), raiz `/var/www/painel`.
- **Só a LAN** (`allow 10.1.0.0/16`): a página lista IPs e serviços internos.
- Certificado Let's Encrypt por DNS-01 da Cloudflare (mesmo `dns-credentials.ini` do PatchMon).
- AdGuard: rewrite `painel.rafaelmarconi.com.br → 10.1.1.100` (o curinga público aponta para as WANs).
- Logos: [homarr-labs/dashboard-icons](https://github.com/homarr-labs/dashboard-icons), copiados em
  `www/icons/` (a página não carrega nada de fora).

## Status

`painel-status.py` (`/usr/local/bin/painel-status`) roda a cada minuto pelo `painel-status.timer`
como `www-data`, verifica cada URL do `services.json` (ou o campo `check`) e grava
`/var/www/painel/status/status.json`. Conta como no ar qualquer resposta HTTP < 500
(login 401/403 e redirecionamentos incluídos). Os domínios servidos pelo próprio mediacenter são
consultados em 127.0.0.1, porque o host não usa os rewrites do AdGuard e não há NAT loopback.

## Adicionar ou mudar um serviço

Edite `www/services.json` (nome, descrição, url, `icon` em `www/icons/` ou `letter`, host, `check`
opcional) e publique:

```bash
cd painel
scp -r www/* rmmarconi@10.1.1.100:painel-install/www/
ssh rmmarconi@10.1.1.100 'sudo install -m 644 ~/painel-install/www/index.html ~/painel-install/www/services.json /var/www/painel/ && sudo install -m 644 ~/painel-install/www/icons/* /var/www/painel/icons/'
```
