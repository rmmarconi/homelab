# VM iot

Ubuntu 26.04 (cloud image) no Proxmox, ID 104: 4 vCPU, 4 GB, 250 GB.

| Placa | Rede | IP | Gateway |
|---|---|---|---|
| eth0 | Servidores, VLAN 100 | 10.1.1.12/24 | 10.1.1.1 (única rota padrão) |
| eth1 | IoT, VLAN 2 | 10.1.2.12/24 | — |
| ens20 | Default (**temporária**) | 10.1.0.12/24 | — |

A placa na rede default existe só até as câmeras irem para a VLAN IoT; depois
remova `net2` da VM e `/etc/netplan/70-default-temp.yaml`.

## Serviços (`docker-compose.yml`, rede do host)

- **Mosquitto** (1883) — broker MQTT do Home Assistant, do Frigate e, no
  futuro, do Zigbee2MQTT. Sem senha: só a própria VM e o HA (10.1.1.11)
  alcançam a porta.
- **Frigate 0.18** — NVR das 3 câmeras Tuya. O go2rtc embutido abre **uma**
  conexão por câmera (a Sala e a Varanda só aceitam uma) e redistribui para
  gravação, HA (RTSP 8554) e WebRTC (8555).

Todos os containers usam `network_mode: host` para que o `ufw` valha de fato
(portas publicadas pelo Docker passam por cima dele). Regras em `firewall.sh`.

## Credenciais das câmeras

`frigate/config.yml` vai para o git com `__RTSP_USER__`/`__RTSP_PASS__`.
Na VM: `sudo ./frigate/set-frigate-cred.sh`.

## Por que não é um add-on do Home Assistant

No HAOS 18.3 (Docker 29.7) o Supervisor tenta dar ao primeiro add-on o IP
`172.30.33.0` (início da faixa dos add-ons), que o Docker não consegue usar:
o container fica fora da rede `hassio` e nem o HA nem o ingress o alcançam.
Fora do HAOS o problema não existe, e o Frigate não cai junto com o HA.
