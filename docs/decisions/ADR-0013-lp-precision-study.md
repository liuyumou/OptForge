# ADR-0013: A Bounded LP Precision Study Before Recipe Selection

Status: accepted (study design; measurements pending)
Owner: experiment tooling and numerical backend
Introduced: GPU LP precision research, GPUP-0
Last reviewed commit: bootstrap (first commit containing this document)
Supersedes: none; extends the evidence policy without changing ADR-0011's existing split
Superseded by: none

## Context

The user requires the highest practical solver performance, sound experiments, and
ablations before choosing a precision recipe. They selected single-solve latency
and eight GPU-hours for the first campaign, and deferred repeated-solve throughput
and full MILP search performance. Existing timing scripts are development
diagnostics. [ADR-0011](ADR-0011-scale-split.md) explicitly says its Taillard scale
split is visible during development and is not held-out evidence.

## Decision

Use fresh-process end-to-end time to an original-model validated candidate and the
required conservatively certified gap as the primary endpoint. Include setup,
transfers, quantization, packing/padding, audits, replay, fallback, and final host
checks. Algorithm-only and warm-resident timings are secondary diagnostics. Do not
infer LP or MILP acceleration from a kernel throughput number.

Specify an LP-only experiment harness and its records under
[SPEC-0013](../specifications/SPEC-0013-lp-precision-experiments.md) before implementing
it. Python remains development/validation tooling, Rust owns runtime behavior,
and neither the general C10 runner nor the C9 SDK is introduced by this decision.

Cap the initial campaign at eight GPU-hours: 0.5 calibration/profiling, 2 screening,
2 ablations, 2.5 frozen-finalist validation/held-out evaluation, and 1 repeatability
or anomaly investigation. Include failed study jobs in the ledger. Run only one
GPU job across the host under the shared lease. Exhaustion yields an interim
report, not permission to exceed the cap or discard inconvenient outcomes.

Before comparative trials, freeze manifests, grouped development/validation/held-out
partitions, numerical targets, seeds, candidate grids, limits, and statistical
analysis. Register concrete split/seed/threshold choices in a follow-up decision
record and experiment configuration before measurement; this ADR creates no
instances, threshold, or split by naming them. Existing inspected cases stay
visible-development data. Never tune from held-out outcomes and continue calling
the same data held-out for the revised recipe.

Use paired per-instance comparisons with blocked randomized run order, three
screening repetitions, and at least ten finalist repetitions when the cap permits.
Record incomplete evidence explicitly. Retain unsuccessful runs and report success
coverage alongside time and uncertainty. Avoid a single score that hides failures
or workload-specific regressions. Ablate both individual components and the
specified interactions; independent final certification is never removed.

Compare against pinned HiGHS, the existing host and GPU FP64 paths, and a tuned,
algorithmically matched FP64 control. Separate controller and execution changes
from arithmetic changes. Select on validation, freeze finalists, then evaluate
held-out cases. Support explicit presets only when evidence justifies them. A
negative result can retain FP64 or FP32 as the best tested recipe. Automatic
portfolios and dispatch policy are not authorized here.

## Alternatives

Select FP8/Tensor Cores in advance: rejected because padding, low reuse, numerical
recovery, and extra iterations can erase their gains. Reuse the visible Taillard
split as held-out data: rejected because it was already used for development.
Run a full Cartesian search: rejected because its cost does not fit the selected
budget. Optimize batch throughput or MILP first: deferred to separate tracks at
the user's request.

## Consequences

The campaign requires new versioned artifacts and a baseline profile before new
performance claims. Eight hours may be insufficient to select a supported recipe;
the honest output then is an interim report and a separately budgeted follow-up.
A study on one host establishes no general hardware ranking. New datasets need
license and provenance records. No performance preset or default changes in slice 0.

## Implementation and tests

The [roadmap](../plans/gpu-lp-precision-roadmap.md) assigns the harness to GPUP-2,
component measurements to GPUP-3 through GPUP-8, coordinated comparisons to GPUP-9,
and recipe documentation to GPUP-10. SPEC-0013 maps the intended artifact,
measurement, budget, leakage, and analysis checks; none is reported implemented by
this documentation slice. Full gates and provenance-bearing evidence precede any
performance claim.
