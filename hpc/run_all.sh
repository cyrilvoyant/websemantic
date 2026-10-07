#!/usr/bin/env bash
# Orchestrator, started from a JupyterLab terminal of an H200 session (the SSH login node has no GPU and Python 3.6).
# /workspace = /lustre/data/cyril.voyant.kg ; project in /workspace/semantic/websemantic.
#
#   MODE=smoke (default): preflight + 2 cases per domain, conditions F000 and F111, 1 repetition.
#   MODE=full           : preflight + whole factorial campaign (qualifiers then pilot, 3 repetitions).
# A smoke run never turns into the full campaign: the full one needs an explicit MODE=full.
#
# 1. Preflight barrier, sequential, before any model call: CPU environment (pinned pyrcel 2.0.0, import path and
#    source hash recorded), reproducibility of the three published examples (S9), GPU environment.
# 2. Two lanes in parallel: GPU = for each open model (Qwen, then Mistral): vLLM server, E1 campaign, server stopped;
#    CPU = numerical replay, one parallel job per (model, domain), whenever the set of answers changes, then a final
#    replay. If one lane fails, the other is stopped. Status files are written atomically, in UTC.
# 3. A lock directory + heartbeat prevent two simultaneous runs; push.ps1 refuses to push while the heartbeat is fresh.
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"          # .../websemantic/semantic-sim-layer
BASE="$(dirname "$HERE")"                          # .../websemantic
MODE="${MODE:-smoke}"
case "$MODE" in smoke|full) ;; *) echo "MODE must be smoke or full"; exit 1;; esac
CAMPAIGN="${CAMPAIGN:-$(date -u +%Y%m%dT%H%M%SZ)-$MODE}"
LOGS="$BASE/logs/$CAMPAIGN"; mkdir -p "$LOGS"
# Open models, two families, served one after the other on the H200 (both ungated on Hugging Face, checked 2026-10-07):
# Qwen2.5-72B-Instruct (Qwen licence; YaRN x2 for a 64k context) and Mistral-Small-3.2-24B-Instruct-2506 (Apache-2.0).
MODELS="${MODELS:-qwen mistral}"
GPU_ENV="$BASE/venv-gpu"; CPU_ENV="$BASE/venv-cpu"
MAX_HOURS="${MAX_HOURS:-48}"; REPLAY_EVERY="${REPLAY_EVERY:-600}"
LOCK="$BASE/run_all.lock.d"; HEARTBEAT="$BASE/heartbeat"
RUNS="$BASE/benchmark-reserve/runs/e1"
export HF_HOME="$BASE/hf-cache"
VLLM_PID=""; GPU_PID=""; CPU_PID=""

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" || {
  echo "Python >= 3.11 required (pyrcel 2.0.0); found $(python3 --version). Use a JupyterLab H200 terminal."; exit 1; }

# ---------- lock: one run at a time; a stale lock (heartbeat older than 5 min) is taken over ----------
fresh() { [ -f "$HEARTBEAT" ] && [ $(( $(date +%s) - $(stat -c %Y "$HEARTBEAT") )) -lt 300 ]; }
if ! mkdir "$LOCK" 2>/dev/null; then
  if fresh; then echo "Another run_all.sh is active ($(cat "$LOCK/campaign" 2>/dev/null)). Stop."; exit 1; fi
  echo "Stale lock found (no heartbeat for 5 min): taken over."
fi
echo "$CAMPAIGN" > "$LOCK/campaign"; touch "$HEARTBEAT"

