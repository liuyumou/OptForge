#!/usr/bin/env bash
# Device acceptance for SPEC-0010. Run under tools/gpu_job.sh, which takes the host
# lease and names one physical UUID:
#
#   bash tools/gpu_job.sh GPU-<uuid> bash tools/gpu_check.sh
#
# This is deliberately not part of tools/check.sh. The ordinary gate is CPU-only and
# must stay that way: every task record in this project states a resource budget, and
# a gate that silently took the host lease and ran kernels would make the ones saying
# "CPU only" false. It would also contend on a lock that permits one holder per host.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${AI_OPTIMIZER_GPU_LEASE:-}" != "inherited" ]]; then
    echo "gpu_check: no inherited lease; run this under tools/gpu_job.sh" >&2
    exit 2
fi

cargo="${AI_OPTIMIZER_CARGO:-cargo}"
if ! command -v "$cargo" >/dev/null 2>&1; then
    for candidate in /tmp/ai-optimizer-cargo/bin/cargo "$HOME/.cargo/bin/cargo"; do
        if [[ -x "$candidate" ]]; then cargo="$candidate"; break; fi
    done
fi

if [[ ! -f target/native/cuda/schedule_eval.cubin ]]; then
    echo "gpu_check: no code object; run bash tools/setup_cuda.sh first" >&2
    exit 2
fi

export AI_OPTIMIZER_GPU=1
"$cargo" test --release -p optimizer-cuda --test device
# The device-backed producer lives with the other scheduling producers, so its
# contracts do too; both suites are device acceptance and neither is complete alone.
"$cargo" test --release -p optimizer-schedule-examples --test device
# The first-order LP kernels under SPEC-0011. A third suite rather than a third
# case in an existing one: it is a different contract with a different oracle, and
# its bitwise agreement is with the host engine rather than with an exact integer
# recurrence.
"$cargo" test --release -p optimizer-lp-cuda --test device

sanitizer="${AI_OPTIMIZER_COMPUTE_SANITIZER:-compute-sanitizer}"
if ! command -v "$sanitizer" >/dev/null 2>&1; then
    for candidate in /usr/local/cuda/bin/compute-sanitizer; do
        if [[ -x "$candidate" ]]; then sanitizer="$candidate"; break; fi
    done
fi
if ! command -v "$sanitizer" >/dev/null 2>&1; then
    echo "################################################################################"
    echo "# WARNING: compute-sanitizer NOT found. Kernel memory, race, initialization and"
    echo "# synchronization checking did NOT run. This is NOT complete device acceptance"
    echo "# and must not be recorded as one."
    echo "################################################################################"
    exit 0
fi

# The test binary is rebuilt above, so pick the newest matching artifact rather than
# hard-coding a hash that changes on every edit.
# All three suites build a binary called `device-*`; sanitize each, newest first,
# and require all three to be present so a rename cannot silently drop one from the
# gate.
mapfile -t binaries < <(ls -t target/release/deps/device-* | grep -v '\.d$' | head -3)
if [[ ${#binaries[@]} -lt 3 ]]; then
    echo "gpu_check: expected three device test binaries, found ${#binaries[@]}" >&2
    exit 2
fi
# One thread: the sanitizers serialize device work anyway, and a parallel harness
# makes a reported hazard hard to attribute to a test.
for tool in memcheck racecheck initcheck synccheck; do
    for binary in "${binaries[@]}"; do
        echo "gpu_check: compute-sanitizer --tool $tool $(basename "$binary")"
        "$sanitizer" --tool "$tool" "$binary" --test-threads 1
    done
done
echo "gpu_check: device acceptance and all four sanitizers passed"
