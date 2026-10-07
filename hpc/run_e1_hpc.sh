#!/usr/bin/env bash
# E1 factorial campaign with an open-weight model on one H200 (JupyterLab terminal, Lustre mounted on /workspace).
# Usage: bash hpc/run_e1_hpc.sh   (from /workspace/websemantic/semantic-sim-layer)
set -euo pipefail
MODEL="${MODEL:-Qwen/Qwen2.5-72B-Instruct}"
SERVED="${SERVED:-qwen2.5-72b}"
ENV=/workspace/venv-e1
LOG=/workspace/logs; mkdir -p "$LOG"
export HF_HOME=/workspace/hf-cache          # model weights stay on Lustre, never in Git
if [ ! -d "$ENV" ]; then python3 -m venv "$ENV"; "$ENV/bin/pip" install -q "vllm>=0.6" pyyaml; fi
nvidia-smi --query-gpu=name,memory.total --format=csv | tee "$LOG/gpu.txt"
# FP8 weights (~72 GB) fit one H200; YaRN x2 gives 64k tokens of context (largest prompt ~45k tokens).
nohup "$ENV/bin/vllm" serve "$MODEL" --served-model-name "$SERVED" --quantization fp8 --max-model-len 65536 \
  --rope-scaling '{"rope_type":"yarn","factor":2.0,"original_max_position_embeddings":32768}' \
  --port 8000 --seed 0 > "$LOG/vllm.log" 2>&1 &
until curl -sf http://localhost:8000/v1/models >/dev/null; do sleep 20; done
echo "server ready" | tee -a "$LOG/e1.log"
for CORPUS in qualifiers pilot; do
  for REP in 1 2 3; do
    "$ENV/bin/python" evaluation/e1/run_e1.py --model "local:$SERVED" --corpus "$CORPUS" --reps "$REP" --pause 0 \
      --conditions F000,F100,F010,F001,F110,F101,F011,F111 >> "$LOG/e1.log" 2>&1
  done
done
echo "E1 done" | tee -a "$LOG/e1.log"
