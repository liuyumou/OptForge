# Independent delivery mechanisms — GPUP-DELIVERY3

Status: implemented; confirmation complete; two scoped cold comparisons meet retention
Date: 2026-11-12
Contract: [SPEC-0034](../specifications/SPEC-0034-delivery3.md)
Decision: [ADR-0067](../decisions/ADR-0067-delivery3.md)
Prospective criteria: [DELIVERY3 plan](../plans/lp-delivery3.md)

## Implementation and diagnostic selection

The isolated [executor](../../research/lp-delivery3/src/main.rs) independently
selects batching, startup overlap, both, or the control. Configuration is fixed
for the process, rejects unknown/conflicting overrides, and applies equally to
nativefast and gridfp4x2 at both final tiers. Batching covers the retained checker
request/response transport, borrowed request serialization, and solver response emission. Overlap alone retains
unbuffered serialization. The public solver default is unchanged.

The complete numerical state machine is byte-exact with DELIVERY2. Model,
controller, device and independent checker arithmetic remain imported from their
retained sources. Exact binary64 serialization, signed zeros, original-model
certificates, fresh assessments, receipt bindings, bounded/truncated frames,
poisoned failed connections and owned startup cleanup remain required.

Optional instrumentation records parent setup intervals and request/response
spans, child setup/decode/assessment/output durations, and prepared durable
response and teardown costs. Streaming serialization/write is one measured
span; child and parent views overlap and must not be added. Complete cold time
still includes process exit and durable stdout/stderr. Its remaining startup,
transport and teardown overhead is charged even where not separately attributed.

All **256 instrumented and 512 uninstrumented diagnostic cells** complete,
containing 1536 fresh solves across four families, four configurations, both
lanes/tiers and cold/prepared use. The uninstrumented cohort alone selects
**overlap for cold** and **batching for prepared**, using the rule frozen before
those measurements. The combined variant and unfavorable observations remain
in the evidence. These exploratory choices are not retention conclusions.

Strict dense512 uninstrumented diagnostic medians, four independent sessions:

| Lifecycle | Lane | Control ms | Batching ms | Overlap ms | Combined ms |
| --- | --- | ---: | ---: | ---: | ---: |
| Cold | Native | 742.448 | 732.490 | 520.946 | 538.308 |
| Cold | FP4 | 750.321 | 724.745 | 527.466 | 537.109 |
| Prepared | Native | 23.380 | 21.893 | 23.813 | 21.838 |
| Prepared | FP4 | 22.788 | 20.816 | 23.460 | 21.527 |

Batching reduces prepared checker-phase medians: native 6.234 to 4.755 ms, FP4
5.861 to 4.758 ms. GPU work remains 200 updates. These fresh-session measurements
do not reproduce DELIVERY2's prepared slowdown as a universal batching effect;
startup overlap alone provides no consistent prepared benefit. They do not
establish the exact cause of DELIVERY2's earlier unfavorable measurements or a
significant ranking between close diagnostic variants. Marginal phase medians
are not an additive decomposition of median complete time.

## Frozen confirmation and interpretation

The new cohort contains 32 complete blocks, each with all twelve retained
families, both lanes and tiers, cold/prepared lifecycles and matched control and
candidate. Pair order is counterbalanced and stratum order randomized with a
recorded seed. There are 6144 lifecycle cells: 3072 fresh cold solves and 3072
fresh prepared sessions with three reset solves each, for 12288 solves. The
prepared session median is one replicate; its three solves are not treated as
independent sessions. Setup, first solve, batch cost and teardown remain visible.

The target is the median block geometric mean of complete-time ratios on dense
128/256/512, with a 1.10x lower confidence-bound requirement. Every certified
family has a separate guard on paired excess cost above max(2%, 0.10 ms).
All 96 declared metrics use simultaneous 95% median intervals, ranks 6 and 27
among 32 blocks. Intervals crossing a threshold remain inconclusive. Exact
correctness and unchanged coverage are hard requirements. Intentional refusals
remain in coverage and outside certified speed ratios. Cold and prepared
eligibility are separate.

