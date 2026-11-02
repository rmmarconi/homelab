# MacBook Pro M3 — LLM local (2026-11-02)

MacBook Pro M3 (8 GB, 10 núcleos de GPU, macOS 26.4.1) dedicado a rodar um LLM pequeno para o
homelab. Wi-Fi em 10.1.0.76 (uso pessoal) e adaptador USB AX88179A (`en5`) em **10.1.1.30/24**, na
VLAN de servidores — a VLAN de servidores não alcança 10.1.0.0/24 (firewall do UniFi).

```
OpenClaw (10.1.1.20) ──HTTP + Bearer──▶ llama-server 10.1.1.30:8081 (Qwen3.5 4B Q4_K_M, Metal)
Prometheus (10.1.1.15) ─▶ :8081/metrics (job llama-server) · :9100 node_exporter (job node, instance macbook)
Grafana: Sistema → "MacBook LLM" (scripts/gen-macbook-llm-dashboard.py)
```

## Serviços (LaunchDaemons em /Library/LaunchDaemons, cópias aqui)

| Plist | O quê |
|---|---|
| `br.homelab.llama-server` | llama.cpp (Homebrew) como `rmmarconi`: `-ngl 99 -fa on -ctk/-ctv q8_0 -c 65536 -t 4 --parallel 1 --cache-reuse 256 --jinja --metrics`, raciocínio desligado (`enable_thinking: false`), chave em `~/.config/llm/api-key` (600) |
| `br.homelab.node-exporter` | node_exporter (Homebrew) como `nobody` em 10.1.1.30:9100, sem o coletor `thermal` (não funciona no M3) |
| `br.homelab.gpu-wired-limit` | `sysctl iogpu.wired_limit_mb=6144` no boot (padrão ~5,3 GB) |

```bash
sudo launchctl bootout system/br.homelab.llama-server
sudo launchctl bootstrap system /Library/LaunchDaemons/br.homelab.llama-server.plist
tail -f ~/Library/Logs/llm/llama-server.log
```

## Ajustes do macOS

- Docker Desktop parado e fora do login (`AutoStart: false`); só tinha um Caddy/FlareSolverr de teste
  antigo (`media.flamingosparadise`), sem uso. Contêineres preservados.
- App do Ollama parado (o modelo `llama3.1:8b` continua em `~/.ollama`).
- `pmset -a sleep 0 disksleep 0 powernap 0 autorestart 1 womp 1 lowpowermode 0 displaysleep 5` e
  `disablesleep 1` (funciona com a tampa fechada).
- Atualizações do macOS não instalam nem reiniciam sozinhas.
- `~/models` fora do Spotlight (`.metadata_never_index`) e do Time Machine.
- sudo sem senha: `/etc/sudoers.d/zz-rmmarconi` (o `zz` faz a regra vir depois da `%admin`, que pede senha).

## Desempenho medido (Qwen3.5 4B Q4_K_M, 2,7 GB)

| | |
|---|---|
| Geração | ~27 tokens/s |
| Leitura de prompt | ~180–220 tokens/s; 45,6 mil tokens em 209 s |
| Llama 3.1 8B Q4 (antes, no Ollama) | 15,9 tokens/s, 18% no CPU, swap a 5,9 GB |

## No OpenClaw

Provedor `macbook` (`openai-completions`, `apiKey: ${MACBOOK_LLM_API_KEY}` em `~/.openclaw/.env`),
modelo `macbook/qwen3.5-4b` (contexto 65 536, `reasoning: false`):

- `agents.defaults.utilityModel` — títulos, narração de progresso e resumos de atividade saem do Mac.
- `agents.defaults.model.fallbacks` — depois do DeepSeek. Os agentes têm `model` próprio (string), e
  nesse caso o OpenClaw não usa fallback; vale para o que usa o padrão (cron sem modelo etc.).
- No catálogo e no `modelPolicy.allow` de todos os agentes: `/model macbook/qwen3.5-4b` em qualquer sessão.

Não é o padrão dos agentes: eles mandam em média ~99 mil tokens por chamada (mediana 46 mil), o que
levaria minutos no Mac e passa do contexto de 64 mil.
