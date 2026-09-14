# LP Certification Arithmetic

Status: implemented under GPUP-1
Owner: numerical backend (optimizer-lp)
Last reviewed commit: bootstrap (first commit containing this document)
Contract: [SPEC-0011](../specifications/SPEC-0011-gpu-lp-backend.md), requirements 11-15 and 13a/14a/14b
Implementation: [certification](../../crates/optimizer-lp/src/certify.rs)
Acceptance: [Rust certificate/gap regressions](../../crates/optimizer-lp/tests/certification.rs),
[primitive enclosures](../../crates/optimizer-lp/src/outward.rs),
[independent rational oracle](../../tools/lp_certification_oracle.py),
[oracle regeneration checks](../../tests/integration/test_lp_certification_oracle.py),
the full native CPU gate, regular device suites, and scoped sanitizer checks.
Evidence and scope: [active task](../../state/active-task.md).

## Bound argument

For canonical minimization, repair row multipliers against infinite row sides,
then recompute z = c - A^T y from the original binary64 coefficients. Weak duality
bounds each row contribution by its chosen finite row endpoint and each variable
contribution by phi(z) = inf over l <= x <= u of z*x. Host arithmetic must bound
these real quantities, not only their nearest-rounded approximations.

Carry finite outward enclosures through every product, fixed-tree addition, and
subtraction. For a reduced-cost interval [a,b], phi is concave, so its minimum on
the interval is min(phi(a),phi(b)). Its maximum is at an endpoint or at zero when
zero lies in the interval. Evaluate the endpoints outward. If an endpoint needs
an infinite variable side, no finite certificate is available from this enclosure;
this says nothing about whether the original LP is bounded. A truly exact zero
reduced cost contributes zero even for a free variable.

The final lower endpoint bounds the canonical minimum. Negation converts it
exactly into an upper bound for maximization. The nearest-rounded value and its
outward-enclosed difference from that endpoint remain diagnostic Certificate fields;
they are not used to reconstruct the authoritative bound by a rounded subtraction.
Finite overflow anywhere that prevents an enclosure causes an explicit refusal.

## Arithmetic assumptions

The host uses IEEE-754 binary64, round-to-nearest ties-to-even, gradual underflow,
and separate additions/subtractions (no fast-math reassociation). Addition uses
Knuth's TwoSum residual to choose outward adjacent values while preserving exact
sums. See [Ogita, Rump and Oishi, Accurate Sum and Dot Product](https://doi.org/10.1137/030601818).
If a residual computation is not finite, use a wider adjacent-value enclosure or
refuse; never interpret it as exact.

Products use the adjacent representable values unless exactness is established
from their binary significands and exponents. The significand product fits in
106 bits and is checked with safe u128 arithmetic. This exactness test handles
subnormals without relying on a fused-product residual that could itself underflow
to zero. The resulting numerical bounds are binary64; integer bit decomposition
only decides when a product is exactly representable. Zero operands are exact.

The fixed partition and tree order are shared with the existing reduction helper;
interval propagation does not change the iteration kernels or their arithmetic.
This is conservative interval evaluation, not an exact or tight LP solver. Lost
correlations can weaken a bound, and uncertainty on an infinite side can cause a
refusal even when an exact reduced cost happens to vanish.

## Objective and gap authority

Model::evaluate continues to report its ordinary recomputed binary64 objective
and its existing tolerance-based feasibility verdict. A separate outward objective
enclosure is used solely to assess gap closure. This preserves record compatibility
and prevents cancellation in a reported objective from spuriously closing a gap.
It does not turn tolerance-feasible candidates into exactly feasible points.

Convert the supplied certified bound to the canonical minimization direction.
Enclose objective minus bound. Compare the entire gap enclosure against the
existing policy: its lower endpoint must be at least minus the absolute tolerance,
and its upper endpoint must fit the absolute-plus-relative allowance. For the
relative scale, use a lower bound on max(abs(objective),abs(bound)); evaluate the
allowance downward. Nonfinite objective, gap, scale, or allowance arithmetic cannot
close. Exact arithmetic at zero tolerance may close; uncertain arithmetic may not.

Both LP backends share this check. The reported LP gap is a nonnegative conservative
upper bound in absolute objective units, not a recomputation from the rounded
objective field and not HiGHS's relative MIP gap. A missing enclosure yields an
absent gap and prevents an optimality claim while retaining other valid evidence.

## Limits and validation

Exact rational fixtures independently evaluate the stored binary64 inputs rather
than reproducing the interval implementation. Cases cover cancellation, sign changes,
free/infinite bounds, underflow, overflow, and both objective directions. Arithmetic
fixtures include signed zero, ties, exponent extremes, and cancellation reductions.
Device integration is tested under the shared lease; no device kernel changes.
No performance improvement or convergence-rate claim is made by this repair.

To reproduce the exact-rational fixtures without editing them, run:

```bash
python3 tools/lp_certification_oracle.py
cargo test -p optimizer-lp --locked
```

`--write` on the oracle regenerates the committed correctness fixture for review;
it is not an experiment seed/split change. The ordinary Python integration gate
checks that committed bytes reproduce the independent rational calculation. The
full acceptance gate also tests the host backend integration; GPU integration and
sanitizers run only under the explicit device lease.

The bounded sanitizer scope used for this host-side repair preserves the full
regular device suite and its memory-check results, then checks three relevant LP
cases under each sanitizer. The original 20,000-iteration publication test remains
unchanged. To reproduce the scoped checks, first build the test executable and use
the executable path Cargo prints:

```bash
cargo test --release -p optimizer-lp-cuda --test device --no-run
bash tools/gpu_job.sh GPU-<uuid> bash -s -- <lp-device-test-executable> <<'SH'
set -euo pipefail
export AI_OPTIMIZER_GPU=1
for tool in memcheck racecheck initcheck synccheck; do
    for test in a_device_maximization_uses_the_host_gap_enclosure \
        the_device_iterates_match_the_host_engine_bitwise \
        the_device_matches_the_host_on_a_line_wider_than_one_segment; do
        compute-sanitizer --error-exitcode 99 --tool "$tool" "$1" \
            --exact "$test" --test-threads 1
    done
done
SH
```

Each invocation must report one executed, passing test (not a device skip or zero
matching tests) and zero sanitizer errors. These scoped results do not claim that
the entire broad sanitizer gate completed; its stopped racecheck is recorded in
the slice evidence.
