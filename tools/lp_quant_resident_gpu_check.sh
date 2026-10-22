#!/usr/bin/env bash
# A scoped sanitizer job, always launched by the shared-host allocator.
set -euo pipefail
cd "$(dirname "$0")/.."
test "${AI_OPTIMIZER_GPU_LEASE:-}" = inherited
test -n "${CUDA_VISIBLE_DEVICES:-}"
test "$#" = 2
binary="$1"
sanitizer="$2"
export AI_OPTIMIZER_GPU=1
exec /usr/local/cuda/bin/compute-sanitizer --tool "$sanitizer" --error-exitcode 86 --target-processes all "$binary" resident_ --nocapture --test-threads 1
