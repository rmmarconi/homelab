#!/usr/bin/env python3
"""Gera a configuração dos dashboards Lovelace "Casa" e "Ar-condicionado".

Imprime dois JSON (um por linha) prontos para `lovelace/config/save`.
"""
import json

ACS = [  # chave, nome curto, entidade climate
    ("escritorio", "Escritório", "climate.c03937630d3f"),
    ("clara", "Clara", "climate.c0393762fa51"),
    ("suite", "Suite", "climate.c0393762e6bc"),
]
CAMERAS = [  # entidade de vídeo, nome, sensor de movimento
    # Só a câmera UniFi (Escritório). As 3 câmeras Tuya gravam no UniFi Protect,
    # que não repassa vídeo de câmeras de terceiros para o HA.
    ("camera.escritorio_high_resolution_channel", "Escritório", "binary_sensor.escritorio_movimento"),
]
PESSOAS = [
    ("device_tracker.iphone_de_r", "iPhone de Rafael", "sensor.iphone_de_r_bateria"),
    ("device_tracker.apple_watch_de_rafael_m", "Apple Watch de Rafael", "sensor.apple_watch_de_rafael_m_bateria"),
    ("device_tracker.macbook_pro_m5_de_rafael", "MacBook de Rafael", "sensor.macbook_pro_m5_de_rafael_bateria"),
    ("device_tracker.iphone_de_bruna_2", "iPhone de Bruna", "sensor.iphone_de_bruna_2_bateria"),
    ("device_tracker.apple_watch_de_maria_de_fatima", "Watch de Maria de Fátima", "sensor.apple_watch_de_maria_de_fatima_bateria"),
    ("device_tracker.iphone_4", "iPhone", "sensor.iphone_bateria_2"),
    ("device_tracker.iphone_3", "iPhone", "sensor.iphone_bateria"),
]


def heading(text, icon=None):
    h = {"type": "heading", "heading": text, "heading_style": "title"}
    if icon:
        h["icon"] = icon
    return h


def tile(entity, name=None, icon=None, features=None, **kw):
    c = {"type": "tile", "entity": entity}
    if name:
        c["name"] = name
    if icon:
        c["icon"] = icon
    if features:
        c["features"] = features
        c["features_position"] = "bottom"
    c.update(kw)
    return c


def section(cards, span=None):
    s = {"type": "grid", "cards": cards}
    if span:
        s["column_span"] = span
    return s


AC_FEATURES = [{"type": "climate-hvac-modes", "hvac_modes": ["off", "cool", "dry", "fan_only", "auto"]},
               {"type": "target-temperature"}]


def solar_cards(compacto=True):
    c = [heading("Energia solar", "mdi:solar-power-variant"),
         tile("sensor.solar_potencia", "Gerando agora", icon="mdi:solar-power", grid_options={"columns": 6}),
         tile("sensor.solar_energia_hoje", "Gerado hoje", icon="mdi:solar-panel", grid_options={"columns": 6}),
         tile("sensor.solar_economia_hoje", "Economia hoje", grid_options={"columns": 6}),
         tile("sensor.solar_economia_no_mes", "Economia no mês", grid_options={"columns": 6})]
    if compacto:
        c.append({"type": "history-graph", "title": "Geração (24 h)", "hours_to_show": 24,
                  "entities": [{"entity": "sensor.solar_potencia", "name": "Potência"}]})
    return c


