#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES=""
cargo fmt --manifest-path research/lp-delivery4/Cargo.toml --check
cargo clippy --manifest-path research/lp-delivery4/Cargo.toml --all-targets --locked -- -D warnings
cargo test --manifest-path research/lp-delivery4/Cargo.toml --locked
cargo build --manifest-path research/lp-delivery4/Cargo.toml --release --locked
python3 -m unittest discover -s tests/integration -p 'test_lp_delivery4.py'
# In-repository wildcard exceptions require the explicit metadata audit.
python3 - <<'PY'
import json
import subprocess
import sys
sys.path.insert(0, 'tools')
from lp_delivery4_dependencies import audit
metadata=json.loads(subprocess.check_output(['cargo','metadata','--manifest-path','research/lp-delivery4/Cargo.toml','--locked','--offline','--format-version','1']))
audit(metadata)
print('DELIVERY4 exact dependency/path audit: passed')
PY
cargo deny --manifest-path research/lp-delivery4/Cargo.toml --locked --offline check --config research/lp-delivery4/deny.toml
