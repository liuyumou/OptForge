# SPEC-0013: Bounded LP Precision Experiments

Status: accepted; GPUP-2 implemented and measured; later slices pending
Scope: LP-only development measurement, ablations, evidence, and recipe selection
Owner: experiment tooling and numerical backend
Introduced: GPU LP precision research, GPUP-0
Last reviewed commit: bootstrap (first commit containing this document)
Supersedes: none; extends SPEC-0007 for a separately versioned LP study
Implementation: GPUP-2 CLI/backend observations and tools/ LP harness; GPUP-3 through GPUP-10 pending
Tests: implementation mapping below; [baseline evidence](../benchmarks/lp-baseline-gpup2.md)

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

The version-1 contract below and ADR-0014 finalize these choices before GPUP-2 behavior.
Existing strict schemas cannot be extended by unversioned extra fields. Resume
means resuming a study ledger; it does not introduce solver checkpoint restart.

### GPUP-2 version-1 wire contract

All objects reject unknown/duplicate fields and nonfinite numbers. Hashes are
SHA-256 of exact bytes; local paths are confined to their declared root. The JSON
schemas are normative for field spelling and required/optional distinctions.

- lp-campaign-v1: identity, hashed manifest references, configuration grid,
  solve/LP settings, partition, seeds, repetitions, analysis, resource limits,
  pinned device and immutable total/phase/slice GPU allocations.
- lp-manifest-v1: identity/partition, instance ID, family/group, model path,
  byte hash/size, source/license and generator version/seed/parameters.
- lp-endpoint-v1: model hash, requested backend, unchanged solve record,
  canonical row-ID multiplier witness or explicit absence, recomputed host
  assessment, work/memory/phase diagnostics and fallback reason. Assessment
  contains feasibility/objective, certificate or refusal, conservative gap and
  classification. Native statuses/bounds are diagnostics, not certificates.
- lp-trial-v1: campaign/config/instance/block/repetition/order, timing/profile
  mode, provenance/limits, process outcome, nanosecond elapsed/queue/lease time,
  memory method, hashed output references and verified endpoint or absence.
- lp-ledger-v1: append-only reserve/settle/recover events with campaign hash,
  monotone sequence, reservation/trial identity, phase, CPU/GPU class and
  reserved/charged nanoseconds. Flush and fsync before work; exclusively lock
  campaign mutation through execution. The canonical ledger directory is derived
  from campaign identity, independently of output paths, and binds one output
  directory so changing --output cannot reset consumption. Recover unresolved reservations at full
  cost. Never bypass an ambiguous/corrupt ledger. Preserve a torn trailing event
  as crash evidence before repairing it under the exclusive lock.

The supervisor starts a foreground process group, sends SIGINT at ten seconds,
cancellation or sampled RSS overflow, and escalates to SIGKILL within two further
seconds. Preserve bounded stdout/stderr and partial output. A leased supervisor
owns the deadline independently of the outer runner; retain the lease until
children are reaped. Queue wait is separate. Charge unexpected overruns fully and
stop further jobs. Reserve enough for teardown before acquiring the lease.

Diagnostic entry points share ordinary backend execution. A dual witness must
match the candidate assessment even if the work limit ends between checks.
Independent host checking occurs before completed evidence output. Profiles use
synchronized phase boundaries and remain separate from primary samples. Unavailable
measurements carry a reason; zero means measured zero or an inapplicable operation.

Frozen choices are in [ADR-0014](../decisions/ADR-0014-lp-baseline-protocol.md).
Requirements 24-31 and 33 retain their GPUP-9/10 implementation gates; accepting
this contract does not authorize held-out evaluation or preset selection in GPUP-2.

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

The maintainer accepted this contract for GPUP-2. Preserve existing
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

GPUP-2 includes explicitly synthetic trial/ledger schema examples,
[executable reproduction instructions](../benchmarks/lp-precision-study.md), and
[a measured development baseline](../benchmarks/lp-baseline-gpup2.md) with hashed
raw evidence. GPUP-9/10 retain the held-out comparison and recipe-selection gates.

## Acceptance tests

