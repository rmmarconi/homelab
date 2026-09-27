#!/usr/bin/env python3
"""Gera os dashboards "Home Assistant - Sistema" e "Home Assistant - Casa".

As consultas seguem o padrão de nomes da integração prometheus: do HA
(hass_sensor_power_w, hass_sensor_temperature_celsius, ...), então os painéis
se preenchem sozinhos à medida que novas integrações entram no HA.

Uso: python3 scripts/gen-ha-dashboards.py   (a partir de monitoring/)
"""
import json
import os

P = {"type": "prometheus", "uid": "prometheus"}
J = 'job="homeassistant"'
# Domínios sem estado próprio (ficam "unknown" até serem usados): não contam como problema
NOSTATE = 'domain!~"button|conversation|tts|stt|event|scene|script|notify"'
OUT = "grafana/dashboards/homeassistant"


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


def stat(title, expr, x, w, h=4, unit="short", color="text", decimals=None, thr=None,
         maps=None, cm="value", noval="0", legend=None, text="value"):
    fc = {"unit": unit, "noValue": noval, "color": {"mode": "fixed", "fixedColor": color}}
    if decimals is not None:
        fc["decimals"] = decimals
    if thr:
        fc["thresholds"] = {"mode": "absolute", "steps": thr}
        fc["color"] = {"mode": "thresholds"}
    if maps:
        fc["mappings"] = maps
    tg = t(expr, instant=True)
    if legend:
        tg["legendFormat"] = legend
    return {"type": "stat", "title": title, "datasource": P, "targets": [tg],
            "gridPos": {"h": h, "w": w, "x": x, "y": 0}, "fieldConfig": {"defaults": fc},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": cm,
                        "graphMode": "none", "textMode": text, "justifyMode": "center",
                        "orientation": "horizontal"}}


def ts(title, targets, x, w, h=7, unit="short", noval=None, right=True, stack=False, bars=False):
    custom = {"fillOpacity": 10}
    if stack:
        custom["stacking"] = {"mode": "normal"}
    if bars:
        custom.update({"drawStyle": "bars", "fillOpacity": 70})
    d = {"unit": unit, "custom": custom}
    if noval:
        d["noValue"] = noval
    return {"type": "timeseries", "title": title, "datasource": P, "targets": targets,
            "gridPos": {"h": h, "w": w, "x": x, "y": 0}, "fieldConfig": {"defaults": d, "overrides": []},
            "options": {"legend": {"displayMode": "table" if right else "list",
                                   "placement": "right" if right else "bottom",
                                   "calcs": ["lastNotNull", "max"] if right else []},
                        "tooltip": {"mode": "multi", "sort": "desc"}}}


def table(title, expr, x, w, h, cols, rename, noval, hide=()):
    ov = [{"matcher": {"id": "byName", "options": c}, "properties": [{"id": "custom.hidden", "value": True}]}
          for c in hide]
    return {"type": "table", "title": title, "datasource": P,
            "gridPos": {"h": h, "w": w, "x": x, "y": 0},
            "targets": [t(expr, instant=True, format="table")],
            "transformations": [{"id": "organize", "options": {
                "excludeByName": {"Time": True, "__name__": True, "instance": True, "job": True},
                "indexByName": {c: i for i, c in enumerate(cols)}, "renameByName": rename}}],
            "fieldConfig": {"defaults": {"noValue": noval}, "overrides": ov},
            "options": {"cellHeight": "sm", "showHeader": True}}


def bargauge(title, expr, x, w, h, legend, unit="short", **defaults):
    d = {"unit": unit}
    d.update(defaults)
    return {"type": "bargauge", "title": title, "datasource": P,
            "gridPos": {"h": h, "w": w, "x": x, "y": 0},
            "targets": [t(expr, instant=True, legendFormat=legend)],
            "fieldConfig": {"defaults": d},
            "options": {"orientation": "horizontal", "displayMode": "gradient",
                        "reduceOptions": {"calcs": ["lastNotNull"]}}}


