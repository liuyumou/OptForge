#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cargo fmt --manifest-path research/lp-mixed2-reuse/Cargo.toml --check
cargo clippy --manifest-path research/lp-mixed2-reuse/Cargo.toml --locked --offline --all-targets -- -D warnings
cargo test --manifest-path research/lp-mixed2-reuse/Cargo.toml --locked --offline
cargo build --manifest-path research/lp-mixed2-reuse/Cargo.toml --release --locked --offline
cargo deny --manifest-path research/lp-mixed2-reuse/Cargo.toml --locked --offline check --config research/lp-mixed2-reuse/deny.toml
python3 -m unittest discover -s tests/integration -p 'test_lp_mixed2_reuse.py'
python3 tools/lp_mixed2_reuse_analysis.py verify