GPUP-2 assertions are implemented in tests/integration/test_lp_study.py,
optimizer-experiment LP unit tests, and the two study_observation device tests.
Later-slice mappings remain pending; measured acceptance and exact device/sanitizer
coverage are recorded in [active task](../../state/active-task.md).

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

### Implemented GPUP-2 acceptance mapping

- Requirements 1-5: frozen generation, exact witness construction, grouped partitions,
  altered seed/target/config/hash/path refusals in ProtocolTests and the gate's
  lp_generate.py materialization comparison.
- Requirements 6-9: Ledger reservation/recovery/phase/concurrency tests, forced
  process cleanup, and isolated simulated shared-lock tests. Device execution
  remains opt-in under the actual host lease.
- Requirements 10-18: known-delay child, separate profile flags, deterministic
  schedule, complete trial intents/results, requested/executed identity and the
  lp_gpu_cli_check.py actual-device fallback check.
- Requirements 19-21: optimizer-experiment::lp unit tests preserve assessment/witness
  alignment; corrupted claims and malformed duals fail; EndpointTests checks
  native minimization/maximization witnesses and the standalone verifier.
- Requirements 22-23: exact paired ratios, censored failures, incomplete counts and
  fallback exclusion in ProtocolTests; raw trial/ledger coverage is required by
  lp_report.py.
- Requirements 32, 34-35: five strict schemas, old artifact gates unchanged, task
  resource/evidence state, native gate receipt and scoped device acceptance.

## Open questions

ADR-0014 and the frozen version-1 artifacts now specify the initial instances,
seeds, targets, limits and analysis. All three baselines provide untrusted row
multipliers for independent host certification; native status alone is insufficient. Eight GPU-hours may yield only an
interim result. The fastest configuration and its useful workload range remain
hypotheses until the later controlled study is complete. GPUP-2 development
measurements establish baseline costs and coverage, with no recipe selected.

## ADR-0016 supplementary version-2 interfaces

The frozen lp-matched-v2 campaign names four configuration/binary roles, profile
instances, immutable baseline budget authority, prior consumption, supplementary
allowance and admission policy. Trial-v2 additionally records that authority hash,
pre-reservation activity reference/wait, and schema snapshot hash. Version-1
campaign, manifest, trial, ledger and endpoint schemas remain byte-for-byte intact.
The budget ledger retains its original authority/hash and output binding; new
study IDs do not create another spending allowance.

Endpoint-v2 is emitted only when cuda-lp-matched is requested. Its optional control
object records host-restart-weight-v1, logical and physical steps, LP kernel
launches, assessments, KKT evaluations, restarts, weight and stop reason. Physical
steps are null after a fault if completion is unknown. Missing controller data
before opening/initialization is explicitly unavailable. Payload integrity includes
this object. The verifier rejects impossible identity, stop/work or assessment
alignment claims and independently rechecks the original model and certificate.
Legacy solves still emit endpoint-v1. New readers accept both versions.

`optimizer lp-study replay --model MODEL --evidence ENDPOINT --output FRESH
[--device UUID]` verifies the source and executes its recorded implementation;
a historical fallback therefore replays HiGHS. It independently checks the new
endpoint, refuses existing outputs and uses the normal selected-device/lease and
fallback boundary. Elapsed-time termination can differ on replay; a fresh endpoint
is evidence, not an assertion that a timeout reproduced bit for bit.

Tooling validation: test_lp_overheads.py and test_lp_matched.py cover immutable
schema reuse, strictness, v1 preservation, activity/admission races, frozen paired
analysis and actual CPU child/replay/verification boundaries. Existing ledger,
crash, cleanup, failure and partition tests remain acceptance requirements.

Supplementary acceptance: [GPUP-3 report](../benchmarks/lp-matched-fp64-gpup3.md),
160/160 retained attempts, no invalid/missing evidence, 251.845179881 additional
GPU seconds and 445.988045904 cumulative seconds. All 12 development instances
received three repetitions; four received separate profiles. Validation/held-out
partitions remain unmeasured. Low-precision ablations and recipe selection remain
pending. Full native and scoped device/sanitizer evidence is recorded in active task.
