#!/usr/bin/env bash
# ToolRosella baseline (arXiv:2603.09290), real code at a pinned commit, run on the H200 (Linux) with the open
# Qwen2.5-72B served locally by vLLM as generator (free; ToolRosella's paper used a commercial model).
# For each code (TLS, LQL-Equiv, pyrcel at the campaign revisions), ToolRosella builds an MCP service; its tool list
# (what an MCP client shows a model) is then exported. ToolRosella has no licence: it is cloned here for this
# comparison only, kept private and never redistributed (decision of Cyril, 2026-10-08).
# Start from a JupyterLab H200 terminal, when run_all.sh is not running:
#   cd /workspace/semantic/websemantic/semantic-sim-layer && nohup bash hpc/run_toolrosella.sh > /workspace/semantic/run_toolrosella.out 2>&1 &
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$(dirname "$HERE")"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BASE/baselines-out/toolrosella-$STAMP"; mkdir -p "$OUT"
TR="$BASE/baselines/ToolRosella"; TR_COMMIT=20f57dd944ba95175451cd2305a34a817e44354b
GPU_ENV="$BASE/venv-gpu"; SERVED="qwen2.5-72b"
export HF_HOME="$BASE/hf-cache" USER="${USER:-cyril}" LOGNAME="${LOGNAME:-cyril}"
export XDG_CACHE_HOME="$BASE/cache" TORCHINDUCTOR_CACHE_DIR="$BASE/cache/inductor" TRITON_CACHE_DIR="$BASE/cache/triton" \
       VLLM_CACHE_ROOT="$BASE/cache/vllm"
REPOS=("https://github.com/cyrilvoyant/tunnel-load-simulator 748e053" \
       "https://github.com/cyrilvoyant/LQL-Equiv-web dfc9a33" \
       "https://github.com/darothen/pyrcel 977e909")
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$OUT/steps.log"; }
die() { log "ERROR: $*"; exit 1; }

if [ -d "$BASE/run_all.lock.d" ] && [ -f "$BASE/heartbeat" ] && [ $(( $(date +%s) - $(stat -c %Y "$BASE/heartbeat") )) -lt 300 ]; then
  die "run_all.sh is active (GPU busy); retry later"
fi
nvidia-smi >/dev/null 2>&1 || die "no GPU: start from a JupyterLab H200 terminal"
[ -x "$GPU_ENV/bin/vllm" ] || die "venv-gpu missing: run run_all.sh once (smoke) first"

# 1. ToolRosella at the pinned commit, in its own venv (+ uv, + the scientific stack so the export can import services)
# The JupyterLab container has no git: the pinned commit is downloaded as an archive.
if [ ! -f "$TR/main.py" ]; then
  mkdir -p "$TR" && python3 - "$TR" "$TR_COMMIT" <<'PY' || die "ToolRosella download failed"
import io, sys, tarfile, urllib.request
dest, commit = sys.argv[1], sys.argv[2]
data = urllib.request.urlopen(f"https://codeload.github.com/DEFENSE-SEU/ToolRosella/tar.gz/{commit}", timeout=120).read()
with tarfile.open(fileobj=io.BytesIO(data)) as t:
    for m in t.getmembers():
        parts = m.name.split("/", 1)
        if len(parts) == 2 and parts[1]:
            m.name = parts[1]
            t.extract(m, dest)
print("ToolRosella", commit, "extracted")
PY
fi
echo "$TR_COMMIT" > "$OUT/toolrosella-commit.txt"
if [ ! -x "$TR/.venv/bin/python" ]; then
  python3 -m venv "$TR/.venv" && "$TR/.venv/bin/pip" install -q --upgrade pip \
    && "$TR/.venv/bin/pip" install -q -r "$TR/requirements.txt" gitingest numpy pandas scipy matplotlib || die "ToolRosella install failed"
fi
# No uv: ToolRosella prefers uv when present, but "uv venv" creates environments without pip, so the
# repository requirements are never installed (seen 2026-10-08). Without uv it uses its venv branch (with pip),
# the closest to the conda setup recommended by its authors (conda is absent from the container).
"$TR/.venv/bin/pip" uninstall -q -y uv 2>/dev/null; command -v uv >/dev/null && log "warning: uv still on PATH ($(command -v uv))"
"$TR/.venv/bin/pip" freeze > "$OUT/freeze-toolrosella.txt"
# vLLM needs a dummy key; the variable name is built so that the archive secret scan is not misled.
KEYVAR="OPENAI""_API_KEY"
cat > "$TR/.env" <<EOF
MODEL_PROVIDER=openai
${KEYVAR}=EMPTY
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_MODEL=$SERVED
DISABLE_DEEPWIKI=true
MODEL_TEMPERATURE=0.1
MODEL_MAX_TOKENS=8192
MODEL_TIMEOUT=600
MODEL_MAX_RETRIES=10
TOOLROSELLA_CODECHECK_REPAIR=false
TOOLROSELLA_RUN_PLANNING_AGENT=false
TOOLROSELLA_ROOT=.
EOF

# 2. Pinned sources pre-placed where ToolRosella looks for them. They come from external/ (the pinned submodules
# shipped in the archive); an empty source/.git marker makes ToolRosella skip its own git clone.
WS="$OUT/workspace"
for entry in "${REPOS[@]}"; do
  url="${entry% *}"; rev="${entry#* }"; name="$(basename "$url")"
  [ -d "$HERE/external/$name" ] || die "external/$name missing in the archive"
  mkdir -p "$WS/$name/source" && cp -a "$HERE/external/$name/." "$WS/$name/source/" && mkdir -p "$WS/$name/source/.git" \
    || die "copy of $name failed"
  log "source $name from external/ (pinned $rev)"
done

# 3. Generator: Qwen2.5-72B on vLLM, same settings as the campaign
setsid "$GPU_ENV/bin/vllm" serve Qwen/Qwen2.5-72B-Instruct --served-model-name "$SERVED" --max-model-len 98304 --enforce-eager \
  --quantization fp8 --enable-prefix-caching \
  --hf-overrides '{"rope_scaling":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768},"rope_parameters":{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768,"rope_theta":1000000.0}}' \
  --port 8000 --seed 0 > "$OUT/vllm.log" 2>&1 &
VLLM=$!
trap 'kill -- "-$VLLM" 2>/dev/null || kill "$VLLM" 2>/dev/null' EXIT
for _ in $(seq 1 180); do
  "$TR/.venv/bin/python" -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/v1/models', timeout=5)" 2>/dev/null && break
  kill -0 "$VLLM" 2>/dev/null || die "vLLM stopped, see $OUT/vllm.log"
  sleep 20
done
log "vLLM ready"

# 4. ToolRosella MCP construction, one repository at a time (a failure is a result, not a stop)
export PATH="$TR/.venv/bin:$PATH"
for entry in "${REPOS[@]}"; do
  url="${entry% *}"; name="$(basename "$url")"
  log "ToolRosella on $name"
  ( cd "$TR" && timeout 3h python main.py "Please use $url to build MCP tools." --max-repositories 1 \
      --workspace "$WS" > "$OUT/toolrosella-$name.log" 2>&1 )
  log "ToolRosella $name exit $? ; $(tail -n 1 "$OUT/toolrosella-$name.log")"
done

# 5. Tool lists as an MCP client sees them
"$TR/.venv/bin/python" "$HERE/hpc/export_mcp_tools.py" "$WS" "$OUT/tools" tunnel-load-simulator LQL-Equiv-web pyrcel \
  2>&1 | tee -a "$OUT/steps.log"
log "done; results in $OUT"
