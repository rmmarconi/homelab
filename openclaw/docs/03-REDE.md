# Rede (UniFi) e DNS (Pi-hole)

## UniFi — somente observação
Os dados vêm do **UnPoller** no Prometheus e dos **eventos do roteador** no Loki. Nenhum agente tem credencial do UniFi, e nenhum deve ter.

- Dispositivos: gateway **UCG Fiber** ("Flamingos Paradise"), APs **U7 Pro 1º Andar** e **U7 Pro Escritório**, switch **USW Flex 2.5G 8 PoE**.
- Métricas úteis (PromQL): `unpoller_device_uptime_seconds`, `unpoller_device_upgradable`, `unpoller_client_uptime_seconds` (clientes), `unpoller_device_wan_receive_bytes_total{wan=~"Go Internet|Eletrodata"}`, `unpoller_wan_interface_state`.
- Logs do roteador (LogQL): `{job="unifi"}` com labels `category`, `event`, `severity`.
- NetFlow: `netflow_bytes_total{direction,local_ip,service}`.

## Pi-hole (LXC 100 e 101)
- Acesso: `pct exec 100 -- pihole <cmd>` no Proxmox (sem senha).
- **Problema conhecido:** listas diferentes entre os dois (pihole-1 ~79 mil domínios, pihole-2 ~1,37 milhão). O nebula-sync (LXC 106) não está sincronizando as listas/gravity. Investigar e propor correção.
- Métricas: `pihole_dns_queries_today`, `pihole_ads_percentage_today`, `pihole_domains_being_blocked`.
