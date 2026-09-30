# 08 — Métricas do OpenClaw e dashboards no Grafana

Tudo o que é preciso para montar e manter o dashboard do OpenClaw **sem sudo, sem SSH e sem copiar segredos**.
A coleta já está pronta e roda sozinha (configurada em 2026-09-30).

## Como os dados chegam ao Prometheus

| Job (`job=`) | Alvo | O que traz | Persistência |
|---|---|---|---|
| `openclaw` | `10.1.1.20:18790/api/diagnostics/prometheus` | runtime do gateway (plugin diagnostics-prometheus): tokens, custo, chamadas ao modelo, execuções, ferramentas, entregas, fila, latência, memória do processo | **zera a cada restart do gateway** → sempre `increase()`/`rate()` |
| `node` com `instance="openclaw"` | `10.1.1.20:9100` | CPU, memória, disco, rede, load, systemd da VM + o arquivo `openclaw.prom` abaixo | contínuo |
| (dentro do job `node`) | textfile `/var/lib/prometheus/node-exporter/openclaw.prom` | inventário: agentes, rotinas, histórico de execuções, tokens por sessão | recalculado a cada 5 min a partir do estado persistente |

- O nginx da VM (porta 18790) injeta o token do gateway e só aceita o monitor 10.1.1.15. **Não existe e não deve existir token do gateway no Prometheus.**
- O gerador do inventário é `~/.local/bin/openclaw-inventory-exporter` (timer systemd de usuário `openclaw-inventory-exporter.timer`). Fonte: `homelab/openclaw/metrics/`.
- **Nunca** copie `~/.openclaw/openclaw.json` para outra máquina ou para `/tmp`: ele contém todos os segredos.

## Métricas de inventário (`instance="openclaw"`, job `node`)

| Métrica | Labels | Uso |
|---|---|---|
| `openclaw_agents` | — | quantidade de agentes |
| `openclaw_agent_info` | agent, agent_name, model | tabela de agentes e modelo de cada um |
| `openclaw_cron_jobs` / `openclaw_cron_jobs_enabled` | — | rotinas agendadas (total / habilitadas) |
| `openclaw_cron_job_enabled` | routine, job_id, agent | 1/0 por rotina |
| `openclaw_cron_job_last_status` | routine, job_id, agent, **status** (ok, error, skipped, never) | último resultado de cada rotina (valor sempre 1; filtre por `status`) |
| `openclaw_cron_job_consecutive_errors` | routine, job_id, agent | erros seguidos |
| `openclaw_cron_job_last_run_timestamp_seconds` / `..._next_run_...` | routine, job_id, agent | "há quanto tempo rodou" / "quando roda" (`time() - x`, unidade `dateTimeFromNow`) |
| `openclaw_cron_job_last_duration_seconds` | routine, job_id, agent | duração da última execução |
| `openclaw_cron_job_last_delivery` | routine, job_id, agent, delivery | entrega no Telegram (delivered, not-delivered, not-requested) |
| `openclaw_cron_runs_total` | routine, job_id, agent, **status** (ok, error, skipped) | **execuções com sucesso e com erro** (histórico completo) |
| `openclaw_cron_run_duration_seconds_total` | idem | tempo gasto em rotinas |
| `openclaw_cron_runs_window` | window (24h, 7d, 30d), agent, status | execuções por janela, já contadas (use em stats: não depende do histórico do Prometheus) |
| `openclaw_task_runs_total` | agent, task_kind, status (succeeded, failed…) | subagentes e tarefas em segundo plano |
| `openclaw_sessions` | agent, session_kind, provider, model | sessões existentes |
| `openclaw_session_tokens` | agent, session_kind, provider, model, token_type (input, output, total) | tokens acumulados por agente (sobrevive a restart) |
| `openclaw_sessions_active_1h` | — | sessões com atividade na última hora |
| `openclaw_inventory_exporter_success` / `_last_run_timestamp_seconds` | — | saúde da própria coleta |

O nome da rotina está no label **`routine`** (o label `job` é do Prometheus e vale `node`). Rotinas já apagadas aparecem com `routine` igual ao id.

`openclaw_cron_runs_total` é o total histórico: para períodos, prefira `openclaw_cron_runs_window`; `increase()` só funciona depois que a série acumular histórico (coleta iniciada em 2026-09-30).