These are repeated timing blocks of constructed development families, not
held-out models or a measured production workload. The device is shared.
Boundary telemetry and descriptive lag correlations are retained; restarting
processes and randomizing order do not prove independent, comparable block
effects. The interval interpretation is conditional on that assumption.

## Software and device admission

The full native gate passes 638 Rust tests, 663 Python tests, replay, dependency,
artifact, documentation and smoke checks. The isolated crate passes 25 Rust
tests; the nine new Python contracts are included in the full Python count.
1224 fresh CPU assessments match 102 retained original serial endpoints.
77 process/configuration cases cover both instrumentation modes, malformed and
truncated frames, terminal eligibility, EOF and invalid configuration/model input.

Device admission passes 168 lifecycle cases, eight setup-failure cases and 128
fresh-session smoke cells containing 384 solves. Four variants retain exact
checkpoint, cancellation, recovery, original-model certificate and physical-work
behavior. Instrumentation preserves all numerical results. The original four
sanitizers are reused only for the unchanged source-bound device image; no new
sanitizer execution is claimed.

## Confirmation results

All **6144 lifecycle cells / 12288 solves** complete with exact retained
endpoints, certificates, audits, checkpoints, recovery and per-solve work.
There are **11264 certificates** across all eleven bounded families at both tiers
and **1024 intentional refusals**. No scientific cell was retried. The 768
separate diagnostic cells contain another 1536 certified solves.

The dense cold benefit passes in all four lane/tier comparisons. Full retention
also requires every family guard: it passes for **native at 1e-9** and **FP4 at
1e-7**; the remaining cold comparisons are inconclusive. Prepared batching has
positive aggregate point estimates, but no prepared comparison qualifies under
the predeclared 1.10x benefit requirement. These are conditional measured-gate
outcomes under the block-independence assumption, not a general deployment claim.

| Lifecycle | Tier | Lane | Dense block-ratio median | Simultaneous interval | Full decision |
| --- | --- | --- | ---: | --- | --- |
| cold | 1e-7 | Native | 1.192365x | 1.163016–1.216653 | inconclusive |
| cold | 1e-7 | FP4 | 1.185689x | 1.160799–1.217034 | supported |
| cold | 1e-9 | Native | 1.198665x | 1.178748–1.212821 | supported |
| cold | 1e-9 | FP4 | 1.194082x | 1.160733–1.217614 | inconclusive |
| prepared | 1e-7 | Native | 1.044813x | 1.017858–1.092454 | insufficient-benefit |
| prepared | 1e-7 | FP4 | 1.054508x | 1.029715–1.095259 | insufficient-benefit |
| prepared | 1e-9 | Native | 1.059557x | 1.028634–1.119831 | inconclusive |
| prepared | 1e-9 | FP4 | 1.044251x | 1.022025–1.105137 | inconclusive |

All family-guard point estimates are favorable, and no guard has an interval
entirely above its material-regression boundary. **Inconclusive does not mean
proven harm or proven non-regression.** The unresolved guards are:

| Lifecycle | Tier | Lane | Family | Excess-cost median ms | Simultaneous interval ms |
| --- | --- | --- | --- | ---: | --- |
| cold | 1e-7 | Native | coupled-inequality | -11.943 | -24.226–2.884 |
| cold | 1e-7 | Native | ranged-one-sided | -17.200 | -35.577–1.135 |
| cold | 1e-9 | FP4 | coupled-equality | -20.841 | -30.987–6.748 |
| cold | 1e-9 | FP4 | coupled-inequality | -14.641 | -27.108–1.878 |
| cold | 1e-9 | FP4 | ill-scaled-coupled | -12.741 | -26.274–3.768 |
| prepared | 1e-7 | Native | dense-generic-128 | -0.496 | -1.153–0.121 |
| prepared | 1e-7 | FP4 | dense-rich-65 | -0.636 | -1.462–0.210 |
| prepared | 1e-9 | FP4 | dense-rich-65 | -1.024 | -2.028–0.327 |
| prepared | 1e-9 | FP4 | ill-scaled-generic-128 | -1.202 | -2.091–0.650 |

