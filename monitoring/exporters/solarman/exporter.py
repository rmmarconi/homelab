#!/usr/bin/env python3
"""Exporter Prometheus para microinversores Deye/Solarman (só biblioteca padrão).

Lê os registradores Modbus pelo protocolo Solarman V5 (TCP 8899 do logger
Wi-Fi embutido no micro). Não usa a senha da interface web: o protocolo só
exige o número de série do logger, que se descobre com
  echo -n WIFIKIT-214028-READ | nc -u -w2 <ip> 48899

Variáveis de ambiente:
  SOLARMAN_TARGETS  lista "nome=ip:serial" separada por vírgula
                    ex.: micro1=10.2.0.251:3926222475,micro2=10.2.0.190:3926982436
  SITE              rótulo do local (padrão: pais)
  PORT              porta do /metrics (padrão 9595)

À noite o micro desliga junto com o logger: solarman_up fica 0 e as demais
séries somem até o sol voltar (o painel usa last_over_time).
"""
import os
import random
import socket
import struct
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "9595"))
SITE = os.environ.get("SITE", "pais")
TIMEOUT = float(os.environ.get("SOLARMAN_TIMEOUT", "5"))


def targets():
    out = []
    for item in os.environ.get("SOLARMAN_TARGETS", "").split(","):
        item = item.strip()
        if not item:
            continue
        name, rest = item.split("=", 1)
        ip, serial = rest.rsplit(":", 1)
        out.append((name, ip, int(serial)))
    return out


# ---------- Modbus RTU + Solarman V5 ----------

def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return struct.pack("<H", crc)


def v5_frame(serial, modbus):
    seq = random.randint(0, 0xFFFF)
    payload = b"\x02" + b"\x00\x00" + b"\x00" * 12 + modbus
    head = struct.pack("<HHHI", len(payload), 0x4510, seq, serial)
    body = head + payload
    return b"\xa5" + body + bytes([sum(body) & 0xFF]) + b"\x15"


def read_regs(sock, serial, start, count, slave=1):
    rtu = struct.pack(">BBHH", slave, 3, start, count)
    sock.sendall(v5_frame(serial, rtu + crc16(rtu)))
    need = 25 + 5 + 2 * count + 2  # cabeçalho V5 + RTU + checksum/fim
    buf = b""
    deadline = time.time() + TIMEOUT
    while len(buf) < need and time.time() < deadline:
        chunk = sock.recv(1024)
        if not chunk:
            break
        buf += chunk
        if buf[:1] == b"\xa5" and len(buf) >= 3:
            need = 3 + struct.unpack("<H", buf[1:3])[0] + 10
    if len(buf) < 30 or buf[0] != 0xA5:
        raise IOError(f"resposta V5 inválida ({len(buf)} bytes)")
    rtu_resp = buf[25:-2]
    if rtu_resp[1] & 0x80:
        raise IOError(f"exceção Modbus {rtu_resp[2]}")
    n = rtu_resp[2]
    if crc16(rtu_resp[:3 + n]) != rtu_resp[3 + n:5 + n]:
        raise IOError("CRC Modbus inválido")
    return list(struct.unpack(f">{n // 2}H", rtu_resp[3:3 + n]))


def read_inverter(ip, serial, attempts=3):
    """Lê os 3 blocos; o logger às vezes ignora um pedido, então reconecta e tenta de novo."""
    regs = {}
    blocks = [(0, 20), (59, 33), (109, 8)]
    err = None
    for _ in range(attempts):
        try:
            with socket.create_connection((ip, 8899), timeout=TIMEOUT) as s:
                s.settimeout(TIMEOUT)
                while blocks:
                    start, count = blocks[0]
                    for i, v in enumerate(read_regs(s, serial, start, count)):
                        regs[start + i] = v
                    blocks.pop(0)
            return regs
        except (OSError, IndexError) as e:
            err = e
            time.sleep(1)
    raise err


def u32(regs, lo):
    return regs[lo] + (regs[lo + 1] << 16)


def decode(regs):
    sn = "".join(chr(regs[r] >> 8) + chr(regs[r] & 0xFF) for r in range(3, 8)).strip("\x00 ")
    pv = {}
    for i, (d, tot) in enumerate(((65, 69), (66, 71), (67, 74), (68, 77)), start=1):
        v = regs[109 + 2 * (i - 1)] / 10
        a = regs[110 + 2 * (i - 1)] / 10
        pv[i] = {"voltage": v, "current": a, "power": round(v * a, 1),
                 "today": regs[d] / 10, "total": u32(regs, tot) / 10}
    return {
        "serial": sn,
        "rated_w": regs[16] / 10,
        "ac_w": u32(regs, 86) / 10,
        "today": regs[60] / 10,
        "total": u32(regs, 63) / 10,
        "grid_v": regs[73] / 10,
        "grid_hz": regs[79] / 100,
        "temp_c": (regs[90] - 1000) / 100,
        "pv": pv,
    }


