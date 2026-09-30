#!/usr/bin/env python3
"""Gera o dashboard "OpenClaw" (uid openclaw-overview).

Fontes (ver openclaw/docs/08-OPENCLAW-METRICAS.md):
  job="openclaw"                    runtime do gateway (zera no restart: sempre increase/rate)
  job="node", instance="openclaw"   VM + textfile de inventário (agentes, rotinas, execuções, tokens)

O dashboard é publicado pela API na pasta OpenClaw (não é provisionado por arquivo),
para que o agente observabilidade possa mantê-lo com `hl-grafana push`.

Uso: python3 scripts/gen-openclaw-dashboard.py   (a partir de monitoring/)
"""
import json
import os

P = {"type": "prometheus", "uid": "prometheus"}
RT = 'job="openclaw"'                      # runtime do gateway
INV = 'job="node",instance="openclaw"'     # inventário e VM
AG = 'agent=~"$agent"'
OUT = "grafana/dashboards/openclaw"

VERDE, AMARELO, VERMELHO, AZUL, ROXO, CINZA = "green", "#EAB839", "red", "#5794F2", "#B877D9", "text"


def t(expr, ref="A", **kw):
    return dict({"datasource": P, "expr": expr, "refId": ref}, **kw)


class Board:
    def __init__(self):
        self.y = 0
        self.panels = []

    def row(self, title):
        self.panels.append({"type": "row", "title": title, "collapsed": False, "panels": [],
                            "gridPos": {"h": 1, "w": 24, "x": 0, "y": self.y}})
        self.y += 1

    def add(self, *panels):
        h = 0
        for p in panels:
            p["gridPos"]["y"] = self.y
            self.panels.append(p)
            h = max(h, p["gridPos"]["h"])
        self.y += h


def thr(*steps):
    """thr(VERDE, (1, VERMELHO)) → degraus de limiar."""
    out = [{"color": steps[0], "value": None}]
    out += [{"color": c, "value": v} for v, c in steps[1:]]
    return out


def stat(title, expr, x, w, h=4, unit="short", color=AZUL, decimals=None, th=None, maps=None,
         noval="0", legend=None, text="value", desc=None, graph=False):
    fc = {"unit": unit, "noValue": noval, "color": {"mode": "fixed", "fixedColor": color}}
    if decimals is not None:
        fc["decimals"] = decimals
    if th:
        fc["thresholds"] = {"mode": "absolute", "steps": th}
        fc["color"] = {"mode": "thresholds"}
    if maps:
        fc["mappings"] = maps
    tg = t(expr, instant=not graph)
    if legend:
        tg["legendFormat"] = legend
    p = {"type": "stat", "title": title, "datasource": P, "targets": [tg],
         "gridPos": {"h": h, "w": w, "x": x, "y": 0}, "fieldConfig": {"defaults": fc, "overrides": []},
         "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "value",
                     "graphMode": "area" if graph else "none", "textMode": text,
                     "justifyMode": "center", "orientation": "auto", "wideLayout": True}}
    if desc:
        p["description"] = desc
    return p


def ts(title, targets, x, w, h=8, unit="short", stack=False, bars=False, interval=None,
       legend="table", calcs=("sum", "max"), desc=None, overrides=None, minv=None, maxv=None):
    custom = {"fillOpacity": 12, "lineWidth": 2, "showPoints": "never", "spanNulls": True}
    if stack:
        custom["stacking"] = {"mode": "normal"}
    if bars:
        custom.update({"drawStyle": "bars", "fillOpacity": 80, "lineWidth": 1})
    d = {"unit": unit, "custom": custom, "color": {"mode": "palette-classic"}}
    if minv is not None:
        d["min"] = minv
    if maxv is not None:
        d["max"] = maxv
    p = {"type": "timeseries", "title": title, "datasource": P, "targets": targets,
         "gridPos": {"h": h, "w": w, "x": x, "y": 0},
         "fieldConfig": {"defaults": d, "overrides": overrides or []},
         "options": {"legend": {"displayMode": legend, "placement": "bottom" if legend == "list" else "right",
                                "calcs": list(calcs) if legend == "table" else []},
                     "tooltip": {"mode": "multi", "sort": "desc"}}}
    if interval:
        p["interval"] = interval
    if desc:
        p["description"] = desc
    return p


def bargauge(title, expr, x, w, h, legend, unit="short", desc=None, color=None, decimals=None):
    d = {"unit": unit, "color": {"mode": "continuous-BlPu"} if not color else {"mode": "fixed", "fixedColor": color},
         "min": 0}
    if decimals is not None:
        d["decimals"] = decimals
    p = {"type": "bargauge", "title": title, "datasource": P,
         "gridPos": {"h": h, "w": w, "x": x, "y": 0},
         "targets": [t(expr, instant=True, legendFormat=legend)],
         "fieldConfig": {"defaults": d, "overrides": []},
         "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True,
                     "valueMode": "color", "namePlacement": "left", "sizing": "auto",
                     "reduceOptions": {"calcs": ["lastNotNull"]}}}
    if desc:
        p["description"] = desc
    return p


