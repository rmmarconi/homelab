# Monitoring — UniFi, Proxmox e Pi-hole

Stack de observabilidade do homelab rodando em uma VM Ubuntu 26.04 (2 vCPU, 4 GB RAM) no Proxmox, toda em Docker Compose.

```
                 ┌──────────────── VM monitor (10.1.1.15) ────────────────┐
UniFi API  ────► │ UnPoller ─┐                                            │
Proxmox API ───► │ pve-exporter ─┤                                        │
Pi-hole API ───► │ pihole-exporter ─┼──► Prometheus ──┐                   │
node-exporter ─► │ (pve, piholes, VM) ┘                │                  │
                 │                                     ├──► Grafana :3000 │
UniFi SIEM ────► │ :514  ┐                             │                  │
 (CEF/syslog)    │       ├──► Vector ──► Loki ─────────┘                  │
UniFi NetFlow ─► │ :2055 ─► GoFlow2 ┘   └──► métricas NetFlow ► Prometheus │
                 └────────────────────────────────────────────────────────┘
```

| Serviço | Imagem | Função | Porta |
|---|---|---|---|
| UnPoller | `ghcr.io/unpoller/unpoller` | métricas da controladora UniFi (gateway, APs, switches, clientes, DPI, WANs) | 9130 (interna) |
| Prometheus | `prom/prometheus` | séries temporais — 90 dias / 40 GB | 9090 |
| Loki | `grafana/loki` | logs — 30 dias | 3100 |
| Vector | `timberio/vector` | recebe syslog/CEF da UniFi e fluxos do GoFlow2, envia ao Loki e gera métricas | 514/udp+tcp, 9598 (interna) |
| GoFlow2 | `netsampler/goflow2` | coletor NetFlow v5/v9, IPFIX e sFlow | 2055/udp, 6343/udp |
| pve-exporter | `prompve/prometheus-pve-exporter` | VMs, containers e storages do Proxmox | 9221 (interna) |
| pihole-exporter | `ekofr/pihole-exporter` | estatísticas DNS dos Pi-holes v6 | 9617 (interna) |
| node-exporter | `prom/node-exporter` | métricas do host (VM) | 9100 (interna) |
| Grafana | `grafana/grafana` | dashboards | 3000 |

Cada container tem `mem_limit` para que um serviço sozinho não derrube a VM.

## Dashboards

Próprios (versionados em `grafana/dashboards/unifi/`):

- **UniFi – Consumo por WAN** — download/upload exatos por link (período, hoje, mês), throughput, total diário, % do link contratado, estado das WANs, erros.
- **UniFi – NetFlow** — top clientes (com nome vindo do UnPoller), serviços, protocolos, destinos e portas remotas, fluxos brutos.
- **UniFi – Logs do Roteador** — eventos SIEM (CEF) com filtros por categoria, evento, severidade e busca.

Da comunidade (baixados por `scripts/fetch-dashboards.sh`): UnPoller 11310–11315 e 23027, Node Exporter Full (1860), Proxmox via Prometheus (10347), Pi-hole Exporter (10176).

## Instalação

```bash
# na VM (Ubuntu 26.04)
sudo apt install -y docker.io docker-compose-v2 jq
sudo usermod -aG docker $USER   # relogar

git clone https://github.com/rmmarconi/homelab.git
cd homelab/monitoring
cp .env.example .env && chmod 600 .env
./scripts/fetch-dashboards.sh
```

Ajuste para a sua rede:

- `prometheus/prometheus.yml` — IPs do Proxmox e dos Pi-holes; o `metric_relabel_configs` do job `unpoller` mapeia interface → nome da WAN (`eth1` = Go Internet, `eth4` = Eletrodata no UCG Fiber). Descubra o seu com `unpoller_device_port_*` (label `port_ip`) e um `whois` no IP público.
- `docker-compose.yml` — `PIHOLE_HOSTNAME` do pihole-exporter.
- `vector/vector.yaml` — `local_nets`: inclua o seu prefixo IPv6 público delegado no lugar de `2001:db8::/56`, senão o tráfego IPv6 dos clientes é classificado como "externo".

Grave os segredos sem digitá-los na linha de comando:

```bash
./scripts/set-secret.sh GF_SECURITY_ADMIN_PASSWORD
./scripts/set-secret.sh UP_UNIFI_DEFAULT_PASS
./scripts/set-secret.sh PIHOLE_PASSWORD        # senha1,senha2 (uma por Pi-hole)
./scripts/set-secret.sh PVE_TOKEN_VALUE
docker compose up -d
```

> Mudou o `.env`? Use `docker compose up -d --force-recreate <serviço>` — o `up -d` normal não percebe alterações em `env_file`.
> Mudou `prometheus.yml`? Use `docker compose restart prometheus` — arquivos montados individualmente não acompanham a substituição do arquivo no host.

## Credenciais nas fontes

**UniFi** — crie um usuário local *somente leitura* (sem SSO) ou uma API key em *Settings → Control Plane → Integrations*. Se a VM estiver em outra VLAN, libere no firewall zone-based: origem `IP da VM` → zona *Gateway*, TCP 443.

**Proxmox** — usuário auditor com token:

```bash
pveum user add monitor@pve --comment "Prometheus"
pveum acl modify / --users monitor@pve --roles PVEAuditor
pveum user token add monitor@pve prometheus --privsep 0
```

E o node-exporter no host e nos LXC: `apt install prometheus-node-exporter`.

**Pi-hole v6** — gere uma *App password* em *Settings → Web interface / API* em **cada** Pi-hole (o nebula-sync não sincroniza app passwords).

## Integrações na UniFi

- **Syslog/SIEM**: *Settings → Control Plane → Integrations → Activity Logging (SIEM Server)* → `IP da VM`, porta 514.
- **NetFlow**: *Settings → CyberSecure / Traffic & Firewall → NetFlow* → `IP da VM`, porta 2055, v9 ou IPFIX.

## Detalhes que custaram tempo

- **O UniFi SIEM envia CEF sem cabeçalho `<PRI>`** (`Sep 26 20:12:25 host CEF:0|Ubiquiti|UniFi Network|...`). O `loki.source.syslog` do Alloy/Promtail rejeita (`invalid or unsupported framing`) e o `tcpdump` mostra `(invalid)`. Por isso o Vector recebe o socket cru e usa `parse_cef` no VRL.
- **O netconsole não funciona em `vmbr0` com portas veth** de LXC (`veth doesn't support polling`) — para capturar logs do Proxmox remotamente use `journalctl -f | socat - UDP:...`.
- **Pi-hole com várias instâncias**: se uma falha na autenticação, o exporter não publica métricas de nenhuma.
- **Nomes de clientes no NetFlow**: o join é feito no PromQL com `unpoller_client_uptime_seconds` (labels `ip` e `name`), sem enriquecer no pipeline.
