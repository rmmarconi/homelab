#!/usr/bin/env python3
"""Gera o dashboard "TVs" (uid tvs) — TVs da casa via ADB no Home Assistant.

TVs: suite = Fire TV Stick 4K (10.1.0.41); sala = TCL Smart TV Pro, Google TV (10.1.0.150).
Variável $tv escolhe a TV; o painel "Comparativo" mostra as duas.

Fontes:
  Loki {job="tv"}: uma linha por minuto com a TV ligada (labels app/estado, JSON com titulo/app_id),
                   enviada pela automação tv_suite_coleta do pacote homeassistant/packages/tv_suite.yaml.
                   1 linha = 1 minuto, então count_over_time = minutos.
  Prometheus: hass_sensor_duration_h / hass_binary_sensor_state das entidades tv_suite_*.

Uso: python3 scripts/gen-tv-dashboard.py   (a partir de monitoring/)
"""
import json
import os

P = {"type": "prometheus", "uid": "prometheus"}
L = {"type": "loki", "uid": "loki"}
OUT = "grafana/dashboards/homeassistant"
TV = '{job="tv", tv="$tv"}'
APPS = '{job="tv", tv="$tv", app!~"Início|Configurações|Desligada"}'
TODAS = '{job="tv", app!~"Início|Configurações|Desligada"}'
AZUL, VERDE, ROXO, AMARELO, CINZA = "#5794F2", "green", "#B877D9", "#EAB839", "text"


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


def stat(title, expr, x, w, h=4, unit="short", color=AZUL, ds=P, decimals=None, maps=None, desc=None):
    d = {"unit": unit, "noValue": "0", "color": {"mode": "fixed", "fixedColor": color}}
    if decimals is not None:
        d["decimals"] = decimals
    if maps:
        d["mappings"] = maps
        d["color"] = {"mode": "thresholds"}
        d["thresholds"] = {"mode": "absolute", "steps": [{"color": CINZA, "value": None}, {"color": VERDE, "value": 1}]}
    p = {"type": "stat", "title": title, "datasource": ds, "gridPos": {"h": h, "w": w, "x": x, "y": 0},
         "targets": [{"datasource": ds, "expr": expr, "refId": "A", "instant": True, **({"queryType": "instant"} if ds is L else {})}],
         "fieldConfig": {"defaults": d, "overrides": []},
         "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "value", "graphMode": "none",
                     "textMode": "value", "justifyMode": "center"}}
    if desc:
        p["description"] = desc
    return p


def onoff(on, off):
    return [{"type": "value", "options": {"0": {"text": off, "color": CINZA}, "1": {"text": on, "color": VERDE}}}]