def sistema():
    b = Board()
    up = [{"type": "value", "options": {"1": {"text": "no ar", "color": "green"}, "0": {"text": "FORA", "color": "red"}}}]
    b.row("Estado")
    b.add(stat("Home Assistant", f"max(up{{{J}}})", 0, 4, maps=up, cm="background"),
          stat("Uptime do core", f"time() - max(process_start_time_seconds{{{J}}})", 4, 4, unit="s", decimals=1),
          stat("Entidades", f"count(hass_entity_available{{{J}}})", 8, 4, color="#3274D9"),
          stat("Indisponíveis", f"count(hass_entity_available{{{J},{NOSTATE}}} == 0) or vector(0)", 12, 4,
               thr=[{"color": "green", "value": None}, {"color": "orange", "value": 1}, {"color": "red", "value": 5}]),
          stat("Atualizações pendentes", f"count(hass_update_state{{{J}}} == 1) or vector(0)", 16, 4,
               thr=[{"color": "green", "value": None}, {"color": "orange", "value": 1}]),
          stat("Áreas", f"count(hass_area_info{{{J}}})", 20, 4))
    b.add(table("Atualizações disponíveis", f"hass_update_state{{{J}}} == 1", 0, 12, 6,
                ["friendly_name", "entity"], {"friendly_name": "Componente", "entity": "Entidade"},
                "tudo atualizado", hide=("Value", "domain")),
          table("Entidades indisponíveis", f"hass_entity_available{{{J},{NOSTATE}}} == 0", 12, 12, 6,
                ["friendly_name", "entity", "domain"],
                {"friendly_name": "Nome", "entity": "Entidade", "domain": "Domínio"},
                "nenhuma entidade indisponível", hide=("Value",)))
    b.row("Atividade")
    b.add(ts("Mudanças de estado por minuto, por domínio",
             [t(f"sum by (domain) (rate(hass_state_change_total{{{J}}}[$__rate_interval])) * 60", legendFormat="{{domain}}")],
             0, 12, stack=True, bars=True),
          bargauge("Entidades que mais mudam de estado (período)",
                   f"topk(12, sum by (friendly_name) (increase(hass_state_change_total{{{J}}}[$__range])))",
                   12, 12, 7, "{{friendly_name}}", decimals=0))
    b.add({"type": "piechart", "title": "Entidades por domínio", "datasource": P,
           "gridPos": {"h": 7, "w": 8, "x": 0, "y": 0},
           "targets": [t(f"count by (domain) (hass_entity_available{{{J}}})", instant=True, legendFormat="{{domain}}")],
           "options": {"pieType": "donut", "legend": {"displayMode": "table", "placement": "right", "values": ["value"]},
                       "reduceOptions": {"calcs": ["lastNotNull"]}}},
          ts("Entidades sem atualizar há mais de 1 h",
             [t(f"count((time() - hass_last_updated_time_seconds{{{J}}}) > 3600) or vector(0)", legendFormat="paradas há mais de 1 h")],
             8, 16, right=False))
    b.row("Processo do Home Assistant (core)")
    b.add(ts("CPU", [t(f"rate(process_cpu_seconds_total{{{J}}}[$__rate_interval])", legendFormat="core")], 0, 8, unit="percentunit", right=False),
          ts("Memória residente", [t(f"process_resident_memory_bytes{{{J}}}", legendFormat="RSS")], 8, 8, unit="bytes", right=False),
          ts("Descritores de arquivo abertos", [t(f"process_open_fds{{{J}}}", legendFormat="abertos"),
                                                t(f"process_max_fds{{{J}}}", "B", legendFormat="limite")], 16, 8, right=False))
    return {"title": "Home Assistant - Sistema", "uid": "ha-sistema", "tags": ["homeassistant"],
            "timezone": "browser", "schemaVersion": 39, "time": {"from": "now-24h", "to": "now"},
            "refresh": "1m", "panels": b.panels,
            "links": [{"title": "Home Assistant - Casa", "type": "link", "url": "/d/ha-casa", "icon": "dashboard"},
                      {"title": "Abrir o Home Assistant", "type": "link", "url": "http://10.1.1.11/",
                       "targetBlank": True, "icon": "external link"}]}


