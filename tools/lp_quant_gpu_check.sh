#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ "${AI_OPTIMIZER_GPU_LEASE:-}" == inherited ]] || { echo 'quant acceptance requires inherited lease' >&2; exit 2; }
export AI_OPTIMIZER_GPU=1
/usr/local/cuda/bin/compute-sanitizer --error-exitcode 99 --tool "$2" "$1" quant_sanitizer_smoke --exact --test-threads 1 --nocapture
