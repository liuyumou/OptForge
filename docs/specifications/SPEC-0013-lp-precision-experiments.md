# SPEC-0013: Bounded LP Precision Experiments

Status: draft; harness and study not implemented
Scope: LP-only development measurement, ablations, evidence, and recipe selection
Owner: experiment tooling and numerical backend
Introduced: GPU LP precision research, GPUP-0
Last reviewed commit: bootstrap (first commit containing this document)
Supersedes: none; extends SPEC-0007 for a separately versioned LP study
Implementation: pending GPUP-2 through GPUP-10
Tests: planned requirement mapping below; no measured results in slice 0

## Purpose

Make a precision recipe an experimentally supported conclusion. The selected
objective is certified single-solve latency, and the first campaign is bounded to
eight GPU-hours under [ADR-0013](../decisions/ADR-0013-lp-precision-study.md).
Numerical authority remains [SPEC-0011](SPEC-0011-gpu-lp-backend.md) and the future
[SPEC-0012](SPEC-0012-mixed-precision-lp.md), never this performance contract.

This is development/validation tooling over the project's LP solve boundary,
not the C10 general comparative runner, C9 Python SDK, or C7 portfolio API. It
introduces no external dataset, preset, default, or measured claim in slice 0.

## Terminology

A *campaign* is a frozen study identity with a persistent budget ledger. A *trial*
is one configuration/instance/repetition execution, successful or otherwise. A
*block* pairs configurations on one instance/repetition under comparable conditions.
*Screening*, *validation*, and *held-out evaluation* have different roles: the
first two may select settings, the last evaluates frozen settings. A *certified
endpoint* requires original-model validation and the prescribed conservative gap,
not merely a backend's reported optimal flag.

## Requirements

### Inputs and budgets

1. A study MUST freeze its configuration grid, numerical targets, seeds, manifests,
   partitions, resource limits, and analysis procedure before comparative timing.
2. Every manifest MUST identify source/license, generator/version/parameters if used,
   unique instance IDs, hashes, and grouped split membership.
3. Related generated instances and transformed variants MUST remain in one partition.
4. Previously inspected Taillard instances MUST remain development diagnostics rather
   than be relabeled held-out evidence.
5. A split, seed, threshold, tolerance, or default change MUST have a decision record
   and a new experiment identity before the changed trials run.
6. The first campaign MUST enforce a total cap of 28,800 seconds of GPU job wall time
   including failed trials and profiling, with the phase allocations below.
7. A restarted harness MUST recover prior consumption from its ledger rather than
   reset the budget; uncertain consumption after a crash MUST be conservatively charged.
8. Each trial MUST have explicit CPU, memory, work, and wall-time limits within the
   remaining campaign allocation, with cancellation and partial output recorded.
9. All GPU jobs MUST execute on one selected device under the shared host-wide lease.

### Measurement

10. Primary timing MUST use a monotonic clock around a fresh-process single solve,
    from process launch through completion of its validated/certified output.
11. End-to-end timing MUST include input/setup, device creation, transfers,
    quantization, packing/padding, iteration, audits, recovery, fallback, and final host checks.
12. Comparisons MUST match original models, required accuracy, stopping contracts,
    resource limits, and declared CPU/GPU conditions.
13. Profiling MUST run separately from definitive timing; warm-resident and kernel-only
    measurements MUST be labeled secondary diagnostics.
14. Configuration order MUST be blocked and reproducibly randomized from recorded seeds.
15. Screening MUST use three repetitions and finalist comparisons MUST use at least
    ten per planned block, or explicitly report incomplete evidence when budget-limited.
16. Each trial MUST record source revision/dirty state, input/config/manifest hashes,
    hardware/UUID/driver, toolchain/code-object identity, timing method, relevant thermal
    conditions, and observed competing activity or explicit unavailability of telemetry.
17. Raw results MUST retain every attempted trial, including unsupported cases,
    numerical failures, timeouts, cancellations, and fallback execution.
18. A result's requested and executed backends/arithmetic MUST be distinguished so
    that CPU fallback time cannot be attributed to successful GPU computation.

### Validation and analysis

19. Successful endpoint classification MUST independently check the original model's
    candidate, objective, and conservative bound/gap evidence rather than trust device
    diagnostics or a backend status alone.
20. Baseline comparisons MUST include pinned HiGHS, existing host/GPU FP64, and the
    tuned algorithmically matched FP64 control as those implementations become available.
21. A baseline without the required conservative bound evidence MUST be labeled as a
    reference timing rather than silently counted as a certified endpoint.
