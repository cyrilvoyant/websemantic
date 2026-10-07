#!/usr/bin/env bash
# Stub test of hpc/run_all.sh: fake GPU, vLLM, venvs; checks normal end, GPU failure, CPU preflight failure, lock.
SRC="$(cd "$(dirname "$0")/../.." && pwd)/hpc/run_all.sh"
T="${TMPDIR:-/tmp}/ws-run-all-stub"; rm -rf "$T"; mkdir -p "$T/bin"
mk() { printf '#!/usr/bin/env bash\n%s\n' "$2" > "$1"; chmod +x "$1"; }
mk "$T/bin/nvidia-smi" 'echo "H200, 141 GB"'
mk "$T/bin/python3" 'if [ "$1" = "-" ]; then shift; f=$(mktemp); cat > "$f"; python "$f" "$@"; rc=$?; rm -f "$f"; exit $rc; fi; exec python "$@"'
setup() {
  rm -rf "$T/w"; W="$T/w/websemantic"; mkdir -p "$W/semantic-sim-layer/hpc" "$W/benchmark-reserve/runs/e1"
  cp "$SRC" "$W/semantic-sim-layer/hpc/"
  for v in cpu gpu; do mkdir -p "$W/venv-$v/bin"; mk "$W/venv-$v/bin/pip" 'echo "stub==1"'; done
  mk "$W/venv-cpu/bin/python" '[ "$1" = "-m" ] && [ -n "${FAIL_REPRO:-}" ] && exit 3; exit 0'
  mk "$W/venv-gpu/bin/python" 'case "$*" in *run_e1*) [ -n "${FAIL_GPU:-}" ] && exit 4
     d=$(dirname "$0")/../../benchmark-reserve/runs/e1/local_x__t; mkdir -p "$d"; echo "{}" > "$d/a$RANDOM.json"; sleep 1;; esac; exit 0'
  cat > "$W/venv-gpu/bin/fake_vllm.py" <<'PY'
import http.server, json, sys
name = sys.argv[sys.argv.index("--served-model-name") + 1]
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"data": [{"id": name}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", 8000), H).serve_forever()
PY
  mk "$W/venv-gpu/bin/vllm" 'exec python "$(dirname "$0")/fake_vllm.py" "$@"'
}
run() { (cd "$W/semantic-sim-layer" && PATH="$T/bin:$PATH" CAMPAIGN=t REPLAY_EVERY=1 timeout 120 bash hpc/run_all.sh > "$T/out.txt" 2>&1; echo $? > "$T/rc"); }
check() { # name expected_rc
  local rc; rc=$(cat "$T/rc")
  local left; left=$(python -c "import socket;s=socket.socket();print(int(s.connect_ex(('127.0.0.1',8000))==0))")
  echo "$1: rc=$rc (want $2) gpu=$(sed -n 's/.*"step": "\([^"]*\)".*/\1/p' "$W/status-gpu.json" 2>/dev/null) cpu=$(sed -n 's/.*"step": "\([^"]*\)".*/\1/p' "$W/status-cpu.json" 2>/dev/null) lock=$([ -d "$W/run_all.lock.d" ] && echo kept || echo released) server_left=$left"
}
setup; MODE=full run; check "normal full run" 0; tail -n 1 "$T/out.txt"
setup; FAIL_GPU=1 MODE=full run; check "GPU lane fails" 1; tail -n 2 "$T/out.txt"
setup; FAIL_REPRO=1 run; check "CPU preflight fails (no model call)" 1; ls "$W/benchmark-reserve/runs/e1"
setup; mkdir "$W/run_all.lock.d"; touch "$W/heartbeat"; run; check "second launch while active" 1; tail -n 1 "$T/out.txt"
setup; MODE=bogus run; check "bad MODE" 1
# slow preflight: a concurrent launch during the preflight must be refused (heartbeat kept fresh)
setup; mk "$W/venv-cpu/bin/python" '[ "$1" = "-m" ] && sleep 4; exit 0'
(cd "$W/semantic-sim-layer" && PATH="$T/bin:$PATH" CAMPAIGN=slow HEARTBEAT_EVERY=1 STALE_S=3 REPLAY_EVERY=1 MODE=smoke timeout 120 bash hpc/run_all.sh > "$T/slow.txt" 2>&1) &
sleep 6
(cd "$W/semantic-sim-layer" && PATH="$T/bin:$PATH" CAMPAIGN=second STALE_S=3 timeout 60 bash hpc/run_all.sh > "$T/second.txt" 2>&1; echo "concurrent launch during slow preflight: rc=$? (want 1) $(tail -n 1 "$T/second.txt")")
wait; echo "slow run: $(tail -n 1 "$T/slow.txt")"
# stale lock: dead owner on this host, old heartbeat -> taken over
setup; mkdir "$W/run_all.lock.d"; echo "$(hostname):999999:old" > "$W/run_all.lock.d/owner"; touch -d '1 hour ago' "$W/heartbeat"
run; check "stale lock takeover" 0; grep -m1 "taken over" "$T/out.txt"
# live owner on this host -> refused even with an old heartbeat
setup; sleep 100 & LIVE=$!; mkdir "$W/run_all.lock.d"; echo "$(hostname):$LIVE:other" > "$W/run_all.lock.d/owner"; touch -d '1 hour ago' "$W/heartbeat"
run; check "live owner, old heartbeat" 1; kill $LIVE
