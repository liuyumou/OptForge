#!/usr/bin/env bash
set -euo pipefail
python3 tools/lp_general_scale_imports.py --id "$1"
cargo fmt --manifest-path research/lp-general-lowbit/Cargo.toml --check
cargo build --release --manifest-path research/lp-general-lowbit/Cargo.toml
cargo test --release --manifest-path research/lp-general-lowbit/Cargo.toml
cargo clippy --manifest-path research/lp-general-lowbit/Cargo.toml --all-targets -- -D warnings
python3 -m unittest discover -s tests/integration -p 'test_lp_general*.py'
python3 tools/lp_general_scale_admit.py cpu --id "$1"
mkdir "artifacts/gpup-general-v1/$2"
cp research/lp-general-lowbit/target/release/lp-general-lowbit "artifacts/gpup-general-v1/$2/executor"
cp artifacts/gpup-general-v1/fast-image-v10/tensor.cubin "artifacts/gpup-general-v1/$2/tensor.cubin"
cp artifacts/gpup-general-v1/fast-image-v10/tensor.sass "artifacts/gpup-general-v1/$2/tensor.sass"
