# Nobreak SMS (GAM2000BiBiW)

Ligado ao **pve (10.1.1.254)** por cabo serial + adaptador USB Prolific PL2303
(`067b:23a3`, serial `BVDAb2A7N12`). A interface web/Wi‑Fi do nobreak (10.1.0.69)
não é usada: exige login e só é alcançável da VLAN Default.

## Fluxo

```
nobreak --serial/USB--> pve: NUT (driver sms_ser) -> upsd :3493
                                   |-> upsmon (desligamento do pve em bateria baixa)
                                   |-> Home Assistant: integração "Network UPS Tools" (10.1.1.254:3493, sem login)
                                   '-> monitor: nut-exporter :9199 -> Prometheus (job "nut") -> Grafana "Energia / Nobreak SMS"
```

## pve (`/etc/nut`, backups `*.bak-20261111`)

- `nut.conf`: `MODE=netserver`
- `ups.conf`:
  ```
  [sms]
    driver = sms_ser
    port = /dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_BVDAb2A7N12-if00-port0
    desc = "SMS GAM2000BiBiW (rack)"
    pollinterval = 5
  ```
- `upsd.conf`: `LISTEN 127.0.0.1 3493` e `LISTEN 10.1.1.254 3493`
- `upsd.users` / `upsmon.conf` (640 root:nut): usuário `upsmon` (primary) com senha
  aleatória gerada no host — **não está no git**. Leitura de variáveis não exige login.
- `upsmon`: padrão do Debian — em `OB LB` (na bateria + bateria baixa) executa
  `shutdown -h +0` no pve, que desliga VMs/LXCs de forma ordenada.
- udev `/etc/udev/rules.d/90-nut-sms.rules` dá o tty ao grupo `nut`:
  ```
  SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="23a3", ATTRS{serial}=="BVDAb2A7N12", GROUP="nut", MODE="0660"
  ```
- Serviços: `nut-driver@sms`, `nut-server`, `nut-monitor`.

Teste: `upsc sms@10.1.1.254`

## Limitações do driver `sms_ser`

Não informa autonomia estimada (`battery.runtime`) nem potência em W; só carga (%).
`input.voltage.nominal` vem como texto (`EBiS115`).

## Home Assistant

Integração NUT criada em 2026-11-11 (host 10.1.1.254, porta 3493, sem usuário).
Entidades: `sensor.sms_status`, `sensor.sms_dados_do_status`, `sensor.sms_carga`,
`sensor.sms_carga_da_bateria`, `sensor.sms_tensao_de_entrada`,
`sensor.sms_tensao_de_saida`, `sensor.sms_status_de_carregamento`
(temperatura e beeper existem desabilitadas por padrão).
