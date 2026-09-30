# Home Assistant (VM 105)

- URL da API: `http://10.1.1.11/api/` (porta **80**, não 8123). Token do OpenClaw: arquivo `~/.config/homelab/ha_token` (lido pelos comandos `hl-*`; nunca imprima).
- Integrações: UniFi, UniFi Protect (só a câmera do Escritório), Jellyfin, iCloud, IPP (impressora HP), Gree (3 ar-condicionados), Tuya Local (medidor solar ERZ04C), HACS, Prometheus.
- Packages em `/config/packages`: `ar_condicionado.yaml` (tempo de uso, potência/consumo **estimados**, custo) e `solar.yaml` (geração, economia).
- Ar-condicionados: `climate.c03937630d3f` (Escritório), `climate.c0393762fa51` (Clara), `climate.c0393762e6bc` (Suite).
- **Bug conhecido:** no HAOS 18.3 o primeiro add-on recebe o IP 172.30.33.0 e fica sem rede. Não instale add-ons sem avisar.
- Backup automático do HA **não está configurado** — recomendar.
- As 3 câmeras Tuya (Sala, Cozinha, Varanda) ficam **só no UniFi Protect**, fora do HA, por decisão do Rafael.
