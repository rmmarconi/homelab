#!/usr/bin/env python3
"""Exporter Prometheus mínimo para o Jellyfin (só biblioteca padrão).

Variáveis de ambiente:
  JELLYFIN_URL      ex.: http://10.1.1.100:8096
  JELLYFIN_API_KEY  chave criada em Painel > Chaves de API
  PORT              porta do /metrics (padrão 9594)
"""
import calendar
import json
import os
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

URL = os.environ.get("JELLYFIN_URL", "http://127.0.0.1:8096").rstrip("/")
KEY = os.environ.get("JELLYFIN_API_KEY", "")
PORT = int(os.environ.get("PORT", "9594"))
ACTIVE_WINDOW = 600  # sessão "ativa" = atividade nos últimos 10 min


def api(path):
    req = urllib.request.Request(URL + path, headers={
        "Authorization": f'MediaBrowser Token="{KEY}"',
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def esc(v):
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def lbl(**kw):
    return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in kw.items()) + "}"



def collect():
    out = []
    add = out.append
    t0 = time.time()
    try:
        info = api("/System/Info")
        sessions = api("/Sessions")
        counts = api("/Items/Counts")
        users = api("/Users")
    except Exception as e:  # noqa: BLE001
        add("# HELP jellyfin_up 1 se a API respondeu")
        add("# TYPE jellyfin_up gauge")
        add("jellyfin_up 0")
        add(f"# erro: {esc(e)}")
        return "\n".join(out) + "\n"

    add("# TYPE jellyfin_up gauge")
    add("jellyfin_up 1")
    add("# TYPE jellyfin_info gauge")
    add("jellyfin_info" + lbl(version=info.get("Version", ""), server=info.get("ServerName", "")) + " 1")
    add("# TYPE jellyfin_pending_restart gauge")
    add(f"jellyfin_pending_restart {int(bool(info.get('HasPendingRestart')))}")
    add("# TYPE jellyfin_update_available gauge")
    add(f"jellyfin_update_available {int(bool(info.get('HasUpdateAvailable')))}")

    add("# HELP jellyfin_items Itens na biblioteca por tipo")
    add("# TYPE jellyfin_items gauge")
    for k, v in counts.items():
        if k.endswith("Count"):
            add("jellyfin_items" + lbl(type=k[:-5]) + f" {v}")

    add("# TYPE jellyfin_users gauge")
    add(f"jellyfin_users {len(users)}")

    now = time.time()
    active = 0
    streams = {"DirectPlay": 0, "DirectStream": 0, "Transcode": 0}
    bitrate = 0
    add("# HELP jellyfin_now_playing 1 por reprodução em andamento")
    add("# TYPE jellyfin_now_playing gauge")
    for s in sessions:
        last = s.get("LastActivityDate", "")
        try:
            ts = calendar.timegm(time.strptime(last[:19], "%Y-%m-%dT%H:%M:%S"))  # Jellyfin devolve UTC
        except Exception:
            ts = 0
        if now - ts <= ACTIVE_WINDOW:
            active += 1
        item = s.get("NowPlayingItem")
        if not item:
            continue
        play = s.get("PlayState", {}) or {}
        method = play.get("PlayMethod") or "DirectPlay"
        streams[method] = streams.get(method, 0) + 1
        ti = s.get("TranscodingInfo") or {}
        bitrate += ti.get("Bitrate") or item.get("Bitrate") or 0
        title = item.get("Name", "")
        if item.get("SeriesName"):
            title = f'{item["SeriesName"]} - {title}'
        add("jellyfin_now_playing" + lbl(
            user=s.get("UserName", ""), client=s.get("Client", ""), device=s.get("DeviceName", ""),
            title=title, type=item.get("Type", ""), method=method,
            paused=str(bool(play.get("IsPaused"))).lower(),
            video_codec=ti.get("VideoCodec", ""), reason=",".join(ti.get("TranscodeReasons", []) or []),
        ) + " 1")

    add("# HELP jellyfin_sessions_active Sessões com atividade nos últimos 10 minutos")
    add("# TYPE jellyfin_sessions_active gauge")
    add(f"jellyfin_sessions_active {active}")
    add("# HELP jellyfin_streams Reproduções em andamento por método")
    add("# TYPE jellyfin_streams gauge")
    for m, n in streams.items():
        add("jellyfin_streams" + lbl(method=m) + f" {n}")
    add("# TYPE jellyfin_streams_bitrate_bps gauge")
    add(f"jellyfin_streams_bitrate_bps {bitrate}")
    add("# TYPE jellyfin_scrape_duration_seconds gauge")
    add(f"jellyfin_scrape_duration_seconds {time.time() - t0:.3f}")
    return "\n".join(out) + "\n"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/metrics":
            self.send_response(404); self.end_headers(); return
        body = collect().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if not KEY:
        print("JELLYFIN_API_KEY vazia: o exporter vai publicar jellyfin_up 0 até ela ser definida", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