def solar_view():
    agora = solar_cards(compacto=False) + [
        tile("sensor.solar_energia_mes", "Gerado no mês", icon="mdi:solar-panel-large", grid_options={"columns": 6}),
        tile("sensor.solar_cobertura_do_ar_condicionado_hoje", "Solar cobre do ar hoje", icon="mdi:air-conditioner", grid_options={"columns": 6}),
        {"type": "gauge", "entity": "sensor.solar_potencia", "name": "Potência (W)", "min": 0, "max": 4000, "needle": True,
         "severity": {"red": 0, "yellow": 400, "green": 1500}}]
    canais = [heading("Por canal do medidor", "mdi:meter-electric"),
              tile("sensor.medidor_de_energia_solar_potencia_a", "Canal A: potência", grid_options={"columns": 6}),
              tile("sensor.medidor_de_energia_solar_potencia_b", "Canal B: potência", grid_options={"columns": 6}),
              tile("sensor.solar_energia_a_hoje", "Canal A: hoje", grid_options={"columns": 6}),
              tile("sensor.solar_energia_b_hoje", "Canal B: hoje", grid_options={"columns": 6}),
              {"type": "entities", "title": "Rede elétrica", "entities": [
                  {"entity": "sensor.medidor_de_energia_solar_tensao_a", "name": "Tensão A"},
                  {"entity": "sensor.medidor_de_energia_solar_tensao_b", "name": "Tensão B"},
                  {"entity": "sensor.medidor_de_energia_solar_corrente_a", "name": "Corrente A"},
                  {"entity": "sensor.medidor_de_energia_solar_corrente_b", "name": "Corrente B"},
                  {"entity": "sensor.medidor_de_energia_solar_total_energy", "name": "Total acumulado"}]}]
    graficos = [heading("Histórico", "mdi:chart-areaspline"),
                {"type": "history-graph", "title": "Potência por canal (hoje)", "hours_to_show": 24,
                 "entities": [{"entity": "sensor.medidor_de_energia_solar_potencia_a", "name": "Canal A"},
                              {"entity": "sensor.medidor_de_energia_solar_potencia_b", "name": "Canal B"}]},
                {"type": "statistics-graph", "title": "Geração por dia (kWh)", "chart_type": "bar", "period": "day",
                 "days_to_show": 30, "stat_types": ["change"],
                 "entities": [{"entity": "sensor.medidor_de_energia_solar_total_energy", "name": "Geração"}]},
                {"type": "statistics-graph", "title": "Geração solar x ar-condicionado por dia (kWh)", "chart_type": "bar",
                 "period": "day", "days_to_show": 30, "stat_types": ["change"],
                 "entities": [{"entity": "sensor.medidor_de_energia_solar_total_energy", "name": "Solar"}] +
                             [{"entity": f"sensor.ar_{k}_energia", "name": f"Ar {n}"} for k, n, _ in ACS]},
                {"type": "history-graph", "title": "Tensão da rede (24 h)", "hours_to_show": 24,
                 "entities": [{"entity": "sensor.medidor_de_energia_solar_tensao_a", "name": "Fase A"},
                              {"entity": "sensor.medidor_de_energia_solar_tensao_b", "name": "Fase B"}]}]
    return {"title": "Solar", "path": "solar", "icon": "mdi:solar-power-variant", "type": "sections", "max_columns": 3,
            "sections": [section(agora), section(canais), section(graficos, 2)]}


