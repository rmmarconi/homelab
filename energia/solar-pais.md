# Solar — casa dos pais

3 microinversores Deye de 2 kW (4 placas cada, 12 placas), com logger Wi-Fi
Solarman embutido, acessíveis pela VPN site-to-site:

| Micro | IP | Serial do logger | Serial do inversor |
|---|---|---|---|
| micro1 | 10.2.0.251 | 3926222475 | 2301090577 |
| micro2 | 10.2.0.190 | 3926982436 | — |
| micro3 | 10.2.0.186 | 3926442305 | 2301090547 |

## Coleta

`monitoring/exporters/solarman/exporter.py` (container `solarman-exporter` no
monitor, porta 9595, job `solarman`). Fala o protocolo **Solarman V5** na porta
TCP 8899 e lê os registradores Modbus do micro. Não usa a senha da interface web:
basta o serial do logger, descoberto com

```
echo -n WIFIKIT-214028-READ | nc -u -w2 10.2.0.251 48899
```

O logger ignora pedidos de vez em quando; o exporter lê cada micro a cada 30 s em
segundo plano, tenta 3 vezes e serve o último valor bom por até 5 min. À noite os
micros desligam (logger junto) e as séries somem até o sol voltar.

Registradores usados (mapa Deye micro): 3–7 serial · 16 potência nominal ·
60 energia do dia · 63/64 energia total · 65–68 energia do dia por placa ·
69/70, 71/72, 74/75, 77/78 total por placa · 73 tensão da rede ·
79 frequência · 86/87 potência CA · 90 temperatura · 109–116 tensão/corrente por placa.

Métricas: `solar_pv_{voltage_volts,current_amperes,power_watts,energy_today_kwh,energy_total_kwh}{inverter,pv}`,
`solar_{ac_power_watts,energy_today_kwh,energy_total_kwh,grid_voltage_volts,grid_frequency_hertz,temperature_celsius}{inverter}`,
`solarman_up`, `solar_info`.

## Dashboard

Grafana › Energia › **Solar - Casa dos pais** (`/d/solar-pais`), gerado por
`monitoring/scripts/gen-solar-dashboard.py`: potência e geração agora, por placa
(potência, tensão, corrente, gerado hoje, desempenho relativo à média), por micro
(potência CA, temperatura, tensão e frequência da rede) e histórico diário.

## Pendência: rota da VPN

A VPN só encaminha a rede 10.1.0.0/24; o monitor (10.1.1.15) não alcança 10.2.0.0/24.
É preciso incluir 10.1.1.0/24 nas redes da VPN site-to-site no UniFi (dos dois lados).
