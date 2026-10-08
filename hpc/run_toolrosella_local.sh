#!/usr/bin/env bash
# ToolRosella baseline, best-effort configuration, run locally (Windows, Git Bash): the generator is an online model,
# so no GPU is needed. Same pinned ToolRosella commit and pinned codes as hpc/run_toolrosella.sh.
# Best effort, decided 2026-10-08 after the H200 run (Qwen2.5-72B generator: 1/3 conversions, failures traced to
# generated files mixing Markdown fences and prose, which ToolRosella's extraction keeps as code):
#   - generator closer to the one recommended by the authors (gpt-5 / claude-4-sonnet): codestral-latest (free tier);
#   - ToolRosella's documented repair switch on (TOOLROSELLA_CODECHECK_REPAIR=true; default false);
#   - ATTEMPTS independent attempts per code (fresh workspace each); a code counts as converted if one attempt
#     passes ToolRosella's own criterion. ToolRosella's code is not modified.
# Usage: bash hpc/run_toolrosella_local.sh [attempts]   (from semantic-sim-layer; ToolRosella in ../baselines/ToolRosella
# with its .venv-tr and a private .env holding the generator key)
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TR="$(dirname "$HERE")/baselines/ToolRosella"
ATTEMPTS="${1:-3}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$(dirname "$HERE")/baselines/toolrosella-local-$STAMP"; mkdir -p "$OUT"
REPOS=("https://github.com/cyrilvoyant/tunnel-load-simulator 748e053" \
       "https://github.com/cyrilvoyant/LQL-Equiv-web dfc9a33" \
       "https://github.com/darothen/pyrcel 977e909")
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$OUT/steps.log"; }
PY="$TR/.venv-tr/Scripts/python.exe"
[ -x "$PY" ] || { log "ERROR: ToolRosella venv missing"; exit 1; }
command -v uv >/dev/null && { log "ERROR: uv on PATH (pip-less uv branch); remove it first"; exit 1; }
export TOOLROSELLA_CODECHECK_REPAIR=true PYTHONIOENCODING=utf-8 PYTHONUTF8=1
log "ToolRosella 20f57dd, generator $(grep -m1 '^OPENAI_MODEL=' "$TR/.env" | cut -d= -f2), repair on, $ATTEMPTS attempts"
for a in $(seq 1 "$ATTEMPTS"); do
  WS="$OUT/a$a/workspace"
  for entry in "${REPOS[@]}"; do
    url="${entry% *}"; rev="${entry#* }"; name="$(basename "$url")"
    # pinned source pre-placed; an empty .git marker makes ToolRosella skip its own clone (as on the H200)
    mkdir -p "$WS/$name/source" && cp -a "$HERE/external/$name/." "$WS/$name/source/" && rm -rf "$WS/$name/source/.git" \
      && mkdir -p "$WS/$name/source/.git" || { log "ERROR: copy of $name failed"; exit 1; }
    log "attempt $a: ToolRosella on $name (pinned $rev)"
    ( cd "$TR" && timeout 2h "$PY" main.py "Please use $url to build MCP tools." --max-repositories 1 \
        --workspace "$(cygpath -w "$WS")" > "$OUT/a$a/toolrosella-$name.log" 2>&1 )
    code=$?
    ok=$(grep -q "Code execution successful, review passed" "$OUT/a$a/toolrosella-$name.log" && echo success || echo failure)
    env=$(grep -ao '"type": *"[a-z]*"' "$WS/$name/mcp_output/env_info.json" 2>/dev/null | head -1)
    log "attempt $a: $name exit $code, $ok, env $env, $(tail -n 1 "$OUT/a$a/toolrosella-$name.log")"
    venv_py=$(ls -d "$WS/$name/${name}"_*_venv/Scripts/python.exe 2>/dev/null | head -1)
    if [ -n "$venv_py" ]; then  # tools/list as a client sees it, in the environment ToolRosella built for the code
      ( cd "$WS/$name" && "$venv_py" "$HERE/hpc/export_mcp_tools.py" "$WS" "$OUT/a$a/tools" "$name" ) >> "$OUT/steps.log" 2>&1
    fi
  done
done
log "done; results in $OUT"
