# Rede (UniFi) e DNS (AdGuard Home)

## UniFi — somente observação
Os dados vêm do **UnPoller** no Prometheus e dos **eventos do roteador** no Loki. Nenhum agente tem credencial do UniFi, e nenhum deve ter.

- Dispositivos: gateway **UCG Fiber** ("Flamingos Paradise"), APs **U7 Pro 1º Andar** e **U7 Pro Escritório**, switch **USW Flex 2.5G 8 PoE**.
- Métricas úteis (PromQL): `unpoller_device_uptime_seconds`, `unpoller_device_upgradable`, `unpoller_client_uptime_seconds` (clientes), `unpoller_device_wan_receive_bytes_total{wan=~"Go Internet|Eletrodata"}`, `unpoller_wan_interface_state`.
- Logs do roteador (LogQL): `{job="unifi"}` com labels `category`, `event`, `severity`.
- NetFlow: `netflow_bytes_total{direction,local_ip,service}`.

## DNS — AdGuard Home (LXC 107 adguard-1 e 108 adguard-2)
- Substituiu os Pi-holes em 2026-10-20, com os mesmos IPs (10.1.1.3/.4), IPv6, MACs e VLAN. Pi-holes (100/101) e nebula-sync (106) ficam **parados**.
- Saúde: `~/.openclaw/tools/homelab/bin/hl-check dns` (serviço, resolução, bloqueio, última sincronização).
- Sincronização: `adguardhome-sync` no adguard-1 copia tudo para o adguard-2 a cada 10 min. Ele ativa listas mesmo que estejam desativadas na origem: para tirar uma lista, **remover**.
- **Nunca** readicionar `zangadoprojets/Adsandtrackers`: tem linhas `.com` que bloqueiam a internet inteira no AdGuard.
- Métricas: job `adguard` (adguard-exporter), prefixo `adguard_`; node-exporter com `instance=adguard-1/2`.
- Painel web: http://10.1.1.3 e http://10.1.1.4 (usuário admin; senha só com o Rafael).
