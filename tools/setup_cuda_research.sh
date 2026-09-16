#!/usr/bin/env bash
# Provision only ADR-0021; never rebuild archived/legacy code objects.
set -euo pipefail
cd "$(dirname "$0")/.."
out="$(pwd)/target/native/cuda"
mkdir -p "$out"
exec 9>"$out/build.lock"
flock --exclusive 9
nvcc="${AI_OPTIMIZER_NVCC:-/usr/local/cuda/bin/nvcc}"
for stage in cubin ptx; do
  "$nvcc" --"$stage" -std=c++17 -arch=sm_120 -O3 -lineinfo -fmad=false -ftz=false \
    -o "$out/lp_pdhg_research.$stage" cuda/lp_pdhg_research/lp_pdhg_research.cu
done
