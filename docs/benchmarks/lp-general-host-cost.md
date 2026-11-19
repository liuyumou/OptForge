# General LP preparation, assessment and control cost

Status: development measurements complete, 2026-11-19, under
[SPEC-0045](../specifications/SPEC-0045-general-lowbit-lp.md).

This continuation reduces shared host overhead in the isolated general LP
executor. It preserves the original reduction tree, arithmetic order, strict
original-model certificate criteria, control and certificate cadences, and the
fast-image-v10 CUDA image. Public solver defaults remain unchanged.

## Implementation

The final candidate retains the original host products, spectral preparation
and control calculations. An initial in-place product reduction preserved exact
arithmetic but slightly regressed preparation in the structural pilot. Its
source, admitted image and complete first cohort are retained separately; the
second candidate restores the original product path.

The cached exact certificate uses scratch arrays sized to the next power of two
of the current column length, instead of initializing three 2048-element arrays
for every short column. Every outward reduction operation is unchanged.

Feasibility preparation borrows the immutable original model instead of cloning
it. Canonical dense variable IDs use a checked direct index; arbitrary IDs retain
binary lookup. The original expression order, bound checks and first errors stay
unchanged. Historical checker sources remain intact; isolated derivatives and
their provenance are retained in the research crate. The existing lazy preparation
policy and fresh evaluation of every endpoint are unchanged.

The fast solver already reused the merit of unchanged state. That optimization
is preserved; no control checks are removed by this continuation.

## Evaluation protocol

The frozen comparison includes all six connected 1 M structural families and
the public square31/scpm1 models. Each generated family contributes seed 831001;
timing repetitions do not add independent problem instances. Both executables use the default Rust target,
native/FP32/FP4x2, two rotated-order repetitions, a 1000-update cap, 250-update
certificate cadence, 100-update control cadence and a 30-second solver limit.
The primary cost includes a fresh process, full response transport and a fresh
independent final original-model certificate. Intermediate endpoint auditing and
archive compression are separately measured and retained. Equal-work pairs must
match complete numerical transcripts exactly; deadline differences stay explicit.

This is descriptive development on bounded work, not broad certified-solve
confirmation. The full historical rosters, public-model failures and 16 M capacity
refusals in the [scale report](lp-general-scale.md) remain applicable. Shared host
gains do not establish an incremental FP4 benefit.

## Retained first candidate

The [first complete cohort](lp-general-host-cost-pilot-results.json) retains all
96 measurements and 48 exact equal-work pairs. Scale-image-v8 combines checker
changes with in-place host products. Its descriptive median old/new ratios are
1.213 for assessment, 1.043 for complete measured cost, and 0.982 for initial
host preparation. Preparation medians in the six structural families range from
0.948 to 0.996, so the product change is not retained in the final candidate.
All favorable, unfavorable and uncertified observations remain in this cohort;
the subsequent candidate is measured in a new complete cohort without pooling.

## Final fixed-work comparison

The [final cohort](lp-general-host-cost-results.json) retains 96/96 measurements,
48/48 exact equal-work transcript pairs and every independent endpoint check.
The final image is scale-image-v9, using the default Rust target. Median old/new
ratios are 1.267 for assessment, 1.067 for complete measured cost, 1.003 for
initial host preparation and 1.000 for execution. These correspond to about
21.1% less assessment time and 6.3% less complete time. The preparation and
execution differences do not establish a benefit in those partitions.
The assessment partition includes original-A control, certificates, lazy checker
setup, continuation and checker release. Its reduction measures the bundled host
change; individual optimization contributions were not separately timed.

| Family / public model | Complete-cost ratio | Assessment ratio |
| --- | ---: | ---: |
| Irregular | 1.088 | 1.292 |
| Wide | 1.061 | 1.293 |
| Tall | 1.051 | 1.170 |
| Coupled blocks | 1.073 | 1.277 |
| Ill-scaled | 1.039 | 1.263 |
| Degenerate | 1.079 | 1.266 |
| square31 | 1.020 | 1.158 |
| scpm1 | 1.116 | 1.461 |

Ratios above one favor the candidate. Each row has six pairs: three lanes and
two repetitions. Overall native, FP32 and FP4x2 complete-cost medians are 1.081,
1.043 and 1.068. All numerical endpoints, assessments, work counts, recovery and
accepted FP4 work match the corresponding control. Only the tall model certifies
within this 1000-update cap: each version/lane certifies 2/16 observations.
The six jointly certified pairs have a 1.051 complete-cost median. Other rows
remain bounded-work attribution, not successful-solve latency claims.