status() {  # lane step detail -> status-<lane>.json, atomic, UTC
  python3 - "$BASE/status-$1.json" "$2" "$3" "$CAMPAIGN" <<'PY'
import json, os, sys, time
path, step, detail, campaign = sys.argv[1:]
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump({"campaign": campaign, "step": step, "detail": detail,
               "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, f, indent=1)
os.replace(tmp, path)
PY
}

cleanup() {
  for p in "$GPU_PID" "$CPU_PID"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done
  VLLM_PID=$(cat "$LOGS/vllm.pid" 2>/dev/null || true)          # safety net if a lane died without its own trap
  if [ -n "$VLLM_PID" ]; then kill -- "-$VLLM_PID" 2>/dev/null || kill "$VLLM_PID" 2>/dev/null; fi
  rm -rf "$LOCK"
}
trap cleanup EXIT
trap 'echo "interrupted"; exit 130' INT TERM

fail() { status "$1" error "$2"; echo "ERROR [$1]: $2"; exit 1; }   # in a lane subshell, exits that lane only

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

# ---------- 1. preflight barrier (sequential; any failure stops everything before a model call) ----------
status cpu preflight "CPU environment"
# pyrcel comes from the pinned source in external/pyrcel (977e909). The archive has no .git, so setuptools-scm
# needs the version given explicitly; the check verifies that exact version is the one imported.
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PYRCEL=2.0.0
ensure_env "$CPU_ENV" cpu \
  "import numpy, pandas, yaml, rdflib, pydantic, jax, pyrcel, importlib.metadata as m; assert m.version('pyrcel') == '2.0.0'" \
  numpy pandas pyyaml rdflib pydantic "jax[cpu]" "$HERE/external/pyrcel"
{ "$CPU_ENV/bin/python" -c "import pyrcel, importlib.metadata as m; print('pyrcel', m.version('pyrcel'), pyrcel.__file__)"
  echo "external/pyrcel source sha256: $(cd "$HERE/external/pyrcel" && find . -type f ! -path './.git*' -print0 | sort -z \
        | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)"; } > "$LOGS/pyrcel-provenance.txt" || fail cpu "pyrcel provenance"
export JAX_ENABLE_X64=true JAX_PLATFORMS=cpu PYTHONPATH="$HERE/src:$HERE/evaluation/e1"

status cpu preflight "reproducibility of the three examples (S9)"
mkdir -p "$LOGS/repro"; : > "$LOGS/repro/summary.txt"; bad=0
for M in tls lql pyrcel; do
  if "$CPU_ENV/bin/python" -m websemantic.replay "$HERE/examples/$M-complete.json" --model "$M" --workspace "$HERE" \
       --output-dir "$LOGS/repro" > "$LOGS/repro/$M.json" 2>&1; then echo "$M ok" >> "$LOGS/repro/summary.txt"
  else echo "$M FAILED" >> "$LOGS/repro/summary.txt"; bad=1; fi
done
[ "$bad" -eq 0 ] || fail cpu "reproducibility failures, see logs/$CAMPAIGN/repro/summary.txt"

status gpu preflight "GPU environment"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv > "$LOGS/gpu.txt" 2>&1 \
  || fail gpu "no GPU visible: start run_all.sh from a JupyterLab H200 session"
ensure_env "$GPU_ENV" gpu "import vllm, yaml, mistral_common" "vllm>=0.9.1,<1" "mistral_common>=1.6.2" pyyaml

# ---------- 2. lanes ----------
if [ "$MODE" = smoke ]; then CORPORA="qualifiers"; REPS="1"; CONDS="F000,F111"; LIMIT=2
else CORPORA="qualifiers pilot"; REPS="1 2 3"; CONDS="F000,F100,F010,F001,F110,F101,F011,F111"; LIMIT=0; fi
TAG="$CAMPAIGN"
SETSID=""; command -v setsid >/dev/null && SETSID="setsid"   # own process group: vLLM workers stopped together

model_spec() {  # key -> HF id, served name, extra vLLM arguments
  case "$1" in
    qwen) HF_ID="Qwen/Qwen2.5-72B-Instruct"; SERVED="qwen2.5-72b"
          EXTRA=(--quantization fp8 --kv-cache-dtype fp8 --enable-prefix-caching --rope-scaling '{"rope_type":"yarn","factor":2.0,"original_max_position_embeddings":32768}');;
    mistral) HF_ID="mistralai/Mistral-Small-3.2-24B-Instruct-2506"; SERVED="mistral-small-3.2-24b"
          EXTRA=(--tokenizer-mode mistral --config-format mistral --load-format mistral --enable-prefix-caching);;
    *) return 1;;
  esac
}

stop_vllm() {  # lane-level: the PID lives in the lane, is written to a file for the parent, and its group is killed
  if [ -n "${LANE_VLLM:-}" ]; then kill -- "-$LANE_VLLM" 2>/dev/null || kill "$LANE_VLLM" 2>/dev/null
    for _ in $(seq 1 30); do kill -0 "$LANE_VLLM" 2>/dev/null || break; sleep 2; done; fi
  LANE_VLLM=""; rm -f "$LOGS/vllm.pid"
}

