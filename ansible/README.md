# Ansible do homelab

Configuração de todos os servidores, do jeito que estão em produção (2026-10). Complementa o
[Terraform](https://github.com/rmmarconi/homelab-terraform) (que cria VMs, LXCs, rede e DNS):
o Terraform faz a máquina existir, o Ansible deixa ela igual à de hoje.

| Role | Onde | O que faz |
|---|---|---|
| `common` | todos | fuso, pacotes, IPv4 preferido, node-exporter |
| `proxmox_host` | pve | repositórios sem assinatura, `/etc/hosts`, GRUB (C-states, memtest), offload da NIC, journald, log remoto, temperatura, turbo desligado |
| `backup_nas` | pve | storage NFS do UNAS, vzdump diário com retenção, backup da configuração do host, métricas de backup |
| `homeassistant` | pve → VM 105 | entrega os pacotes de `homeassistant/packages` e reinicia o HA se mudarem |
| `monitor` | monitor | stack de observabilidade (`monitoring/`), `.env` do vault, backup do Grafana |
| `openclaw` | openclaw | OpenClaw fixado, ferramentas `hl-*`, docs dos agentes, métricas, backup do estado |
| `adguard` | LXC 107/108 (via `pct`) | AdGuard Home com checksum, configuração por API, adguardhome-sync |
| `mediacenter` | mediacenter | nginx, Shlink, exporters, ufw, ajustes do Jellyfin, backup dos dados no UNAS |

## Backups (UNAS 2, 10.1.1.253, SMB `proxmox_backup`, storage `unas-backup`)

| O quê | Como | Quando | Retenção |
|---|---|---|---|
| VMs e LXCs inteiros (inclui HA, Grafana/Prometheus/Loki, OpenClaw, AdGuard) | vzdump `homelab-diario`, zstd, snapshot | 02:30 | 7 diários, 4 semanais, 3 mensais |
| Configuração do Proxmox (`/etc/pve`, rede, GRUB, units, `config.db`) | `pve-config-backup` | 02:00 | 30 dias |
| Dados de aplicação nas VMs (Grafana, estado do OpenClaw) | scripts locais às 01:45/01:50, vão dentro do vzdump | diário | 3 dias locais + retenção do vzdump |
| Mediacenter (bancos, configs dos *arr/Jellyfin/Seerr, Shlink, WordPress, nginx, certificados) | `mediacenter-backup` direto no NFS | 03:30 | 14 dias |
| Repositórios `homelab` e `homelab-terraform` | bare repos em `git/` | a cada push | histórico completo |

A mídia de `/data` (3,2 TB) não entra: é rebaixável e não cabe no UNAS junto do resto.

## Uso

A máquina de controle é a VM monitor (o Python do Mac é novo demais para o ansible-core):

```bash
ssh -A rmmarconi@10.1.1.15
cd ~/homelab/ansible
ansible-galaxy collection install -r requirements.yml
cp vault.example.yml group_vars/all/vault.yml && ansible-vault encrypt group_vars/all/vault.yml
ansible-playbook site.yml --check --diff          # sempre antes
ansible-playbook site.yml --limit pve --tags backup
```

`-A` repassa as chaves SSH do Mac; nada de chave privada na VM.

## Restaurar

- **VM/LXC:** Proxmox → storage `unas-backup` → Backups → Restore (ou `qmrestore`/`pct restore`).
- **Proxmox do zero:** reinstalar o PVE, `tar --zstd -xf host-config/pve-*.tar.zst -C /` (exceto `/etc/pve`,
  que volta via `config.db`), depois `ansible-playbook site.yml --limit pve` e o Terraform.
- **Mediacenter:** reinstalar com o `install-debian.sh`, extrair `apps/mediacenter/mediacenter-*.tar.zst`,
  `zstd -dc mariadb-all.sql.zst | mysql`, copiar os bancos de `sqlite/` (cópias consistentes com
  sufixo `.snapshot`: tirar o sufixo ao restaurar, com o app parado) e rodar o role `mediacenter`.
- **OpenClaw:** extrair `openclaw-*.tar.zst` (está dentro do vzdump da VM 103, em `/var/backups/homelab`)
  e renomear os `*.sqlite.snapshot` para `*.sqlite` com o gateway parado.