def casa():
    clima = [heading("Clima", "mdi:thermometer")]
    for k, n, e in ACS:
        clima.append(tile(e, f"Ar {n}", features=AC_FEATURES, state_content=["hvac_mode", "current_temperature"]))
    clima += [tile("sensor.ar_condicionado_potencia_total", "Potência dos ares", grid_options={"columns": 6}),
              tile("sensor.ar_condicionado_custo_hoje", "Custo hoje", grid_options={"columns": 6}),
              {"type": "weather-forecast", "entity": "weather.forecast_casa", "forecast_type": "daily", "show_forecast": True}]

    cams = [heading("Câmeras", "mdi:cctv")]
    for cam, n, mov in CAMERAS:
        cams.append({"type": "picture-entity", "entity": cam, "name": n, "show_state": False,
                     "camera_view": "live"})
    cams.append({"type": "glance", "show_state": True, "state_color": True,
                 "entities": [{"entity": mov, "name": n} for _, n, mov in CAMERAS if mov]})
    cams.append(tile("alarm_control_panel.flamingos_paradise_alarm_manager", "Alarme"))

    pessoas = [heading("Pessoas e dispositivos", "mdi:account-group")]
    for dt, n, bat in PESSOAS:
        pessoas.append(tile(dt, n, grid_options={"columns": 6}))
    pessoas.append({"type": "entities", "title": "Baterias", "state_color": True,
                    "entities": [{"entity": bat, "name": n} for _, n, bat in PESSOAS]})

    rede = [heading("Rede", "mdi:router-network"),
            tile("sensor.flamingos_paradise_state", "Gateway", grid_options={"columns": 6}),
            tile("sensor.usw_flex_2_5g_8_poe_state", "Switch", grid_options={"columns": 6}),
            tile("sensor.u7_pro_escritorio_state", "AP Escritório", grid_options={"columns": 6}),
            tile("sensor.u7_pro_1o_andar_state", "AP 1º andar", grid_options={"columns": 6}),
            tile("sensor.leviata_clients", "Wi-Fi Leviatã", icon="mdi:wifi", grid_options={"columns": 6}),
            tile("sensor.matrix_clients", "Wi-Fi Matrix", icon="mdi:wifi", grid_options={"columns": 6}),
            {"type": "gauge", "entity": "sensor.flamingos_paradise_storage_utilization", "name": "Disco das câmeras",
             "severity": {"green": 0, "yellow": 85, "red": 95}, "needle": True}]

    midia = [heading("Mídia e impressora", "mdi:multimedia"),
             tile("sensor.mediacenter_clientes_ativos", "Jellyfin: assistindo", icon="mdi:play-network"),
             tile("sensor.hp_smart_tank_710_720_series", "Impressora", icon="mdi:printer")]
    for cor, nome in (("black", "Preto"), ("cyan", "Ciano"), ("magenta", "Magenta"), ("yellow", "Amarelo")):
        midia.append({"type": "gauge", "entity": f"sensor.hp_smart_tank_710_720_series_{cor}_cartridge",
                      "name": nome, "severity": {"red": 0, "yellow": 15, "green": 30},
                      "grid_options": {"columns": 3, "rows": 2}})

    sistema = [heading("Sistema", "mdi:home-assistant"),
               tile("update.home_assistant_core_update", "Home Assistant Core"),
               tile("update.home_assistant_operating_system_update", "Home Assistant OS"),
               tile("update.home_assistant_supervisor_update", "Supervisor"),
               tile("update.flamingos_paradise_firmware", "Firmware do gateway"),
               tile("update.u7_pro_escritorio_firmware", "Firmware AP Escritório"),
               tile("update.u7_pro_1o_andar_firmware", "Firmware AP 1º andar"),
               tile("update.usw_flex_2_5g_8_poe_firmware", "Firmware do switch"),
               tile("sensor.backup_last_successful_automatic_backup", "Último backup", icon="mdi:backup-restore")]

    inicio = {"title": "Início", "path": "inicio", "icon": "mdi:home", "type": "sections", "max_columns": 4,
              "sections": [section(clima), section(solar_cards()), section(cams), section(pessoas), section(rede), section(midia), section(sistema)]}
    cameras = {"title": "Câmeras", "path": "cameras", "icon": "mdi:cctv", "type": "sections", "max_columns": 2,
               "sections": [section([{"type": "picture-entity", "entity": cam, "name": n, "camera_view": "live",
                                      "show_state": False}] + ([tile(mov, "Movimento")] if mov else [])) for cam, n, mov in CAMERAS]}
    return {"title": "Casa", "views": [inicio, solar_view(), cameras]}


