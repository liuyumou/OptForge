#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=""
cargo fmt --manifest-path research/lp-mixed2/Cargo.toml --check
cargo clippy --manifest-path research/lp-mixed2/Cargo.toml --locked --offline --all-targets -- -D warnings
cargo test --manifest-path research/lp-mixed2/Cargo.toml --locked --offline
cargo build --manifest-path research/lp-mixed2/Cargo.toml --locked --offline
python3 -B tools/lp_mixed2_oracle.py --output "${1:-artifacts/gpup-mixed2-v1/oracle-v1.json}"
python3 -m unittest discover -s tests/integration -p 'test_lp_mixed2.py'
cargo deny --manifest-path research/lp-mixed2/Cargo.toml --locked --offline check --config research/lp-mixed2/deny.toml