def casa():
    b = Board()
    sol = 'entity=~"(?i).*(solar|inversor|inverter|pv|ions|micro|geracao|production).*"'
    onoff = [{"type": "value", "options": {"1": {"text": "ligado", "color": "green"}, "0": {"text": "desligado", "color": "text"}}}]
    b.row("Energia e solar")
    SOLP = f'hass_sensor_power_w{{{J},entity="sensor.solar_potencia"}}'
    TOT = f'hass_sensor_energy_kwh{{{J},entity="sensor.medidor_de_energia_solar_total_energy"}}'
    MON = lambda e: f'{{__name__=~"hass_sensor_monetary.*",{J},entity="{e}"}}'
    b.add(stat("Gerando agora", f"sum({SOLP})", 0, 4, unit="watt", decimals=0, color="#FADE2A", noval="-"),
          stat("Gerado hoje", f'sum(hass_sensor_energy_kwh{{{J},entity="sensor.solar_energia_hoje"}})', 4, 4, unit="kwatth", decimals=2, color="#FADE2A", noval="-"),
          stat("Gerado no mês", f'sum(hass_sensor_energy_kwh{{{J},entity="sensor.solar_energia_mes"}})', 8, 4, unit="kwatth", decimals=1, color="#FADE2A", noval="-"),
          stat("Economia hoje", f'sum({MON("sensor.solar_economia_hoje")})', 12, 4, unit="currencyBRL", decimals=2, color="green", noval="-"),
          stat("Economia no mês", f'sum({MON("sensor.solar_economia_no_mes")})', 16, 4, unit="currencyBRL", decimals=2, color="green", noval="-"),
          stat("Pico de hoje", f"max_over_time(sum({SOLP})[1d:5m])", 20, 4, unit="watt", decimals=0, color="#FF9830", noval="-"))
    b.add(ts("Geração solar por canal do medidor",
             [t(f'hass_sensor_power_w{{{J},entity=~"sensor\\.medidor_de_energia_solar_potencia_[ab]"}}', legendFormat="{{friendly_name}}")],
             0, 16, h=8, unit="watt", stack=True, noval="sem medidor solar"),
          ts("Geração por dia (kWh)",
             [t(f"increase({TOT}[1d])", legendFormat="gerado")], 16, 8, h=8, unit="kwatth", bars=True, right=False))
    b.panels[-1]["interval"] = "1d"
    b.panels[-1]["timeFrom"] = "30d"
    b.add(ts("Potência de todos os sensores (W)", [t(f'hass_sensor_power_w{{{J},entity!="sensor.solar_potencia"}}', legendFormat="{{friendly_name}}")],
             0, 12, h=7, unit="watt", noval="nenhum sensor de potência"),
          ts("Tensão da rede", [t(f'hass_sensor_voltage_v{{{J}}}', legendFormat="{{friendly_name}}")],
             12, 12, h=7, unit="volt", noval="nenhum sensor de tensão"))
    b.row("Clima")
    b.add(ts("Temperatura", [t(f"hass_sensor_temperature_celsius{{{J}}}", legendFormat="{{friendly_name}}"),
                             t(f"hass_climate_current_temperature_celsius{{{J}}}", "B", legendFormat="{{friendly_name}} (clima)")],
             0, 12, h=8, unit="celsius", noval="nenhum sensor de temperatura ainda"),
          ts("Umidade", [t(f"hass_sensor_humidity_percent{{{J}}}", legendFormat="{{friendly_name}}")],
             12, 12, h=8, unit="percent", noval="nenhum sensor de umidade ainda"))
    b.row("Dispositivos")
    b.add(bargauge("Baterias", f"sort(hass_sensor_battery_percent{{{J}}})", 0, 8, 8, "{{friendly_name}}",
                   unit="percent", min=0, max=100, noValue="nenhum dispositivo com bateria",
                   thresholds={"mode": "absolute", "steps": [{"color": "red", "value": None},
                                                            {"color": "orange", "value": 20},
                                                            {"color": "green", "value": 40}]}),
          stat("Portas, janelas e sensores", f"max by (friendly_name) (hass_binary_sensor_state{{{J}}})", 8, 8, h=8,
               maps=[{"type": "value", "options": {"1": {"text": "ativo", "color": "orange"}, "0": {"text": "inativo", "color": "green"}}}],
               cm="background", noval="nenhum sensor binário", legend="{{friendly_name}}", text="value_and_name"),
          stat("Luzes e tomadas",
               f"max by (friendly_name) (hass_switch_state{{{J}}}) or max by (friendly_name) (hass_light_brightness_percent{{{J}}} > bool 0)",
               16, 8, h=8, maps=onoff, cm="background", noval="nenhuma luz ou tomada",
               legend="{{friendly_name}}", text="value_and_name"))
    return {"title": "Home Assistant - Casa", "uid": "ha-casa", "tags": ["homeassistant", "energia"],
            "timezone": "browser", "schemaVersion": 39, "time": {"from": "now-24h", "to": "now"},
            "refresh": "1m", "panels": b.panels,
            "links": [{"title": "Home Assistant - Sistema", "type": "link", "url": "/d/ha-sistema", "icon": "dashboard"}]}


