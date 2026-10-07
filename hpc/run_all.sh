#!/usr/bin/env bash
# Orchestrator, to be started from a JupyterLab terminal of an H200 session (the SSH login node has no GPU and
# Python 3.6). /workspace = /lustre/data/cyril.voyant.kg ; project in /workspace/semantic/websemantic.
# Two lanes in parallel, each in series, each with its own status file (atomic writes):
#   GPU lane: validated environment -> vLLM server (open model) -> E1 factorial, 3 repetitions, qualifiers then pilot
#   CPU lane: validated environment -> numerical replay when new answers appear -> final replay -> reproducibility (S9)
# Every step checks its exit code; a failure stops the lane with status "error" (never "done").
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"          # .../websemantic/semantic-sim-layer
BASE="$(dirname "$HERE")"                          # .../websemantic
LOGS="$BASE/logs"; mkdir -p "$LOGS"
MODEL="${MODEL:-Qwen/Qwen2.5-72B-Instruct}"; SERVED="${SERVED:-qwen2.5-72b}"
GPU_ENV="$BASE/venv-gpu"; CPU_ENV="$BASE/venv-cpu"
MAX_HOURS="${MAX_HOURS:-48}"
export HF_HOME="$BASE/hf-cache"

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" || {
  echo "Python >= 3.11 required (pyrcel 2.0.0); found $(python3 --version). Use a JupyterLab H200 terminal."; exit 1; }

