# Proxmox (pve, 10.1.1.254)

- Hardware: Lenovo ThinkCentre Tiny, i7-4785T (4c/8t, TjMax 75 °C), 16 GB (2× 8 GB Crucial), SSD "UP Gamer" 1 TB (SATA).
- Kernel com `intel_idle.max_cstate=1 processor.max_cstate=1` (mitigação de travamentos). Journal enviado em tempo real ao mediacenter (serviço `journal-forward`).
- **Histórico:** travamentos/desligamentos abruptos ligados à **energia elétrica** (o mediacenter caía no mesmo minuto). Fonte/tomada/nobreak são suspeitos. Registre qualquer boot inesperado.
- Storage: thin pool `pve/data` (815 GB). Já chegou a 97,7% (incidente) — **alerte acima de 80%**.
- Não há backup automático das VMs configurado (vzdump). Recomende, não configure sem aprovação.

## VMs e containers

| ID | Nome | vCPU/RAM | Observação |
|---|---|---|---|
| 100 | pihole-1 (LXC) | 2/512 MB | **parado** desde 2026-10-20 (rollback) |
| 101 | pihole-2 (LXC) | 2/512 MB | **parado** desde 2026-10-20 (rollback) |
| 102 | monitor | 1/3 GB | stack de monitoramento |
| 103 | openclaw | 4/4 GB | este agente (gateway usa ~1,7 GB) |
| 105 | homeassistant | 4/3 GB, disco 182 GB | HAOS; balloon desligado |
| 106 | nebula-sync (LXC) | 2/512 MB | **parado** desde 2026-10-20 |
| 107 | adguard-1 (LXC) | 2/768 MB | DNS primário 10.1.1.3 (AdGuard Home + adguardhome-sync) |
| 108 | adguard-2 (LXC) | 2/768 MB | DNS secundário 10.1.1.4 (AdGuard Home) |

## Verificações úteis (leitura)

`pveversion`, `qm list`, `pct list`, `pvesm status`, `lvs pve`, `journalctl --list-boots | tail`, `last -x | head`, `sensors`, `smartctl -H -A /dev/sda`, `apt list --upgradable`.

## Atualização (somente com aprovação, na janela)

1. `apt update && apt list --upgradable` → apresente a lista.
2. Com aprovação: `apt full-upgrade -y`. Se houver kernel novo, **pergunte** antes de reiniciar o host (derruba tudo).
3. Depois: conferir `qm list`/`pct list` e se o Home Assistant e o monitor voltaram.
