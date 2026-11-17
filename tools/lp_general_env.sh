#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Same provisioned native toolchain used by tools/check.sh on this host.
if ! command -v cargo >/dev/null 2>&1; then
    export PATH="/tmp/ai-optimizer-cargo/bin:$PATH"
    export RUSTUP_HOME="/tmp/ai-optimizer-rustup"
    export CARGO_HOME="/tmp/ai-optimizer-cargo"
fi
exec "$@"