def ar_condicionado():
    b = Board()
    ACE = 'entity=~"sensor\\.ar_(escritorio|clara|suite)_%s"'
    LIG = f'hass_binary_sensor_state{{{J},entity=~"binary_sensor\\.ar_.*_ligado"}}'
    tot = lambda e: f'hass_sensor_{e}{{{J}'
    b.row("Agora")
    b.add(stat("Aparelhos ligados", f"sum({LIG})", 0, 4, color="#3274D9"),
          stat("Potência estimada", f'sum(hass_sensor_power_w{{{J},entity="sensor.ar_condicionado_potencia_total"}})', 4, 4, unit="watt", decimals=0),
          stat("Consumo hoje", f'sum(hass_sensor_energy_kwh{{{J},entity="sensor.ar_condicionado_consumo_hoje"}})', 8, 4, unit="kwatth", decimals=2),
          stat("Custo hoje", f'sum({{__name__=~"hass_sensor_monetary.*",{J},entity="sensor.ar_condicionado_custo_hoje"}})', 12, 4, unit="currencyBRL", decimals=2, color="green"),
          stat("Consumo no mês", f'sum(hass_sensor_energy_kwh{{{J},entity="sensor.ar_condicionado_consumo_no_mes"}})', 16, 4, unit="kwatth", decimals=1),
          stat("Custo no mês", f'sum({{__name__=~"hass_sensor_monetary.*",{J},entity="sensor.ar_condicionado_custo_no_mes"}})', 20, 4, unit="currencyBRL", decimals=2, color="green"))
    b.add(stat("Modo de cada aparelho", f'max by (friendly_name, mode) (hass_climate_mode{{{J}}} == 1)', 0, 12, h=4,
               legend="{{friendly_name}}: {{mode}}", text="name", cm="background",
               maps=[{"type": "value", "options": {"1": {"color": "blue"}}}]),
          bargauge("Tempo ligado hoje", f'max by (friendly_name) (hass_sensor_duration_h{{{J},{ACE % "tempo_ligado_hoje"}}})',
                   12, 12, 4, "{{friendly_name}}", unit="h", decimals=1, min=0, max=24))
    b.row("Temperatura")
    b.add(ts("Temperatura do cômodo e desejada",
             [t(f'max by (friendly_name) (hass_climate_current_temperature_celsius{{{J}}})', legendFormat="{{friendly_name}} (cômodo)"),
              t(f'max by (friendly_name) (hass_climate_target_temperature_celsius{{{J}}})', "B", legendFormat="{{friendly_name}} (desejada)")],
             0, 16, h=8, unit="celsius"),
          ts("Diferença cômodo − desejada",
             [t(f'max by (friendly_name) (hass_climate_current_temperature_celsius{{{J}}}) - on(friendly_name) max by (friendly_name) (hass_climate_target_temperature_celsius{{{J}}})', legendFormat="{{friendly_name}}")],
             16, 8, h=8, unit="celsius", right=False))
    b.row("Uso e consumo (estimado)")
    b.add(ts("Potência estimada por aparelho",
             [t(f'max by (friendly_name) (hass_sensor_power_w{{{J},{ACE % "potencia_estimada"}}})', legendFormat="{{friendly_name}}")],
             0, 16, h=8, unit="watt", stack=True),
          {"type": "state-timeline", "title": "Ligado / desligado", "datasource": P,
           "gridPos": {"h": 8, "w": 8, "x": 16, "y": 0},
           "targets": [t(f'max by (friendly_name) ({LIG})', legendFormat="{{friendly_name}}")],
           "fieldConfig": {"defaults": {"mappings": [{"type": "value", "options": {"1": {"text": "ligado", "color": "blue"}, "0": {"text": "desligado", "color": "transparent"}}}]}},
           "options": {"showValue": "never", "mergeValues": True, "rowHeight": 0.8}})
    b.add(ts("Consumo por dia (kWh)",
             [t(f'max by (friendly_name) (increase(hass_sensor_energy_kwh{{{J},{ACE % "energia"}}}[1d]))', legendFormat="{{friendly_name}}")],
             0, 16, h=8, unit="kwatth", stack=True, bars=True),
          bargauge("Custo no mês por aparelho", f'max by (friendly_name) ({{__name__=~"hass_sensor_monetary.*",{J},{ACE % "custo_no_mes"}}})',
                   16, 8, 8, "{{friendly_name}}", unit="currencyBRL", decimals=2))
    b.panels[-2]["interval"] = "1d"
    b.panels[-2]["timeFrom"] = "30d"
    b.add(bargauge("Tempo ligado no mês", f'max by (friendly_name) (hass_sensor_duration_h{{{J},{ACE % "tempo_ligado_no_mes"}}})',
                   0, 12, 6, "{{friendly_name}}", unit="h", decimals=1),
          bargauge("Consumo no mês por aparelho", f'max by (friendly_name) (hass_sensor_energy_kwh{{{J},{ACE % "consumo_mes"}}})',
                   12, 12, 6, "{{friendly_name}}", unit="kwatth", decimals=1))
    return {"title": "Home Assistant - Ar-condicionado", "uid": "ha-ar", "tags": ["homeassistant", "clima", "energia"],
            "timezone": "browser", "schemaVersion": 39, "time": {"from": "now-24h", "to": "now"},
            "refresh": "1m", "panels": b.panels,
            "description": "Consumo e potência são ESTIMADOS (a Gree não mede consumo). Ajuste a potência nominal no painel Ar-condicionado do HA.",
            "links": [{"title": "Home Assistant - Casa", "type": "link", "url": "/d/ha-casa", "icon": "dashboard"},
                      {"title": "Abrir no Home Assistant", "type": "link", "url": "http://10.1.1.11/ar-condicionado", "targetBlank": True, "icon": "external link"}]}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for d, name in ((sistema(), "ha-sistema.json"), (casa(), "ha-casa.json"), (ar_condicionado(), "ha-ar-condicionado.json")):
        with open(os.path.join(OUT, name), "w") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        print(f"{name}: {len(d['panels'])} painéis")
