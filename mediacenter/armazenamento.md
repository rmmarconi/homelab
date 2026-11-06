# Armazenamento do mediacenter (2026-11-06)

`/data` (mídias e torrents) fica num volume LVM nos dois Seagate ST2000NM0055 de 2 TB:

- VG `media` (`/dev/sda` + `/dev/sdb`, discos inteiros), LV `data` linear, ext4 `-m 0 -T largefile4`, rótulo `data`.
- **Sem redundância**: se um disco falhar, perde-se o volume inteiro. O conteúdo pode ser baixado de novo; as configurações ficam no NVMe e no backup.
- fstab: `UUID=… /data ext4 defaults,noatime,nofail,x-systemd.device-timeout=30s 0 2`. Se o volume faltar, o servidor sobe mesmo assim.
- qbittorrent, sonarr, radarr, lidarr e bazarr têm `RequiresMountsFor=/data` (drop-in `data-mount.conf`). Sem o volume, eles não sobem e não enchem o NVMe.
- Estrutura: `/data/media/{movies,tv,music}` e `/data/torrents/incomplete`, dono `mediacenter:mediacenter`, modo 2775.

Para incluir o terceiro disco (`sdc`, por exemplo):

```bash
wipefs -a /dev/sdc && pvcreate /dev/sdc && vgextend media /dev/sdc
lvextend -r -l +100%FREE media/data
```

## Reset de 2026-11-06

O conteúdo foi zerado e as configurações mantidas. Backup prévio: `/root/mediacenter-pre-reset-20261106-1204.tgz` (também no UNAS, em `mediacenter/`).

- Sonarr e Radarr: apagados séries, filmes, episódios, arquivos, histórico, fila, blocklist e coleções. Ficaram perfis, indexadores, cliente de download, raízes e nomenclatura.
- Bazarr: apagados séries, filmes e histórico de legendas.
- qBittorrent: apagados os torrents (`BT_backup`).
- Jellyfin: biblioteca zerada pela varredura e coleções apagadas.

O Jellyfin não remove itens de uma pasta de biblioteca vazia (proteção contra disco desmontado). Para zerar, crie um arquivo qualquer na pasta, varra a biblioteca e apague o arquivo.

O Jellyfin responde na raiz `https://media.rafaelmarconi.com.br`; `jellyfin.media…` continua como alias. O vhost está em `/etc/nginx/sites-available/mediacenter.conf`.
