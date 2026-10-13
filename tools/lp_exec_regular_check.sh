#!/usr/bin/env bash
# Already-built suites: driver/scheduling, scheduling producer and LP kernels.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ "${AI_OPTIMIZER_GPU_LEASE:-}" == inherited && $# == 3 ]] || { echo 'three regular device suites and inherited lease required' >&2; exit 2; }
export AI_OPTIMIZER_GPU=1
for binary in "$@"; do
  "$binary" --test-threads 1 --nocapture
done
