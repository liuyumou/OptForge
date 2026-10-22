#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ "${AI_OPTIMIZER_GPU_LEASE:-}" == inherited ]] || { echo 'refinement acceptance requires inherited lease' >&2; exit 2; }
export AI_OPTIMIZER_GPU=1
if [[ "${2:-regular}" == regular ]]; then
    "$1" --test-threads 1 --nocapture
else
    /usr/local/cuda/bin/compute-sanitizer --error-exitcode 99 --tool "$2" "$1" refine_ --test-threads 1 --nocapture
fi
