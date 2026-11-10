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