def ar():
    resumo = [heading("Agora", "mdi:air-conditioner"),
              tile("sensor.ar_condicionado_aparelhos_ligados", "Aparelhos ligados", icon="mdi:air-conditioner", grid_options={"columns": 6}),
              tile("sensor.ar_condicionado_potencia_total", "Potência estimada", grid_options={"columns": 6}),
              tile("sensor.ar_condicionado_consumo_hoje", "Consumo hoje", grid_options={"columns": 6}),
              tile("sensor.ar_condicionado_custo_hoje", "Custo hoje", grid_options={"columns": 6}),
              tile("sensor.ar_condicionado_consumo_no_mes", "Consumo no mês", grid_options={"columns": 6}),
              tile("sensor.ar_condicionado_custo_no_mes", "Custo no mês", grid_options={"columns": 6}),
              {"type": "history-graph", "title": "Potência estimada (24 h)", "hours_to_show": 24,
               "entities": [{"entity": f"sensor.ar_{k}_potencia_estimada", "name": n} for k, n, _ in ACS]}]
    secs = [section(resumo, 2)]
    for k, n, e in ACS:
        cards = [heading(f"Ar {n}", "mdi:air-conditioner"),
                 {"type": "thermostat", "entity": e, "name": n,
                  "features": [{"type": "climate-hvac-modes", "hvac_modes": ["off", "cool", "dry", "fan_only", "heat", "auto"]},
                               {"type": "climate-fan-modes", "style": "dropdown"},
                               {"type": "climate-preset-modes", "style": "dropdown"}]},
                 tile(f"sensor.ar_{k}_tempo_ligado_hoje", "Ligado hoje", icon="mdi:timer-outline", grid_options={"columns": 6}),
                 tile(f"sensor.ar_{k}_tempo_ligado_no_mes", "Ligado no mês", icon="mdi:timer", grid_options={"columns": 6}),
                 tile(f"sensor.ar_{k}_consumo_dia", "Consumo hoje", icon="mdi:lightning-bolt", grid_options={"columns": 6}),
                 tile(f"sensor.ar_{k}_custo_hoje", "Custo hoje", grid_options={"columns": 6}),
                 tile(f"sensor.ar_{k}_consumo_mes", "Consumo no mês", icon="mdi:lightning-bolt", grid_options={"columns": 6}),
                 tile(f"sensor.ar_{k}_custo_no_mes", "Custo no mês", grid_options={"columns": 6}),
                 {"type": "history-graph", "title": "Temperatura (24 h)", "hours_to_show": 24,
                  "entities": [{"entity": f"sensor.ar_{k}_temperatura", "name": "no cômodo"},
                               {"entity": f"sensor.ar_{k}_temperatura_desejada", "name": "desejada"}]},
                 {"type": "entities", "entities": [
                     {"entity": f"switch.{e.split('.')[1]}_quiet_mode", "name": "Modo silencioso"},
                     {"entity": f"switch.{e.split('.')[1]}_xtra_fan", "name": "X-Fan (secagem)"},
                     {"entity": f"switch.{e.split('.')[1]}_luz_do_painel", "name": "Luz do painel"}]}]
        secs.append(section(cards))
    visao = {"title": "Visão geral", "path": "visao-geral", "icon": "mdi:air-conditioner", "type": "sections",
             "max_columns": 3, "sections": secs}
    hist = [heading("Histórico", "mdi:chart-bar"),
            {"type": "statistics-graph", "title": "Consumo por dia (kWh, estimado)", "chart_type": "bar",
             "period": "day", "days_to_show": 30, "stat_types": ["change"],
             "entities": [{"entity": f"sensor.ar_{k}_energia", "name": n} for k, n, _ in ACS]},
            {"type": "statistics-graph", "title": "Consumo por mês (kWh, estimado)", "chart_type": "bar",
             "period": "month", "days_to_show": 365, "stat_types": ["change"],
             "entities": [{"entity": f"sensor.ar_{k}_energia", "name": n} for k, n, _ in ACS]},
            {"type": "history-graph", "title": "Quando esteve ligado (7 dias)", "hours_to_show": 168,
             "entities": [{"entity": f"binary_sensor.ar_{k}_ligado", "name": n} for k, n, _ in ACS]},
            {"type": "statistics-graph", "title": "Temperatura dos cômodos (média por hora, 7 dias)", "period": "hour",
             "days_to_show": 7, "stat_types": ["mean"], "chart_type": "line",
             "entities": [{"entity": f"sensor.ar_{k}_temperatura", "name": n} for k, n, _ in ACS]},
            {"type": "entities", "title": "Tempo ligado", "entities":
                [item for k, n, _ in ACS for item in (
                    {"type": "section", "label": f"Ar {n}"},
                    {"entity": f"sensor.ar_{k}_tempo_ligado_hoje", "name": "Hoje"},
                    {"entity": f"sensor.ar_{k}_tempo_ligado_na_semana", "name": "Na semana"},
                    {"entity": f"sensor.ar_{k}_tempo_ligado_no_mes", "name": "No mês"})]}]
    historico = {"title": "Histórico", "path": "historico", "icon": "mdi:chart-bar", "type": "sections",
                 "max_columns": 2, "sections": [section(hist[:3], 2), section(hist[3:], 2)]}
    ajustes = [heading("Ajustes da estimativa", "mdi:tune"),
               {"type": "markdown", "content":
                "A Gree **não mede consumo**. A potência é **estimada** a partir da potência nominal de cada "
                "aparelho, do modo de operação e da diferença entre a temperatura do cômodo e a desejada "
                "(aparelhos inverter trabalham com mais carga quanto maior a diferença).\n\n"
                "Para a estimativa ficar próxima da conta de luz, informe abaixo a **potência nominal de "
                "refrigeração** de cada aparelho (etiqueta do Inmetro ou manual, em W) e a tarifa com impostos."},
               {"type": "entities", "entities": [{"entity": "input_number.tarifa_energia", "name": "Tarifa (R$/kWh)"}] +
                [{"entity": f"input_number.ac_{k}_potencia_nominal", "name": f"Potência nominal: {n}"} for k, n, _ in ACS]}]
    aj = {"title": "Ajustes", "path": "ajustes", "icon": "mdi:tune", "type": "sections", "max_columns": 1,
          "sections": [section(ajustes)]}
    return {"title": "Ar-condicionado", "views": [visao, historico, aj]}


if __name__ == "__main__":
    print(json.dumps(casa(), ensure_ascii=False))
    print(json.dumps(ar(), ensure_ascii=False))
