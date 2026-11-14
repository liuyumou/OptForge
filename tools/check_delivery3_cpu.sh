#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=""
cargo fmt --manifest-path research/lp-delivery3/Cargo.toml --check
cargo clippy --manifest-path research/lp-delivery3/Cargo.toml --all-targets --locked -- -D warnings
cargo test --manifest-path research/lp-delivery3/Cargo.toml --locked
cargo build --manifest-path research/lp-delivery3/Cargo.toml --release --locked
python3 -m unittest discover -s tests/integration -p 'test_lp_delivery3.py'
