#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cargo fmt --manifest-path research/lp-mixed2-checker2/Cargo.toml --check
cargo clippy --manifest-path research/lp-mixed2-checker2/Cargo.toml --locked --offline --all-targets -- -D warnings
cargo test --manifest-path research/lp-mixed2-checker2/Cargo.toml --locked --offline
cargo build --release --manifest-path research/lp-mixed2-checker2/Cargo.toml --locked --offline
cargo deny --manifest-path research/lp-mixed2-checker2/Cargo.toml --locked --offline check --config research/lp-mixed2-checker2/deny.toml
python -m unittest discover -s tests/integration -p 'test_lp_checker2.py'
