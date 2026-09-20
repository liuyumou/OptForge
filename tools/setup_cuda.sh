#!/usr/bin/env bash
# Build the device code objects out of tracked source, under SPEC-0010 and ADR-0009.
#
# nvcc is a provisioning dependency, never a build dependency: an ordinary
# `cargo build` must keep working on a host with no toolkit and no device, so this
# script is what a maintainer runs and the build script only probes for its output.
set -euo pipefail
cd "$(dirname "$0")/.."
out="$(pwd)/target/native/cuda"
src="$(pwd)/cuda"

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
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --tuned-only ) ]]; then
    echo "usage: setup_cuda.sh [--tuned-only]" >&2
    exit 2
fi
if [[ "${1:-}" != --tuned-only ]]; then
for stage in cubin ptx; do
    "$nvcc" --"$stage" -arch="sm_${arch}" -O3 -lineinfo \
        -o "$out/schedule_eval.$stage" "$src/schedule_eval/schedule_eval.cu"
done

# The linear-programming kernels are built with -fmad=false. Fused multiply-add
# rounds once where the host rounds twice, and it is the only contraction that
# stands between these kernels and bitwise agreement with the host engine: Rust
# never contracts, and IEEE-754 binary64 add, multiply, divide and square root are
# correctly rounded and identical to x86-64 otherwise. Disabling it costs nothing
# measurable here, because SPEC-0011's own arithmetic puts the sparse product at
# roughly 0.17 operations per byte with about fivefold headroom before the FP64
# rate could bind.
#
# That agreement is a property of this toolchain pair rather than a contract:
# requirement 8 asks only for same-device reproducibility. The device suite
# re-verifies it on every run instead of assuming it.
for stage in cubin ptx; do
    "$nvcc" --"$stage" -arch="sm_${arch}" -O3 -lineinfo -fmad=false \
        -o "$out/lp_pdhg.$stage" "$src/lp_pdhg/lp_pdhg.cu"
done

# A second code object with an atomic reduction substituted, built only so the
# determinism assertion can be shown to be able to fail. Nothing loads it outside
# the test that exists to watch it break the assertion, which is what SPEC-0011's
# acceptance section asks for.
"$nvcc" --cubin -arch="sm_${arch}" -O3 -lineinfo -fmad=false \
    -DAI_OPTIMIZER_ATOMIC_REDUCTION \
    -o "$out/lp_pdhg_atomic.cubin" "$src/lp_pdhg/lp_pdhg.cu"

"$nvcc" --version | tail -2
echo "setup_cuda: wrote $out/schedule_eval.{cubin,ptx}, $out/lp_pdhg.{cubin,ptx}"
echo "setup_cuda: and $out/lp_pdhg_atomic.cubin for sm_${arch}"

fi

# GPUP-4 uses a separate code object; ordinary Cargo builds never invoke nvcc.
"$nvcc" --cubin -arch="sm_${arch}" -O3 -lineinfo -fmad=false \
    -o "$out/lp_pdhg_tuned.cubin" "$src/lp_pdhg_tuned/lp_pdhg_tuned.cu"
"$nvcc" --ptx -arch="sm_${arch}" -O3 -lineinfo -fmad=false \
    -o "$out/lp_pdhg_tuned.ptx" "$src/lp_pdhg_tuned/lp_pdhg_tuned.cu"

# GPUP-5 retains all preceding code-object identities.
for stage in cubin ptx; do
    "$nvcc" --"$stage" -arch="sm_${arch}" -O3 -lineinfo -fmad=false -ftz=false \
        -o "$out/lp_pdhg_precision.$stage" "$src/lp_pdhg_precision/lp_pdhg_precision.cu"
done
