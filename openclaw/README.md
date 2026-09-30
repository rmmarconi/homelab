# OpenClaw — equipe de agentes do homelab

OpenClaw 2026.9.7 na VM 103 (10.1.1.20), modelo **DeepSeek** (v4-pro; v4-flash nas verificações).

| Agente | Área | Workspace |
|---|---|---|
| 🖥️ infra | Proxmox, VMs, LXCs, atualizações | `~/.openclaw/workspace/agents/infra` |
| 🌐 rede | UniFi, WANs, NetFlow, Pi-hole (só observa) | `…/agents/rede` |
| 📊 observabilidade | Prometheus/Grafana/Loki, relatório diário | `…/agents/observabilidade` |
| 🏠 casa | Home Assistant, ar-condicionado, solar | `…/agents/casa` |
| 🎬 midia | mediacenter | `…/agents/midia` |
| ✍️ blog | rafaelmarconi.com.br (só rascunhos) | `…/agents/blog` |

- `docs/` → `~/.openclaw/workspace/docs/homelab/` (base de conhecimento, sem segredos; `00-POLITICA.md` é obrigatório).
- `bin/` → `~/.openclaw/tools/homelab/bin/` (comandos `hl-*`: leitura com comandos fixos; `hl-blog-rascunho` cria rascunho).
- `exec-approvals.json` → `openclaw approvals set --file` : padrão `allowlist` + `ask: on-miss` + `askFallback: deny`.
  Só os `hl-*` e leituras básicas rodam sem aprovação; o resto pede aprovação no Telegram e é negado nas rotinas.
- `cron-jobs.tsv` → rotinas (`openclaw cron add --declaration-key …`), entrega no último chat do Telegram.
- `agents/*/AGENTS.md` → instruções de cada agente; `main-homelab.md` é anexado ao AGENTS.md do `main`.

## Acesso (feito pelo Rafael, uma vez)
- Chave `~/.ssh/openclaw_homelab` da VM openclaw autorizada no Proxmox (root), monitor, mediacenter
  (`from="10.1.1.20"`) e Hostinger.
- Token do Home Assistant em `~/.config/homelab/ha_token` (chmod 600).
- UniFi e Pi-hole: sem credenciais — dados vêm do Prometheus/Loki e de `pct exec` no Proxmox.
