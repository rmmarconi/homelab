#!/usr/bin/env python3
"""Gera o dashboard "MacBook LLM" (uid macbook-llm) — LLM local no MacBook Pro M3 (8 GB).

O MacBook (10.1.1.30, adaptador USB na VLAN de servidores) roda o llama-server com o
Qwen3.5 4B, usado pelo OpenClaw como utilityModel e fallback (provedor "macbook").

Fontes (Prometheus):
  job llama-server: métricas llamacpp:* do llama-server (chave em secrets/macbook_llm_key)
  job node, instance macbook: node_exporter do Homebrew (sem o coletor thermal)

Uso: python3 scripts/gen-macbook-llm-dashboard.py   (a partir de monitoring/)
"""
import json
import os

P = {"type": "prometheus", "uid": "prometheus"}
OUT = "grafana/dashboards/sistema"
LL = '{job="llama-server"}'
MB = '{instance="macbook"}'
AZUL, VERDE, ROXO, AMARELO, VERMELHO = "#5794F2", "green", "#B877D9", "#EAB839", "red"


class Board:
    def __init__(self):
        self.y, self.panels = 0, []

    def row(self, title):
        self.panels.append({"type": "row", "title": title, "collapsed": False, "panels": [],
                            "gridPos": {"h": 1, "w": 24, "x": 0, "y": self.y}})
        self.y += 1

    def add(self, *ps):
        h = 0
        for p in ps:
            p["gridPos"]["y"] = self.y
            self.panels.append(p)
            h = max(h, p["gridPos"]["h"])
        self.y += h


def stat(title, expr, x, w, unit="short", color=AZUL, decimals=None, steps=None, maps=None, desc=None):
    d = {"unit": unit, "noValue": "0", "color": {"mode": "fixed", "fixedColor": color}}
    if decimals is not None:
        d["decimals"] = decimals
    if steps:
        d["color"] = {"mode": "thresholds"}
        d["thresholds"] = {"mode": "absolute", "steps": steps}
    if maps:
        d["mappings"] = maps
    p = {"type": "stat", "title": title, "datasource": P, "gridPos": {"h": 4, "w": w, "x": x, "y": 0},
         "targets": [{"datasource": P, "expr": expr, "refId": "A", "instant": True}],
         "fieldConfig": {"defaults": d, "overrides": []},
         "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "value", "graphMode": "none",
                     "textMode": "value", "justifyMode": "center"}}
    if desc:
        p["description"] = desc
    return p


def ts(title, targets, x, w, h=8, unit="short", stack=False, desc=None):
    p = {"type": "timeseries", "title": title, "datasource": P, "gridPos": {"h": h, "w": w, "x": x, "y": 0},
         "targets": [{"datasource": P, "expr": e, "legendFormat": leg, "refId": chr(65 + i)}
                     for i, (e, leg) in enumerate(targets)],
         "fieldConfig": {"defaults": {"unit": unit, "custom": {"fillOpacity": 15, "lineWidth": 2,
                                                               "stacking": {"mode": "normal" if stack else "none"}}},
                         "overrides": []},
         "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}}}
    if desc:
        p["description"] = desc
    return p


def main():
    b = Board()
    b.row("Agora")
    b.add(
        stat("llama-server", f"up{LL}", 0, 3, maps=[{"type": "value", "options": {
            "0": {"text": "fora", "color": VERMELHO}, "1": {"text": "no ar", "color": VERDE}}}],
            steps=[{"color": VERMELHO, "value": None}, {"color": VERDE, "value": 1}]),
        stat("Geração (média)", f"llamacpp:predicted_tokens_seconds{LL}", 3, 4, "short", VERDE, 1,
             desc="tokens/s de geração, média desde o início do servidor"),
        stat("Leitura de prompt (média)", f"llamacpp:prompt_tokens_seconds{LL}", 7, 4, "short", AZUL, 0,
             desc="tokens/s de processamento de prompt; prompts de 46 mil tokens levam ~3,5 min"),
        stat("Em processamento", f"llamacpp:requests_processing{LL}", 11, 3, color=ROXO),
        stat("Na fila", f"llamacpp:requests_deferred{LL}", 14, 3,
             steps=[{"color": VERDE, "value": None}, {"color": AMARELO, "value": 1}]),
        stat("Swap usado", f"node_memory_swap_used_bytes{MB}", 17, 3, "bytes",
             steps=[{"color": VERDE, "value": None}, {"color": AMARELO, "value": 2e9}, {"color": VERMELHO, "value": 4e9}],
             desc="acima de 1–2 GB o modelo ou o contexto está grande demais para os 8 GB"),
        stat("Ligado há", f"time() - node_boot_time_seconds{MB}", 20, 4, "s", AZUL),
    )
    b.row("Uso do modelo")
    b.add(
        ts("Tokens por minuto", [
            (f"rate(llamacpp:tokens_predicted_total{LL}[5m]) * 60", "gerados"),
            (f"rate(llamacpp:prompt_tokens_total{LL}[5m]) * 60", "prompt (novos)"),
            (f"rate(llamacpp:prompt_tokens_cached_total{LL}[5m]) * 60", "prompt (cache)"),
        ], 0, 12),
        ts("Tempo ocupado", [
            (f"rate(llamacpp:prompt_seconds_total{LL}[5m])", "lendo prompt"),
            (f"rate(llamacpp:tokens_predicted_seconds_total{LL}[5m])", "gerando"),
        ], 12, 12, unit="percentunit", stack=True, desc="fração do tempo em que o servidor esteve trabalhando"),
    )
    b.row("MacBook")
    b.add(
        ts("Memória (8 GB)", [
            (f"node_memory_wired_bytes{MB}", "presa (modelo na GPU)"),
            (f"node_memory_active_bytes{MB}", "ativa"),
            (f"node_memory_compressed_bytes{MB}", "comprimida"),
            (f"node_memory_free_bytes{MB}", "livre"),
        ], 0, 8, unit="bytes", stack=True),
        ts("Swap", [(f"node_memory_swap_used_bytes{MB}", "usado")], 8, 8, unit="bytes"),
        ts("Carga e CPU", [
            (f"node_load1{MB}", "load 1m"),
            (f'sum(rate(node_cpu_seconds_total{{instance="macbook",mode!="idle"}}[5m]))', "núcleos em uso"),
        ], 16, 8),
    )
    dash = {"uid": "macbook-llm", "title": "MacBook LLM", "tags": ["llm", "openclaw", "macbook"],
            "timezone": "browser", "refresh": "30s", "schemaVersion": 39,
            "time": {"from": "now-6h", "to": "now"}, "panels": b.panels}
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/macbook-llm.json", "w") as f:
        json.dump(dash, f, indent=2, ensure_ascii=False)
    print(f"{OUT}/macbook-llm.json: {len(b.panels)} painéis")


if __name__ == "__main__":
    main()