22. Reports MUST show paired per-instance timing, uncertainty, success coverage,
    iteration/audit/retry/transition counts, memory, and certificate quality.
23. Failures and censored timeouts MUST NOT be dropped to improve reported speedups.
24. Single-component ablations MUST cover residency, fusion, controller changes,
    matrix compression, vector quantization, scaling, working-state precision,
    Tensor Core execution, and adaptive recovery for retained candidates.
25. Interaction studies MUST include format by scaling, precision by audit interval,
    and tile density by execution path for surviving applicable candidates.
26. Every timed ablation MUST retain final independent certification.
27. Candidate selection MUST use development/validation results before finalist
    configurations and analysis are frozen for held-out evaluation.
28. Held-out results MUST NOT tune a recipe that is still claimed to be evaluated
    independently on those same results.
29. Correctness and success coverage MUST take precedence over speed in recommendations.
30. A study with insufficient evidence or no reliable improvement MUST report that
    outcome and retain the tuned baseline rather than invent a winning low-precision preset.
31. Reports MUST distinguish best-tested configuration claims from any global
    performance optimum, including hardware/workload limits and negative results.

### Artifacts and acceptance

32. New LP study artifacts MUST have their own versioned schemas, strict validation,
    provenance checks, and migration notes without changing existing record meanings.
33. A supported preset MUST reference the frozen validation/held-out evidence and
    decision record that justify its scope and numerical settings.
34. Each slice MUST record its documentation, acceptance tests, CPU/GPU budget and
    actual consumption, unresolved issues, and next dependency-ready handoff.
35. The harness MUST pass the full native CPU gate and applicable lease/device checks
    before any generated output is presented as acceptance evidence.

## Interfaces

Planned artifacts: LP campaign configuration, frozen instance manifest, candidate
grid, append-only trial records and budget ledger, independently checked endpoint
records, and a report referencing the raw evidence. These require separate versioned
schemas from the bootstrap smoke result. The CLI solve contract is the workload
entry point; Python under tools/ is orchestration/analysis tooling, not a runtime SDK.

Trial records include nanosecond timings, phase timings, instance/config identity,
block/repetition/order, solver limits, status, diagnostics, executed arithmetic,
accepted/rejected/audit work, peak-memory measurement and method, original-model
validation, certificate outcome, and all provenance in requirement 16. Unsupported
or unavailable measurements are explicit, not fabricated zeros. Reports reference
raw record hashes and the analysis configuration.

Schema names and exact wire fields, subprocess timeout/cleanup behavior, and the
ledger crash-reservation algorithm must be finalized before GPUP-2 implementation.
Existing strict schemas cannot be extended by unversioned extra fields. Resume
means resuming a study ledger; it does not introduce solver checkpoint restart.

## State and invariants

The campaign allocation is fixed as follows:

| Phase | GPU seconds |
| --- | --- |
| Calibration, profiling, baseline sizing | 1,800 |
| Screening | 7,200 |
| Ablations and interactions | 7,200 |
| Frozen-finalist validation and held-out evaluation | 9,000 |
| Repeatability/anomaly reserve | 3,600 |
| Total | 28,800 |

Charge the entire GPU study job after lease acquisition through teardown, including
host phases inside that job. Queue wait is reported separately and is not GPU use.
No two device selections run simultaneously. Do not start a job without sufficient
reserved budget for its configured bound. Charge failed jobs and conservative crash
reservations. Keep CPU-only study and acceptance costs in separate visible totals.
Each implementation slice declares acceptance-only GPU work separately; it is not
unrecorded campaign spending. Reallocating phase budgets needs a recorded protocol
revision before the affected trials, within the unchanged eight-hour overall cap.

Use workload families covering current structured relaxations, irregular sparse
operators, dense tiles, difficult scaling/cancellation, and independently checkable
small LPs. Freeze exact IDs/sizes/seeds and licenses before trials. Do not choose a
family only because preliminary timing favors Tensor Cores. Keep unsupported and
out-of-memory cases visible rather than reducing the suite after seeing results.

Use three screening repetitions; a finalist planned block needs ten or more.
Report paired per-instance median latency and ratios with 95% confidence intervals
using a predeclared paired resampling procedure. Preserve configuration pairing
and treat problem instances, not repeated timings alone, as the units for claims
across problems. Repeated runs measure timing variability; they do not establish
generalization. State uncertainty when samples or timer resolution are inadequate.
The resampling seed/count and any multiple-comparison procedure are frozen with
the analysis configuration before comparisons. Do not add an aggregate winner
score that hides per-instance failures or regressions.

