# PatchMon (2026-11-10)

Inventário de pacotes e atualizações de todos os hosts Linux, com agente em cada um. Roda em Docker
no mediacenter, porque o Proxmox não tem RAM para mais uma VM (7,6 GB no total, ~690 MB livres).

- `/opt/patchmon`: `docker-compose.yml` oficial (server, PostgreSQL 17, Redis 7, guacd), `.env`
  com os segredos (600, gerados com `openssl rand`) e `compose.local.yml` (cópia aqui).
  - A porta fica só em `127.0.0.1:3000`.
  - O volume `ssh_data` guarda os known_hosts do terminal web.
  - `COMPOSE_FILE` no `.env` junta os dois arquivos.
- `https://patchmon.rafaelmarconi.com.br`: nginx (`nginx-patchmon.conf`) com certificado DNS-01
  da Cloudflare. **Só a LAN** (`allow 10.1.0.0/16`); a internet recebe 403. O registro curinga público
  aponta para as WANs, mas da VLAN de servidores a volta pelo IP público não funciona, então os agentes
  precisam do rewrite `patchmon.rafaelmarconi.com.br → 10.1.1.100` no AdGuard.
- Cuidado: o servidor tem terminal SSH e RDP pelo navegador e pode **aplicar atualizações** nos hosts.
  Quem tem a conta admin manda em todos os hosts. Use 2FA.

```bash
cd /opt/patchmon && docker compose pull && docker compose up -d   # atualizar
```

## Agentes

Cadastro por token de auto-enrollment (Configurações → Integrações → Auto-Enrollment & API):
- `POST /api/v1/auto-enrollment/enroll` com `X-Auto-Enrollment-Key/Secret` para hosts comuns;
- `.../auto-enrollment/script?type=proxmox-lxc` no Proxmox para os LXCs.

| Host | Agente |
|---|---|
| pve (10.1.1.254), monitor, openclaw, mediacenter, adguard-1 | sim |
| homeassistant (HAOS) | não: sem gerenciador de pacotes |
| MacBook | não: o agente não tem versão para macOS |
| adguard-2 (108) | desligado em 2026-11-10 (`onboot 0`) |

## Configuração (2026-11-11)

Feita pela UI/API do PatchMon (sessão do admin). Estado no banco do PatchMon, não em arquivos.

### Grupos (um host pode estar em vários)

| Grupo | Hosts | Uso |
|---|---|---|
| Hosts físicos | pve, mediacenter | tipo |
| VMs | monitor, openclaw | tipo |
| Containers LXC | adguard-1 | tipo |
| Críticos | pve, adguard-1 | hypervisor + DNS; janela separada |
| Serviços | mediacenter, monitor, openclaw | aplicações |
| Docker | mediacenter, monitor | hosts com Docker |

### Políticas de patch

Política só define **quando** um patch run disparado/aprovado executa; nada é aplicado sozinho.

| Política | Grupo | Execução |
|---|---|---|
| Serviços - janela 04:00 | Serviços | 04:00 America/Sao_Paulo |
| Críticos - janela 05:00 | Críticos | 05:00 America/Sao_Paulo (depois dos serviços) |

### Relatórios agendados (destino: Internal Alerts)

- **Resumo semanal do homelab** — segunda 08:00, todas as seções, top 20.
- **Diário - segurança e pendências** — todo dia 07:30: pacotes de segurança, hosts por updates, alertas abertos, hosts offline (top 10).

### Alertas

- `host_down`: limiar 300 s (era 30 s; o pve sob carga gerava falsos alertas), lembrete a cada 12 h.
- `host_pending_updates_exceeded`: ligado, > 20 pacotes, checa a cada 60 min, lembrete 24 h.
- `host_security_updates_exceeded`: ligado, ≥ 1 update de segurança, checa a cada 60 min, lembrete 24 h.
- Event rule extra para Internal Alerts: updates excedidos, patch_run_failed/completed, reboot required, host_recovered.

### Agentes

- Atualização automática dos agentes: ligada (master + por host).
- Cache de pacotes: "refresh if stale" (60 min), para não rodar `apt update` a cada relatório no pve sobrecarregado.
- Intervalo de relatório: 1 h. `apt` sem retries (recomendação de segurança do PatchMon) mantido.

### Automações

Jobs internos do servidor com horários fixos (limpezas, checagem de versão, monitor de status a cada 5 min, etc.).
Todos com status Success em 2026-11-11; não há agendamento configurável além do intervalo dos agentes.

### Não configurado (decisão pendente)

- Destino externo (webhook/ntfy/e-mail): hoje relatórios e alertas só aparecem dentro do PatchMon.
- Compliance (OpenSCAP) continua sob demanda; varredura periódica pesaria no pve.
- Integração Docker nos agentes de mediacenter/monitor.
