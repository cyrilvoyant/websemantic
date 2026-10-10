"""Local stand-in for the Cloudflare relay, to test the web app on localhost (never deployed).

Serves webapp/ on http://localhost:8000 and the relay on http://localhost:8787 (open
http://localhost:8000/?relay=http://localhost:8787). Same prompt as relay/worker.js; the Mistral key is read from the
local .env (a Codestral key works with MISTRAL_MODEL=codestral-latest).
Usage: python tools/dev_relay.py
"""

import json
import os
import re
import threading
import urllib.request
from functools import partial
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "webapp"
SYSTEM = re.search(r"const SYSTEM = `(.*?)`;", (ROOT / "relay" / "worker.js").read_text(encoding="utf-8"), re.S).group(1)
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines() if (ROOT / ".env").exists() else []:
    if line.startswith("MISTRAL_API_KEY=") and not os.environ.get("MISTRAL_API_KEY"):
        os.environ["MISTRAL_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
MODEL = os.environ.get("MISTRAL_MODEL", "codestral-latest")


class Relay(BaseHTTPRequestHandler):
    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        c = json.loads((WEB / "llm" / f"{body['code']}.json").read_text(encoding="utf-8"))
        prompt = (f"SUPPORTED TASKS: {json.dumps(c['tasks'], ensure_ascii=False)}\nCONTRACT:\n{c['contract']}\n"
                  f"PARAMETERS:\n{json.dumps(c['params'], ensure_ascii=False)}\n"
                  f"CURRENT SCENARIO:\n{json.dumps(body.get('state') or {}, ensure_ascii=False)}\n"
                  f"REPLY LANGUAGE for message and questions: {'French' if body.get('lang') == 'fr' else 'English'}\n"
                  f"NEW MESSAGE:\n{body['message']}")
        host = "codestral.mistral.ai" if MODEL.startswith("codestral") else "api.mistral.ai"
        payload = {"model": MODEL, "temperature": 0, "response_format": {"type": "json_object"},
                   "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
        req = urllib.request.Request(f"https://{host}/v1/chat/completions", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + os.environ["MISTRAL_API_KEY"]})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = json.load(r)
            self._send(200, {"parsed": json.loads(raw["choices"][0]["message"]["content"])})
        except Exception:  # noqa: BLE001 - local test tool
            self._send(503, {"error": "llm"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    web = ThreadingHTTPServer(("127.0.0.1", 8000), partial(SimpleHTTPRequestHandler, directory=str(WEB)))
    threading.Thread(target=web.serve_forever, daemon=True).start()
    print("web app: http://localhost:8000/?relay=http://localhost:8787", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8787), Relay).serve_forever()