## Métricas de runtime mais úteis (job `openclaw`)

- `openclaw_model_tokens_total{agent,channel,model,provider,token_type}` — token_type: input, output, cache_read, prompt, total.
- `openclaw_model_cost_usd_total{agent,channel,model,provider}` — custo estimado em US$.
- `openclaw_model_call_total{model,provider,outcome,error_category}` e `openclaw_model_call_duration_seconds_bucket`.
- `openclaw_run_completed_total{channel,trigger,outcome}`, `openclaw_harness_run_total{outcome,error_category}`, `openclaw_run_duration_seconds_bucket`.
- `openclaw_tool_execution_total{tool,outcome}`, `openclaw_tool_execution_duration_seconds_bucket`.
- `openclaw_message_delivery_total{channel,delivery_kind,outcome}`.
- `openclaw_memory_bytes{kind}` (rss, heap_used…), `openclaw_gateway_rpc_requests_total`, `openclaw_queue_lane_size`, `openclaw_session_queue_depth`.
- Lista completa e atual: `hl-grafana metrics openclaw_`.

## Consultas prontas

```promql
# agentes e rotinas
openclaw_agents
openclaw_cron_jobs_enabled
# execuções de rotinas: sucesso x erro no período do painel
sum by (status) (openclaw_cron_runs_window{window="7d"})
# histórico completo
sum by (status) (openclaw_cron_runs_total)
# rotinas com erro agora
openclaw_cron_job_last_status{status="error"}
# tokens por dia (runtime; barras diárias com intervalo 1d)
sum by (agent) (increase(openclaw_model_tokens_total{token_type="total"}[1d]))
# tokens totais acumulados por agente (persistente)
sum by (agent) (openclaw_session_tokens{token_type="total"})
# custo por dia
sum(increase(openclaw_model_cost_usd_total[1d]))
# CPU e memória da VM
100 * (1 - avg(rate(node_cpu_seconds_total{instance="openclaw",mode="idle"}[$__rate_interval])))
100 * (1 - node_memory_MemAvailable_bytes{instance="openclaw"} / node_memory_MemTotal_bytes{instance="openclaw"})
# memória do processo do gateway
openclaw_memory_bytes{kind="rss"}
# gateway no ar
up{job="openclaw"}
```

Para "tokens por dia" use painel de barras com `interval: 1d` e `increase(...[1d])`; em time series comum use `$__interval`.

## Ferramenta `hl-grafana` (liberada para o agente observabilidade)

```
~/.openclaw/tools/homelab/bin/hl-grafana list [texto]
~/.openclaw/tools/homelab/bin/hl-grafana get <uid> [saida.json]
~/.openclaw/tools/homelab/bin/hl-grafana validate <arquivo.json>
~/.openclaw/tools/homelab/bin/hl-grafana push <arquivo.json> [pasta]
~/.openclaw/tools/homelab/bin/hl-grafana metrics [prefixo]
```

- Conta de serviço **openclaw** no Grafana, papel Editor, token em `~/.config/homelab/grafana_token` (600). Não leia nem imprima o token; a ferramenta usa sozinha.
- Pasta padrão: **OpenClaw** (uid `openclaw`). O dashboard precisa de `uid` fixo (use `openclaw-overview`). O `push` sobrescreve e o Grafana guarda o histórico de versões.
- Fluxo: editar o JSON em `~/.openclaw/workspace/agents/observabilidade/dashboards/` → `validate` (0 erros) → `push` → conferir em http://10.1.1.15:3000/d/openclaw-overview.
- Datasource: Prometheus uid `prometheus`, Loki uid `loki`.

## Padrão visual dos dashboards do homelab

- Linhas (row) por assunto, na ordem: Visão geral (stats) → Execuções → Tokens e custo → Modelos/latência → Ferramentas e entregas → VM (CPU, memória, disco, rede) → Saúde da coleta.
- Stats no topo com cor por limiar (verde/amarelo/vermelho), unidades corretas (`short`, `percent`, `bytes`, `s`, `currencyUSD`, `dateTimeFromNow`).
- Tabelas para agentes e rotinas (última execução, próxima, status, erros seguidos), com value mappings (ok = verde, error = vermelho).
- Variáveis: `agent` (label_values(openclaw_agent_info, agent)), com "All".
- Títulos e descrições em português. Nada de segredo, IP público ou dado pessoal em painel.
