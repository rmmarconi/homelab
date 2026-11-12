#!/usr/bin/env python3
"""Verifica cada serviço do services.json e grava status.json (lido pela página).
"up" = qualquer resposta HTTP < 500 (401/403 de tela de login contam como no ar)."""
import json, os, socket, ssl, sys, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/var/www/painel"
OUT = os.path.join(ROOT, "status", "status.json")
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
OPENER = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=CTX))

def check(s):
    url = s.get("check", s["url"]); t0 = time.monotonic()
    try:
        r = OPENER.open(urllib.request.Request(url, method="GET", headers={"User-Agent": "painel-status"}), timeout=6)
        code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        return s["url"], {"up": False, "error": type(e).__name__}
    return s["url"], {"up": code < 500, "code": code, "ms": int((time.monotonic() - t0) * 1000)}

svcs = [s for c in json.load(open(os.path.join(ROOT, "services.json")))["categories"] for s in c["services"]]
# O próprio mediacenter não usa os rewrites do AdGuard: os domínios servidos pelo nginx daqui
# resolveriam para o IP público (sem NAT loopback). Para eles, conecta em 127.0.0.1 (SNI mantido).
LOCAL = {urllib.parse.urlsplit(s.get("check", s["url"])).hostname for s in svcs if s.get("host") == "mediacenter"} - {"10.1.1.100"}
_gai = socket.getaddrinfo
socket.getaddrinfo = lambda h, *a, **k: _gai("127.0.0.1" if h in LOCAL else h, *a, **k)

with ThreadPoolExecutor(12) as ex:
    res = dict(ex.map(check, svcs))
tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump({"checked_at": int(time.time()), "results": res}, f)
os.replace(tmp, OUT)
