# GPU LP Performance Research and Implementation Roadmap

Status: approved 2026-10-12 order; GPUP-ASSESS evaluated with scoped benefit; GPUP-7 contract is next
Owner: numerical backend and experiment tooling
Introduced: GPU LP precision research track (GPUP)
Last reviewed commit: 62516e8cef59104442fa359a2e2440af8a59f033 (precision architecture review, 2026-10-12)
Implementation: [backlog](../../state/backlog.yaml), [active task](../../state/active-task.md)
Acceptance: the slice gates below; [GPUP-2 baseline evidence](../benchmarks/lp-baseline-gpup2.md), [GPUP-3 matched evidence](../benchmarks/lp-matched-fp64-gpup3.md), [GPUP-4 tuned evidence](../benchmarks/lp-tuned-fp64-gpup4.md)

## Objective and working agreement

Optimize **end-to-end single-solve latency at the required feasibility and
certified-gap tolerances**, including setup, transfers, numerical checks, recovery,
and final certification. This is the user's selected priority. Repeated-solve
throughput and full MILP search performance are separate tracks, not substitutes for
this objective. On 2026-09-20 the user pulled the repeated-solve track,
GPUP-THROUGHPUT, ahead of GPUP-6 because the GPUP-5C evidence shows the remaining
cost is outside arithmetic; it keeps its own specification, endpoint and budget.

Implement one dependency-ready slice at a time. Each leaves a buildable,
documented result, acceptance evidence, and a handoff. Update active-task state
before work; record evidence, limitations, and a local commit afterward. Do not
publish or push without authorization. The user selected an **eight GPU-hour cap**
for the first experiment campaign.

FP32-to-FP8 computation and Tensor Core execution are in scope. FP8 is a candidate,
not a required winner. The final recipe follows measurements and ablations; an
experiment that finds the tuned baseline faster is a useful negative result.
This track follows C6 but does not complete C7, C9, or the general C10 runner.

## Current design order (2026-10-12)

The user requested durable designs and experiments before more implementation.
[ADR-0033](../decisions/ADR-0033-lp-precision-design-order.md) changes planning order
only. The [architecture plan](lp-precision-architecture-2026-10-12.md) records
component motivation, algorithm sensitivity, exact-tail proofs, low-level choices
and rejection conditions. [SPEC-0020](../specifications/SPEC-0020-lp-expansion-arithmetic.md)
and [SPEC-0021](../specifications/SPEC-0021-lp-refinement.md) began as draft numerical
contracts. Bounded subsets are now accepted through ADR-0034/0035/0036/0037;
extensions remain draft. The [experiment design](../benchmarks/lp-precision-design-experiments.md)
is proposed; it independently admits no trials, seeds, defaults or GPU allowance.

| Priority / slice | Bounded deliverable | Gate before advancing |
| --- | --- | --- |
| 1 — GPUP-REP (complete) | CPU validation and acceptance of a bounded exact-storage/expansion contract; compare original bits with compact mixed tails, prove range/rounding and reject invalid formats. | Independent oracle, exact codec and primitive obligations, actual layout/memory analysis, accepted SPEC-0020 subset and explicit later resource contract. Zero GPU work in this slice. |
| 2 — GPUP-EXEC (complete) | Lean operator executor: cache vector splits, remove avoidable per-nonzero recombination/conversion, preserve integer-guard meaning and test admitted launch schedules. | Same-arithmetic controls, generated instruction review, full range and sanitizer acceptance; both tuned and precision FP64 comparisons; packing-inclusive cost. |
| 3 — GPUP-STATE (complete bounded admission investigation) | CPU scalar/primitive validation, first full-bin refusal and compact FMA challenge under ADR-0036. Full controller/state remains gated. | Original construction uses 255 registers and spills; compact full-range FMA fits at 40 registers with zero spills and 5900 additional independent cases per construction. 6170 device cases, four scalar sanitizers and 36 verified primitive timings on PRO 6000; no solver benefit, original evidence retained. |
| 4 — GPUP-REFINE (complete) | ADR-0037 native FP64 outer correction LPs, guarded FP32/anchored products, charged recovery/checkpoints and strict replay. | 108 retained attempts, 48 verified endpoints, 30/96 certified timings; full native/device/sanitizer/replay gates. Only initial host-certified small-4 succeeds in refinement; no product benefit/preset. Expansion masters remain gated. |
| 5 — GPUP-ASSESS (complete) | ADR-0039 fixed_200/bounded_800 on tuned FP64 and existing accumulation FP32, preserving 200-update numerical checks. | 16 CPU trajectories/320 boundary witnesses; all 60 attempts retained, 57 endpoints verified, 24/48 timings certified. Six bitwise profile pairs, full native/device/replay/sanitizer gates; scoped 1.0272x FP64 irregular-32768 gain, unchanged coverage and no preset. |
| 6 — GPUP-7 | Accept quantization/FP8 error-budget interface, then admitted uniform/selective sparse candidates. | Representation/arithmetic error in original units, canonical transpose, norm/step validity, bounded promotion and memory; reject insufficient-accuracy formats before timing. |
| Conditional — GPUP-8 | Shape-admit sparse/dense Tensor Core or integer execution for actual sm_120 single-RHS work. | Same-operand accuracy, overflow/accumulator analysis, packing/padding costs and scoped device gates. A documented rejection/defer decision is valid; no mandatory Tensor Core implementation. |
| 7 — GPUP-9 | Small component/interaction blocks, frozen finalists and independent held-out comparison. | Coverage-first certified total latency, repeatability/uncertainty, full failures and budget ledger; final recipe may omit optional components. |
| 8 — GPUP-10 | Package only supported recipes. | Accepted evidence and admission rules; no preset if gains or coverage are inconclusive. |