gpu_lane() {
  LANE_VLLM=""
  trap stop_vllm EXIT
  trap 'stop_vllm; exit 143' TERM INT
  for KEY in $MODELS; do
    model_spec "$KEY" || fail gpu "unknown model key $KEY"
    status gpu server "starting $HF_ID"
    $SETSID "$GPU_ENV/bin/vllm" serve "$HF_ID" --served-model-name "$SERVED" --max-model-len 65536 "${EXTRA[@]}" \
      --port 8000 --seed 0 > "$LOGS/vllm-$KEY.log" 2>&1 &
    LANE_VLLM=$!; echo "$LANE_VLLM" > "$LOGS/vllm.pid"
    for _ in $(seq 1 180); do                                  # up to 1 h for download + loading
      curl -sf http://localhost:8000/v1/models | grep -q "\"$SERVED\"" && break
      kill -0 "$LANE_VLLM" 2>/dev/null || fail gpu "vLLM stopped for $KEY, see logs/$CAMPAIGN/vllm-$KEY.log"
      sleep 20
    done
    curl -sf http://localhost:8000/v1/models | grep -q "\"$SERVED\"" || fail gpu "vLLM not serving $SERVED after 1 h"
    for CORPUS in $CORPORA; do
      for REP in $REPS; do
        # One client per (domain, condition), all at once: vLLM batches the concurrent requests on the GPU.
        status gpu e1 "$SERVED $CORPUS rep $REP (parallel clients)"
        local pids=() names=() i
        for D in tls lqlequiv pyrcel; do
          for C in ${CONDS//,/ }; do
            "$GPU_ENV/bin/python" "$HERE/evaluation/e1/run_e1.py" --model "local:$SERVED" --tag "$TAG" --corpus "$CORPUS" \
              --domains "$D" --conditions "$C" --reps "$REP" --limit "$LIMIT" --pause 0 \
              >> "$LOGS/e1-$KEY-$D-$C.log" 2>&1 &
            pids+=("$!"); names+=("$D $C")
          done
        done
        for i in "${!pids[@]}"; do
          wait "${pids[$i]}" || fail gpu "E1 $SERVED $CORPUS rep $REP ${names[$i]} failed"
        done
      done
    done
    stop_vllm
  done
  status gpu done "campaign finished ($MODELS)"
}

fingerprint() {  # changes when an answer is added, removed or replaced (name, size, mtime)
  find "$RUNS" -name '*.json' ! -name 'contexts-*' -printf '%P %s %T@\n' 2>/dev/null | sort | sha256sum | cut -d' ' -f1
}

replay_all() {  # deterministic, idempotent replay of this campaign's answers; failures logged and counted
  local n_fail=0 M
  local pids=() names=() i
  status cpu replay "$1"
  for M in "$RUNS"/*__"$TAG"/; do               # one parallel job per (model, domain): distinct output files
    [ -d "$M" ] || continue
    M=$(basename "$M")
    for D in tls lqlequiv pyrcel; do
      "$CPU_ENV/bin/python" "$HERE/evaluation/e1/numeric_e1.py" "$M" "$D" >> "$LOGS/replay-$M-$D.log" 2>&1 &
      pids+=("$!"); names+=("$M $D")
    done
  done
  for i in "${!pids[@]}"; do
    wait "${pids[$i]}" || { echo "$(date -u +%FT%TZ) replay ${names[$i]} failed" >> "$LOGS/cpu-failures.log"; n_fail=$((n_fail + 1)); }
  done
  return "$n_fail"
}

cpu_lane() {
  local start last="" now; start=$(date +%s)
  while kill -0 "$GPU_PID" 2>/dev/null; do
    now=$(fingerprint)
    if [ "$now" != "$last" ]; then replay_all "new answers"; last="$now"; fi
    [ $(( $(date +%s) - start )) -gt $(( MAX_HOURS * 3600 )) ] && fail cpu "time limit ${MAX_HOURS} h reached"
    sleep "$REPLAY_EVERY"
  done
  replay_all "final" || fail cpu "final replay: $? failure(s), see logs/$CAMPAIGN/cpu-failures.log"
  status cpu done "replay finished"
}

gpu_lane > "$LOGS/gpu.log" 2>&1 &
GPU_PID=$!
cpu_lane > "$LOGS/cpu.log" 2>&1 &
CPU_PID=$!

# Supervision: heartbeat every 10 s; the first lane that fails stops the other.
GPU_RC=""; CPU_RC=""
while :; do
  touch "$HEARTBEAT"
  if [ -z "$GPU_RC" ] && ! kill -0 "$GPU_PID" 2>/dev/null; then wait "$GPU_PID"; GPU_RC=$?; fi
  if [ -z "$CPU_RC" ] && ! kill -0 "$CPU_PID" 2>/dev/null; then wait "$CPU_PID"; CPU_RC=$?; fi
  if [ "${GPU_RC:-0}" -ne 0 ] || [ "${CPU_RC:-0}" -ne 0 ]; then
    echo "a lane failed (gpu=${GPU_RC:-running}, cpu=${CPU_RC:-running}): stopping the other"; break
  fi
  [ -n "$GPU_RC" ] && [ -n "$CPU_RC" ] && break
  sleep 10
done
echo "campaign $CAMPAIGN ($MODE): gpu lane exit ${GPU_RC:-killed}, cpu lane exit ${CPU_RC:-killed}"
[ "${GPU_RC:-1}" -eq 0 ] && [ "${CPU_RC:-1}" -eq 0 ]
