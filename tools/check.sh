#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Review and minimal build images sometimes install rustup outside PATH. Resolve
# Cargo through rustup before starting the gate so a missing toolchain is
# reported directly instead of appearing as an unrelated shell failure.
if ! command -v cargo >/dev/null 2>&1; then
    if command -v rustup >/dev/null 2>&1; then
        cargo_path=$(rustup which cargo 2>/dev/null || true)
        if [[ -n "$cargo_path" && -x "$cargo_path" ]]; then
            export PATH="$(dirname "$cargo_path"):$PATH"
        fi
    fi
fi
if ! command -v cargo >/dev/null 2>&1; then
    cat >&2 <<'EOF'
acceptance gate: Cargo is unavailable. Install the pinned toolchain from
rust-toolchain.toml or put its bin directory on PATH before running tools/check.sh.
If this command is running under a review sandbox, verify that the sandbox can
start processes; namespace failures occur before Cargo is invoked.
EOF
    exit 127
fi

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
