#!/usr/bin/env bash
# ADR-0030: invoked only by the bounded setup acceptance supervisor.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${AI_OPTIMIZER_GPU_LEASE:-}" != inherited ]]; then
  echo 'setup acceptance requires inherited shared host lease' >&2
  exit 2
fi
export AI_OPTIMIZER_GPU=1
if [[ -x /tmp/ai-optimizer-cargo/bin/cargo ]]; then
  export PATH="/tmp/ai-optimizer-cargo/bin:$PATH"
fi
if [[ -z "${RUSTUP_HOME:-}" && -d /tmp/ai-optimizer-rustup ]]; then
  export RUSTUP_HOME=/tmp/ai-optimizer-rustup
fi
export CARGO_BUILD_JOBS=4
log=$(mktemp /tmp/gpup-setup-gpu-gate.XXXXXX)
trap 'rm -f "$log"' EXIT
reject_uncovered() {
  if rg -q 'SKIP|RACECHECK SUMMARY: [1-9]' "$log"; then
    echo 'setup gate has skipped coverage or race hazards' >&2
    exit 2
  fi
}
if [[ "${1:-}" == regular ]]; then
  for package in optimizer-cuda optimizer-schedule-examples optimizer-lp-cuda; do
    cargo test --release -p "$package" --test device -- --test-threads 1 --nocapture 2>&1 | tee "$log"
    reject_uncovered
  done
elif [[ "${1:-}" == cli ]]; then
  python3 tools/lp_adaptive_cli_check.py
else
  binary=$(cargo test --release -p optimizer-lp-cuda --test device --no-run --message-format=json | python3 -c 'import sys,json; rows=[json.loads(line) for line in sys.stdin]; files=[r["executable"] for r in rows if r.get("reason")=="compiler-artifact" and r.get("target",{}).get("name")=="device" and r.get("executable")]; assert len(files)==1; print(files[0])')
  "${AI_OPTIMIZER_COMPUTE_SANITIZER:-/usr/local/cuda/bin/compute-sanitizer}" --error-exitcode 99 --tool "$1" "$binary" primary_ --test-threads 1 --nocapture 2>&1 | tee "$log"
  reject_uncovered
fi
