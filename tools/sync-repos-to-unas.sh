#!/bin/sh
# Copia os repositórios homelab e homelab-terraform para o UNAS como repositórios git "bare"
# (histórico completo), via Proxmox, que monta o NFS em /mnt/pve/unas-backup.
# Uso (do Mac, na pasta que contém os dois repositórios):  homelab/tools/sync-repos-to-unas.sh
set -eu
PVE=root@10.1.1.254
GITDIR=/mnt/pve/unas-backup/git
ssh "$PVE" "mountpoint -q /mnt/pve/unas-backup || pvesm status --storage unas-backup >/dev/null; ls /mnt/pve/unas-backup >/dev/null"
for r in homelab homelab-terraform; do
  b=$(git -C "$r" branch --show-current)
  # repositório incompleto (ex.: SMB caiu no meio) é recriado; HEAD aponta para o branch real
  ssh "$PVE" "mkdir -p $GITDIR && { git --git-dir=$GITDIR/$r.git rev-parse --git-dir >/dev/null 2>&1 || { rm -rf $GITDIR/$r.git; git init -q --bare -b $b $GITDIR/$r.git; }; } && git --git-dir=$GITDIR/$r.git symbolic-ref HEAD refs/heads/$b"
  git -C "$r" remote get-url unas >/dev/null 2>&1 || git -C "$r" remote add unas "$PVE:$GITDIR/$r.git"
  git -C "$r" push -q unas --all && git -C "$r" push -q unas --tags
  echo "ok: $r -> unas:$GITDIR/$r.git ($(git -C "$r" rev-parse --short HEAD))"
done
