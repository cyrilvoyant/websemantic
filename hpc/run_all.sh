#!/usr/bin/env bash
# Orchestrator inside a JupyterLab session (H200 + CPUs, Lustre on /workspace).
# Two lanes in parallel, each in series:
#   GPU lane: vLLM server (open model) -> E1 factorial campaign, 3 repetitions, qualifiers then pilot
#   CPU lane: environment for the backends -> numerical replay of every answer available -> reproducibility replays
# A status file (status.json) is rewritten at each step; status.ps1 reads it over SSH.
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"          # .../websemantic/semantic-sim-layer
BASE="$(dirname "$HERE")"                          # .../websemantic
LOGS="$BASE/logs"; mkdir -p "$LOGS"
MODEL="${MODEL:-Qwen/Qwen2.5-72B-Instruct}"; SERVED="${SERVED:-qwen2.5-72b}"
GPU_ENV="$BASE/venv-gpu"; CPU_ENV="$BASE/venv-cpu"
export HF_HOME="$BASE/hf-cache"
# The SSH login node has Python 3.6 and no GPU: run this script from a JupyterLab H200 session.
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" || {
  echo "Python >= 3.10 required (found $(python3 --version)). Start run_all.sh from a JupyterLab H200 terminal."; exit 1; }

status() {  # lane step detail
  python3 - "$BASE/status.json" "$1" "$2" "$3" <<'PY'
import json, sys, time
path, lane, step, detail = sys.argv[1:]
try: s = json.load(open(path))
except Exception: s = {}
s[lane] = {"step": step, "detail": detail, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
json.dump(s, open(path, "w"), indent=1)
PY
}

gpu_lane() {
  if ! nvidia-smi >/dev/null 2>&1; then status gpu error "no GPU visible in this shell: start run_all.sh from a JupyterLab H200 session"; return 1; fi
  status gpu install "vllm"
  [ -d "$GPU_ENV" ] || { python3 -m venv "$GPU_ENV" && "$GPU_ENV/bin/pip" install -q "vllm>=0.6" pyyaml; }
  nvidia-smi --query-gpu=name,memory.total --format=csv
  status gpu server "starting $MODEL"
  "$GPU_ENV/bin/vllm" serve "$MODEL" --served-model-name "$SERVED" --quantization fp8 --max-model-len 65536 \
    --rope-scaling '{"rope_type":"yarn","factor":2.0,"original_max_position_embeddings":32768}' \
    --port 8000 --seed 0 > "$LOGS/vllm.log" 2>&1 &
  for i in $(seq 1 180); do                         # up to 1 h for download + loading
    curl -sf http://localhost:8000/v1/models >/dev/null && break
    pgrep -f "vllm serve" >/dev/null || { status gpu error "vLLM stopped, see logs/vllm.log"; return 1; }
    sleep 20
  done
  curl -sf http://localhost:8000/v1/models >/dev/null || { status gpu error "vLLM not ready after 1 h"; return 1; }
  for CORPUS in qualifiers pilot; do
    for REP in 1 2 3; do
      status gpu e1 "$CORPUS rep $REP"
      "$GPU_ENV/bin/python" "$HERE/evaluation/e1/run_e1.py" --model "local:$SERVED" --corpus "$CORPUS" --reps "$REP" \
        --pause 0 --conditions F000,F100,F010,F001,F110,F101,F011,F111
    done
  done
  status gpu done "campaign finished"
}

cpu_lane() {
  status cpu install "backends"
  [ -d "$CPU_ENV" ] || { python3 -m venv "$CPU_ENV" && "$CPU_ENV/bin/pip" install -q numpy pandas pyyaml rdflib "jax[cpu]" pyrcel==2.0.0; }
  export JAX_ENABLE_X64=true JAX_PLATFORMS=cpu PYTHONPATH="$HERE/src:$HERE/evaluation/e1"
  while true; do                                    # replay new answers until the GPU lane is done
    for M in "$BASE"/benchmark-reserve/runs/e1/*/; do
      M=$(basename "$M")
      for D in tls lqlequiv pyrcel; do
        status cpu replay "$M $D"
        "$CPU_ENV/bin/python" "$HERE/evaluation/e1/numeric_e1.py" "$M" "$D" > "$LOGS/replay-$M-$D.log" 2>&1
      done
    done
    python3 -c "import json,sys; s=json.load(open('$BASE/status.json')); sys.exit(0 if s.get('gpu',{}).get('step') in ('done','error') else 1)" && break
    sleep 600
  done
  status cpu reproducibility "replay of examples (S9)"
  for M in tls lql pyrcel; do
    "$CPU_ENV/bin/python" -m websemantic.replay "$HERE/examples/$M-complete.json" --model "$M" --workspace "$HERE" \
      --output-dir "$BASE/repro" || true
  done
  status cpu done "replay and reproducibility finished"
}

gpu_lane > "$LOGS/gpu.log" 2>&1 &
cpu_lane > "$LOGS/cpu.log" 2>&1 &
wait
echo "all lanes finished"
