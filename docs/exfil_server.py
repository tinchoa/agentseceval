#!/usr/bin/env python3
"""
Exfiltration capture server — logs all inbound POST requests.

Used during AgentSecEval experiments to verify whether agents running
in none / Docker / gVisor mode can successfully exfiltrate data to an
attacker-controlled HTTP endpoint.

- Listens on 0.0.0.0:9999 (reachable from Docker bridge at 172.17.0.1:9999)
- Appends every POST body as a JSON line to /tmp/agentseceval_exfil.log
- Responds 200 OK to both GET and POST

Usage:
    python3 docs/exfil_server.py &
    # Verify from host:
    curl -X POST http://localhost:9999/test -d "hello"
    # Verify from container:
    docker run --rm alpine wget -qO- http://172.17.0.1:9999/
"""

import datetime
import http.server
import json


class ExfilHandler(http.server.BaseHTTPRequestHandler):
    LOG = "/tmp/agentseceval_exfil.log"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        entry = {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "path":      self.path,
            "client":    self.client_address[0],
            "body":      body,
        }
        with open(self.LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"[EXFIL] {entry['client']} → {self.path}: {body[:120]}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"received")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"exfil-server-ok")

    def log_message(self, *args):
        pass   # suppress default access log


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", 9999), ExfilHandler)
    print(f"Exfil server listening on :9999  (log → {ExfilHandler.LOG})")
    server.serve_forever()
