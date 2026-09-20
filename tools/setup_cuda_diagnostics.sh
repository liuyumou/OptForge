#!/usr/bin/env bash
# Build the ADR-0022 diagnostic microbenchmarks. Diagnostics only: never a build
# dependency, never a solver path, never evidence outside a charged acceptance run.
set -euo pipefail
cd "$(dirname "$0")/.."
out="$(pwd)/target/native/cuda"
mkdir -p "$out"
exec 9>"$out/build.lock"
flock --exclusive 9
nvcc="${AI_OPTIMIZER_NVCC:-/usr/local/cuda/bin/nvcc}"
"$nvcc" -std=c++17 -arch=sm_120 -O3 -lineinfo -fmad=false -ftz=false -diag-suppress 1650 \
  -o "$out/fp64_pipe_bench" cuda/diagnostics/fp64_pipe_bench.cu
"$nvcc" -std=c++17 -arch=sm_120 -O3 -o "$out/launch_overhead" cuda/diagnostics/launch_overhead.cu
