#!/usr/bin/env python3
"""Gera o dashboard "Solar - Cosme de Farias" (energia/solar-cosme-de-farias.json).

Fonte: exporters/solarman (3 microinversores Deye, 4 placas cada) via job
"solarman". À noite os micros desligam e as séries somem; por isso os
valores "de hoje" e totais usam last_over_time.

Uso: python3 scripts/gen-solar-dashboard.py   (a partir de monitoring/)
"""
import json
import os

P = {"type": "prometheus", "uid": "prometheus"}
S = 'site="cosme-de-farias",inverter=~"$inverter"'
OUT = "grafana/dashboards/energia/solar-cosme-de-farias.json"
YELLOW, GREEN, BLUE, ORANGE = "#FADE2A", "#73BF69", "#5794F2", "#FF9830"
PLACA = "{{inverter}} · placa {{pv}}"


def t(expr, legend=None, ref="A", **kw):
    d = {"datasource": P, "expr": expr, "refId": ref}
    if legend:
        d["legendFormat"] = legend
    d.update(kw)
    return d


class Board:
    def __init__(self):
        self.y, self.panels, self.id = 0, [], 0

    def row(self, title):
        self.id += 1
        self.panels.append({"id": self.id, "type": "row", "title": title, "collapsed": False, "panels": [],
                            "gridPos": {"h": 1, "w": 24, "x": 0, "y": self.y}})
        self.y += 1

    def add(self, *panels):
        h = 0
        for p in panels:
            self.id += 1
            p["id"] = self.id
            p["gridPos"]["y"] = self.y
            self.panels.append(p)
            h = max(h, p["gridPos"]["h"])
        self.y += h


def stat(title, expr, x, w, unit, color, decimals=1, h=4, desc=None, thr=None):
    fc = {"unit": unit, "decimals": decimals, "noValue": "-", "color": {"mode": "fixed", "fixedColor": color}}
    if thr:
        fc["color"] = {"mode": "thresholds"}
        fc["thresholds"] = {"mode": "absolute", "steps": thr}
    p = {"type": "stat", "title": title, "datasource": P, "targets": [t(expr, instant=True)],
         "gridPos": {"h": h, "w": w, "x": x, "y": 0}, "fieldConfig": {"defaults": fc, "overrides": []},
         "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "value", "graphMode": "none",
                     "textMode": "value", "justifyMode": "center"}}
    if desc:
        p["description"] = desc
    return p


def ts(title, targets, x, w, h=8, unit="short", stack=False, bars=False, interval=None, desc=None,
       calcs=("lastNotNull", "max"), decimals=None, legend_right=True, span_nulls=False):
    custom = {"fillOpacity": 12, "lineWidth": 2, "spanNulls": span_nulls, "showPoints": "never"}
    if stack:
        custom["stacking"] = {"mode": "normal"}
    if bars:
        custom.update({"drawStyle": "bars", "fillOpacity": 80, "lineWidth": 1})
    d = {"unit": unit, "custom": custom}
    if decimals is not None:
        d["decimals"] = decimals
    p = {"type": "timeseries", "title": title, "datasource": P, "targets": targets,
         "gridPos": {"h": h, "w": w, "x": x, "y": 0}, "fieldConfig": {"defaults": d, "overrides": []},
         "options": {"legend": {"displayMode": "table", "placement": "right" if legend_right else "bottom",
                                "calcs": list(calcs), "sortBy": "Last *", "sortDesc": True},
                     "tooltip": {"mode": "multi", "sort": "desc"}}}
    if interval:
        p["interval"] = interval
    if desc:
        p["description"] = desc
    return p


