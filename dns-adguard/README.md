# DNS — AdGuard Home

Substituiu os Pi-holes em 2026-10-20. Mesma rede: IPs, IPv6, MACs, gateway e VLAN 100 dos antigos.

| LXC | Nome | IP | Papel |
|---|---|---|---|
| 107 | adguard-1 | 10.1.1.3 / 2804:4c1c:2a:8601::3 | origem do adguardhome-sync |
| 108 | adguard-2 | 10.1.1.4 / 2804:4c1c:2a:8601::4 | réplica |
| 100, 101, 106 | pihole-1, pihole-2, nebula-sync | — | **parados**, `onboot 0`, guardados para rollback |

- AdGuard Home v0.107.79 em `/opt/AdGuardHome` (release oficial, sha256 conferido), serviço `AdGuardHome`.
  Web na porta 80, DNS na 53 (UDP/TCP, IPv4 e IPv6).
- Senha do admin: `/root/adguard-admin.txt` no Proxmox (root 600). Não versionada.
- Configuração aplicada por API com `adguard-apply.py adguard-config.json` (senha pelo stdin):
  upstreams 8.8.8.8/1.1.1.1 (iguais ao Pi-hole), PTR local pelo gateway 10.1.1.1, ratelimit 30/s,
  log de consultas e estatísticas de 7 dias, listas atualizadas a cada 24 h.
- Listas: a união das listas ativas nos dois Pi-holes, **menos** `zangadoprojets/Adsandtrackers`:
  ela tem linhas como `.com`, que o Pi-hole ignorava e o AdGuard trata como "contém .com",
  bloqueando a internet inteira. Não readicionar.
- Regras do usuário: allow/deny do Pi-hole convertidos com `$important`, para manter a prioridade do
  Pi-hole (liberação vence tudo; bloqueio vence as listas).
- Sincronização: `adguardhome-sync` v0.9.4 no adguard-1 (usuário `agsync`, `/etc/adguardhome-sync/config.yaml`
  com a senha, 640), a cada 10 min. Atenção: ele copia listas **ativadas** mesmo que estejam desativadas na
  origem; para tirar uma lista, **remova** em vez de desativar.
- Monitoramento: `adguard-exporter` na VM monitor (job `adguard`) e node-exporter em cada LXC
  (`instance=adguard-1/2`). Dashboard "AdGuard Home" na pasta AdGuard do Grafana.

Rollback: `pct stop 107 108; pct start 100 101 106; pct set 100 --onboot 1` (idem 101 e 106).

## DNS interno (rewrites) — 2026-10-22

Para os serviços do mediacenter não fazerem o caminho LAN → IP público → NAT loopback no gateway
(que alternava entre as duas WANs e causava pausas no Jellyfin do Fire TV), o AdGuard responde dentro
de casa com o IP interno. Mesmo certificado, nada muda nos apps:

| Domínio | Resposta |
|---|---|
| `media.rafaelmarconi.com.br`, `*.media.rafaelmarconi.com.br` | 10.1.1.100 |
| `marconi3dlab.com.br`, `www.marconi3dlab.com.br` | 10.1.1.100 |

`short.x7velo.com` continua pela Cloudflare (proxy), de propósito.
