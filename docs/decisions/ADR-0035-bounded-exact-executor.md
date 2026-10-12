# ADR-0035: Bounded exact sparse-product executor

Status: accepted, 2026-10-13
Owner: numerical backend
Introduced: GPUP-EXEC
Last reviewed commit: bootstrap
Superseded by: none

## Context

The user accepted the GPUP-EXEC implementation plan after ADR-0034's CPU proof.
Full-range exact reductions require thousands of bits. A bounded symbolic-exponent
integer accumulator supplies a smaller, explicit arithmetic target without
mistaking exact storage for exact native FP64 arithmetic.

## Decision

Accept `lp-exec-v1`: finite binary64 inputs, exact products and exact sums followed
by one binary64 nearest-even rounding, with gradual underflow and the accepted
CPU dot signed-zero/exception semantics. Each operand is decoded to a sign,
normalized 53-bit integer significand and signed exponent. A row has at most
65536 terms and nonzero product base exponents span at most 128. Each magnitude
is below 2^106; alignment adds at most 128 bits and row length adds 16, so all
partial sums fit below 2^250. Signed eight-u32-limb arithmetic has 255 magnitude
bits. No terms are omitted. Empty/exactly cancelling sums return positive zero;
nonzero values rounded to zero retain sign. Overflow and nonfinite inputs refuse.
Inexact/subnormal/underflow flags and symbolic half-ulp error bounds are retained.

One canonical array of binary64 coefficient bits, CSR/CSC indices and a transpose
permutation defines both products. Cached and uncached variants use identical
integer arithmetic and lane-strided warp32 reduction. Cached vectors are decoded
once per use epoch; coefficients are decoded in the sparse loop. The executor
retains native FP64 updates and host control/certification. No new solver default,
full expansion state, refinement, checkpoint persistence or fallback is accepted.

Accept shape limits 65536 rows/columns and 2^23 nonzeros, 1 GiB resident and 2 GiB
preparation peak. Checked dimensions/indices/aliasing and source generations are
mandatory. Bind actual scale values and sparse connectivity, and bound prior
scaling error separately from exact represented storage. All resource receipts
include decoded vectors, both sparse views and scratch. Device sparse/decode
paths must have no FP64 arithmetic, at most 128 registers/thread and zero spills.
Only the separate sm_120 image is admitted; ordinary builds do not invoke nvcc.

## Resource authority

The user's accepted plan adds 3600 seconds to the cumulative ceiling, making
21602.574545061 seconds. Task caps are timing 2300 (screening), profiles 450
(ablations), acceptance 850 (repeatability). Explicitly amended campaign phase
caps are screening 9500, ablations 7650 and repeatability 4450 seconds. Baseline
1800, finalists 9000 and overall 28800-second caps remain independently binding.
These caps are ceilings, not a claim that their sum is newly reserved work.
Historical protocols/decisions and every ledger byte remain unchanged. Parent
consumption is 17115.274617853 seconds, 16134 events, SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823.

The frozen protocol admits eight existing development models, four configurations,
three timing repetitions and twelve 200-proposal profiles. Existing primary
10/30-second deadlines and numerical settings/seeds remain. Each GPU request
reserves deadline+6 seconds under the shared host lease. Failures are retained;
primary attempt identities are never retried. Acceptance corrections use distinct
source-bound identities within their own cap. CPU cap is 21600 seconds/four jobs,
host RSS 8 GiB and new scratch/artifacts 32 GiB. No hardware counter availability
is assumed and no permission to bypass profiling restrictions follows.

## Alternatives and consequences

Full-range accumulators, FP32 expansions and Tensor Core products remain separate
candidates. Exact bounded arithmetic can refuse wide-exponent rows and can lose
on register pressure, decoding, integer carries, preparation or total solve work.
A negative result is retained; no preset follows. Native FP64 arithmetic remains
in updates/control and original-model certification remains the sole authority.

## Acceptance

Independent CPU Fraction oracle, range/tie/cancellation/long-row cases, malformed
input/memory/cache/transpose and interruption tests precede device admission.
Full pinned-native acceptance, generated instruction audit, device differentials,
same-device replay and all four scoped sanitizers are required. The study binds
model, source, executable, image, configuration, device and complete endpoint
identity. Every endpoint is independently reassessed against the original model.
Report full coverage and total fresh-process costs, including all preparation,
packing, checks and evidence, with kernel profiles separately labelled.