def bars(title, expr, x, w, h, unit, legend, decimals=1, maxv=None, desc=None, thr=None):
    d = {"unit": unit, "decimals": decimals, "min": 0, "noValue": "-",
         "color": {"mode": "continuous-YlRd"} if not thr else {"mode": "thresholds"}}
    if thr:
        d["thresholds"] = {"mode": "absolute", "steps": thr}
    if maxv is not None:
        d["max"] = maxv
    p = {"type": "bargauge", "title": title, "datasource": P,
         "targets": [t(expr, legend, instant=True, format="time_series")],
         "gridPos": {"h": h, "w": w, "x": x, "y": 0}, "fieldConfig": {"defaults": d, "overrides": []},
         "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True,
                     "valueMode": "color", "namePlacement": "left", "sizing": "auto",
                     "reduceOptions": {"calcs": ["lastNotNull"]}},
         "transformations": [{"id": "sortBy", "options": {"sort": [{"field": "Field", "desc": False}]}}]}
    if desc:
        p["description"] = desc
    return p


def placas_table():
    q = [
        ("A", f"last_over_time(solar_pv_power_watts{{{S}}}[15m])"),
        ("B", f"last_over_time(solar_pv_voltage_volts{{{S}}}[15m])"),
        ("C", f"last_over_time(solar_pv_current_amperes{{{S}}}[15m])"),
        ("D", f"last_over_time(solar_pv_energy_today_kwh{{{S}}}[18h])"),
        ("E", f"last_over_time(solar_pv_energy_total_kwh{{{S}}}[7d])"),
    ]
    names = {"Value #A": "Potência (W)", "Value #B": "Tensão (V)", "Value #C": "Corrente (A)",
             "Value #D": "Hoje (kWh)", "Value #E": "Total (kWh)", "inverter": "Micro", "pv": "Placa"}
    ov = [{"matcher": {"id": "byName", "options": "Potência (W)"},
           "properties": [{"id": "unit", "value": "watt"}, {"id": "decimals", "value": 1},
                          {"id": "custom.cellOptions", "value": {"type": "gauge", "mode": "gradient"}},
                          {"id": "max", "value": 550}, {"id": "color", "value": {"mode": "continuous-YlRd"}}]},
          {"matcher": {"id": "byName", "options": "Hoje (kWh)"},
           "properties": [{"id": "decimals", "value": 1},
                          {"id": "custom.cellOptions", "value": {"type": "gauge", "mode": "lcd"}},
                          {"id": "color", "value": {"mode": "continuous-GrYlRd"}}]},
          {"matcher": {"id": "byName", "options": "Tensão (V)"}, "properties": [{"id": "decimals", "value": 1}]},
          {"matcher": {"id": "byName", "options": "Corrente (A)"}, "properties": [{"id": "decimals", "value": 1}]},
          {"matcher": {"id": "byName", "options": "Total (kWh)"}, "properties": [{"id": "decimals", "value": 1}]}]
    return {"type": "table", "title": "Placas agora", "datasource": P,
            "description": "Último valor de cada placa (CC, antes do micro). Potência = tensão × corrente.",
            "targets": [t(e, ref=r, instant=True, format="table") for r, e in q],
            "gridPos": {"h": 13, "w": 12, "x": 12, "y": 0},
            "fieldConfig": {"defaults": {"custom": {"align": "center"}}, "overrides": ov},
            "options": {"showHeader": True, "sortBy": [{"displayName": "Micro"}]},
            "transformations": [
                {"id": "merge"},
                {"id": "organize", "options": {
                    "excludeByName": {"Time": True, "job": True, "instance": True, "site": True, "__name__": True},
                    "indexByName": {"inverter": 0, "pv": 1, "Value #A": 2, "Value #B": 3, "Value #C": 4,
                                    "Value #D": 5, "Value #E": 6},
                    "renameByName": names}},
                {"id": "sortBy", "options": {"sort": [{"field": "Micro"}, {"field": "Placa"}]}}]}


# ---- Medidores Tuya de Cosme de Farias (via Home Assistant, área "Cosme de Farias") ----
HA = 'job="homeassistant"'
def ent(metric, name):
    return f'{metric}{{{HA},entity="sensor.{name}"}}'