def pie(title, expr, x, w, h, legend, unit="short"):
    return {"type": "piechart", "title": title, "datasource": P,
            "gridPos": {"h": h, "w": w, "x": x, "y": 0},
            "targets": [t(expr, instant=True, legendFormat=legend)],
            "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": "palette-classic"}}, "overrides": []},
            "options": {"pieType": "donut", "legend": {"displayMode": "table", "placement": "right",
                                                       "values": ["value", "percent"]},
                        "reduceOptions": {"calcs": ["lastNotNull"]}, "tooltip": {"mode": "single"}}}


def col(name, unit=None, width=None, cell=None, maps=None, th=None, decimals=None):
    props = []
    if unit:
        props.append({"id": "unit", "value": unit})
    if width:
        props.append({"id": "custom.width", "value": width})
    if cell:
        props.append({"id": "custom.cellOptions", "value": {"type": cell}})
    if maps:
        props.append({"id": "mappings", "value": maps})
    if th:
        props += [{"id": "thresholds", "value": {"mode": "absolute", "steps": th}},
                  {"id": "color", "value": {"mode": "thresholds"}}]
    if decimals is not None:
        props.append({"id": "decimals", "value": decimals})
    return {"matcher": {"id": "byName", "options": name}, "properties": props}


def vmap(pairs):
    """{"ok": ("Sucesso", VERDE)} → value mappings."""
    return [{"type": "value", "options": {k: {"text": v[0], "color": v[1], "index": i}
                                          for i, (k, v) in enumerate(pairs.items())}}]


STATUS = vmap({"ok": ("✔ sucesso", VERDE), "error": ("✖ erro", VERMELHO), "skipped": ("⏭ pulada", AMARELO),
               "never": ("— nunca rodou", CINZA), "succeeded": ("✔ sucesso", VERDE), "failed": ("✖ falhou", VERMELHO)})
ENTREGA = vmap({"delivered": ("entregue", VERDE), "not-delivered": ("não entregue", VERMELHO),
                "not-requested": ("sem entrega", CINZA), "none": ("—", CINZA), "unknown": ("?", AMARELO)})
UPDOWN = [{"type": "value", "options": {"0": {"text": "FORA", "color": VERMELHO}, "1": {"text": "NO AR", "color": VERDE}}}]


def tabela_rotinas(x, w, h):
    base = f'{INV},{AG}'
    q = [
        t(f'openclaw_cron_job_last_status{{{base}}}', "A", instant=True, format="table"),
        t(f'(time() - openclaw_cron_job_last_run_timestamp_seconds{{{base}}}) ', "B", instant=True, format="table"),
        t(f'openclaw_cron_job_next_run_timestamp_seconds{{{base}}} * 1000', "C", instant=True, format="table"),
        t(f'openclaw_cron_job_last_duration_seconds{{{base}}}', "D", instant=True, format="table"),
        t(f'openclaw_cron_job_consecutive_errors{{{base}}}', "E", instant=True, format="table"),
        t(f'sum by (routine, job_id, agent) (openclaw_cron_runs_total{{{base}}})', "F", instant=True, format="table"),
        t(f'openclaw_cron_job_last_delivery{{{base}}}', "G", instant=True, format="table"),
        t(f'openclaw_cron_job_enabled{{{base}}}', "H", instant=True, format="table"),
    ]
    return {"type": "table", "title": "Rotinas agendadas", "datasource": P,
            "description": "Uma linha por rotina do cron do OpenClaw. 'Há' = tempo desde a última execução.",
            "gridPos": {"h": h, "w": w, "x": x, "y": 0}, "targets": q,
            "transformations": [
                {"id": "merge", "options": {}},
                {"id": "organize", "options": {
                    "excludeByName": {"Time": True, "__name__": True, "instance": True, "job": True, "job_id": True,
                                      "Value #A": True, "Value #G": True},
                    "indexByName": {"routine": 0, "agent": 1, "Value #H": 2, "status": 3, "Value #B": 4, "Value #D": 5,
                                    "Value #C": 6, "Value #E": 7, "Value #F": 8, "delivery": 9},
                    "renameByName": {"routine": "Rotina", "agent": "Agente", "status": "Último resultado",
                                     "Value #B": "Última execução (há)", "Value #C": "Próxima execução",
                                     "Value #D": "Duração", "Value #E": "Erros seguidos", "Value #F": "Execuções",
                                     "delivery": "Entrega", "Value #H": "Ativa"}}},
                {"id": "sortBy", "options": {"sort": [{"field": "Próxima execução"}]}},
            ],
            "fieldConfig": {"defaults": {"noValue": "—", "custom": {"align": "auto", "filterable": True}},
                            "overrides": [
                                col("Rotina", width=260), col("Agente", width=130),
                                col("Último resultado", cell="color-text", maps=STATUS, width=140),
                                col("Última execução (há)", unit="s", decimals=0, width=150),
                                col("Próxima execução", unit="dateTimeFromNow", width=150),
                                col("Duração", unit="s", decimals=1, width=90),
                                col("Erros seguidos", cell="color-background", th=thr(VERDE, (1, AMARELO), (3, VERMELHO)), width=110),
                                col("Execuções", width=90),
                                col("Entrega", cell="color-text", maps=ENTREGA, width=120),
                                col("Ativa", cell="color-text", width=70,
                                    maps=[{"type": "value", "options": {"1": {"text": "sim", "color": VERDE},
                                                                        "0": {"text": "não", "color": CINZA}}}]),
                            ]},
            "options": {"cellHeight": "sm", "showHeader": True, "footer": {"show": False}}}


