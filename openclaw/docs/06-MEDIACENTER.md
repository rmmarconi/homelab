# Mediacenter (10.1.1.100, Debian 13, físico)

- Serviços nativos (systemd): jellyfin, qbittorrent, prowlarr, radarr, sonarr, lidarr, bazarr, **seerr** (sucessor do Jellyseerr), flaresolverr. Usuário de serviço `mediacenter`.
- `/data`: LVM **linear sem redundância** sobre sda (500 GB) + sdb (1 TB, ~27 mil horas, o mais velho) + sdc (2 TB). Um disco que falhe compromete tudo. Estado dos apps em `/var/lib/mediacenter` (NVMe).
- `/etc/gai.conf` prefere IPv4 (IPv6 quebrado); FlareSolverr depende do pacote `xvfb`.
- Exportarr (radarr/sonarr/lidarr/prowlarr/bazarr) nas portas 9707–9711; node-exporter com systemd e SMART.
- Firewall ufw: painéis web ainda abertos para qualquer IP (pendente decisão do Rafael sobre portas redirecionadas no roteador). Não altere sem aprovação.
- 77+ atualizações apt pendentes (setembro/2026). Discos sdb/sdc a 50–51 °C.
