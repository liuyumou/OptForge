#!/usr/bin/env bash
# Run only under the separately budgeted GPUP-5 acceptance supervisor.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${AI_OPTIMIZER_GPU_LEASE:-}" != inherited ]]; then
  echo 'precision acceptance requires inherited shared host lease' >&2
  exit 2
fi
export AI_OPTIMIZER_GPU=1
if [[ "${1:-}" == regular ]]; then
  for package in optimizer-cuda optimizer-schedule-examples optimizer-lp-cuda; do
    cargo test --release -p "$package" --test device -- --test-threads 1 --nocapture
  done
else
  binary=$(cargo test --release -p optimizer-lp-cuda --test device --no-run --message-format=json | python3 -c 'import sys,json; rows=[json.loads(line) for line in sys.stdin]; files=[r["executable"] for r in rows if r.get("reason")=="compiler-artifact" and r.get("target",{}).get("name")=="device" and r.get("executable")]; assert len(files)==1; print(files[0])')
  /usr/local/cuda/bin/compute-sanitizer --error-exitcode 99 --tool "$1" "$binary" precision_ --test-threads 1 --nocapture
fi
