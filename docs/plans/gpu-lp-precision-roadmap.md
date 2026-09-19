# GPU LP Performance Research and Implementation Roadmap

Status: approved roadmap; slices 0-5 and GPUP-5B complete; GPUP-5C complete; slices 6-10 pending
Owner: numerical backend and experiment tooling
Introduced: GPU LP precision research track (GPUP)
Last reviewed commit: bootstrap (first commit containing this document)
Implementation: [backlog](../../state/backlog.yaml), [active task](../../state/active-task.md)
Acceptance: the slice gates below; [GPUP-2 baseline evidence](../benchmarks/lp-baseline-gpup2.md), [GPUP-3 matched evidence](../benchmarks/lp-matched-fp64-gpup3.md), [GPUP-4 tuned evidence](../benchmarks/lp-tuned-fp64-gpup4.md)

## Objective and working agreement

Optimize **end-to-end single-solve latency at the required feasibility and
certified-gap tolerances**, including setup, transfers, numerical checks, recovery,
and final certification. This is the user's selected priority. Repeated-solve
throughput and full MILP search performance are future tracks, not substitutes for
this objective.

Implement one dependency-ready slice at a time. Each leaves a buildable,
documented result, acceptance evidence, and a handoff. Update active-task state
before work; record evidence, limitations, and a local commit afterward. Do not
publish or push without authorization. The user selected an **eight GPU-hour cap**
for the first experiment campaign.

FP32-to-FP8 computation and Tensor Core execution are in scope. FP8 is a candidate,
not a required winner. The final recipe follows measurements and ablations; an
experiment that finds the tuned baseline faster is a useful negative result.
This track follows C6 but does not complete C7, C9, or the general C10 runner.

## Contracts and status

- [SPEC-0012](../specifications/SPEC-0012-mixed-precision-lp.md) is accepted for
  implemented GPUP-3/4 shared FP64 control and explicit tuned execution. Later
  precision, recovery and preset requirements remain pending.
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

Every row depends on the preceding row; GPUP-0 depends on C6 and C8. New behavior
requires the relevant draft specification to be accepted before implementation.
Slice 1 repairs the existing SPEC-0011 certification contract. Later slices may
be refined from earlier findings, with changes recorded before affected trials.

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
6/36 for FP32 working state. GPUP-6 is next after completed acceptance. No
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
cumulative inside the unchanged ceiling. GPUP-6 follows and requires its bounded
adaptive contract; no preset is selected.

## Numerical design and candidate methods

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

Next handoff after GPUP-2: accept SPEC-0012 and create the shared resumable FP64
controller under GPUP-3. The baseline completed 144 attempts and consumed
173.148261443 GPU seconds; preserve that ledger consumption. Host/GPU controller
differences and limited GPU certified coverage are documented in the baseline report.
Full MILP integration and repeated-solve
throughput are separately listed in
the backlog; neither follows automatically from a faster LP kernel.
