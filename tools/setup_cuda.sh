#!/usr/bin/env bash
# Build the device code objects out of tracked source, under SPEC-0010 and ADR-0009.
#
# nvcc is a provisioning dependency, never a build dependency: an ordinary
# `cargo build` must keep working on a host with no toolkit and no device, so this
# script is what a maintainer runs and the build script only probes for its output.
set -euo pipefail
cd "$(dirname "$0")/.."
out="$(pwd)/target/native/cuda"
src="$(pwd)/cuda/schedule_eval"

nvcc="${AI_OPTIMIZER_NVCC:-nvcc}"
if ! command -v "$nvcc" >/dev/null 2>&1; then
    for candidate in /usr/local/cuda/bin/nvcc /usr/local/cuda-13/bin/nvcc; do
        if [[ -x "$candidate" ]]; then nvcc="$candidate"; break; fi
    done
fi
if ! command -v "$nvcc" >/dev/null 2>&1; then
    echo "setup_cuda: nvcc not found; set AI_OPTIMIZER_NVCC or install the CUDA toolkit" >&2
    echo "setup_cuda: the workspace still builds without it and reports an unsupported device backend" >&2
    exit 127
fi

mkdir -p "$out"
# Serialize with the same style of lock the native library build uses, so two
# checkouts provisioning at once cannot interleave writes into one output file.
exec 9>"$out/build.lock"
flock --exclusive 9

# sm_120 is the development hardware's compute capability. The cubin is its fast
# path and avoids driver compilation at load; the PTX beside it is what lets a
# later capability load at all. An earlier capability is refused rather than run,
# which is SPEC-0010 requirement 4.
arch="${AI_OPTIMIZER_CUDA_ARCH:-120}"
for stage in cubin ptx; do
    "$nvcc" --"$stage" -arch="sm_${arch}" -O3 -lineinfo \
        -o "$out/schedule_eval.$stage" "$src/schedule_eval.cu"
done

"$nvcc" --version | tail -2
echo "setup_cuda: wrote $out/schedule_eval.cubin and $out/schedule_eval.ptx for sm_${arch}"
