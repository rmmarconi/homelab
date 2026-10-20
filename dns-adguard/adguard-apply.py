#!/usr/bin/env python3
"""Aplica adguard-config.json num AdGuard Home pela API. Senha do admin lida do stdin."""
import base64, json, sys, urllib.request
URL = "http://127.0.0.1"
pw = sys.stdin.readline().strip()
cfg = json.load(open(sys.argv[1]))
AUTH = "Basic " + base64.b64encode(f"admin:{pw}".encode()).decode()

def api(path, body=None, method=None):
    r = urllib.request.Request(URL + path, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Authorization": AUTH, "Content-Type": "application/json"},
                               method=method or ("POST" if body is not None else "GET"))
    with urllib.request.urlopen(r, timeout=180) as resp:
        t = resp.read()
        return json.loads(t) if t[:1] in (b"{", b"[") else t.decode()

api("/control/dns_config", cfg["dns"])
api("/control/querylog/config/update", cfg["querylog"], "PUT")
api("/control/stats/config/update", cfg["stats"], "PUT")
api("/control/filtering/config", cfg["filtering"])
have = {f["url"] for f in api("/control/filtering/status").get("filters") or []}
for f in cfg["filters"]:
    if f["url"] not in have:
        api("/control/filtering/add_url", {"name": f["name"], "url": f["url"], "whitelist": False})
api("/control/filtering/set_rules", {"rules": cfg["user_rules"]})
api("/control/filtering/refresh", {"whitelist": False})
st = api("/control/filtering/status")
tot = sum(f.get("rules_count", 0) for f in st.get("filters") or [])
print("listas:", len(st.get("filters") or []), "| regras carregadas:", tot, "| regras do usuário:", len(st.get("user_rules") or []))
d = api("/control/dns_info")
print("upstreams:", d.get("upstream_dns"), "| PTR local:", d.get("local_ptr_upstreams"), "| ratelimit:", d.get("ratelimit"))
