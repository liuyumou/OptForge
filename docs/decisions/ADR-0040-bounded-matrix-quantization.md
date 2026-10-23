# ADR-0040: Bounded matrix quantization and selective sparse execution

Status: accepted, 2026-10-22, by the user's implementation-plan approval
Owner: numerical backend
Introduced: GPUP-7
Last reviewed commit: bootstrap
Superseded by: none

## Decision

Accept the matrix-only quantization subset of SPEC-0012 requirements 13–21 and
24–38 and SPEC-0021 requirements 7–10, 14–20. Original binary64 host assessment
and conservative certification remain authoritative at unchanged 1e-9 tolerances.
The isolated precision-research interface is lp-quant-v1; existing records,
selectors, numerical bodies and archived sources/images remain unchanged.

Use IEEE binary16 and CUDA E4M3/E5M2 encodings with direct binary64 nearest-even
conversion and maximum-based power-of-two scales. Saturation and silent nonzero
deletion are forbidden. Canonical sparse 32-by-32 coordinate tiles and coefficient
IDs supply both orientations, shared scales and sticky promotion masks. FP64
masters, updates and controller state are retained. Low tiles use FP32 operands,
products and fixed reductions; tile results combine in FP64. Promoted tiles use
original scaled FP64 coefficients and FP64 operands. No contraction or FTZ.

Outward summaries include original preconditioning error, representation,
operand conversion, products, reduction and original-unit unscaling. Separate
primal/dual absolute product budgets are 1e-7. These bound local products only,
not accumulated trajectories or final feasibility. A fixed conservative norm
envelope admits every possible promoted representation before controller creation.
Uniform failure promotes the operator; selective failure promotes all low tiles
contributing to violated rows/columns. More than 25% promoted coefficients or
eight selective transitions promotes the entire operator. Native exhaustion is
a named refusal. Promotion invalidates generation-bound caches atomically.

Audit interval 32, primal/dual absolute and relative tolerances 1e-7, reference
endpoint adoption, whole-window restore and charged replay are explicit. There
is no demotion. Snapshots bind the originating session and complete numerical,
operator/promotion and controller state; deadlines and physical work never roll
back. Keep each 200-update restart/weight/original-model assessment boundary and
fresh final certification. Interruptions and failures retain their stop reason.

Vector FP16/FP8 quantization, stochastic rounding, Tensor Cores, refinement or
assessment-policy combinations, sessions, persistence and presets remain gated.
A verified accuracy refusal or negative latency result is a valid outcome.

## Conservative arithmetic construction

The exact scaled coefficient is enclosed from the original coefficient and both
recorded scale values. For each oriented tile group, sum absolute coefficient
errors outward and multiply by the current input-block infinity norm. Add the
coefficient one-norm times the maximum FP32 operand-conversion error. A tile
contains at most 32 terms per output: gamma_64 times the absolute product-sum
envelope plus 64 least-subnormal allowances bounds multiplication and fixed-tree
addition, including gradual underflow and propagation through the outer sum.
Each term encounters at most six tile roundings and at most 2048 oriented tile
groups contribute to an output; gamma_64 and the 64-subnormal allowance cover
that cross term conservatively. Add the FP64 inter-tile summation bound
and divide outward by the positive output scale. No division by an activity
near zero is used. Native tiles retain prior scaling and FP64 arithmetic error.

For any admitted nonzero nearest-even quantized value, abs(q) <= 2*abs(B); values
lost to zero are refused/promoted. Therefore twice the absolute original-scaled
coefficient enclosure supplies a format-independent norm envelope for all six
candidates and matched FP64. Its induced row/column bounds fix the common safe
step before controller creation. These local envelopes do not establish a
trajectory-wide error bound. CPU guards currently scan oriented tile summaries
and FP64 updates run on the host; their full cost must remain visible.

## Resources and frozen comparison

Add 3600 GPU seconds, raising the cumulative ceiling from 21602.574545061 to
25202.574545061 seconds. Task category caps are 2300 screening timing, 450
ablation profiles and 850 repeatability acceptance. Campaign phase ceilings are
baseline/screening/ablations/repeatability/finalists 1800/11800/8100/5300/9000;
the independent 28800-second total remains. Preserve every historical protocol
and ledger byte: 16816 events, 19730.939812844 seconds, SHA-256
dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c.

Six format/policy candidates, matched FP64 and tuned FP64 give at most 96 timings:
small-4, scheduling-20x5, irregular-2048 and irregular-32768, three repetitions.
Use existing 10/30-second deadlines, 50000 updates, seed 17, order seed 17001 and
analysis seed 17002. Eight 2000-update irregular-32768 profiles use 30 seconds.
Deadline-plus-six reservations are timing 2016, profiles 288 and acceptance 816
seconds. CPU refusal excludes dependent cells without replacement or retry.
Acceptance reservations comprise 180-second ordinary, 240-second project and
four 90-second sanitizer jobs. All failures and uncertain work remain charged.

Only GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 may execute, under the shared host
lease and selected-device activity admission. CPU cap 21600 seconds/four jobs,
RSS 8 GiB, device buffers 1 GiB, preparation 2 GiB and new artifacts 32 GiB.
Checked shape bounds are 65536 rows/columns and 2^23 nonzeros. Unused allowance
reserves no later task. Delivery is a local commit, without publication or merge.

## Acceptance

Independent integer/Fraction encoding, tie, range and sparse error-bound oracles;
CPU admission on the eight GPUP-EXEC models; strict evidence and restoration
counterexamples; full pinned-native gate; ordinary/new device differentials,
same-device replay and four scoped sanitizers. Freeze exact source, executable,
image and request identities before execution. Independently check every endpoint
and report full fresh-process cost, coverage, low work and promoted fractions.

Final CPU admission passes all 56 model/configuration cases, including seven
retained scaling-256 numerical refusals, after 162015 independent format and
3072 original-unit product components. The initial cohort remains separate.
[Final CPU admission](../benchmarks/data/quant/cpu-admission.json) and the exact
[pre-device source bridge](../benchmarks/data/quant/cpu-source-bridge.json) retain
the numerical source identities and the lifetime-only memory repair.
