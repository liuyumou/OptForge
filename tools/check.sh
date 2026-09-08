#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cargo fmt --all --check
cargo clippy --workspace --all-targets --all-features --locked -- -D warnings
cargo test --workspace --all-features --locked
cargo build --workspace --locked
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps --locked
cargo deny --locked check
python3 tools/validate_artifacts.py
python3 -m unittest discover -s tests/integration -p 'test_*.py'
python3 tools/build_docs.py
python3 tools/benchmark_smoke.py