status() {  # lane step detail -> status-<lane>.json, written atomically
  python3 - "$BASE/status-$1.json" "$2" "$3" <<'PY'
import json, os, sys, time
path, step, detail = sys.argv[1:]
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump({"step": step, "detail": detail, "time": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=1)
os.replace(tmp, path)
PY
}

fail() { status "$1" error "$2"; echo "ERROR [$1]: $2"; exit 1; }

ensure_env() {  # env_dir lane "import check" pip-args...   (an incomplete venv is rebuilt, never trusted)
  local env="$1" lane="$2" check="$3"; shift 3
  if ! { [ -x "$env/bin/python" ] && "$env/bin/python" -c "$check" >/dev/null 2>&1; }; then
    rm -rf "$env" && python3 -m venv "$env" || fail "$lane" "venv creation failed"
    "$env/bin/pip" install -q --upgrade pip || fail "$lane" "pip upgrade failed"
    "$env/bin/pip" install -q "$@" || fail "$lane" "dependency installation failed"
    "$env/bin/python" -c "$check" || fail "$lane" "import check failed after installation"
  fi
  "$env/bin/pip" freeze > "$LOGS/freeze-$lane.txt" || fail "$lane" "pip freeze failed"
}

gpu_lane() {
  nvidia-smi >/dev/null 2>&1 || fail gpu "no GPU visible: start run_all.sh from a JupyterLab H200 session"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
  status gpu install "vllm"
  ensure_env "$GPU_ENV" gpu "import vllm, yaml" "vllm>=0.6,<1" pyyaml
  status gpu server "starting $MODEL"
  "$GPU_ENV/bin/vllm" serve "$MODEL" --served-model-name "$SERVED" --quantization fp8 --max-model-len 65536 \
    --rope-scaling '{"rope_type":"yarn","factor":2.0,"original_max_position_embeddings":32768}' \
    --port 8000 --seed 0 > "$LOGS/vllm.log" 2>&1 &
  local vllm_pid=$!
  trap 'kill "$vllm_pid" 2>/dev/null' EXIT
  for _ in $(seq 1 180); do                                   # up to 1 h for download + loading
    curl -sf http://localhost:8000/v1/models >/dev/null && break
    kill -0 "$vllm_pid" 2>/dev/null || fail gpu "vLLM stopped, see logs/vllm.log"
    sleep 20
  done
  curl -sf http://localhost:8000/v1/models >/dev/null || fail gpu "vLLM not ready after 1 h"
  for CORPUS in qualifiers pilot; do
    for REP in 1 2 3; do
      status gpu e1 "$CORPUS rep $REP"
      "$GPU_ENV/bin/python" "$HERE/evaluation/e1/run_e1.py" --model "local:$SERVED" --corpus "$CORPUS" --reps "$REP" \
        --pause 0 --conditions F000,F100,F010,F001,F110,F101,F011,F111 || fail gpu "E1 $CORPUS rep $REP exited with $?"
    done
  done
  status gpu done "campaign finished"
}

replay_all() {  # numeric replay of every model and domain; failures are logged and counted
  local n_fail=0
  for M in "$BASE"/benchmark-reserve/runs/e1/*/; do
    M=$(basename "$M")
    for D in tls lqlequiv pyrcel; do
      status cpu replay "$M $D ($1)"
      "$CPU_ENV/bin/python" "$HERE/evaluation/e1/numeric_e1.py" "$M" "$D" >> "$LOGS/replay-$M-$D.log" 2>&1 \
        || { echo "$(date '+%F %T') replay $M $D exit $?" >> "$LOGS/cpu-failures.log"; n_fail=$((n_fail + 1)); }
    done
  done
  return "$n_fail"
}

count_answers() { find "$BASE/benchmark-reserve/runs/e1" -name '*.json' ! -name 'contexts-*' 2>/dev/null | wc -l; }

cpu_lane() {
  local gpu_pid="$1" start last="" now; start=$(date +%s)
  status cpu install "backends from pinned sources"
  # pyrcel is installed from the pinned source shipped in external/pyrcel (977e909, v2.0.0), not from PyPI.
  ensure_env "$CPU_ENV" cpu "import numpy, pandas, yaml, rdflib, pydantic, jax, pyrcel" \
    numpy pandas pyyaml rdflib pydantic "jax[cpu]" "$HERE/external/pyrcel"
  export JAX_ENABLE_X64=true JAX_PLATFORMS=cpu PYTHONPATH="$HERE/src:$HERE/evaluation/e1"
  while kill -0 "$gpu_pid" 2>/dev/null; do                     # replay only when new answers appeared
    now=$(count_answers)
    if [ "$now" != "$last" ]; then replay_all "$now answers"; last="$now"; fi
    [ $(( $(date +%s) - start )) -gt $(( MAX_HOURS * 3600 )) ] && fail cpu "time limit ${MAX_HOURS} h reached"
    sleep 600
  done
  replay_all "final" || fail cpu "final replay: $? failure(s), see logs/cpu-failures.log"
  status cpu reproducibility "replay of the three examples (S9)"
  mkdir -p "$BASE/repro"; : > "$BASE/repro/summary.txt"
  local bad=0
  for M in tls lql pyrcel; do
    if "$CPU_ENV/bin/python" -m websemantic.replay "$HERE/examples/$M-complete.json" --model "$M" --workspace "$HERE" \
         --output-dir "$BASE/repro" > "$BASE/repro/$M.json" 2>&1; then echo "$M ok" >> "$BASE/repro/summary.txt"
    else echo "$M FAILED (exit $?)" >> "$BASE/repro/summary.txt"; bad=1; fi
  done
  [ "$bad" -eq 0 ] || fail cpu "reproducibility failures, see repro/summary.txt"
  status cpu done "replay and reproducibility finished"
}

gpu_lane > "$LOGS/gpu.log" 2>&1 &
GPU_PID=$!
cpu_lane "$GPU_PID" > "$LOGS/cpu.log" 2>&1 &
CPU_PID=$!
wait "$GPU_PID"; GPU_RC=$?
wait "$CPU_PID"; CPU_RC=$?
echo "gpu lane exit $GPU_RC, cpu lane exit $CPU_RC"
[ "$GPU_RC" -eq 0 ] && [ "$CPU_RC" -eq 0 ]