def main():
    b = Board()
    b.row("Agora")
    b.add(
        stat("TV", 'max(hass_binary_sensor_state{entity="binary_sensor.tv_${tv}_ligada"})', 0, 3, maps=onoff("LIGADA", "desligada")),
        stat("Reproduzindo", 'max(hass_binary_sensor_state{entity="binary_sensor.tv_${tv}_reproduzindo"})', 3, 3,
             maps=onoff("SIM", "não")),
        {"type": "table", "title": "No momento", "datasource": L, "gridPos": {"h": 4, "w": 10, "x": 6, "y": 0},
         "description": "Última leitura do Fire TV (a cada minuto, com a TV ligada).",
         "targets": [{"datasource": L, "refId": "A", "expr": TV + ' | json', "queryType": "range", "maxLines": 1}],
         "transformations": [{"id": "extractFields", "options": {"source": "labels"}},
                             {"id": "organize", "options": {
                                 "excludeByName": {"labels": True, "id": True, "tsNs": True, "Line": True, "job": True, "tv": True,
                                                   "detected_level": True, "service_name": True, "app_id": True, "estado_extracted": True, "app_extracted": True},
                                 "indexByName": {"Time": 0, "app": 1, "titulo": 2, "estado": 3},
                                 "renameByName": {"Time": "Horário", "app": "App", "titulo": "Título", "estado": "Estado"}}},
                             {"id": "limit", "options": {"limitField": 1}}],
         "fieldConfig": {"defaults": {"noValue": "TV desligada"}, "overrides": []},
         "options": {"showHeader": True, "cellHeight": "md"}},
        stat("Ligada hoje", 'max(hass_sensor_duration_h{entity="sensor.tv_${tv}_ligada_hoje"})', 16, 2, unit="h", decimals=1),
        stat("Assistindo hoje", 'max(hass_sensor_duration_h{entity="sensor.tv_${tv}_reproduzindo_hoje"})', 18, 2, unit="h",
             decimals=1, color=ROXO, desc="Tempo com algo tocando (estado playing)."),
        stat("Na semana", 'max(hass_sensor_duration_h{entity="sensor.tv_${tv}_ligada_na_semana"})', 20, 2, unit="h", decimals=1),
        stat("No mês", 'max(hass_sensor_duration_h{entity="sensor.tv_${tv}_ligada_no_mes"})', 22, 2, unit="h", decimals=1),
    )

    b.row("Tempo de uso")
    bars = {"drawStyle": "bars", "fillOpacity": 80, "lineWidth": 1, "stacking": {"mode": "normal"}}
    b.add(
        {"type": "timeseries", "title": "Minutos por app, por dia", "datasource": L, "interval": "1d",
         "gridPos": {"h": 9, "w": 12, "x": 0, "y": 0},
         "targets": [{"datasource": L, "refId": "A", "queryType": "range", "legendFormat": "{{app}}",
                      "expr": f'sum by (app) (count_over_time({APPS} [1d]))'}],
         "fieldConfig": {"defaults": {"unit": "m", "custom": bars, "color": {"mode": "palette-classic"}}, "overrides": []},
         "options": {"legend": {"displayMode": "table", "placement": "right", "calcs": ["sum"]},
                     "tooltip": {"mode": "multi", "sort": "desc"}}},
        {"type": "timeseries", "title": "Uso ao longo do dia (minutos por hora)", "datasource": L, "interval": "1h",
         "gridPos": {"h": 9, "w": 12, "x": 12, "y": 0},
         "targets": [{"datasource": L, "refId": "A", "queryType": "range", "legendFormat": "{{app}}",
                      "expr": f'sum by (app) (count_over_time({TV} [1h]))'}],
         "fieldConfig": {"defaults": {"unit": "m", "max": 60, "custom": bars, "color": {"mode": "palette-classic"}}, "overrides": []},
         "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi", "sort": "desc"}}},
    )
    b.add(
        {"type": "piechart", "title": "Tempo por app (período)", "datasource": L, "gridPos": {"h": 9, "w": 8, "x": 0, "y": 0},
         "targets": [{"datasource": L, "refId": "A", "queryType": "instant", "legendFormat": "{{app}}",
                      "expr": f'sum by (app) (count_over_time({APPS} [$__range]))'}],
         "fieldConfig": {"defaults": {"unit": "m", "color": {"mode": "palette-classic"}}, "overrides": []},
         "options": {"pieType": "donut", "reduceOptions": {"calcs": ["lastNotNull"]},
                     "legend": {"displayMode": "table", "placement": "right", "values": ["value", "percent"]}}},
        {"type": "timeseries", "title": "Horas por dia (ligada x assistindo)", "datasource": P, "interval": "1h",
         "gridPos": {"h": 9, "w": 16, "x": 8, "y": 0},
         "targets": [{"datasource": P, "refId": "A", "legendFormat": "ligada",
                      "expr": 'max_over_time(hass_sensor_duration_h{entity="sensor.tv_${tv}_ligada_hoje"}[1h])'},
                     {"datasource": P, "refId": "B", "legendFormat": "assistindo",
                      "expr": 'max_over_time(hass_sensor_duration_h{entity="sensor.tv_${tv}_reproduzindo_hoje"}[1h])'}],
         "fieldConfig": {"defaults": {"unit": "h", "decimals": 1, "custom": {"fillOpacity": 15, "lineWidth": 2}}, "overrides": []},
         "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}},
         "description": "Acumulado do dia (zera à meia-noite)."},
    )

    b.add(
        {"type": "timeseries", "title": "Comparativo: minutos por TV, por dia", "datasource": L, "interval": "1d",
         "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0},
         "description": "Todas as TVs, independentemente do seletor. Minutos em algum app (fora do launcher).",
         "targets": [{"datasource": L, "refId": "A", "queryType": "range", "legendFormat": "{{tv}}",
                      "expr": f'sum by (tv) (count_over_time({TODAS} [1d]))'}],
         "fieldConfig": {"defaults": {"unit": "m", "custom": {**bars, "stacking": {"mode": "none"}}, "color": {"mode": "palette-classic"}},
                         "overrides": [{"matcher": {"id": "byName", "options": "suite"}, "properties": [{"id": "displayName", "value": "Suíte"}]},
                                       {"matcher": {"id": "byName", "options": "sala"}, "properties": [{"id": "displayName", "value": "Sala"}]}]},
         "options": {"legend": {"displayMode": "table", "placement": "right", "calcs": ["sum", "mean"]}, "tooltip": {"mode": "multi"}}},
    )

    b.row("O que foi assistido")
    b.add(
        {"type": "table", "title": "Títulos no período (minutos)", "datasource": L, "gridPos": {"h": 11, "w": 10, "x": 0, "y": 0},
         "description": "Só aparecem títulos de apps que publicam o que está tocando (MediaSession).",
         "targets": [{"datasource": L, "refId": "A", "queryType": "instant", "format": "table",
                      "expr": f'sum by (app, titulo) (count_over_time({TV} | json | titulo != "" [$__range]))'}],
         "transformations": [{"id": "organize", "options": {"excludeByName": {"Time": True},
                                                            "renameByName": {"app": "App", "titulo": "Título", "Value #A": "Minutos"}}},
                             {"id": "sortBy", "options": {"sort": [{"field": "Minutos", "desc": True}]}}],
         "fieldConfig": {"defaults": {"noValue": "—"}, "overrides": [
             {"matcher": {"id": "byName", "options": "Minutos"}, "properties": [{"id": "unit", "value": "m"}, {"id": "custom.cellOptions", "value": {"type": "gauge"}}]}]},
         "options": {"showHeader": True, "cellHeight": "sm"}},
        {"type": "logs", "title": "Linha do tempo (minuto a minuto)", "datasource": L, "gridPos": {"h": 11, "w": 14, "x": 10, "y": 0},
         "targets": [{"datasource": L, "refId": "A", "queryType": "range",
                      "expr": TV + ' | json | line_format "{{.app}}  ·  {{ if .titulo }}{{.titulo}}{{ else }}—{{ end }}  ·  {{.estado}}"'}],
         "options": {"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending", "dedupStrategy": "consecutive",
                     "enableLogDetails": True}},
    )

    var = {"name": "tv", "label": "TV", "type": "custom", "query": "Suíte : suite,Sala : sala",
           "current": {"text": "Suíte", "value": "suite"},
           "options": [{"text": "Suíte", "value": "suite", "selected": True}, {"text": "Sala", "value": "sala", "selected": False}]}
    d = {"uid": "tvs", "title": "TVs", "tags": ["homeassistant", "tv"], "templating": {"list": [var]}, "timezone": "browser",
         "refresh": "1m", "time": {"from": "now-7d", "to": "now"}, "schemaVersion": 39, "graphTooltip": 1,
         "description": "TVs da casa (Suíte: Fire TV 10.1.0.41; Sala: TCL Google TV 10.1.0.150): apps, títulos, horários e tempo de uso.",
         "panels": b.panels}
    os.makedirs(OUT, exist_ok=True)
    json.dump(d, open(f"{OUT}/tvs.json", "w"), indent=1, ensure_ascii=False)
    print(f"{OUT}/tvs.json: {sum(p['type'] != 'row' for p in b.panels)} painéis")


if __name__ == "__main__":
    main()
