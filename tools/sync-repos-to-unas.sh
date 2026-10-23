#!/bin/sh
# Copia os repositórios homelab e homelab-terraform para o UNAS como repositórios git "bare"
# (histórico completo), via Proxmox, que monta o NFS em /mnt/pve/unas-backup.
# Uso (do Mac, na pasta que contém os dois repositórios):  homelab/tools/sync-repos-to-unas.sh
set -eu
PVE=root@10.1.1.254
GITDIR=/mnt/pve/unas-backup/git
ssh "$PVE" "mountpoint -q /mnt/pve/unas-backup || pvesm status --storage unas-backup >/dev/null; ls /mnt/pve/unas-backup >/dev/null"
for r in homelab homelab-terraform; do
  ssh "$PVE" "mkdir -p $GITDIR && [ -d $GITDIR/$r.git ] || git init -q --bare $GITDIR/$r.git"
  git -C "$r" remote get-url unas >/dev/null 2>&1 || git -C "$r" remote add unas "$PVE:$GITDIR/$r.git"
  git -C "$r" push -q unas --all && git -C "$r" push -q unas --tags
  echo "ok: $r -> unas:$GITDIR/$r.git ($(git -C "$r" rev-parse --short HEAD))"
done
