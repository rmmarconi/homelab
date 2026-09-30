# Inventário do homelab

Repositório com toda a configuração: https://github.com/rmmarconi/homelab (clone local em `~/homelab`, só leitura).

## Redes (UniFi Cloud Gateway Fiber "Flamingos Paradise")

| Rede | Faixa | Uso |
|---|---|---|
| Default | 10.1.0.0/24 (gw 10.1.0.1) | computadores, celulares, TVs, câmeras Tuya |
| Servidores (VLAN 100) | 10.1.1.0/24 (gw 10.1.1.1) | Proxmox, VMs, Pi-holes, mediacenter |
| IoT (VLAN 2) | 10.1.2.0/24 (gw 10.1.2.1) | ar-condicionado Gree, medidor solar Tuya, inversores |

- WANs: **Go Internet** (PPPoE, porta 2/eth1) e **Eletrodata** (PPPoE, porta 5/eth4) em balanceamento; **Starlink** de backup.
- **IPv6 de saída está quebrado em toda a rede** (timeouts). Hosts afetados foram configurados para preferir IPv4 (`/etc/gai.conf`). Não "conserte" isso no roteador por conta própria.
- DNS: Pi-hole 10.1.1.3 e 10.1.1.4.

## Hosts

| Host | IP | Tipo | Função | Acesso |
|---|---|---|---|---|
| pve | 10.1.1.254 | Proxmox VE 9 (Lenovo Tiny i7-4785T, 16 GB, SSD 1 TB) | hypervisor | `ssh root@10.1.1.254` |
| monitor | 10.1.1.15 | VM 102, Ubuntu 26.04, 3 GB | Prometheus, Grafana, Loki, Vector, UnPoller, GoFlow2, exporters | `ssh rmmarconi@10.1.1.15` |
| homeassistant | 10.1.1.11 (+10.1.0.233, +10.1.2.204) | VM 105, HAOS 18.3, 3 GB | automação residencial | API HTTP porta **80** |
| openclaw | 10.1.1.20 | VM 103, Ubuntu 26.04, 4 GB | este OpenClaw | local |
| pihole-1 / pihole-2 | 10.1.1.3 / 10.1.1.4 | LXC 100 / 101 | DNS | via Proxmox `pct exec` |
| nebula-sync | — | LXC 106 | sincroniza os Pi-holes | via Proxmox |
| mediacenter | 10.1.1.100 | físico, Debian 13 | Jellyfin + *arr nativos, `/data` LVM 3,2 TB | `ssh rmmarconi@10.1.1.100` |
| rafaelmarconi.com.br | Hostinger 82.25.72.87:65002 | WordPress 7.1 + tema Marconi | blog técnico | `ssh -p 65002 u819599816@82.25.72.87` (WP-CLI) |

Na mesma conta Hostinger há outros sites (blog.certiflink.com, sf.digi6.com.br): **não toque neles**.
O site **marconi3dlab.com.br** é outro projeto, cuidado pelo agente `wordpress`.

## Painéis

- Grafana: http://10.1.1.15:3000 · Prometheus: http://10.1.1.15:9090 · Loki: http://10.1.1.15:3100
- Home Assistant: http://10.1.1.11/ (dashboards `painel-casa`, `ar-condicionado`, Energia)
- UniFi: https://10.1.0.1 (somente o Rafael)
