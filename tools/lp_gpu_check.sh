#!/usr/bin/env bash
# GPUP-3 acceptance: regular suites plus all four sanitizers on added observations.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${AI_OPTIMIZER_GPU_LEASE:-}" != inherited ]]; then
  echo "lp_gpu_check: inherited host lease required" >&2
  exit 2
fi
export AI_OPTIMIZER_GPU=1
sanitizer="${AI_OPTIMIZER_COMPUTE_SANITIZER:-/usr/local/cuda/bin/compute-sanitizer}"
if [[ ! -x "$sanitizer" ]]; then
  echo "lp_gpu_check: all four sanitizers are required" >&2
  exit 2
fi
for package in optimizer-cuda optimizer-schedule-examples optimizer-lp-cuda; do
  cargo test --release -p "$package" --test device -- --test-threads 1 --nocapture 2>&1 | tee "/tmp/gpup3-${package}.log"
  if rg -q 'SKIP' "/tmp/gpup3-${package}.log"; then
    echo "lp_gpu_check: skipped device acceptance" >&2
    exit 2
  fi
done
binary=$(cargo test --release -p optimizer-lp-cuda --test device --no-run --message-format=json | python3 -c 'import sys,json; records=[json.loads(line) for line in sys.stdin]; paths=[r["executable"] for r in records if r.get("reason")=="compiler-artifact" and r.get("target",{}).get("name")=="device" and r.get("executable")]; assert len(paths)==1; print(paths[0])')
for tool in memcheck racecheck initcheck synccheck; do
  "$sanitizer" --error-exitcode 99 --tool "$tool" "$binary" study_observation --test-threads 1 --nocapture 2>&1 | tee "/tmp/gpup3-${tool}.log"
  if rg -q 'SKIP' "/tmp/gpup3-${tool}.log"; then exit 2; fi
  "$sanitizer" --error-exitcode 99 --tool "$tool" "$binary" matched_control --test-threads 1 --nocapture 2>&1 | tee "/tmp/gpup3-matched-${tool}.log"
  if rg -q 'SKIP' "/tmp/gpup3-matched-${tool}.log"; then exit 2; fi
done
# Exercise the actual CLI evidence path and pinned fallback under the same lease.
python3 tools/lp_gpu_cli_check.py
echo "GPUP-3 device acceptance passed; sanitizers: two study_observation and three matched_control cases"