A timeout is censored at its recorded limit, never treated as successful completion.
For successful pairs, ratios describe that subset explicitly; the full paired
coverage table remains alongside it. A stopped or incomplete study is not a zero
speedup. Validation selects candidates; held-out data estimates their effect. If
an anomaly forces recipe changes, affected held-out cases become development data
for that revision and require a new independent evaluation partition and record.

The candidate families and initial grids are in the
[roadmap](../plans/gpu-lp-precision-roadmap.md#numerical-design-and-candidate-methods).
Use staged screening rather than their full product. Preserve eliminated methods
and reasons in the report; mark inapplicable ablations rather than inventing a
result. No final-certification-disabled timing enters a performance claim.

## Errors and recovery

Malformed artifacts, duplicate identities, hash mismatches, path escapes,
inconsistent seeds/configurations, missing provenance, interrupted ledgers,
unsupported formats/hardware, and exhausted budgets produce explicit errors or
partial-study status. Keep failure outputs. Resume cannot bypass trial budgets or
reclassify an unsuccessful run. Backend/device failure and numerical recovery are
separate events. Existing availability/fallback behavior remains observable.

## Compatibility and versioning

Accept this draft and complete its wire contracts before GPUP-2. Preserve existing
SPEC-0007 artifacts and existing Taillard manifests unchanged. A new manifest and
decision record are required for the concrete LP partitions; this document creates
none. Automatic dispatch/default changes and the general C10 API remain outside
this contract. Future schema revisions include old-reader/migration fixtures.

## Security and resource limits

Validate local manifest paths, byte sizes, hashes, and subprocess limits before
execution. External data needs source/license/checksum review and bounded retrieval;
large datasets and raw reports stay outside tracked source. No external publishing
or hosting is authorized. The host lease, explicit time/memory/CPU limits, and
crash-safe budget ledger are acceptance properties, not runner conveniences.

## Examples

If FP8 halves iteration time but doubles the iteration count and adds audits, the
report uses measured end-to-end completion, not the kernel speedup. If it reaches
a time limit on a baseline-successful case, that is a coverage loss, not an omitted
pair. If a fallback solves the model, it is counted with its full cost and labeled
with the backend actually executed.

No measured example is provided in GPUP-0. GPUP-2 will add explicitly synthetic
schema examples plus executable reproduction instructions. GPUP-9/10 supply real
provenance-bearing results only after trials and independent validation.

## Acceptance tests

All mappings are planned. Named implementation tests and actual evidence must
replace the pending descriptions slice by slice.

| Requirements | Planned assertion | Slice |
| --- | --- | --- |
| 1-5 | Frozen grid/manifest identities; altered seed/hash/split refusals; related-instance leakage and inspected-data fixtures. | GPUP-2 |
| 6-9 | Simulated clock and interrupted-ledger recovery; no budget reset/overrun; CPU/GPU accounting; single-host lease exclusion. | GPUP-2 |
| 10-15 | Instrumented child with known phase delays; full timing boundaries; profiling separation; deterministic block order; repetition completeness. | GPUP-2 |
| 16-18 | Required provenance and telemetry absence; unsupported/failure/timeout retention; requested-versus-executed fallback fields. | GPUP-2 |
| 19-21 | Perturbed candidate/objective/bound/status fixtures fail independent checks; equal-contract baseline versus reference-only labels. | GPUP-1, GPUP-2 |
| 22-23 | Hand-checkable paired/censored fixtures; uncertainty and coverage tables cannot hide failed trials. | GPUP-2, GPUP-9 |
| 24-26 | Ablation matrix accounts for every retained component and applicable interaction; certification always enabled. | GPUP-9 |
| 27-31 | Frozen finalist identity; held-out retuning refusal; insufficient/negative evidence reports without preset promotion. | GPUP-9 |
| 32-35 | Strict schema/provenance/migration cases; preset-to-evidence links; slice ledger and documentation; full gates. | GPUP-2, GPUP-10 |

## Open questions

Concrete instances, generator dimensions, seeds, split membership, numerical
thresholds, repetition scheduling within phase caps, and analysis parameters need
recorded freezing before trials. They are not chosen silently by this draft.
GPUP-2 must define how each baseline supplies independently checkable bound evidence;
pinned HiGHS status alone is not a substitute. Eight GPU-hours may yield only an
interim result. The fastest configuration and its useful workload range remain
hypotheses until the study is complete.
