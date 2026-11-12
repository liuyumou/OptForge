#!/usr/bin/env bash
# Isolated research workspaces need explicit CPU coverage outside the root workspace.
set -euo pipefail
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=""
mkdir -p target
for package in lp-fp4-gpu-pilot lp-fp4-fast lp-fp4-integrate lp-fp4-accel lp-fp4-checker; do
    cargo test --manifest-path "research/$package/Cargo.toml" --release --locked
    cargo build --manifest-path "research/$package/Cargo.toml" --release --locked
done
python3 -m unittest discover -s tests/integration -p 'test_lp_fp4*.py'