def tabela_agentes(x, w, h):
    q = [
        t(f'openclaw_agent_info{{{INV},{AG}}}', "A", instant=True, format="table"),
        t(f'sum by (agent) (openclaw_session_tokens{{{INV},{AG},token_type="total"}})', "B", instant=True, format="table"),
        t(f'sum by (agent) (openclaw_sessions{{{INV},{AG}}})', "C", instant=True, format="table"),
        t(f'sum by (agent) (openclaw_cron_job_enabled{{{INV},{AG}}})', "D", instant=True, format="table"),
        t(f'sum by (agent) (openclaw_cron_runs_window{{{INV},{AG},window="7d",status="error"}})', "E", instant=True, format="table"),
        t(f'sum by (agent) (increase(openclaw_model_cost_usd_total{{{RT},{AG}}}[$__range]))', "F", instant=True, format="table"),
    ]
    return {"type": "table", "title": "Agentes", "datasource": P,
            "description": "Tokens acumulados vêm das sessões existentes (persistem entre restarts). Custo = período selecionado.",
            "gridPos": {"h": h, "w": w, "x": x, "y": 0}, "targets": q,
            "transformations": [
                {"id": "merge", "options": {}},
                {"id": "organize", "options": {
                    "excludeByName": {"Time": True, "__name__": True, "instance": True, "job": True, "Value #A": True},
                    "indexByName": {"agent": 0, "agent_name": 1, "model": 2, "Value #B": 3, "Value #C": 4,
                                    "Value #D": 5, "Value #E": 6, "Value #F": 7},
                    "renameByName": {"agent": "Agente", "agent_name": "Nome", "model": "Modelo",
                                     "Value #B": "Tokens (acumulado)", "Value #C": "Sessões", "Value #D": "Rotinas",
                                     "Value #E": "Erros de rotina (7d)", "Value #F": "Custo no período"}}},
                {"id": "sortBy", "options": {"sort": [{"field": "Tokens (acumulado)", "desc": True}]}},
            ],
            "fieldConfig": {"defaults": {"noValue": "0", "custom": {"align": "auto"}},
                            "overrides": [
                                col("Tokens (acumulado)", unit="short", cell="gauge"),
                                col("Erros de rotina (7d)", cell="color-background", th=thr(VERDE, (1, VERMELHO))),
                                col("Custo no período", unit="currencyUSD", decimals=3),
                            ]},
            "options": {"cellHeight": "sm", "showHeader": True}}