CARGA = "monitor_de_carga_cosme_de_farias_"
REDE = "monitor_geral_de_energia_cosme_de_farias_"
IMP = ent("hass_sensor_energy_kwh", REDE + "energia_consumida")     # comprado da concessionária
EXP = ent("hass_sensor_energy_kwh", REDE + "energia_produzida")     # injetado na rede
CASA = ent("hass_sensor_energy_kwh", CARGA + "total_energy")        # consumo da casa
SOL_TOT = 'solar_energy_total_kwh{site="cosme-de-farias"}'
KWH_TO_W = 3600 * 1000


def inc(expr, rng="$__range"):
    return f"sum(increase({expr}[{rng}]))"


def rate_w(expr, rng="10m"):
    return f"sum(rate({expr}[{rng}])) * {KWH_TO_W}"


def casa_e_rede(b):
    gerado = f"sum(max_over_time({SOL_TOT}[$__range]) - min_over_time({SOL_TOT}[$__range]))"
    b.row("Casa e rede (medidores Tuya)")
    b.add(stat("Consumo da casa agora", ent("hass_sensor_power_w", CARGA + "total_active_power"), 0, 4, "watt", BLUE, 0,
               desc="Monitor de carga (soma das fases A e B)."),
          stat("Rede agora (+ compra / − injeta)", f"({rate_w(IMP)}) - ({rate_w(EXP)})", 4, 4, "watt", "text", 0,
               desc="Calculado pelos contadores de energia consumida e produzida do medidor da concessionária (média de 10 min).",
               thr=[{"color": GREEN, "value": None}, {"color": ORANGE, "value": 0.5}]),
          stat("Comprado no período", inc(IMP), 8, 4, "kwatth", ORANGE, 1),
          stat("Injetado no período", inc(EXP), 12, 4, "kwatth", GREEN, 1),
          stat("Saldo (injetado − comprado)", f"{inc(EXP)} - {inc(IMP)}", 16, 4, "kwatth", "text", 1,
               thr=[{"color": "red", "value": None}, {"color": GREEN, "value": 0}]),
          stat("Consumo da casa no período", inc(CASA), 20, 4, "kwatth", BLUE, 1))
    b.add(stat("Autossuficiência", f"clamp(1 - ({inc(IMP)}) / ({inc(CASA)}), 0, 1)", 0, 6, "percentunit", GREEN, 0,
               desc="Parte do consumo da casa que não veio da concessionária (1 − comprado ÷ consumo)."),
          stat("Autoconsumo do solar", f"clamp(1 - ({inc(EXP)}) / ({gerado}), 0, 1)", 6, 6, "percentunit", YELLOW, 0,
               desc="Parte da geração usada na própria casa (1 − injetado ÷ gerado)."),
          stat("Tensão da rede", ent("hass_sensor_voltage_v", REDE + "tensao"), 12, 6, "volt", "text", 1),
          stat("Fator de potência (rede)", f"avg({{{HA},__name__='hass_sensor_power_factor_percent',entity=~'sensor.{REDE}power_factor_[ab]'}}) / 100",
               18, 6, "percentunit", "text", 0))
    b.add(ts("Casa, sol e rede", [
              t(ent("hass_sensor_power_w", CARGA + "total_active_power"), "Consumo da casa", "A"),
              t('sum(solar_ac_power_watts{site="cosme-de-farias"})', "Geração solar", "B"),
              t(rate_w(IMP, "5m"), "Comprado da rede", "C"),
              t(f"-({rate_w(EXP, '5m')})", "Injetado na rede (−)", "D")],
             0, 24, 10, "watt", decimals=0, calcs=("lastNotNull", "mean", "max"),
             desc="Comprado/injetado vêm dos contadores do medidor da concessionária (média de 5 min); injeção aparece negativa."))
    b.add(ts("Consumo da casa por fase", [t(f'hass_sensor_power_w{{{HA},entity=~"sensor.{CARGA}potencia_[ab]"}}', "{{friendly_name}}")],
             0, 12, 8, "watt", stack=True, decimals=0, legend_right=False),
          ts("Medidor da concessionária por fase", [t(f'hass_sensor_power_w{{{HA},entity=~"sensor.{REDE}potencia_[ab]"}}', "{{friendly_name}}")],
             12, 12, 8, "watt", decimals=0, legend_right=False))
    b.add(ts("Energia por dia", [
              t(inc(CASA, "1d"), "Consumo da casa", "A"),
              t(f"sum(max_over_time({SOL_TOT}[1d]) - min_over_time({SOL_TOT}[1d]))", "Geração solar", "B"),
              t(inc(IMP, "1d"), "Comprado", "C"),
              t(inc(EXP, "1d"), "Injetado", "D")],
             0, 16, 9, "kwatth", bars=True, interval="1d", decimals=1, calcs=("mean", "sum"), legend_right=False),
          ts("Tensão (rede e carga)", [t(f'hass_sensor_voltage_v{{{HA},entity=~"sensor.({REDE}|{CARGA})tensao"}}', "{{friendly_name}}")],
             16, 8, 9, "volt", decimals=1, legend_right=False, calcs=("lastNotNull", "min", "max")))


