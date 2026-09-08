#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 2 || "$1" != GPU-* ]]; then
  echo "usage: bash tools/gpu_job.sh GPU-UUID command [args...]" >&2
  exit 2
fi
device="$1"
shift
export CUDA_VISIBLE_DEVICES="$device"
export AI_OPTIMIZER_GPU_LOCK="${AI_OPTIMIZER_GPU_LOCK:-/tmp/ai-optimizer-gpu.lock}"
# Keep the parent flock process alive until the foreground job exits. The child
# also inherits the descriptor, retaining ownership if the parent is terminated.
exec flock --exclusive --timeout 300 "$AI_OPTIMIZER_GPU_LOCK" "$@"