Guard values are candidate minus control minus the allowed max(2%, 0.10 ms),
computed within each block. The displayed intervals are simultaneous across all
96 metrics; they are not ordinary unadjusted per-model intervals.

Strict dense512 confirmation medians:

| Lifecycle | Lane | Control ms | Candidate ms | Ratio | Candidate |
| --- | --- | ---: | ---: | ---: | --- |
| cold | Native | 715.848 | 517.069 | 1.384434x | overlap |
| cold | FP4 | 725.834 | 515.360 | 1.408401x | overlap |
| prepared | Native | 22.442 | 20.836 | 1.077050x | batch |
| prepared | FP4 | 22.031 | 20.131 | 1.094372x | batch |

Dense512 prepared totals now improve in both lanes. Checker medians fall from
6.364 to 4.869 ms for native and 6.130 to 4.853 ms for FP4; both strict lanes
still perform 200 updates. The chosen batching-only prepared route avoids the
unhelpful setup-overlap choice and the independent-session design removes the
previous single-session inference weakness. The exact cause of DELIVERY2's
old regression remains unproved; its original results and failed gate are intact.

During confirmation, pinned-device boundary samples show 0–54% utilization,
15–61327 MiB global device memory, 2302–2325 MHz SM clocks and 30–39 C temperature.
These are whole shared-device observations, not this task's buffer consumption.
They do not attribute all activity to a particular process. Descriptive lag-one
dense512 paired-ratio correlations range from -0.349 to +0.170. Neither these
correlations nor fresh processes establish independence; inference remains
conditional and the environment changes are retained without excluding blocks.

## Evidence, preservation and handoff

[Results and per-family decisions](data/delivery3-result-v1.json) include all
medians, CPU admission, device references, phase profiles, environment samples and
references to 38 compressed per-block evidence shards. The shards contain every
scientific output, stderr log and block receipt. The separate
[cohort archive](data/delivery3-cohorts-v1.json.gz) retains all manifests, full
cell metadata, exact model input text, frozen selection and runner source.
Together the 39 compressed archives occupy about 81.1 MiB. Original raw files,
logs, source snapshots and the admitted executable remain under
`artifacts/gpup-delivery3-v1`; the executable is archived by its content hash.

All 1692 historical files outside the four current navigation/handoff files remain
byte-exact; older dated handoffs and all other backlog task entries are preserved.
The new allocation has no failed reservations or scientific retries. The
independent ceiling is 64000 CPU / 7800 GPU seconds, four CPU slots, sampled
16 GiB host RSS and at most 12 GiB owned device buffers. RSS monitoring is
cooperative, not a hard cgroup memory limit. No historical funds are transferred.
Final acceptance passes all 237 documentation pages, artifact checks, exact
history and other-backlog-entry preservation. Every supervisor cleanup is empty.
The independent allocation is closed at **16305.576622052 CPU /
3232.921317950 GPU seconds**, including 512 preparation and 128
closing-administration CPU seconds. [Acceptance](data/delivery3-acceptance-v1.json),
[exact history](data/delivery3-history-v1.json), and
[final accounting](data/delivery3-accounting-v1.json) retain the receipts.

Keep the research configurations explicit and the public defaults unchanged.
The two qualifying cold comparisons do not justify an outcome-selected dispatcher
or a universal cold/prepared preset. Batching's smaller prepared gains remain
useful diagnostic evidence, not a passed 10% retention gate. MIXED2 remains the
independently ready CPU cost/numerical-contract alternative; TENSOR2 is conditional,
GPUP-8 incomplete and GPUP-9 gated. No new experiment or publication is released.
