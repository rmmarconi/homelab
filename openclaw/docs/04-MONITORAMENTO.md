# Monitoramento (VM monitor, 10.1.1.15)

Docker Compose em `/opt/monitoring` (fonte: `monitoring/` no repositório).

| Serviço | Porta | Função |
|---|---|---|
| Prometheus | 9090 | métricas (90 dias) |
| Loki | 3100 | logs (30 dias) — roteador UniFi e NetFlow |
| Grafana | 3000 | dashboards |
| UnPoller, GoFlow2, Vector, pve-exporter, pihole-exporter, qbittorrent/jellyfin exporters, blackbox | internos | coletores |

## Consultas prontas
- Alvos fora: `up == 0`
- Disco do thin pool (via pve-exporter): `pve_disk_usage_bytes / pve_disk_size_bytes`
- Temperatura da CPU do Proxmox: `node_hwmon_temp_celsius{instance="pve"}`
- Temperatura dos discos do mediacenter: `smartmon_temperature_celsius_raw_value{instance="mediacenter"}` (sdb/sdc já em 50–51 °C)
- `/data` do mediacenter: `1 - node_filesystem_avail_bytes{instance="mediacenter",mountpoint="/data"} / node_filesystem_size_bytes{instance="mediacenter",mountpoint="/data"}`
- WAN por operadora hoje: `increase(unpoller_device_wan_receive_bytes_total{wan="Go Internet"}[1d])`
- Serviços do mediacenter: `node_systemd_unit_state{instance="mediacenter",state="active"}`
- Sondas HTTP: `probe_success{job="blackbox"}`

## Limiares de alerta
CPU Proxmox > 70 °C · thin pool > 80% · `/data` > 85% · disco > 55 °C · qualquer `up == 0` por > 10 min · Pi-hole parado · boot inesperado do Proxmox.
