#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test "${AI_OPTIMIZER_GPU_LEASE:-}" = inherited
test -n "${CUDA_VISIBLE_DEVICES:-}"
test "$#" = 2
export AI_OPTIMIZER_GPU=1
exec /usr/local/cuda/bin/compute-sanitizer --tool "$2" --error-exitcode 86 --target-processes all "$1" tensor_ --nocapture --test-threads 1
