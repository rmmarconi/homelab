#!/bin/sh
# Firewall da VM iot. Rode com sudo. Idempotente.
set -e
ufw --force reset >/dev/null
ufw default deny incoming >/dev/null
ufw default allow outgoing >/dev/null
ufw allow from 10.1.0.0/16 to any port 22 proto tcp comment "SSH da rede interna"
ufw allow from 10.1.1.11 to any port 1883 proto tcp comment "MQTT: Home Assistant"
ufw allow from 10.1.1.11 to any port 5000 proto tcp comment "Frigate API: Home Assistant"
ufw allow from 10.1.1.11 to any port 1984 proto tcp comment "go2rtc API: Home Assistant"
ufw allow from 10.1.1.11 to any port 8554 proto tcp comment "RTSP restream: Home Assistant"
ufw allow from 10.1.0.0/16 to any port 8971 proto tcp comment "Frigate UI autenticada"
ufw allow from 10.1.0.0/16 to any port 8555 comment "WebRTC (navegador)"
ufw allow from 10.1.1.15 to any port 9100 proto tcp comment "node-exporter: Prometheus"
ufw --force enable >/dev/null
ufw status numbered