def board():
    b = Board()
    up = f'solarman_up{{{S}}}'
    b.row("Agora")
    b.add(stat("Potência agora", f"sum(solar_ac_power_watts{{{S}}}) or vector(0)", 0, 4, "watt", YELLOW, 0,
               desc="Potência CA somada dos micros. Zero à noite (micros desligados)."),
          stat("Gerado hoje", f"sum(last_over_time(solar_energy_today_kwh{{{S}}}[18h]))", 4, 4, "kwatth", YELLOW, 1),
          stat("Gerado no período", f"sum(max_over_time(solar_energy_total_kwh{{{S}}}[$__range]) - min_over_time(solar_energy_total_kwh{{{S}}}[$__range]))",
               8, 4, "kwatth", ORANGE, 1, desc="Diferença do contador total no intervalo escolhido no topo do dashboard."),
          stat("Total desde a instalação", f"sum(last_over_time(solar_energy_total_kwh{{{S}}}[7d]))", 12, 4, "kwatth", GREEN, 0),
          stat("Micros online", f"sum(max_over_time({up}[5m])) or vector(0)", 16, 4, "short", BLUE, 0,
               desc="À noite os três ficam offline (o logger desliga junto com o micro)."),
          stat("Temperatura máx.", f"max(last_over_time(solar_temperature_celsius{{{S}}}[15m]))", 20, 4, "celsius", "text", 1,
               thr=[{"color": GREEN, "value": None}, {"color": ORANGE, "value": 60}, {"color": "red", "value": 75}]))

    casa_e_rede(b)

    b.row("Por placa")
    b.add(bars("Potência por placa agora", f"last_over_time(solar_pv_power_watts{{{S}}}[15m])", 0, 12, 13, "watt",
               PLACA, 0, desc="Potência CC de cada placa. Placa bem abaixo das vizinhas = sombra, sujeira ou defeito."),
          placas_table())
    b.add(bars("Gerado hoje por placa", f"last_over_time(solar_pv_energy_today_kwh{{{S}}}[18h])", 0, 12, 13, "kwatth", PLACA, 1),
          bars("Desempenho relativo hoje (placa ÷ média das placas)",
               f"last_over_time(solar_pv_energy_today_kwh{{{S}}}[18h]) / on() group_left() avg(last_over_time(solar_pv_energy_today_kwh{{{S}}}[18h]))",
               12, 12, 13, "percentunit", PLACA, 0, maxv=1.2,
               desc="100% = média. Abaixo de ~85% de forma persistente merece uma olhada (limpeza, sombra, conector).",
               thr=[{"color": "red", "value": None}, {"color": ORANGE, "value": 0.85}, {"color": GREEN, "value": 0.95}]))
    b.add(ts("Potência por placa", [t(f"solar_pv_power_watts{{{S}}}", PLACA)], 0, 24, 10, "watt", decimals=0))
    b.add(ts("Tensão por placa", [t(f"solar_pv_voltage_volts{{{S}}}", PLACA)], 0, 12, 9, "volt", decimals=1,
             legend_right=False, calcs=("lastNotNull", "max")),
          ts("Corrente por placa", [t(f"solar_pv_current_amperes{{{S}}}", PLACA)], 12, 12, 9, "amp", decimals=1,
             legend_right=False, calcs=("lastNotNull", "max")))

    b.row("Por microinversor")
    b.add(ts("Potência CA por micro (empilhado)", [t(f"solar_ac_power_watts{{{S}}}", "{{inverter}}")], 0, 16, 9, "watt",
             stack=True, decimals=0),
          bars("Gerado hoje por micro", f"last_over_time(solar_energy_today_kwh{{{S}}}[18h])", 16, 8, 9, "kwatth",
               "{{inverter}}", 1))
    b.add(ts("Temperatura dos micros", [t(f"solar_temperature_celsius{{{S}}}", "{{inverter}}")], 0, 8, 8, "celsius",
             decimals=1, legend_right=False),
          ts("Tensão da rede", [t(f"solar_grid_voltage_volts{{{S}}}", "{{inverter}}")], 8, 8, 8, "volt",
             decimals=1, legend_right=False, calcs=("lastNotNull", "min", "max")),
          ts("Frequência da rede", [t(f"solar_grid_frequency_hertz{{{S}}}", "{{inverter}}")], 16, 8, 8, "hertz",
             decimals=2, legend_right=False, calcs=("lastNotNull", "min", "max")))

    b.row("Histórico diário")
    b.add(ts("Geração por dia (micros)", [t(f"max_over_time(solar_energy_today_kwh{{{S}}}[1d:5m])", "{{inverter}}")],
             0, 12, 9, "kwatth", stack=True, bars=True, interval="1d", decimals=1, calcs=("mean", "max", "sum"),
             legend_right=False),
          ts("Geração por dia (placas)", [t(f"max_over_time(solar_pv_energy_today_kwh{{{S}}}[1d:5m])", PLACA)],
             12, 12, 9, "kwatth", bars=True, interval="1d", decimals=1, calcs=("mean", "sum"), legend_right=True))
    b.add(ts("Disponibilidade dos loggers", [t(up, "{{inverter}}")], 0, 24, 6, "short", decimals=0,
             desc="1 = respondeu à leitura Modbus. Fica 0 à noite e quando a VPN cai.", calcs=("mean",),
             legend_right=True))

    return {
        "title": "Solar - Cosme de Farias", "uid": "solar-cosme-de-farias", "tags": ["energia", "solar"],
        "timezone": "browser", "refresh": "1m", "description": "Microinversores Deye (geração por placa) e medidores Tuya da casa e da concessionária", "schemaVersion": 39, "editable": True,
        "time": {"from": "now/d", "to": "now/d"},
        "templating": {"list": [{
            "name": "inverter", "label": "Micro", "type": "query", "datasource": P,
            "query": {"query": 'label_values(solar_info{site="cosme-de-farias"}, inverter)', "refId": "v"},
            "definition": 'label_values(solar_info{site="cosme-de-farias"}, inverter)',
            "refresh": 2, "multi": True, "includeAll": True, "allValue": ".*",
            "current": {"text": ["All"], "value": ["$__all"]}}]},
        "panels": b.panels,
    }


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(board(), f, ensure_ascii=False, indent=1)
    print("ok", OUT)
