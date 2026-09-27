# homelab

Infraestrutura do meu homelab: um Proxmox VE em um Lenovo ThinkCentre Tiny (i7-4785T, 16 GB), rede UniFi (Cloud Gateway Fiber, U7 Pro, USW Flex 2.5G) com duas WANs em balanceamento e Starlink de backup, Pi-hole redundante e uma stack de monitoramento.

| Pasta | Conteúdo | Status |
|---|---|---|
| [`monitoring/`](monitoring/) | Prometheus, Grafana, Loki, Vector, UnPoller, GoFlow2 e exporters de Proxmox/Pi-hole em Docker Compose | ✅ em produção |
| `ansible/` | configuração dos hosts e deploy da stack | 🚧 próximo passo |
| `terraform/` | criação das VMs/LXC no Proxmox | 🚧 próximo passo |

## Câmeras

A câmera UniFi (Escritório) e as 3 Tuya (ONVIF) gravam no UniFi Protect do
Cloud Gateway. Só a do Escritório aparece no Home Assistant: o Protect não
repassa vídeo de câmeras de terceiros, e a Sala e a Varanda aceitam uma única
conexão RTSP. Um Frigate numa VM à parte funcionou, mas pesou demais no host
e foi removido (ver histórico do git, pasta `iot/`).

## Rede

| Host | IP | Função |
|---|---|---|
| pve | 10.1.1.254 | Proxmox VE 9 |
| pihole-1 / pihole-2 | 10.1.1.3 / 10.1.1.4 | DNS (LXC), sincronizados por nebula-sync |
| homeassistant | 10.1.1.11 (+ 10.1.0.233 default, 10.1.2.204 IoT) | Home Assistant OS (VM 105) |
| openclaw | 10.1.1.20 | VM (desligada) |
| monitor | 10.1.1.15 | VM Ubuntu 26.04 com a stack de monitoramento |
| mediacenter | 10.1.1.100 | host físico separado |

Nenhum segredo é versionado: cada pasta tem um `.env.example` e o `.gitignore` bloqueia `.env`, `*.tfstate` e `*.tfvars`.

## Licença

GPL-3.0 — veja [LICENSE](LICENSE).