## Ordinary single-solve comparison

The [single-solve cohort](lp-general-host-cost-solve-results.json) completes all
48 measurements on the same eight models, with 20000-update maxima,
500-update certificate cadence, 30-second solve limits and one repetition.
Every version/lane certifies 5/8 models: irregular, wide, tall, coupled and
degenerate. Ill-scaled and square31 reach the iteration limit without a
certificate. On scpm1, each final candidate reaches all 20000 updates without a
certificate; the previous native/FP32/FP4 controls hit the wall limit after
18400/19000/18900 accepted updates respectively. Those three unequal-work
comparisons do not establish successful-solve speedups.

All 21 pairs without deadlines retain exact full numerical transcripts. The
three deadline pairs retain exact common assessment prefixes; 509 paired
intermediate assessments agree exactly across the cohort. The 15 jointly
certified pairs have a descriptive median old/new complete-cost ratio of 1.052,
or about 4.9% less time. Among all 21 exact pairs, the assessment ratio is 1.204,
or about 16.9% less time; unsuccessful solves remain separate from solve-time
claims. Initial preparation and execution remain near parity.

| Lane | Jointly certified pairs | Complete-cost median ratio | Regressing pairs |
| --- | ---: | ---: | ---: |
| Native | 5 | 1.052 | 0 |
| FP32 | 5 | 1.073 | 1 |
| FP4x2 | 5 | 1.009 | 1 |

Both regressing pairs are coupled: FP32 takes 1.434 versus 1.381 seconds, and
FP4x2 takes 1.372 versus 1.371 seconds. The coupled FP4 solve retains 75% accepted
FP4 product work, but its complete time is effectively flat. The other four
certified FP4-configured cases have no actual FP4 tiles. These results establish
shared overhead savings on this development population, not broad FP4
superiority. One solve repetition per model/lane provides no confirmation or
generalization beyond the declared models. All cost partitions, negative
observations and historical scale outcomes remain available; no cause is
assigned to individual timing variations.

## Acceptance

Each candidate passes 37 isolated Rust tests, 24 exact compact/JSON input
comparisons, 32 host arithmetic/preparation probes and cached checker comparisons
on six admission families. Tests cover original certificate bits and refusals,
complete feasibility reports, cancellation, signed zeros, subnormals, overflow
and every specialized scratch-size boundary. Each image also passes 60 exact GPU
continuation/recovery/cancellation comparisons and four 20-case sanitizer suites
(memcheck, racecheck, initcheck and synccheck).

The full native gate passes 638 repository Rust and 827 Python tests, committed
record replay and documentation checks. The final candidate reuses this gate
for the unchanged public/core sources and has fresh isolated and device admission.
The online advisory fetch failed; the gate's cached advisory check passed.
Historical checker sources, public defaults and the CUDA image remain exact.

## Reproduction and resources

Build and CPU admission use `tools/lp_general_scale_cpu.sh` with a fresh job/image
identity. `tools/lp_general_host_cost.py device` runs the unchanged-image device
comparisons and four sanitizer suites. Its `freeze` action writes the matched
protocol; `tools/lp_general_scale_bench.py campaign` executes it. The `report`
action retains every cell and exact-pair attribution. All execution runs through
the existing supervised budget wrapper with fresh immutable identities.

The independent allocation remains 240000 CPU / 30000 GPU seconds, with the
prospective phase caps recorded in SPEC-0045. Four CPU slots, 16 GiB sampled RSS,
12 GiB owned device buffers, the pinned GPU lease, one-second supervision and
all 100 ms advisories remain unchanged. Large evidence stays local; only compact
results and delivery receipts are tracked.

## Portable delivery

The local archive contains 20092 files in 23 parts (1284824895 compressed bytes).
It verifies all 91476 checked prior scale-evidence bindings. Replay from an
extracted root passes 240 campaign responses, 280 admission responses and
2749 assessments, including 483 distinct serial witnesses. It retains all
three cohorts, both candidate sources, every endpoint and their completed
execution receipts. Packaging, replay and closing receipts are bound separately
in the delivery validation. There are no missing, partial or raw-only responses
in this delivery.

[Delivery validation](lp-general-host-cost-validation.json) records source,
image, resource, archive and replay bindings. All new scientific reservations
pass with empty cleanup. Fresh processes do not imply flushed caches. The
allocation remains open and public adoption remains separate.

Open settled checkpoint: 195952.885224432 CPU / 25975.890687406 GPU seconds.