def openclaw():
    b = Board()

    # ── Visão geral ────────────────────────────────────────────────────────────
    b.row("Visão geral")
    b.add(
        stat("Gateway", f'max(up{{{RT}}})', 0, 3, maps=UPDOWN, th=thr(VERMELHO, (1, VERDE)), noval="FORA",
             desc="Prometheus consegue ler as métricas do gateway (nginx :18790 → 127.0.0.1:18789)."),
        stat("Versão", f'max by (build_id) (openclaw_gateway_build_info{{{RT}}})', 3, 4, legend="{{build_id}}",
             text="name", color=CINZA, noval="?"),
        stat("Agentes", f'max(openclaw_agents{{{INV}}})', 7, 2, color=AZUL),
        stat("Rotinas ativas", f'max(openclaw_cron_jobs_enabled{{{INV}}})', 9, 2, color=AZUL),
        stat("Rotinas com erro", f'count(openclaw_cron_job_last_status{{{INV},{AG},status="error"}}) or vector(0)', 11, 3,
             th=thr(VERDE, (1, VERMELHO)), desc="Rotinas cuja última execução terminou em erro."),
        stat("Execuções 24h ✔", f'sum(openclaw_cron_runs_window{{{INV},{AG},window="24h",status="ok"}}) or vector(0)', 14, 2,
             color=VERDE),
        stat("Execuções 24h ✖", f'sum(openclaw_cron_runs_window{{{INV},{AG},window="24h",status="error"}}) or vector(0)', 16, 2,
             th=thr(VERDE, (1, VERMELHO))),
        stat("Sessões ativas (1h)", f'max(openclaw_sessions_active_1h{{{INV}}})', 18, 2, color=ROXO),
        stat("CPU da VM", f'100 * (1 - avg(rate(node_cpu_seconds_total{{{INV},mode="idle"}}[5m])))', 20, 2,
             unit="percent", decimals=0, th=thr(VERDE, (70, AMARELO), (90, VERMELHO))),
        stat("Memória da VM", f'100 * (1 - node_memory_MemAvailable_bytes{{{INV}}} / node_memory_MemTotal_bytes{{{INV}}})',
             22, 2, unit="percent", decimals=0, th=thr(VERDE, (80, AMARELO), (92, VERMELHO))),
    )
    b.add(
        stat("Tokens no período", f'sum(increase(openclaw_model_tokens_total{{{RT},{AG},token_type="total"}}[$__range]))',
             0, 4, h=5, unit="short", decimals=1, color=AZUL, graph=False,
             desc="Tokens consumidos no intervalo selecionado (entrada + saída + cache)."),
        stat("Tokens hoje", f'sum(increase(openclaw_model_tokens_total{{{RT},{AG},token_type="total"}}[1d]))',
             4, 4, h=5, decimals=1, color=AZUL, desc="Últimas 24 horas."),
        stat("Tokens acumulados", f'sum(openclaw_session_tokens{{{INV},{AG},token_type="total"}})', 8, 4, h=5,
             decimals=2, color=ROXO, desc="Soma das sessões existentes (não zera com restart do gateway)."),
        stat("Custo no período", f'sum(increase(openclaw_model_cost_usd_total{{{RT},{AG}}}[$__range]))', 12, 4, h=5,
             unit="currencyUSD", decimals=2, color=AMARELO, desc="Estimativa do OpenClaw pela tabela de preços do provedor."),
        stat("Custo hoje", f'sum(increase(openclaw_model_cost_usd_total{{{RT},{AG}}}[1d]))', 16, 4, h=5,
             unit="currencyUSD", decimals=2, color=AMARELO),
        stat("Chamadas ao modelo com erro", f'sum(increase(openclaw_model_call_total{{{RT},outcome="error"}}[$__range])) or vector(0)',
             20, 4, h=5, th=thr(VERDE, (1, AMARELO), (5, VERMELHO)),
             desc="Inclui saldo esgotado, limite de taxa e falhas de rede."),
    )

    # ── Tokens e custo ────────────────────────────────────────────────────────
    b.row("Tokens e custo")
    b.add(
        ts("Tokens por dia, por agente",
           [t(f'sum by (agent) (increase(openclaw_model_tokens_total{{{RT},{AG},token_type="total"}}[1d]))', legendFormat="{{agent}}")],
           0, 12, h=9, bars=True, stack=True, interval="1d", calcs=("sum", "mean"),
           desc="Barras diárias. Os contadores do gateway começaram em 2026-09-30."),
        ts("Custo por dia (US$)",
           [t(f'sum by (agent) (increase(openclaw_model_cost_usd_total{{{RT},{AG}}}[1d]))', legendFormat="{{agent}}")],
           12, 12, h=9, unit="currencyUSD", bars=True, stack=True, interval="1d", calcs=("sum", "mean")),
    )
    b.add(
        ts("Consumo de tokens por tipo",
           [t(f'sum by (token_type) (rate(openclaw_model_tokens_total{{{RT},{AG},token_type=~"input|output|cache_read"}}[$__rate_interval])) * 60',
              legendFormat="{{token_type}}")],
           0, 12, unit="short", stack=True, desc="Tokens por minuto. cache_read = reaproveitado do cache (mais barato).",
           overrides=[{"matcher": {"id": "byName", "options": "output"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": ROXO}}]},
                      {"matcher": {"id": "byName", "options": "input"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": AZUL}}]},
                      {"matcher": {"id": "byName", "options": "cache_read"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": VERDE}}]}]),
        bargauge("Tokens no período por agente",
                 f'sort_desc(sum by (agent) (increase(openclaw_model_tokens_total{{{RT},{AG},token_type="total"}}[$__range])))',
                 12, 6, 8, "{{agent}}"),
        bargauge("Tokens acumulados por agente",
                 f'sort_desc(sum by (agent) (openclaw_session_tokens{{{INV},{AG},token_type="total"}}))',
                 18, 6, 8, "{{agent}}", desc="Sessões existentes, desde o início de cada sessão."),
    )
    b.add(
        pie("Tokens por modelo (período)",
            f'sum by (model) (increase(openclaw_model_tokens_total{{{RT},{AG},token_type="total"}}[$__range]))', 0, 8, 8, "{{model}}"),
        pie("Tokens por canal (período)",
            f'sum by (channel) (increase(openclaw_model_tokens_total{{{RT},{AG},token_type="total"}}[$__range]))', 8, 8, 8, "{{channel}}"),
        stat("Aproveitamento de cache",
             f'sum(increase(openclaw_model_tokens_total{{{RT},{AG},token_type="cache_read"}}[$__range])) / '
             f'sum(increase(openclaw_model_tokens_total{{{RT},{AG},token_type="prompt"}}[$__range])) * 100',
             16, 4, h=8, unit="percent", decimals=0, th=thr(VERMELHO, (30, AMARELO), (60, VERDE)), noval="—",
             desc="Parte do prompt servida pelo cache do provedor. Quanto maior, menor o custo."),
        stat("Custo médio por 1M tokens",
             f'sum(increase(openclaw_model_cost_usd_total{{{RT},{AG}}}[$__range])) / '
             f'(sum(increase(openclaw_model_tokens_total{{{RT},{AG},token_type="total"}}[$__range])) / 1e6)',
             20, 4, h=8, unit="currencyUSD", decimals=3, color=AMARELO, noval="—"),
    )

    b.add(
        ts("Tokens por requisição (p50 / p95)",
           [t(f'histogram_quantile(0.5, sum by (le) (rate(openclaw_gen_ai_client_token_usage_bucket{{{RT}}}[$__rate_interval])))', "A", legendFormat="p50"),
            t(f'histogram_quantile(0.95, sum by (le) (rate(openclaw_gen_ai_client_token_usage_bucket{{{RT}}}[$__rate_interval])))', "B", legendFormat="p95")],
           0, 24, h=7, calcs=("mean", "max"),
           desc="Tamanho típico de cada chamada ao modelo. Prompts muito grandes encarecem e deixam o agente lento."),
    )

    # ── Rotinas e execuções ───────────────────────────────────────────────────
    b.row("Rotinas e execuções")
    b.add(
        bargauge("Execuções de rotinas: últimas 24 h", f'sum by (status) (openclaw_cron_runs_window{{{INV},{AG},window="24h"}})',
                 0, 8, 6, "{{status}}"),
        bargauge("Execuções de rotinas: últimos 7 dias", f'sum by (status) (openclaw_cron_runs_window{{{INV},{AG},window="7d"}})',
                 8, 8, 6, "{{status}}"),
        bargauge("Execuções de rotinas: últimos 30 dias", f'sum by (status) (openclaw_cron_runs_window{{{INV},{AG},window="30d"}})',
                 16, 8, 6, "{{status}}"),
    )
    for p in b.panels[-3:]:
        p["fieldConfig"]["overrides"] = [
            {"matcher": {"id": "byName", "options": n}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": c}}]}
            for n, c in (("ok", VERDE), ("error", VERMELHO), ("skipped", AMARELO))]
        p["fieldConfig"]["defaults"]["mappings"] = []
        p["options"]["displayMode"] = "basic"
    b.add(tabela_rotinas(0, 24, 11))
    b.add(
        ts("Execuções de rotinas por hora",
           [t(f'sum by (status) (increase(openclaw_cron_runs_total{{{INV},{AG}}}[1h]))', legendFormat="{{status}}")],
           0, 8, bars=True, stack=True, interval="1h",
           overrides=[{"matcher": {"id": "byName", "options": n}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": c}}]}
                      for n, c in (("ok", VERDE), ("error", VERMELHO), ("skipped", AMARELO))]),
        ts("Execuções de agentes (turnos)",
           [t(f'sum by (outcome, channel) (increase(openclaw_run_completed_total{{{RT}}}[$__rate_interval]))',
              legendFormat="{{channel}} · {{outcome}}")],
           8, 8, bars=True, stack=True, desc="Cada resposta completa de um agente, por canal (telegram, webchat, cron…)."),
        ts("Subagentes e tarefas em segundo plano",
           [t(f'sum by (status) (openclaw_task_runs_total{{{INV},{AG}}})', legendFormat="{{status}}")],
           16, 8, calcs=("lastNotNull",), desc="Total acumulado por status."),
    )
    b.add(
        stat("Taxa de sucesso dos turnos",
             f'100 * sum(increase(openclaw_run_completed_total{{{RT},outcome="completed"}}[$__range])) / '
             f'clamp_min(sum(increase(openclaw_run_completed_total{{{RT}}}[$__range])), 1)',
             0, 4, h=8, unit="percent", decimals=1, th=thr(VERMELHO, (80, AMARELO), (95, VERDE)), noval="—",
             desc="Turnos de agente concluídos sem erro no período (ideia do painel do agente observabilidade)."),
        ts("Turnos por gatilho",
           [t(f'sum by (trigger) (increase(openclaw_run_completed_total{{{RT}}}[$__rate_interval]))', legendFormat="{{trigger}}")],
           4, 10, bars=True, stack=True, desc="user = mensagem do Rafael; cron = rotina; heartbeat, subagent…"),
        ts("Harness por desfecho",
           [t(f'sum by (outcome, error_category) (increase(openclaw_harness_run_total{{{RT}}}[$__rate_interval]))',
              legendFormat="{{outcome}} · {{error_category}}")],
           14, 10, bars=True, stack=True),
    )
    b.add(
        ts("Duração das execuções (p50 / p95)",
           [t(f'histogram_quantile(0.5, sum by (le) (rate(openclaw_run_duration_seconds_bucket{{{RT}}}[$__rate_interval])))', "A", legendFormat="p50"),
            t(f'histogram_quantile(0.95, sum by (le) (rate(openclaw_run_duration_seconds_bucket{{{RT}}}[$__rate_interval])))', "B", legendFormat="p95")],
           0, 12, unit="s", calcs=("mean", "max")),
        ts("Tempo gasto em rotinas por agente",
           [t(f'sum by (agent) (increase(openclaw_cron_run_duration_seconds_total{{{INV},{AG}}}[1h]))', legendFormat="{{agent}}")],
           12, 12, unit="s", bars=True, stack=True, interval="1h"),
    )

    # ── Agentes ──────────────────────────────────────────────────────────────
    b.row("Agentes")
    b.add(tabela_agentes(0, 24, 10))

    # ── Modelo (DeepSeek) ─────────────────────────────────────────────────────
    b.row("Modelo e provedor")
    b.add(
        ts("Chamadas ao modelo",
           [t(f'sum by (model, outcome) (increase(openclaw_model_call_total{{{RT}}}[$__rate_interval]))',
              legendFormat="{{model}} · {{outcome}}")], 0, 8, bars=True, stack=True),
        ts("Latência do modelo (p50 / p95)",
           [t(f'histogram_quantile(0.5, sum by (le) (rate(openclaw_model_call_duration_seconds_bucket{{{RT}}}[$__rate_interval])))', "A", legendFormat="p50"),
            t(f'histogram_quantile(0.95, sum by (le) (rate(openclaw_model_call_duration_seconds_bucket{{{RT}}}[$__rate_interval])))', "B", legendFormat="p95")],
           8, 8, unit="s", calcs=("mean", "max")),
        bargauge("Erros do modelo por categoria (período)",
                 f'sort_desc(sum by (error_category) (increase(openclaw_model_call_total{{{RT},outcome="error"}}[$__range])))',
                 16, 8, 8, "{{error_category}}", color=VERMELHO,
                 desc="Billing = saldo esgotado na DeepSeek (o OpenClaw suspende a chave por alguns minutos)."),
    )

    # ── Ferramentas e mensagens ───────────────────────────────────────────────
    b.row("Ferramentas e mensagens")
    b.add(
        bargauge("Ferramentas mais usadas (período)",
                 f'topk(12, sum by (tool) (increase(openclaw_tool_execution_total{{{RT}}}[$__range])))', 0, 8, 9, "{{tool}}"),
        ts("Execução de ferramentas",
           [t(f'sum by (outcome) (increase(openclaw_tool_execution_total{{{RT}}}[$__rate_interval]))', legendFormat="{{outcome}}")],
           8, 8, h=9, bars=True, stack=True),
        ts("Mensagens entregues",
           [t(f'sum by (channel, outcome) (increase(openclaw_message_delivery_total{{{RT}}}[$__rate_interval]))',
              legendFormat="{{channel}} · {{outcome}}"),
            t(f'sum by (channel) (increase(openclaw_message_received_total{{{RT}}}[$__rate_interval]))', "B",
              legendFormat="recebidas · {{channel}}")],
           16, 8, h=9, bars=True),
    )

    # ── Gateway (processo) ────────────────────────────────────────────────────
    b.row("Gateway (processo Node.js)")
    b.add(
        ts("Memória do gateway",
           [t(f'max by (kind) (openclaw_memory_bytes{{{RT},kind=~"rss|heap_used|heap_total|external"}})', legendFormat="{{kind}}")],
           0, 8, unit="bytes", calcs=("lastNotNull", "max")),
        ts("Atraso do event loop (p99)",
           [t(f'histogram_quantile(0.99, sum by (le) (rate(openclaw_gateway_event_loop_delay_max_seconds_bucket{{{RT}}}[$__rate_interval])))',
              legendFormat="p99")], 8, 8, unit="s", calcs=("mean", "max"),
           desc="Acima de ~200 ms o gateway começa a responder devagar."),
        ts("Filas",
           [t(f'max by (lane) (openclaw_queue_lane_size{{{RT}}})', "A", legendFormat="fila {{lane}}"),
            t(f'max by (state) (openclaw_session_queue_depth{{{RT}}})', "B", legendFormat="sessões {{state}}")],
           16, 8, calcs=("lastNotNull", "max")),
    )
    b.add(
        ts("Requisições RPC por segundo",
           [t(f'topk(8, sum by (method) (rate(openclaw_gateway_rpc_requests_total{{{RT}}}[$__rate_interval])))', legendFormat="{{method}}")],
           0, 12, unit="reqps", stack=True),
        ts("Pressão de memória e workers",
           [t(f'sum by (reason) (increase(openclaw_memory_pressure_total{{{RT}}}[$__rate_interval]))', "A", legendFormat="pressão · {{reason}}"),
            t(f'max(openclaw_worker_count{{{RT}}})', "B", legendFormat="workers")],
           12, 12, calcs=("lastNotNull", "max"),
           desc="O OpenClaw avisa quando o RSS passa do limite. A VM tem 4 GB."),
    )

    b.add(
        ts("Coleta de lixo (GC p99)",
           [t(f'histogram_quantile(0.99, sum by (le) (rate(openclaw_gc_duration_seconds_bucket{{{RT}}}[$__rate_interval])))', legendFormat="p99")],
           0, 8, h=7, unit="s", calcs=("mean", "max")),
        ts("Resultado das RPCs",
           [t(f'sum by (phase, outcome) (increase(openclaw_gateway_rpc_outcomes_total{{{RT}}}[$__rate_interval]))',
              legendFormat="{{phase}} · {{outcome}}")], 8, 10, h=7, bars=True, stack=True),
        stat("Payloads grandes", f'sum(increase(openclaw_payload_large_total{{{RT}}}[$__range])) or vector(0)', 18, 3, h=7,
             th=thr(VERDE, (1, AMARELO)), desc="Mensagens ou respostas acima do limite de tamanho no período."),
        stat("Failovers / alertas", f'(sum(increase(openclaw_model_failover_total{{{RT}}}[$__range])) or vector(0)) + '
             f'(sum(increase(openclaw_liveness_warning_total{{{RT}}}[$__range])) or vector(0))', 21, 3, h=7,
             th=thr(VERDE, (1, AMARELO), (5, VERMELHO)),
             desc="Trocas de modelo por falha + alertas de liveness. Os contadores só aparecem quando acontecem."),
    )

    # ── VM openclaw ──────────────────────────────────────────────────────────
    b.row("VM openclaw (10.1.1.20)")
    b.add(
        ts("CPU",
           [t(f'100 * sum by (mode) (rate(node_cpu_seconds_total{{{INV},mode!~"idle|steal"}}[$__rate_interval])) / scalar(count(node_cpu_seconds_total{{{INV},mode="idle"}}))',
              legendFormat="{{mode}}")], 0, 8, unit="percent", stack=True, minv=0, maxv=100, calcs=("mean", "max")),
        ts("Memória",
           [t(f'node_memory_MemTotal_bytes{{{INV}}} - node_memory_MemAvailable_bytes{{{INV}}}', "A", legendFormat="usada"),
            t(f'node_memory_Cached_bytes{{{INV}}} + node_memory_Buffers_bytes{{{INV}}}', "B", legendFormat="cache"),
            t(f'node_memory_SwapTotal_bytes{{{INV}}} - node_memory_SwapFree_bytes{{{INV}}}', "C", legendFormat="swap usada"),
            t(f'node_memory_MemTotal_bytes{{{INV}}}', "D", legendFormat="total")],
           8, 8, unit="bytes", calcs=("lastNotNull", "max"),
           overrides=[{"matcher": {"id": "byName", "options": "total"},
                       "properties": [{"id": "custom.fillOpacity", "value": 0},
                                      {"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [10, 10]}},
                                      {"id": "color", "value": {"mode": "fixed", "fixedColor": CINZA}}]}]),
        ts("Carga e pressão",
           [t(f'node_load1{{{INV}}}', "A", legendFormat="load 1m"),
            t(f'node_load5{{{INV}}}', "B", legendFormat="load 5m"),
            t(f'rate(node_pressure_memory_waiting_seconds_total{{{INV}}}[$__rate_interval]) * 100', "C", legendFormat="PSI memória %"),
            t(f'rate(node_pressure_cpu_waiting_seconds_total{{{INV}}}[$__rate_interval]) * 100', "D", legendFormat="PSI CPU %")],
           16, 8, calcs=("mean", "max")),
    )
    b.add(
        stat("Disco /", f'100 * (1 - node_filesystem_avail_bytes{{{INV},mountpoint="/"}} / node_filesystem_size_bytes{{{INV},mountpoint="/"}})',
             0, 4, h=7, unit="percent", decimals=0, th=thr(VERDE, (75, AMARELO), (90, VERMELHO))),
        stat("Livre em /", f'node_filesystem_avail_bytes{{{INV},mountpoint="/"}}', 4, 4, h=7, unit="bytes", decimals=1, color=AZUL),
        stat("No ar há", f'time() - node_boot_time_seconds{{{INV}}}', 8, 4, h=7, unit="s", decimals=0, color=CINZA),
        ts("Rede", [t(f'sum(rate(node_network_receive_bytes_total{{{INV},device!~"lo|docker.*|veth.*"}}[$__rate_interval])) * 8', "A", legendFormat="entrada"),
                    t(f'-sum(rate(node_network_transmit_bytes_total{{{INV},device!~"lo|docker.*|veth.*"}}[$__rate_interval])) * 8', "B", legendFormat="saída")],
           12, 6, h=7, unit="bps", legend="list"),
        ts("Disco (E/S)", [t(f'sum(rate(node_disk_read_bytes_total{{{INV}}}[$__rate_interval]))', "A", legendFormat="leitura"),
                           t(f'-sum(rate(node_disk_written_bytes_total{{{INV}}}[$__rate_interval]))', "B", legendFormat="escrita")],
           18, 6, h=7, unit="Bps", legend="list"),
    )

    # ── Saúde da coleta ───────────────────────────────────────────────────────
    b.row("Saúde da coleta")
    b.add(
        stat("Métricas do gateway", f'max(up{{{RT}}})', 0, 4, maps=UPDOWN, th=thr(VERMELHO, (1, VERDE)), noval="FORA"),
        stat("node-exporter da VM", f'max(up{{{INV}}})', 4, 4, maps=UPDOWN, th=thr(VERMELHO, (1, VERDE)), noval="FORA"),
        stat("Inventário", f'max(openclaw_inventory_exporter_success{{{INV}}})', 8, 4,
             maps=[{"type": "value", "options": {"0": {"text": "COM FALHA", "color": VERMELHO}, "1": {"text": "OK", "color": VERDE}}}],
             th=thr(VERMELHO, (1, VERDE)), noval="sem dados", desc="Timer openclaw-inventory-exporter (a cada 5 min)."),
        stat("Última coleta do inventário (há)", f'time() - max(openclaw_inventory_exporter_last_run_timestamp_seconds{{{INV}}})',
             12, 4, unit="s", decimals=0, th=thr(VERDE, (600, AMARELO), (1800, VERMELHO))),
        stat("Duração da coleta", f'max(openclaw_inventory_exporter_duration_seconds{{{INV}}})', 16, 4, unit="s", decimals=1, color=CINZA),
        stat("Séries do gateway", f'max(scrape_samples_scraped{{{RT}}})', 20, 4, color=CINZA),
    )

    return {
        "uid": "openclaw-overview",
        "title": "OpenClaw",
        "description": "Agentes, rotinas, execuções, tokens, custo, modelo, gateway e VM do OpenClaw (10.1.1.20).",
        "tags": ["openclaw", "ia", "homelab"],
        "timezone": "browser",
        "refresh": "1m",
        "time": {"from": "now-7d", "to": "now"},
        "schemaVersion": 39,
        "graphTooltip": 1,
        "editable": True,
        "templating": {"list": [{
            "name": "agent", "label": "Agente", "type": "query", "datasource": P,
            "query": {"query": f"label_values(openclaw_agent_info{{{INV}}}, agent)", "refId": "agent"},
            "definition": f"label_values(openclaw_agent_info{{{INV}}}, agent)",
            "includeAll": True, "multi": True, "allValue": ".*", "refresh": 2, "sort": 1,
            "current": {"text": ["All"], "value": ["$__all"]}}]},
        "annotations": {"list": [{
            "name": "Restart do gateway", "datasource": P, "enable": True, "iconColor": AMARELO,
            "expr": f'changes(openclaw_gateway_build_info{{{RT}}}[2m]) > 0 or resets(openclaw_model_call_total{{{RT}}}[2m]) > 0',
            "step": "2m", "titleFormat": "Gateway reiniciado", "textFormat": "contadores de runtime zerados"}]},
        "links": [{"title": "Proxmox", "type": "dashboards", "tags": ["proxmox"], "asDropdown": False}],
        "panels": b.panels,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    d = openclaw()
    with open(f"{OUT}/openclaw.json", "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    print(f"{OUT}/openclaw.json: {sum(1 for p in d['panels'] if p['type'] != 'row')} painéis")


if __name__ == "__main__":
    main()
