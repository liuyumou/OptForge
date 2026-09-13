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
# Tell the child it does not need to take the lock: this wrapper already holds it
# and execs the child under it, so acquiring again would block on ourselves until
# the timeout below. SPEC-0010 requirement 8.
export AI_OPTIMIZER_GPU_LEASE=inherited
# Keep the parent flock process alive until the foreground job exits. The child
# also inherits the descriptor, retaining ownership if the parent is terminated.
exec flock --exclusive --timeout 300 "$AI_OPTIMIZER_GPU_LOCK" "$@"
