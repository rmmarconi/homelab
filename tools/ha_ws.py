#!/usr/bin/env python3
"""ha_ws.py '<json sem id>' [...] — WebSocket API do Home Assistant (10.1.1.11), só biblioteca padrão.
Token lido de ~/.config/ha/token (nunca impresso). Imprime o 'result' de cada mensagem, uma por linha."""
import base64, json, os, socket, struct, sys

HOST, PORT = os.environ.get("HA_HOST", "10.1.1.11"), 80


def frame(data):
    b = data.encode()
    h = bytearray([0x81])
    n = len(b)
    if n < 126:
        h.append(0x80 | n)
    elif n < 65536:
        h.append(0x80 | 126); h += struct.pack(">H", n)
    else:
        h.append(0x80 | 127); h += struct.pack(">Q", n)
    m = os.urandom(4)
    return bytes(h) + m + bytes(c ^ m[i % 4] for i, c in enumerate(b))


def recv_exact(s, n):
    buf = b""
    while len(buf) < n:
        c = s.recv(n - len(buf))
        if not c:
            raise EOFError
        buf += c
    return buf


def recv(s):
    data = b""
    while True:
        b1, b2 = recv_exact(s, 2)
        n = b2 & 0x7F
        if n == 126:
            n = struct.unpack(">H", recv_exact(s, 2))[0]
        elif n == 127:
            n = struct.unpack(">Q", recv_exact(s, 8))[0]
        data += recv_exact(s, n)
        if b1 & 0x80:
            return json.loads(data)


def main():
    token = open(os.path.expanduser("~/.config/ha/token")).read().strip()
    s = socket.create_connection((HOST, PORT), timeout=120)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall((f"GET /api/websocket HTTP/1.1\r\nHost: {HOST}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += s.recv(1)
    recv(s)
    s.sendall(frame(json.dumps({"type": "auth", "access_token": token})))
    if recv(s).get("type") != "auth_ok":
        sys.exit("auth falhou")
    for i, raw in enumerate(sys.argv[1:], 1):
        msg = json.loads(raw)
        msg["id"] = i
        s.sendall(frame(json.dumps(msg)))
        while True:
            r = recv(s)
            if r.get("id") == i and r.get("type") == "result":
                print(json.dumps(r.get("result") if r.get("success") else {"erro": r.get("error")}, ensure_ascii=False))
                break


if __name__ == "__main__":
    main()
