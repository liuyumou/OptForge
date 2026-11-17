#!/usr/bin/env bash
set -euo pipefail
cargo build --release --manifest-path research/lp-general-lowbit/Cargo.toml
cargo test --manifest-path research/lp-general-lowbit/Cargo.toml
cargo clippy --manifest-path research/lp-general-lowbit/Cargo.toml --all-targets -- -D warnings
python -m unittest discover -s tests/integration -p test_lp_general.py
python tools/lp_general_tensor.py --id "$1"
mkdir "artifacts/gpup-general-v1/$2"
/usr/local/cuda/bin/nvcc -O3 -lineinfo -fmad=false -ftz=false -arch=sm_120a --cubin research/lp-general-lowbit/cuda/tensor.cu -o "artifacts/gpup-general-v1/$2/tensor.cubin"
cp research/lp-general-lowbit/target/release/lp-general-lowbit "artifacts/gpup-general-v1/$2/executor"
/usr/local/cuda/bin/cuobjdump --dump-sass "artifacts/gpup-general-v1/$2/tensor.cubin" > "artifacts/gpup-general-v1/$2/tensor.sass"
