# Home Assistant

HAOS 18.3 numa VM do Proxmox (ID 105, 2 vCPU, 4 GB, 32 GB com discard).

| Interface | Rede | IP | Gateway |
|---|---|---|---|
| enp6s18 (primária) | Servidores, VLAN 100 | 10.1.1.11/24 | 10.1.1.1 (única rota padrão) |
| enp6s19 | Default | 10.1.0.233/24 | — |
| enp6s20 | IoT, VLAN 2 | 10.1.2.204/24 | — |

IPv6 desativado nas três (a saída IPv6 da rede está quebrada). Os três adaptadores
estão habilitados em *Configurações → Sistema → Rede*, senão a descoberta (Gree,
mDNS, SSDP) só acontece na VLAN 100.

## Conteúdo

- `packages/ar_condicionado.yaml` — para os 3 Gree: tempo ligado (dia/semana/mês),
  potência e consumo **estimados**, kWh por dia/mês (utility_meter) e custo em R$.
  Requer no `configuration.yaml`:

  ```yaml
  homeassistant:
    packages: !include_dir_named packages
  recorder:
    purge_keep_days: 35
  ```

- `dashboards/gen_lovelace.py` — gera os dashboards **Casa** (`/painel-casa`) e
  **Ar-condicionado** (`/ar-condicionado`) para `lovelace/config/save`.

## Como a estimativa funciona

A Gree não mede consumo. Para cada aparelho:

- desligado: 0 W; só ventilação: 35 W;
- resfriando/aquecendo/desumidificando: `potência nominal × fator`, com
  `fator = 0,2` se o cômodo já está na temperatura desejada, senão
  `min(1, 0,35 + 0,3 × diferença em °C)`.

A potência nominal (padrão 900 W) e a tarifa (padrão R$ 0,90/kWh) são
`input_number` ajustáveis na aba *Ajustes* do dashboard Ar-condicionado.
