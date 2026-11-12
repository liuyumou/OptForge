#!/usr/bin/env bash
# The DELIVERY2 package is isolated from the root workspace and needs its own gate.
set -euo pipefail
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=""
cargo fmt --manifest-path research/lp-delivery2/Cargo.toml --check
cargo clippy --manifest-path research/lp-delivery2/Cargo.toml --all-targets --locked -- -D warnings
cargo test --manifest-path research/lp-delivery2/Cargo.toml --release --locked
cargo build --manifest-path research/lp-delivery2/Cargo.toml --release --locked
python3 -m unittest discover -s tests/integration -p 'test_lp_delivery2.py'
