#!/usr/bin/env bash
# ADR-0035 provisioning only; no ordinary build invokes nvcc.
set -euo pipefail
cd "$(dirname "$0")/.."
out="$(pwd)/target/native/cuda"
mkdir -p "$out"
exec 9>"$out/build.lock"
flock --exclusive 9
nvcc="${AI_OPTIMIZER_NVCC:-/usr/local/cuda/bin/nvcc}"
for stage in cubin ptx; do
  "$nvcc" --"$stage" -std=c++17 -arch=sm_120 -O3 -lineinfo -fmad=false -ftz=false \
    --ptxas-options=-v -o "$out/lp_pdhg_exec.$stage" cuda/lp_pdhg_exec/lp_pdhg_exec.cu
done
