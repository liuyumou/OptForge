# GPU LP Performance Research and Implementation Roadmap

Status: approved roadmap; slices 0-1 complete; slices 2-10 pending
Owner: numerical backend and experiment tooling
Introduced: GPU LP precision research track (GPUP)
Last reviewed commit: bootstrap (first commit containing this document)
Implementation: [backlog](../../state/backlog.yaml), [active task](../../state/active-task.md)
Acceptance: the slice gates below; no performance results yet

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

- [SPEC-0012](../specifications/SPEC-0012-mixed-precision-lp.md) drafts numerical,
  recovery, and interface requirements. It is not an implemented capability.
- [SPEC-0013](../specifications/SPEC-0013-lp-precision-experiments.md) drafts the
  bounded LP study, its artifacts, and acceptance mapping.
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
| GPUP-3 | Create a resumable FP64 control implementation with shared restart, weight, checkpoint, cancellation, and budget state. | Whole-trajectory and restart checks; identify controller differences from existing implementations. |
| GPUP-4 | Optimize FP64 residency, allocation, transfers, sparse kernels, and compatible fusion where profiling supports it. | Isolated residency/kernel/fusion measurements and numerical checks; a tuned control baseline. |
| GPUP-5 | Add FP32 matrix storage with FP64 arithmetic, then FP32 products/accumulation. Compare FP64 masters and FP32 working state with FP64 correction. | Original-model checks, convergence and range diagnostics, measured storage/arithmetic/state costs. |
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

The planned opt-in backend is `cuda-lp-quantized`; it is not available in slice 0.
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

Next handoff after GPUP-1: finalize the experiment contract and establish the
measurement infrastructure under GPUP-2. Full MILP integration and repeated-solve
throughput are separately listed in
the backlog; neither follows automatically from a faster LP kernel.