This is priority order. The [backlog](../../state/backlog.yaml) records actual
prerequisites separately: refinement does not require expansion state, assessment
scheduling does not require refinement, and final comparisons do not require an
unhelpful Tensor Core path. Simplex/interior-point/ADMM, active-face polishing,
stronger preconditioning and stochastic rounding are conditional branches needing
separate bounded contracts; they do not block the primary PDHG experiment.
An investigation can close with a documented negative/admission result. Completion
of GPUP-STATE or GPUP-REFINE does not require making its candidate a winning or
mandatory component of GPUP-7/9.

Current charge is **19730.939812844 / 21602.574545061 GPU seconds**, with
16816 events and SHA-256
dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c.
[GPUP-ASSESS](../benchmarks/lp-assessment-scheduling-gpup-assess.md) charges
523.674592721 seconds within its 2300-second allocation, preserving the exact
16684-event prefix e83d07792fb0775fc26d8d2cca8a2411f59fcbc94f742cafd8f6b844ffb60535
and every earlier prefix/phase ceiling. Its CPU-only final review strengthens
bitwise replay and profile eligibility while retaining all measured workers and
results. [GPUP-REFINE](../benchmarks/lp-refinement-gpup-refine.md)'s earlier
1541.719136512-second charge, telemetry refusal and report-reader correction remain.
GPUP-7 needs its own accepted quantization/error-budget contract and resource
allocation; unused headroom reserves nothing. Historical handoffs and budgets
below retain their dated stages. Old racecheck/session/mixed-model gaps remain.

## Contracts and status

- [SPEC-0012](../specifications/SPEC-0012-mixed-precision-lp.md) is accepted for
  implemented GPUP-3/4 shared FP64 control and tuned execution, GPUP-5 fixed FP32
  comparisons and GPUP-6 adaptive recovery. Quantization, Tensor Core execution
  and supported presets still need their bounded contracts and acceptance.
- [SPEC-0013](../specifications/SPEC-0013-lp-precision-experiments.md) is accepted;
  GPUP-2 implements the bounded LP study, artifacts and baseline acceptance.
  [ADR-0014](../decisions/ADR-0014-lp-baseline-protocol.md) freezes its concrete protocol.
- [ADR-0012](../decisions/ADR-0012-opt-in-lp-precision.md) narrowly supersedes the
  blanket FP64 and shared-reduction restrictions for a new opt-in backend once
  its prerequisites and accepted specification are in place.
- [ADR-0013](../decisions/ADR-0013-lp-precision-study.md) records the performance
  objective, campaign budget, evidence rules, and separate future directions.

