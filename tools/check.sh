#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Review and minimal build images sometimes install rustup outside PATH. Resolve
# Cargo through rustup before starting the gate so a missing toolchain is
# reported directly instead of appearing as an unrelated shell failure.
if ! command -v cargo >/dev/null 2>&1; then
    # Prefer an explicitly configured toolchain, then the repository validation
    # toolchain, when the shell was launched without its bin directory on PATH
    # (as in minimal review containers).
    for candidate_home in ${AI_OPTIMIZER_CARGO_HOME:-} /tmp/ai-optimizer-cargo "$HOME/.cargo"; do
        if [[ -n "$candidate_home" && -x "$candidate_home/bin/cargo" ]]; then
            export PATH="$candidate_home/bin:$PATH"
            if [[ -z "${RUSTUP_HOME:-}" && -d "${candidate_home%-cargo}-rustup" ]]; then
                export RUSTUP_HOME="${candidate_home%-cargo}-rustup"
            fi
            break
        fi
    done
fi
if ! command -v cargo >/dev/null 2>&1 && command -v rustup >/dev/null 2>&1; then
    cargo_path=$(rustup which cargo 2>/dev/null || true)
    if [[ -n "$cargo_path" && -x "$cargo_path" ]]; then
        export PATH="$(dirname "$cargo_path"):$PATH"
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

# Cheap preconditions run first so a missing dependency or malformed script is
# reported in seconds rather than after several minutes of compilation.
for script in tools/*.sh; do
    bash -n "$script"
done

# The first-order LP kernels must contain no atomic accumulation outside the
# deliberately nondeterministic build. SPEC-0011 requirements 6 to 8 make the
# reduction order a contract, and an atomicAdd would silently make a result depend
# on how the hardware scheduled it -- a defect that reproduces only sometimes and
# only on a device. This is CPU-only and costs nothing, and it is the sole guard on
# a host with no GPU, where the device suite that would catch it reports a skip.
#
# Matched on the call rather than the bare name, because the file documents the
# prohibition in a comment and an earlier version of this check flagged its own
# documentation.
if ! awk '
    /#ifdef AI_OPTIMIZER_ATOMIC_REDUCTION/ { guarded = 1 }
    /#else/ { guarded = 0 }
    /#endif/ { guarded = 0 }
    /atomicAdd\(/ { if (!guarded) exit 1 }
' cuda/lp_pdhg/lp_pdhg.cu; then
    echo "acceptance gate: atomicAdd outside the deliberately nondeterministic build" >&2
    echo "acceptance gate: SPEC-0011 requirements 6 to 8 make the reduction order a contract" >&2
    exit 1
fi
if rg -n 'atomicAdd\(' cuda/lp_pdhg_tuned cuda/lp_pdhg_precision cuda/lp_pdhg_research; then
    echo "acceptance gate: atomic accumulation in tuned kernels" >&2
    exit 1
fi
git diff --check
if ! python3 -c 'import jsonschema, markdown' 2>/dev/null; then
    cat >&2 <<'EOF'
acceptance gate: Python validation dependencies are missing. Install them with
python3 -m pip install -r tools/requirements.txt before running tools/check.sh.
EOF
    exit 127
fi

# SPEC-0002 acceptance requires the pinned native library: differential,
# status-mapping and cancellation evidence cannot be produced without it. A skip
# is permitted for constrained environments but is reported loudly, so a partial
# run can never be recorded as a full acceptance pass.
native_covered=1
if [[ "${AI_OPTIMIZER_SKIP_NATIVE:-0}" == "1" ]]; then
    native_covered=0
    cargo_features=(--no-default-features)
else
    bash tools/setup_highs.sh
    cargo_features=(--all-features)
fi

cargo fmt --all --check
cargo clippy --workspace --all-targets "${cargo_features[@]}" --locked -- -D warnings
cargo test --workspace "${cargo_features[@]}" --locked
cargo build --workspace --locked
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps --locked
# The advisory database is fetched from the network and has intermittently been
# unreachable. Fall back to the cached database rather than either failing the
# gate spuriously or skipping the advisory check: bans, licenses and sources are
# offline anyway, and an absent cache is still a hard failure.
if ! cargo deny --locked check; then
    echo "acceptance gate: retrying advisories against the cached database" >&2
    cargo deny --offline --locked check
fi
python3 tools/lp_generate.py
python3 tools/validate_artifacts.py
python3 -m unittest discover -s tests/integration -p 'test_*.py'
# SPEC-0005 requirement 9: re-execute a record committed at an earlier revision.
# Every other verification test produces its record moments earlier in the same
# process, so none of them exercises the property actually claimed, that a record
# outlives its author. This one re-runs a committed record against the current
# build. It is skipped without the native library, which cannot solve at all.
if [[ "$native_covered" == "1" ]]; then
    python3 tools/verify_committed_record.py
fi
python3 tools/build_docs.py
python3 tools/benchmark_smoke.py

if [[ "$native_covered" == "0" ]]; then
    cat >&2 <<'EOF'

################################################################################
# WARNING: native acceptance NOT covered.
#
# AI_OPTIMIZER_SKIP_NATIVE=1 skipped the pinned HiGHS build, so the SPEC-0002
# differential, status-mapping, cancellation and warm-start evidence did NOT
# run. This is NOT a complete acceptance gate pass and must not be recorded as
# one. Re-run without AI_OPTIMIZER_SKIP_NATIVE for C1 acceptance evidence.
################################################################################
EOF
fi
# This receipt is written only after every full native gate command succeeded.
if [[ "$native_covered" == "1" ]]; then
    python3 - <<'PYRECEIPT'
import sys
sys.path.insert(0, "tools")
from benchmark_lp import source_identity
from lp_protocol import ROOT, write_json
write_json(ROOT / "target/lp-native-gate.json", {"native": True, "source_tree_sha256": source_identity()})
PYRECEIPT
fi