# ---------- Prometheus ----------

def lbl(**kw):
    return "{" + ",".join(f'{k}="{v}"' for k, v in kw.items()) + "}"


def scrape_one(t):
    name, ip, serial = t
    t0 = time.time()
    try:
        return name, ip, decode(read_inverter(ip, serial)), None, time.time() - t0
    except Exception as e:  # noqa: BLE001
        return name, ip, None, e, time.time() - t0


METRICS = [
    ("solarman_up", "1 se o logger respondeu"),
    ("solarman_scrape_seconds", "tempo da leitura Modbus"),
    ("solarman_last_success_timestamp_seconds", "instante da última leitura boa"),
    ("solar_info", "número de série e potência nominal do micro"),
    ("solar_ac_power_watts", "potência CA entregue pelo micro"),
    ("solar_energy_today_kwh", "energia gerada hoje pelo micro"),
    ("solar_energy_total_kwh", "energia gerada desde a instalação"),
    ("solar_grid_voltage_volts", "tensão da rede"),
    ("solar_grid_frequency_hertz", "frequência da rede"),
    ("solar_temperature_celsius", "temperatura do dissipador"),
    ("solar_pv_voltage_volts", "tensão CC da placa"),
    ("solar_pv_current_amperes", "corrente CC da placa"),
    ("solar_pv_power_watts", "potência CC da placa (V x A)"),
    ("solar_pv_energy_today_kwh", "energia gerada hoje pela placa"),
    ("solar_pv_energy_total_kwh", "energia gerada pela placa desde a instalação"),
]


CACHE = {}          # nome -> (resultado, instante da última leitura boa)
POLL = float(os.environ.get("SOLARMAN_POLL", "30"))
MAX_AGE = float(os.environ.get("SOLARMAN_MAX_AGE", "300"))


def poller(t):
    """Lê um micro em loop; o /metrics serve o último valor bom (até MAX_AGE)."""
    while True:
        r = scrape_one(t)
        prev = CACHE.get(t[0])
        if r[2] is not None or prev is None or time.time() - prev[1] > MAX_AGE:
            CACHE[t[0]] = (r, time.time() if r[2] is not None else (prev[1] if prev else 0))
        time.sleep(POLL)


def collect():
    rows = {m: [] for m, _ in METRICS}
    ts = targets()
    if CACHE:
        results = [CACHE[t[0]][0] for t in ts if t[0] in CACHE]
    else:
        with ThreadPoolExecutor(max_workers=max(1, len(ts))) as ex:
            results = list(ex.map(scrape_one, ts))
    for name, ip, d, err, dt in results:
        base = dict(site=SITE, inverter=name)
        rows["solarman_up"].append((base, 0 if d is None else 1))
        rows["solarman_scrape_seconds"].append((base, round(dt, 3)))
        if name in CACHE and CACHE[name][1]:
            rows["solarman_last_success_timestamp_seconds"].append((base, round(CACHE[name][1])))
        if d is None:
            rows["solarman_up"][-1] = (dict(base, error=str(err)[:80].replace('"', "'")), 0)
            continue
        rows["solar_info"].append((dict(base, ip=ip, serial=d["serial"], rated_w=int(d["rated_w"])), 1))
        rows["solar_ac_power_watts"].append((base, d["ac_w"]))
        rows["solar_energy_today_kwh"].append((base, d["today"]))
        rows["solar_energy_total_kwh"].append((base, d["total"]))
        rows["solar_grid_voltage_volts"].append((base, d["grid_v"]))
        rows["solar_grid_frequency_hertz"].append((base, d["grid_hz"]))
        rows["solar_temperature_celsius"].append((base, d["temp_c"]))
        for i, p in d["pv"].items():
            lp = dict(base, pv=str(i))
            rows["solar_pv_voltage_volts"].append((lp, p["voltage"]))
            rows["solar_pv_current_amperes"].append((lp, p["current"]))
            rows["solar_pv_power_watts"].append((lp, p["power"]))
            rows["solar_pv_energy_today_kwh"].append((lp, p["today"]))
            rows["solar_pv_energy_total_kwh"].append((lp, p["total"]))
    out = []
    for m, h in METRICS:
        if not rows[m]:
            continue
        out.append(f"# HELP {m} {h}")
        out.append(f"# TYPE {m} gauge")
        out.extend(f"{m}{lbl(**l)} {v}" for l, v in rows[m])
    return "\n".join(out) + "\n"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        body = collect().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if os.environ.get("ONCE"):
        print(collect(), end="")
    else:
        import threading
        for t in targets():
            threading.Thread(target=poller, args=(t,), daemon=True).start()
            time.sleep(2)
        ThreadingHTTPServer(("", PORT), H).serve_forever()