GPUP-1 repairs the host certifier's cancellation defect, retained in
[known failures](../../state/known-failures.md#lp-certification-can-lose-the-roundoff-allowance-at-zero-reduced-cost),
and the objective/gap arithmetic in both LP backends. Independent exact-rational
regressions establish the repair before lower precision; the ordinary objective
and tolerance-based feasibility report retain their existing meanings. See
[the arithmetic argument and limitations](../architecture/lp-certification.md).

## Implementation slices

The original precision sequence is retained below; GPUP-0 depends on C6 and C8.
The [current design order](#current-design-order-2026-10-12) adds the new bounded
slices; the [2026-09-27 follow-up order](#current-follow-up-order-2026-09-27) records
the completed COPT follow-ups. The backlog records prerequisites separately from
priority. New behavior requires the relevant bounded contract to be accepted
before implementation. Slice 1 repairs the existing SPEC-0011 certification
contract. Later slices may be refined from earlier findings, with changes
recorded before affected trials.

| ID | Deliverable | Completion evidence |
| --- | --- | --- |
| GPUP-0 | Persist this roadmap, dependency-ordered backlog, numerical and experiment drafts, and superseding arithmetic/reproducibility ADR. | Documentation gate; requirement-to-test mapping; explicit budgets and decision rules. |
| GPUP-1 | Repair reduced-cost cancellation with conservative outward bounds; review objective and gap authority. | Independent exact-arithmetic regressions for cancellation, uncertain signs, finite/infinite bounds, and both objective senses. |
| GPUP-2 | Establish the LP-only measurement harness, versioned manifests/results, independent checking, and phase instrumentation. Measure host LP, existing GPU FP64, and pinned HiGHS. | Reproducible records, deliberately failing checks, complete cost accounting, baseline bottleneck report. |
| GPUP-3 | Create a resumable FP64 control implementation with shared restart, weight, checkpoint, cancellation, and budget state. | Complete: whole-trajectory/checkpoint tests, full native and scoped device/sanitizer gates, and 160 supplementary study attempts. Opt-in matched CUDA certifies 27/36 timing runs; legacy remains unchanged. |
| GPUP-4 | Optimize FP64 residency, allocation, transfers, sparse kernels, and compatible fusion where profiling supports it. | Complete: explicit cuda-lp-tuned, bitwise/rational/native/device/scoped sanitizer gates, preserved original failures and a complete 320-attempt correction. Coverage remains 27/36 for every configuration; scoped provisional fusion gains, matched remains the general reference. |
| GPUP-5 | Add FP32 matrix storage with FP64 arithmetic, then FP32 products/accumulation. Compare FP64 masters and FP32 working state with FP64 correction. | Original-model checks, convergence and range diagnostics, measured storage/arithmetic/state costs. |
| GPUP-5B | Investigate exact power-of-two/factored scaling and two/three-component sparse products. | Matched FP64 controls, independent rational/device checks, 840 frozen development attempts and preserved rounding analysis; [report](../benchmarks/lp-exact-components-gpup5b.md). |
| GPUP-5C | Act on the FP64-pipe root cause: integer-pipe guards, fused two-launch schedule, double-float FP32 pairs, explicit tolerance tiers and a frozen development extension. | ADR-0022; twelve-mode bitwise device differentials, rational pair fixtures, research-v2 evidence, manifest v2 with byte-identical v1 outputs, charged 874-attempt study. |
| GPUP-THROUGHPUT | Repeated-solve throughput with explicit matrix, context and device reuse: accepted specification, API and resource budget first; then amortized throughput with complete setup-cost accounting. | Accepted specification before behavior; fresh-process single-solve endpoint and protocol unchanged; setup, context, transfer and per-solve costs reported separately; full native and device gates. |
| GPUP-6 | Add configurable audits, checkpoints, replay, promotion, and optional demotion, initially FP32/FP64. | Fault injection covering full rollback, budget/cancellation accounting, sticky promotion, and guarded demotion. |
| GPUP-7 | Add quantization candidates through a common experimental interface; establish sparse FP8 before Tensor Core comparisons. | Quantizer checks, transpose consistency, guarded conversion, screening against the FP64 control. |
| GPUP-8 | Add hybrid sparse/dense-tile Tensor Core execution on the actual Blackwell target, including FP16/BF16 and FP8 where supported. | Differential kernels, same-device repeatability, sanitizers, and padding/packing-inclusive single-solve timings. |
| GPUP-9 | Screen, tune, ablate components and interactions, freeze finalists, then evaluate held-out data. | Raw provenance, uncertainty, negative results, complete budget ledger, and study report. |
| GPUP-10 | Package only supported recipes as explicit presets with examples, compatibility notes, limitations, and the final report. | Full gates, reproducible instructions, and separation of supported versus experimental behavior. |

GPUP-2 through GPUP-8 collect baseline and development evidence as the components
become available; GPUP-9 conducts the coordinated final comparisons. This does not
postpone all measurement until after implementation. Each slice declares its own
bounded CPU/GPU acceptance budget before work. All study jobs, including failed
trials and profiling, consume the single campaign ledger; acceptance-only GPU work
is separately identified and budgeted, never hidden in benchmark timings.

GPUP-3's [accepted report](../benchmarks/lp-matched-fp64-gpup3.md) records schema/activity
repairs, bit-preserving certification, matched control, failures and raw hashes.
It adds 251.845179881 GPU seconds; cumulative study consumption is 445.988045904.
GPUP-4 preserves that history and all rational tests. Its
[reviewed report](../benchmarks/lp-tuned-fp64-gpup4.md) retains the original 320
attempts, including 24 reference launch failures, and a separately frozen complete
320-attempt correction under ADR-0018. It adds 456.586499157 GPU seconds under the
approved 900-second supplement; cumulative use is 902.574545061 of the exact
1345.988045904 ceiling. Every configuration certifies 27/36 timings. Matched remains
the general reference; fused warp32 is provisional only on three named development
instances. GPUP-5 now adds explicit FP32 comparisons and COPT CPU/GPU PDLP
controls under ADR-0019. Its [report](../benchmarks/lp-fp32-gpup5.md) verifies all
480 attempts and adds 421.636094192 screening seconds, for 1324.210639253 cumulative
seconds beneath the 4502.574545061 slice ceiling. FP64 controls retain 27/36 timing
coverage, versus 12/36 for FP32 storage/products/accumulation/master correction and
6/36 for FP32 working state. GPUP-5B followed after completed acceptance. No
validation/held-out solve, supported preset or publication occurred.

GPUP-5B is complete before GPUP-6 under [ADR-0021](../decisions/ADR-0021-exact-scaling-components.md).
The preserved diagnosis adds 143.056235443 seconds for 1467.266874696 cumulative.
See the [GPUP-5B report](../benchmarks/lp-exact-components-gpup5b.md),
the [rounding investigation](../benchmarks/lp-fp32-rounding-analysis.md) and
[future candidate register](lp-precision-candidates.md). All 840 attempts verify;
new exact/component modes recover 27/36 timing coverage, with slower component
cross-products retained. Full native/device/scoped sanitizer gates pass. New work
uses 697.211414922 study + 70.875589353 acceptance screening seconds, totaling
2235.353878971 cumulative seconds within 4502.574545061 and campaign/phase caps.
All 4996 ledger events preserve the original 3288-event prefix and old artifacts.

GPUP-5C follows under [ADR-0022](../decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md)
after the [root-cause note](../benchmarks/lp-fp64-pipe-root-cause.md) attributed the
component slowdown to the sm_120 FP64 pipe rather than Tensor Cores or bandwidth.
It adds three research modes, research-v2 evidence, tolerance tiers 1e-6/1e-4 and a
development extension. Its [report](../benchmarks/lp-fp64-pipe-gpup5c.md) verifies
806 of 850 admitted attempts; integer guards and fusion are bitwise identical to
the FP64 control and halve update cost, double-float is fastest at scale but
underflows on scheduling LPs, and tiers recover FP32 storage coverage. It used
1493.313474227 study plus 66.091602441 acceptance seconds, for 3794.758955639
cumulative inside the unchanged ceiling. No preset is selected.

GPUP-THROUGHPUT is complete under [SPEC-0014](../specifications/SPEC-0014-lp-repeated-solve-throughput.md)
and [ADR-0023](../decisions/ADR-0023-repeated-solve-throughput.md), both accepted
2026-09-20, the day the user pulled it ahead of GPUP-6. The
GPUP-5C report shows that paired certified-latency ratios stay within 0.92-1.11 of
tuned for every mode and tier, while context creation (208-330 ms) and the fixed
host phases dominate 400-600 ms solves at study size, and at 65536 rows
preconditioning (about 940 ms) and research preparation (about 1020 ms) each exceed
the total kernel time of a 200-proposal run (19-30 ms). No arithmetic slice removes
those costs. With its specification, API and resource budget accepted before any
behavior, the slice kept the fresh-process single-solve endpoint and its protocol
unchanged and never presented amortized throughput as single-solve latency. Its
[report](../benchmarks/lp-repeated-solve-throughput.md) verifies 687 of 705
admitted attempts with 4785/4785 batch solves bitwise identical to fresh singles,
setup amortized to as little as 15.6 ms per solve at N=32 on small-4 (26.6x,
separately labeled), negative results at N=1 and at 32768 rows, and 18 timed-out
65536-row short batches, consuming 2617.929459541 study plus 538.371430691
acceptance seconds for 6951.059845871 cumulative. GPUP-6 follows it under the accepted ADR-0025 contract; its completed
implementation and comparison are recorded below.

## Numerical design and candidate methods

The [2026-09-30 low-precision research review](lp-low-precision-research-2026-09-30.md)
and updated [candidate register](lp-precision-candidates.md) reconcile the completed
studies with proposals for unchanged-1e-9 refinement, a lean precision executor,
scaled double-float, selective error budgets, active-face polishing and
layout-appropriate Tensor Core/integer emulation. That review is preserved as
non-normative historical research. The [2026-10-12 design](lp-precision-architecture-2026-10-12.md)
now supplies proposed numerical contracts and the revised planning order above.
GPUP-REP CPU validation and the bounded GPUP-EXEC executor are complete under
ADR-0034/0035. No proposal is a supported preset or implicit numerical behavior;
GPUP-EXEC has its separately accepted resource amendment and retained evidence.
The original candidate comparisons below are design space, not an admitted grid.

Preserve the original FP64 model. Independent host validation and conservative
certification decide whether a candidate meets the requested contract. Iteration
arithmetic, small residuals, sampled audits, and benchmark agreement grant no
mathematical authority.

Begin with the existing diagonal preconditioning. Quantize one canonical matrix
representation and derive both multiplication orientations from it. Independently
quantizing rows and columns can produce different operators and is not the baseline.
Any alternative must explicitly establish the relationship between its operators.

| Component | Initial comparisons |
| --- | --- |
| Arithmetic | Tuned FP64; FP32 storage only; FP32 computation; FP16/BF16 Tensor Core intermediates; FP8 E4M3 and range-oriented E5M2. |
| Quantized operands | Matrix only versus matrix and iteration vectors. |
| Scaling | Global versus local blocks; power-of-two versus floating-point maximum-based scales. |
| Block size | Canonical tiles of 16, 32, and 64, including metadata, storage, and packing. |
| Rounding | Nearest-even baseline versus reproducibly seeded stochastic rounding. |
| Sensitive values | Whole-operation promotion versus selective higher-precision blocks or outlier residuals; preserve coefficients. |
| Working state | FP64 master state versus FP32 working state with periodic FP64 correction. |
| Execution | Sparse versus hybrid Tensor Core paths with equivalent reconstructed operands. |
| Recovery | Fixed versus adaptive precision; audit intervals 1, 8, 32, and 128 iterations; sticky promotion versus guarded demotion. |

Use staged screening, not the full Cartesian product. Freeze each grid and its
numerical thresholds before the corresponding timed comparisons. These are
experimental candidates, not solver defaults or supported presets.

Cheap checks at conversions/products detect non-finite values, clipping, and
nonzero values becoming zero before projections can hide them. Periodic audits
recompute an update in FP64 from its saved pre-step state. A passing sampled audit
does not certify every preceding step. Failed audits restore the complete window
start and replay at higher precision; retries and reference work consume recorded
budgets. Demotion needs configured clean windows and a stricter margin. Interval 1
provides the expensive per-step reference mode. Final certification is mandatory.

Operator changes must update or conservatively validate step-size assumptions.
Keep a conservative control policy to separate arithmetic gains from convergence
policy changes. Error feedback, FP4, and other methods needing additional analysis
are follow-ons, not prerequisites. No coefficient pruning, artificial sparsity, or
unrecorded tolerance relaxation is part of this roadmap.

Tensor Core tests use the single right-hand side the current solver actually has.
Padding unused matrix-multiply lanes is charged. Do not assume consecutive PDHG
iterations are independent columns, or assume data-center Blackwell instructions
exist on this project's device. Hardware-internal reductions are checked
numerically and for repeatability, not asserted identical to the CPU tree.

## Experiment protocol and selection

The initial campaign budget is 28,800 seconds of GPU job wall time:

| Phase | GPU-hours |
| --- | --- |
| Timing calibration, profiling, baseline sizing | 0.5 |
| Candidate screening | 2 |
| Targeted ablations and interactions | 2 |
| Frozen-finalist validation and held-out evaluation | 2.5 |
| Repeatability checks and anomaly investigation | 1 |

Record actual consumption and stop at the cap. Partial evidence yields an interim
report. Do not spend held-out time on additional tuning or silently borrow from
another campaign. [SPEC-0013](../specifications/SPEC-0013-lp-precision-experiments.md)
defines the measurement and failure rules.

Freeze development, validation, and held-out manifests, seeds, hashes, tolerances,
and resource limits before comparative trials. Previously inspected Taillard cases
remain development diagnostics. Cover structured scheduling relaxations, irregular
sparse LPs, dense-block LPs, scaling/cancellation stress, and independently checkable
small cases. Keep related generated instances and transformations in one partition.
External datasets need explicit source/license/checksum records; no new dataset or
split is frozen merely by naming it here.

Primary timing is fresh-process, end-to-end single-solve latency. Match models,
accuracy, stopping contracts, hardware conditions, and budgets. Use blocked
randomized configuration order, three repetitions for screening, and at least ten
for finalist comparisons where the budget permits. Incomplete repetition counts
are reported, not presented as full finalist evidence. Run profiling separately.

Report paired per-instance timings, confidence intervals, success coverage,
iterations, audit/retry/transition counts, memory, and certificate quality. Include
setup, transfers, packing, padding, scaling, recovery, fallback, and host checks.
Retain failures, unsupported cases, and timeouts rather than dropping them from
speedup denominators. Record source/toolchain/code-object identity, hardware/driver,
thermal conditions, and competing activity. A warm-resident timing can diagnose a
cost but cannot replace the selected single-solve endpoint.

Ablate residency, fusion, controller changes, matrix compression, vector
quantization, scaling, working-state precision, Tensor Core execution, and adaptive
recovery. Include format by scaling, precision by audit interval, and tile density
by execution-path interactions. Final certification is never disabled.

Select on validation data, freeze finalists, then inspect held-out outcomes.
Correctness and success coverage precede speed. Recommend explicit workload-specific
presets only where supported; keep the tuned baseline if no candidate reliably
improves it. State uncertainty, regressions, and negative results. Claims describe
the best tested configurations on the named workloads, not a global performance
maximum. New automatic dispatch or portfolios require their own specification.

## Interfaces, documentation, and handoff

The originally planned opt-in backend name `cuda-lp-quantized` remains reserved
and unavailable. GPUP-5 resolves the [interface handoff](gpup5-interface-handoff.md)
under accepted ADR-0019: explicit lp-precision-v1 extends cuda-lp-tuned, preserving
absent-setting behavior, prior code identities and replay compatibility.
Versioned settings will describe requested/executed arithmetic, quantization,
audits, recovery, and resource limits. Versioned records preserve transitions,
reasons, provenance, and host certification. Existing records remain readable and
existing defaults remain unchanged. Exact schemas and executable examples belong
to the implementing slices after their contracts are accepted.

Each slice updates the relevant specifications, changelog, architecture/tutorial or
operations pages, acceptance mappings, and known failures alongside its code. The
experiment package contains frozen manifests, configuration grids, validation
scripts, raw-result provenance, ablation tables/plots, and reproduction instructions.
Large generated outputs stay outside tracked source under the evidence policy;
reviewed summaries must point to reproducible artifacts.

Run `bash tools/check.sh` with pinned native HiGHS. Device slices also run relevant
tests and sanitizers under `tools/gpu_job.sh`, on one device under the host-wide
lease, sequentially with the CPU gate. No ordinary build may require a toolkit or
device. Runtime work remains Rust inside the existing ownership/unsafe boundaries.

Current handoff: GPUP-7 contract work under the
[2026-10-12 order](#current-design-order-2026-10-12), without starting quantization
behavior or reserving GPU work. [GPUP-ASSESS](../benchmarks/lp-assessment-scheduling-gpup-assess.md)
is complete under ADR-0039 with unchanged coverage and only a scoped FP64 latency
gain. Cheap movement never certifies; mandatory final host authority remains.
[GPUP-REFINE](../benchmarks/lp-refinement-gpup-refine.md) is complete under
ADR-0037/0038 with a bounded negative performance result. Full native/device,
independent rational residuals, strict replay and four scoped sanitizers pass;
only small-4 certifies at the initial host point, before any product work. All
108 attempts, 48 verified endpoints and 30/96 certified timings remain visible.
The current ledger/cumulative charge is recorded above. The following prior
handoff details retain their historical charges and limits.
[GPUP-EXEC](../benchmarks/lp-exact-executor-gpup-exec.md) completes ADR-0035
with explicit range refusals, preserved discovery failures and no total-cost win.
GPUP-STATE closes with the [bounded resource-refusal report](../benchmarks/lp-expansion-state-gpup-state.md)
under ADR-0036. Full-range scalar FMA in its first exact-bin construction exceeds
the 128-register/zero-spill gate in both formats. This is not an impossibility
claim for alternatives. PR 19's compact full-range FMA fits at 40 registers with
zero spills in both formats, removing that scalar resource obstacle. The review
now passes 6170 scalar device cases, four scoped sanitizers and 36 primitive
timing attempts on RTX PRO 6000 Blackwell. No full controller or solver benefit
is admitted. Combined charge is 30.114068273 seconds; the 16452-event ledger and
17665.546083611 / 21602.574545061 seconds preserve every historical prefix/cap.
At that handoff GPUP-REFINE still required its accepted SPEC-0021 subset and allocation.
GPUP-REP accepted CPU
reference contracts without runtime behavior. GPUP-CONVERGENCE is complete under
ADR-0032/SPEC-0013; its [report](../benchmarks/lp-convergence.md) retains 176
attempts and diagnoses work/cost amplification without selecting a preset.
GPUP-COPT-ADAPTER is complete under
SPEC-0019/ADR-0031 with a negative fresh-process bulk construction result.
GPUP-SETUP is complete under
SPEC-0018/ADR-0030 with a measured negative primary-context result.
GPUP-ADAPTIVE-COST is complete under SPEC-0017/ADR-0029; its
[report](../benchmarks/lp-adaptive-host-cost.md) verifies 32 attempts, certifies
24 timings and preserves all 16 numerical/work pairs. GPUP-HOST is complete under SPEC-0016/ADR-0028; its
[report](../benchmarks/lp-immutable-host-input.md) verifies 28 attempts, certifies
24 fresh timings and confirms one fewer model parse with fresh assessments. GPUP-EVIDENCE is complete under SPEC-0015 and
ADR-0027; its [report](../benchmarks/lp-compact-evidence.md) retains all 24 new
attempts, 15 verified endpoints and 12 certified timings. Retain all prior contracts,
reports and ledger history. The original GPUP-2 baseline remains 144 attempts
and 173.148261443 GPU seconds, not a new campaign starting point.
Full MILP integration remains separately listed in the backlog; repeated-solve
throughput is GPUP-THROUGHPUT, complete under accepted
[SPEC-0014](../specifications/SPEC-0014-lp-repeated-solve-throughput.md) and
[ADR-0023](../decisions/ADR-0023-repeated-solve-throughput.md) with its
[report](../benchmarks/lp-repeated-solve-throughput.md). Neither follows
automatically from a faster LP kernel.

## GPUP-6 completion (2026-09-26)

GPUP-6 is complete under accepted ADR-0025 and SPEC-0012: explicit lp-adaptive-v1
ladders/audits, whole-window rollback and charged replay, direct/gradual promotion,
sticky or probed demotion, fresh-single v5 evidence and replay. Original-model
host certification remains authoritative; old kernels, records and defaults remain.
Its [report](../benchmarks/lp-adaptive-gpup6.md) independently verifies
2086 endpoints from 2376 admitted of 2376 planned attempts.
Failed archive-discovery attempts and comparison gaps remain visible; no preset
is selected. Native, regular device and four adaptive sanitizer gates pass.
Campaign consumption is 8912.494084146 s inside the 14402.574545061 s ceiling;
GPUP-6 study 1826.094392481/5400 s, acceptance 70.478730162/900 s.
The 13056-event ledger SHA-256 is
6db55153153e66ed5c2398417d008e4edd278e11153cf87b975345f1a574d34d, preserving the 8278-event prefix
c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a and every earlier prefix.
GPUP-7 remains the next precision feature after the ordered COPT follow-ups below;
it needs its bounded quantization/FP8 interface and resource contract before behavior.
Adaptive sessions, persistent checkpoints and supported presets remain outside GPUP-6; old 65536-row and tuned_cases racecheck gaps remain.


GPUP-COPT is complete under ADR-0026. Its [component-cost report](../benchmarks/lp-copt-comparison.md)
retains all 1140 attempts, independently verifies 948 endpoints and certifies
402/816 primary timings. Evidence output at 65536 rows and COPT graph internals
remain explicit gaps; no winner or preset is selected. Task charge is
5853.941357570 GPU s; cumulative 14766.435441716/18002.574545061 s.
The 15340-event ledger SHA-256 is
5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b,
preserving the 13056-event prefix and every phase cap. Performance repairs ranked
in the report are ordered below. All six follow-ups are now complete with scoped
results and retained limitations. GPUP-7 still needs its accepted contract.


## Current follow-up order (2026-09-27)

Historical ordering and budget snapshot, preserved for its completed studies.
The [2026-10-12 section](#current-design-order-2026-10-12) is the current handoff.

The user requested ordering after GPUP-6 and GPUP-COPT merged. The COPT
[ranked experiments](../benchmarks/lp-copt-comparison.md#ranked-next-experiments)
are the evidence for the first six priorities. Coverage comes first, followed by
measured host costs, then additional arithmetic candidates. The first six rows are
complete under accepted contracts. GPUP-7 through GPUP-10 remain planned bounded
tasks, not accepted behavior changes or performance promises.

| Order | Task | Scope and completion decision |
| --- | --- | --- |
| 1 | **GPUP-EVIDENCE: complete** | [SPEC-0015 report](../benchmarks/lp-compact-evidence.md): four full-witness CPU round trips; 24 new attempts, 15 verified endpoints, 12 certified timings. Compact verifies 12/12 and certifies 9/12, recovering irregular/dense 65536 output; mixed remains time-limited. Historical COPT cells are unchanged. |
| 2 | **GPUP-HOST: complete** | [SPEC-0016 report](../benchmarks/lp-immutable-host-input.md): all 28 attempts verify, 24 fresh timings certify, 14 numerical/work pairs match. Parse/validation calls fall from two to one; sparse reconstruction and every candidate/certificate assessment remain fresh. Scope is one fresh solve, with no session or adaptive-preparation change. |
| 3 | **GPUP-ADAPTIVE-COST: complete** | [SPEC-0017 report](../benchmarks/lp-adaptive-host-cost.md): 32 verified attempts, 24 certified timings, 16 identical numerical/work pairs; full ladders prepare two operators rather than five, with streamed audits and borrowed probes. Arithmetic and recovery remain unchanged; no preset. |
| 4 | **GPUP-SETUP: complete** | [SPEC-0018 report](../benchmarks/lp-fresh-setup.md): 32 verified attempts, 24 certified timings and 16 equal comparisons; four control profiles precede experimental primary contexts. No consistent fresh-process benefit or default change. Persistent contexts remain a separate session endpoint. |
| 5 | **GPUP-COPT-ADAPTER: complete** | [SPEC-0019 report](../benchmarks/lp-copt-adapter.md): 84 verified attempts, 42/72 certified timings, 12 native readbacks and 24 certified acceptance endpoints. Bulk is slower in every certified cell; original wrappers and certification remain, no preset. |
| 6 | **GPUP-CONVERGENCE: complete** | [ADR-0032 report](../benchmarks/lp-convergence.md): 176 retained attempts, 174 verified endpoints and 87/104 certified timings. Per-proposal FP32 savings coexist with unsuccessful amplified work; adaptive audits/probes, reference arithmetic and certification remain explicit. No graph trace, preset or numerical change. |
| 7 | **GPUP-7: quantization interface, then sparse FP8** | Accept the bounded interface, resource and numerical contract before behavior. Stage matrix-only candidates before vector quantization; retain canonical transpose consistency, guards, seeded replay, FP64 controls and development screening. |
| 8 | **GPUP-8: hybrid sparse/Tensor Core execution** | Follow the sparse quantized reference. Compare equivalent represented operands on the actual target, including packing, padding, metadata, setup, certification and recovery for a single right-hand side. |
| 9 | **GPUP-9: controlled ablations and frozen finalists** | Reassess development candidates, select on validation, freeze finalists, then evaluate held-out data with coverage and uncertainty. Keep negative results and reserved finalist resources. |
| 10 | **GPUP-10: evidence-supported recipes** | Package only configurations supported by the final comparisons; retaining tuned FP64 is a valid result. No automatic dispatch or preset follows from the current development studies. |

Priority does not imply an artificial dependency on every earlier row. The main
sequence is GPUP-EVIDENCE → GPUP-HOST → GPUP-ADAPTIVE-COST → GPUP-CONVERGENCE
→ GPUP-7 → GPUP-8 → GPUP-9 → GPUP-10. Setup diagnosis and COPT adapter work
are separately bounded investigations in the indicated priority order, but neither
blocks quantization if unavailable or unjustified by its cost. Work still proceeds
one bounded task at a time. Each implementation declares its acceptance gate and
CPU/GPU budget before starting; public/versioned behavior needs an accepted contract.

After this precision track, GPUP-MILP requires its own integration specification
and full-search study. C7 portfolios remain a separate capability requiring a
specification; C9 SDK and C10 general runner remain separately unspecified.
Adaptive sessions, persistent checkpoints and the old 65536-row throughput gap
are outside this sequence. The historical tuned_cases racecheck gap stays visible
and must be covered for affected supported claims; it is not silently waived by
new arithmetic or by the adaptive sanitizer receipts.

The current cumulative charge is **14766.435441716 / 18002.574545061 GPU s**;
headroom under that ceiling is **3236.139103345 s**, not a new task allowance.
Phase headroom is baseline 629.524234326 s, screening 1086.653583558 s,
ablations 1525.038223925 s and repeatability 1792.348516475 s. Finalists retain
9000 s under the overall 28800 s campaign cap; using more than the current
cumulative ceiling still requires explicit authority. Do not borrow between
phases, spend held-out resources on tuning, or reset the 15340-event ledger.
Start with CPU-only evidence work and small justified comparisons; a new broad
17-configuration campaign is not part of this ordering.

GPUP-EVIDENCE consumes 305.274714773 GPU seconds without new allowance. Carry
15071.710156489 / 18002.574545061 seconds and the 15392-event ledger SHA-256
6a30c1954ff9bc80c733364d8e8a7c0fc4c4439d70b959d2c10996d71993e518 forward;
the 15340-event COPT prefix and all phase caps remain intact.

GPUP-HOST consumes another 134.072418846 GPU seconds without new allowance:
91.461934760 timing, 19.113062965 profiling and 23.497421121 acceptance. Carry
15205.782575335 / 18002.574545061 seconds and the 15452-event ledger SHA-256
90dab78c269b74f511416ddd73cf05e123555ae006b9ad75fc896933a35f9cd2
forward, preserving the 15392-event prefix above. GPUP-ADAPTIVE-COST is now complete
under SPEC-0017/ADR-0029, using 201.890184622 GPU seconds within existing allowance.
Carry 15407.672759957 / 18002.574545061 seconds and the 15528-event ledger
SHA-256 cb0dc57f9f92546f4cc2d93b0de3c8556d6b24517f71b7a6efaa91fa96afedb6; the 15452-event prefix remains intact.
GPUP-SETUP is complete under SPEC-0018/ADR-0030, using 224.608447458 GPU seconds.
Carry 15632.281207415 / 18002.574545061 seconds and 15606 ledger events, SHA-256
ad3d84354f0b74ae62fcc019ee4dcbf29b0a3251d066f1e0f2df11ccb107230b; the 15528-event prefix remains intact.
GPUP-COPT-ADAPTER is complete under accepted SPEC-0019/ADR-0031. Its
[report](../benchmarks/lp-copt-adapter.md) independently verifies all 84 attempts,
certifies 42/72 timings and 10/12 profiles, and retains all interrupted/rejected
outcomes. Twelve native readbacks and 24 min/max/profile endpoints pass; 27/36
timing pairs and 10/12 profile comparisons match, with the remaining CPU-default
pairs deadline-limited. Bulk loading is cheaper, but CSC preparation and cold
SciPy import make this adapter slower in every certified cell. No preset or
runtime/kernel/default change; historical wrappers and evidence remain intact.
Task charge 171.904859644 GPU seconds; cumulative 15804.186067059 /
18002.574545061 seconds, no added allowance. The 15776-event ledger SHA-256
2b99b615dc77da07fb078e1cefc188d2131db5ca671fe9b86f989a6d660606f0 preserves the
15606-event prefix above and every phase cap. The subsequent convergence study
retains this prefix. GPUP-7 still needs its accepted quantization contract.

GPUP-CONVERGENCE is complete under accepted ADR-0032/SPEC-0013. Its
[report](../benchmarks/lp-convergence.md) retains all 176 frozen attempts,
independently verifies 174 endpoints and certifies 87/104 timings
and 32/72 diagnostic profiles. Two dense-65536 accumulation-FP32 timings
have no endpoint; every interruption and rejection remains visible, without retries.
Scoped per-proposal savings do not overcome unsuccessful FP32 work; adaptive
reference arithmetic, recovery and original-model assessments remain material.
Full pre/post native gates, 58 regular device tests, twelve fixed-work pairs and
replays, eight COPT min/max/profile endpoints and ten source-only contracts pass.
Runtime, kernels, settings, defaults and historical evidence remain unchanged;
no preset is selected. CPU-only recovery/report review corrections are exactly bound.
Task charge 1311.088550794 GPU seconds: timing
634.748860654/800, profiles 441.911765452/800,
acceptance 234.427924688/300; cumulative 17115.274617853 /
18002.574545061 seconds, with no new allowance. The 16134-event ledger SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823 preserves the
15776-event prefix 2b99b615dc77da07fb078e1cefc188d2131db5ca671fe9b86f989a6d660606f0
and every phase cap. Historical racecheck/session/mixed-model gaps remain open.
At convergence-study completion the handoff was GPUP-7's contract. The
2026-10-12 order inserted GPUP-REP CPU-only proof/contract validation, now
complete. GPUP-EXEC then completed under its separately accepted ADR-0035.

## GPUP-EXEC completion (2026-10-13)

The [bounded executor report](../benchmarks/lp-exact-executor-gpup-exec.md) retains
108 attempts, verifies 94 endpoints and certifies 58/96 timings. Cached and
uncached exact products agree on all 27 study pairs; native, device, replay and
four scoped sanitizer gates pass. Range refusals, fourteen initial discovery
failures and six control timeouts remain visible. No preset or total-cost win.

Task charge is 520.157397485 seconds: timing 431.684266725/2300, profiles
36.003675982/450 and acceptance 52.469454778/850. ADR-0035 explicitly amends the
cumulative ceiling to 21602.574545061 seconds; consumption is 17635.432015338.
The 16366-event ledger SHA-256 is
4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b,
preserving the 16134-event prefix above and every phase cap. GPUP-STATE is next,
subject to its own primitive/state contract and resource gates. No reservation
for that task follows from unused headroom.
