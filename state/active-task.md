# Active Task

## FP4 GPU exploration and quality-tier roadmap amendment (2026-11-11)

The user authorizes the recommended split between CPU numerical recovery,
bounded GPU feasibility and subsequent certified solver comparison. They also
accept a separately labeled 1e-7 final certificate as an encouraging result when
FP4 produces sufficient speedup. Keep 1e-9 as the strict tier; the old 1e-7 inner
enclosure guard is a different quantity and remains part of the frozen v1 record.

Scope: a superseding planning ADR, explicit independent GPU-pilot/integration
tasks, dual-quality complete-cost criteria, roadmap/design/backlog navigation and
handoffs. No numerical implementation, solver/checker default change, GPU job or
scientific retry runs in this documentation task. Preserve exact old specifications,
ADRs, proposal, sources, results and charges. The old prototype stays incomplete.

Independent documentation envelope: 512 CPU seconds, zero GPU; 128 preparation
and receipt packaging, 320 validation, 64 cleanup; four CPU slots, 6 GiB sampled
host RSS. Use the unchanged supervisor and a new journal under
artifacts/gpup-fp4-gpu-roadmap-v1. No closed-budget transfers. Acceptance: document
links, acyclic/ready dependencies, explicit pilot admission independent of the
600-update gate, matched quality/performance rules, exact historical preservation
and diff hygiene. Local commit after acceptance; no push/publication. Future
experiments begin with a concrete protocol/resource package under their own task.

Delivered: ADR-0058 and aligned roadmap/design/backlog/README/wiki. Next ready is
GPUP-FP4-GPU-PILOT, independently of CPU recovery and old 600-update qualification;
new FP4-INTEGRATE precedes TENSOR2. Future original-model final tiers are 1e-7 and
strict 1e-9. The initial 1.10x cold model-median geometric-mean target uses
same-tolerance native controls, no certified model-median regression or coverage
loss, uncertainty and complete setup/audit/recovery/checking costs.

Acceptance passes 201 documentation pages/internal links, acyclic/ready dependency
checks, unchanged completed tasks and old prototype, exact numerical source/input
bindings, historical roadmap/handoff preservation, documentation-only scope and
diff hygiene. The first memory preflight refused before launching/reserving a
workload; its operator note is retained. The first admitted validator assumed
every old backlog entry had a specification and retains its full 240 CPU-second
failure charge. The separate corrected validator passes at 14.173538052 seconds;
its journal uses only unused 80-second reporting and 64-second cleanup headrooms
inside the original 512-second ceiling. No budget is added or transferred.

Preparation charges 128 seconds; final cleanup reserves and fully charges 64.
Total including that reservation is 446.173538052 CPU / zero GPU seconds. Final
receipts, both journals, failed sources/logs and exact accounting are under
`artifacts/gpup-fp4-gpu-roadmap-v1`; the settled summary is `final-accounting-v1.json`.
No numerical or device experiment ran. Local commit after cleanup; no publication.

## GPUP-FP4-PROTO bounded CPU delivery (2026-11-11)

The requested prototype's CPU slice is implemented under SPEC-0026 / ADR-0057.
Its frozen twelve-cell numerical attempt admits no lane: nine error-guard and
three metadata refusals, zero observations or certificates. Full component
rollback preserves physical work and deadlines. Full prototype acceptance is
incomplete; device implementation/MMA/sanitizers and all 36 pilot/diagnostic cells
are closed and unexecuted. No GPU time is charged.

Frozen v1 sources/results remain exact. The separate v2 local-budget correction
addresses cancellation between pair-rounding and encoding errors; three primitive
tests pass, with no corrected scientific attempt. Full native acceptance passed
638 Rust and 571 Python tests, replay/dependency/artifact/docs/smoke. The later
Python-only launcher failure (Cargo absent from PATH) retains its full 1000 CPU
charge; an environment-only software rerun passes all 574 Python tests. Final receipts:
docs/benchmarks/lp-fp4-proto-gpup-fp4-proto.md.

All new charges remain within the independent 32000 CPU / 1560 GPU envelope.
The formal refusal retains 2400 CPU seconds, preparation 256. Two development
1200-second caps carve disjoint subsets from unused original implementation
headroom, adding no authority. Closed failed journals and all historical charges
are preserved. The reporting/cleanup journal remains separate.

Next ready: GPUP-FP4-RECOVERY-SPEC, CPU-only corrected accounting and proved
trajectory enclosure/precision/cost proposal. Preserve original-model FP64 checks
and 1e-9 certification; no automatic retry, GPU stage, TENSOR2 or GPUP-9 release.
Native control stays supported and GPUP-8 incomplete. Local commit after software
and delivery acceptance; no publication. Earlier task entries retain their scope.

## GPUP-FP4-PROTO implementation (2026-11-11)

The user requests the next prototype. Implement an independent rational PDHG
reference, persistent E2M1 component trajectory with explicitly charged local
FP32-pair rounding, original-unit error/projection admission, rollback/escalation
and source-bound execution records under SPEC-0025. CPU numerical admission
precedes any actual-MMA implementation/admission, sanitizers or profiles. Preserve
the original 1e-9 certificate, all historical sources/results/charges and native
control. A failed numerical gate closes subsequent device/profile execution;
report the remaining unexecuted work and distinguish enclosure refusal from
actual trajectory error. No automatic scientific retry or TENSOR2 execution.

Independent allocation selected under the implementation/time authorization:
32000 CPU seconds, 1560 GPU seconds, four CPU slots, one shared GPU lease,
16 GiB sampled host RSS and 12 GiB admitted device buffers. CPU phases:
implementation 6000 including 256 preparation, proofs 8000, native 8000,
workers 6240, reporting 2960, margin/cleanup 800. Conditional GPU phases:
admission/sanitizers 480, pilot 720, diagnostics 360. The CPU increase over the
proposal funds implementation and trajectory analysis explicitly; no transfer
from any closed task. Use the unchanged in-container supervisor with a new
artifacts/gpup-fp4-proto-v1 journal. Whole reservations must fit; failed/unsettled
jobs retain their full charge. Development fixes preserve failed sources/logs.

Acceptance: independent CPU primitive/trajectory/recovery contracts and one
frozen numerical admission, full CPU/native integration, conditional actual FP4
instruction/device/four-sanitizer/profile gates, explicit all-cell disposition,
source/evidence preservation, settled accounting and empty cleanup. Likely new
reference/runner/tests/specification/ADR/records and conditional device kernel
files; no old numerical source or public default changes. Local commit after
acceptance; no push/publication.

## GPUP-FP4-SPEC completed (2026-11-11)

The executable CPU contract is delivered under SPEC-0025 / ADR-0056: bounded
2/4/8-plane E2M1 encoding, consistent transpose tiles, exact error/projection
oracles, original-unit observation guards, complete transactional checkpoints,
three schemas and frozen source-bound cost/resource admission. The 32 focused
tests and full CPU/native integration pass, including 549 Python tests, replay,
197 documentation pages and smoke. Final accounting/source/cleanup receipts:
docs/benchmarks/lp-fp4-spec-gpup-fp4-spec.md.

The prospective comparison retains 192 cells / 288 endpoints. Retained cold
control review: six ideal per-trial 10% speedup refusals, fifteen profile-needed
rows, three uncertified rows and zero admitted forecasts. No GPU work, native
solver change, final-certificate relaxation or historical scientific rerun.
The independent 16000 CPU / zero GPU envelope remains authoritative; phase
`proofs` in the unchanged supervisor journal implements the contracts allocation.

Next ready: GPUP-FP4-PROTO, starting with CPU reference/trajectory admission.
Prototype and study resource amounts remain proposals, not execution allocations.
Keep native control; GPUP-8 incomplete and GPUP-9 gated. Local commit after
acceptance; no push/publication. The implementation entry below records the
accepted task envelope, and older handoffs remain exact.

## GPUP-FP4-SPEC implementation (2026-11-11)

The user requests implementation and permits as much budget as needed. Implement
SPEC-0025 / ADR-0056 as a separate CPU-only executable numerical/cost contract:
E2M1 component encoding, consistent matrix/transpose tile scales, bounded error
and projection decisions, observation-only audits with full checkpoints, strict
proposal/checkpoint/cost schemas, a frozen development comparison/resource
proposal and focused adversarial contracts. No device executor or solver is
implemented by this slice; FP4-PROTO remains subsequent work.

New independent ceiling: 16000 CPU seconds, zero GPU; four slots, 16 GiB sampled
host RSS. Phases: implementation 3200 including a conservative 256 preparation
charge, contracts 1600, native integration 8000, reporting 2400, cleanup 800.
Use the unchanged in-container CPU supervisor with a fresh journal under
artifacts/gpup-fp4-spec-v1. Whole reservations must fit; failed/unsettled work
retains its full charge. No historical allocation transfer or scientific rerun.

Acceptance: focused independent CPU contracts and proposal/evidence binding,
full tools/check.sh with GPUs hidden, documentation/schema consistency, diff and
historical-source preservation, final accounting and empty cleanup. Likely writes:
new tools/tests/schemas/config/specification/ADR/protocol/report plus current
roadmap/backlog/handoff/changelog. Legacy numerical/checker sources and public
defaults stay unchanged. Local commit after acceptance; no push/publication.

## FP4 persistent-state feasibility and roadmap review completed (2026-11-11)

The user requests assessment and roadmap changes for multiple FP4 components,
reconstruction-free inner iterations and fused kernels. They explicitly select
approximate inner arithmetic with original-model FP64 residual checks and the
unchanged 1e-9 final certificate; exact FP64-equivalent arithmetic is not required.

Scope: primary-source literature/ISA review, retained expansion/resident evidence,
a concrete design proposal, a new planning ADR, roadmap/backlog and handoff.
Acceptance: sourced hardware claims, explicit numerical/cost unknowns, no hidden
per-iteration FP64 round trip, bounded future gates, documentation links, backlog
consistency and unchanged historical numerical sources/results/charges.
This review runs no solver, GPU, compiler, formal arithmetic proof or benchmark.

Separate documentation envelope: 512 CPU seconds (128 preparation/editing,
320 validation, 64 cleanup), four CPU slots, 6 GiB sampled host RSS, zero GPU.
Use the unchanged supervisor with a fresh journal under
artifacts/gpup-fp4-roadmap-v1; historical allocations stay closed. Local commit
after acceptance; no push/publication. Proposed implementation and studies need
their own numerical contracts and resource allocations.

Delivered: docs/plans/lp-fp4-persistent-state.md and ADR-0055, with current
roadmap/backlog/README/wiki navigation aligned. GPUP-FP4-SPEC is next ready;
FP4-PROTO and TENSOR2 remain conditional. MIXED2/DELIVERY2 remain alternatives.
The assessment distinguishes persistent component state from zero-cost local
normalization, counts cross-products and projection/error work, and requires
original-model observation-only audits plus native and FP8/FP16 comparisons.

Acceptance passes 194 documentation pages/internal links, acyclic task/dependency
checks, completed-task and historical-text preservation, documentation-only scope
and diff hygiene. Supervised validation charges 13.863842980 CPU seconds, plus
128 conservatively charged preparation seconds. Final cleanup is separately
reserved within 64 CPU seconds; exact receipts and closed accounting remain in
artifacts/gpup-fp4-roadmap-v1. No arithmetic, device, profile or solver gate ran.

## RESIDENT2 lessons: roadmap revision completed (2026-11-11)

Objective: turn the retained negative result into concrete planning gates and
correct stale forward-looking text. MIXED2 remains the next numerical candidate;
its first step is CPU-only cost admission from retained per-trial evidence.
Make delivery-cost optimization an explicit alternative when arithmetic cannot
meet the proposed total-latency target. Preserve cold/prepared distinctions,
independent 1e-9 certificates and the unresolved mixed-model bound limitation.

Scope: roadmap, a new superseding planning ADR, backlog and current handoff.
Acceptance: documentation/internal links, backlog consistency, diff hygiene and
unchanged numerical sources/evidence. No solver, GPU or historical gate rerun.
Separate documentation-only envelope: 256 CPU seconds (64 preparation/editing,
160 validation, 32 cleanup), four CPU slots, 6 GiB sampled host RSS, zero GPU.
Historical allocations stay closed. Validation uses the unchanged CPU supervisor
with a new journal under artifacts/gpup-resident2-roadmap-v1. Local commit after
acceptance; no push or publication. No future scientific task is released.

ADR-0054 and the roadmap/backlog now record the cost gate, conditional DELIVERY2
alternative, measured limits of synchronization reduction, lifecycle distinction
and separate mixed-model bound-authority problem. Stale export and future
RESIDENT2 implementation text is corrected. MIXED2 remains next ready for
contract/cost preparation against the native control.

Acceptance passes 192 documentation pages/internal links, YAML task/dependency
consistency, unchanged historical handoff/roadmap text, documentation-only scope
and diff hygiene. The supervised validation charges 13.687409792 CPU seconds;
preparation is conservatively charged 64 seconds. Cleanup uses the separately
reserved 32-second stage. Exact receipts/journal are retained under
artifacts/gpup-resident2-roadmap-v1. No numerical code, data, historical charge,
solver setting or scientific criterion changes; no solver/GPU test is rerun.

## GPUP-RESIDENT2 completed; latency retention gate fails (2026-11-11)

The requested bounded implementation and comparison are complete under
SPEC-0024 / ADR-0053. Report: docs/benchmarks/lp-resident2-gpup-resident2.md.
All 64 planned cells completed and delivered 96 endpoints. Control and resident
each certify 42/48; all 42 certified pairs have identical candidate bytes and
iteration counts. All twelve mixed-model normal-limit endpoints now export
65536 primal/dual entries and remain uncertified at variable 3's infinite-bound
refusal. The original 1e-9 authority is unchanged.

The candidate uses exact per-window coefficients, u64 sticky flags, bounded
asynchronous submission and transactional host adoption. Prepared lifecycles
reuse immutable preparation with fresh iterates/controller/checking per solve.
The nontrivial trace reduces synchronizations 58 to 44 at the same 2800 launches,
but increases transfer bytes. The cold model-median geometric mean is 1.027370x;
four of seven certified medians regress. The predeclared total-latency criterion
fails, so retain the native control and select no supported preset.

Acceptance: full CPU/native gate (638 Rust tests, 515 Python tests, replay,
dependency/artifact/docs/smoke), separately verified test-only overflow correction,
five focused Python contracts, device boundary/controller/cancellation/rollback,
four independent transport certificates, and all four zero-error sanitizers.
The original overflow fixture and stale-test-binary failures retain their full
charges; all development/native failures remain recorded. Active study reader:
tools/lp_resident2_study_v4.py. No timing cell was retried. Exact sources and old
scientific results/charges are preserved; the six historical source edits have
an exact additive/test-only bridge.

Task GPU charge is 598.631222067 / 1800 seconds, including all failures.
CPU and final cleanup receipts are in the report's acceptance/accounting files,
within the independent 32000-second ceiling. Historical allocations stay closed.
Next ready: GPUP-MIXED2, using the native control; no next-task execution is
released. GPUP-8 stays incomplete and GPUP-9 gated. Local commit after delivery;
no push or publication was requested.


## GPUP-RESIDENT2 implementation (2026-11-11)

The user requests implementation and permits more time as needed. PR #23 is
merged at 4e62cab04ca2236d419c2deea4063a42a4f519ef; the prerequisite is met.
Implement SPEC-0024 / ADR-0053: non-overlapping delivery phases, cold/prepared
immutable model lifecycles, separate native resident FP64 execution with bounded
submission, coefficient tables and sticky device flags. Preserve exact original
coefficients, host controller boundaries, fresh independent certificates and all
historical evidence. Diagnose normal-limit export without changing bound authority.

New task envelope selected under this implementation/time authorization: 32000
CPU seconds (implementation 8000 including 128 preparation, native acceptance
8000, device acceptance 4000, study 8000, reporting 3200, cleanup 800); four CPU
slots, one shared GPU lease, 16 GiB sampled host RSS, 12 GiB device buffer limit.
New GPU ceiling 1800 seconds (acceptance 600, study 1200), independently accounted
in artifacts/gpup-resident2-v1/resources. No historical funds are transferred.
Per-job full reservations must fit; failed/unsettled reservations remain charged.
Use the unchanged in-container supervisor. All jobs stay in this container.
Development fixes retain failed logs and sources; scientific cells have no automatic
retry. CPU/native admission precedes device checks, sanitizer admission precedes
matched study. No GPUP-8 rerun or GPUP-9 release. No push/publication requested.

Acceptance: focused CPU contracts, full tools/check.sh, device differential and
failure/cancellation checks, four scoped sanitizers, frozen same-transport native
control/candidate cold and prepared cohorts with launch/copy counts, independent
endpoint checking, all-cell coverage and total latency decision. Record an honest
negative or blocked result if admission or performance fails. Likely writes:
new research module/kernels/driver/tools/tests/specification/report and task state;
no legacy numerical source or public solver default changes.


## GPUP-BASELINE PR integration (2026-11-10)

PR #23 is ready for the normal merge path. Local composite acceptance passes
634 Rust tests, 512 Python tests, committed-record replay, all 188 documentation
pages/internal links and CPU smoke. The native build, Clippy, dependency and
artifact gates also pass. The initial full-gate failures and all charges remain
preserved; the last documentation failure is resolved by publishing the original
733-byte JSON receipt at its existing ADR link target. No executable/test source
changed after the passing numerical suite. Final acceptance:
`docs/benchmarks/data/external-baseline-pr-local-acceptance-v5.json`.
Hosted Actions still starts no jobs and reports startup_failure; the full local
command coverage is disclosed in the PR. Integration GPU usage is zero.

The user explicitly requests merging the current changes through a PR before
starting the next task. This authorizes commits, push, PR creation and merge;
older no-publication handoffs below describe their original scope. Integrate the
four unmerged GPUP-8 commits and the completed baseline, diagnosis and roadmap.
GPUP-8 remains incomplete and GPUP-9 remains gated; no new GPU study follows.

Acceptance: preserve recorded scientific sources/results and charges, make the
baseline CPU tests reproducible without local benchmark installations, run the
repository CPU integration gate, inspect the complete PR diff and lockfiles,
require passing CPU/docs/smoke checks, then merge and verify main ancestry. Test-only
portability changes retain their exact prior sources and a separate source bridge.
Likely writes: test support/fixtures, CI dependency pins, integration receipt and
current handoff. No vendor binaries, credentials or ignored experiment directories
are published. Local validation is bounded to four CPU slots and 6000 CPU seconds
(including 128 for preparation); GPU allocation is zero. Hosted CI keeps its
existing 30/10/10-minute CPU/docs/smoke deadlines. Historical allocations remain
closed. The full CPU integration gate is newly authorized for this PR; it does
not rerun the GPU campaign or its formal proof/profile sequence.

Local clean-checkout baseline tests pass with no historical study artifacts or
vendor environments. The v3 source bridge preserves 813 frozen runtime files,
eight exact prior test sources and the original requirements manifest. The first
full local gate found 22 historical test-fixture errors; the portable GPUP-8
fixture correction passes all 79 affected/neighboring CPU tests. Both failed
attempts retain their logs and charges in the v4 integration receipt.

Hosted Actions currently returns startup_failure without starting any jobs;
the earlier main CI annotation explicitly reports an Actions budget restriction.
Run the identical full CPU gate and separate docs/smoke commands locally before
normal merging, record the hosted limitation in the PR, and never bypass branch
protection or manufacture a successful hosted status. This operational fallback
implements the user's already authorized merge; no scientific criterion changes.

## GPUP-BASELINE completed with native-return reporting (2026-11-10)

The user authorized completion and counting cuOpt returns without reported errors
as passes while logging differences. ADR-0052 / SPEC-0023 implement that policy
separately from unchanged strict certification. All 240 planned screening cells
now have settled attempts: 123 reused and 117 new. 198 meet their
comparison policy; 135 certify strictly. CuOpt has 90/96 native-return
passes and 24/96 strict certificates. Normal limits remain limits; explicit
NumericalError remains a native failure. Outer failures and missing certificates
remain separate even when a native return passed. Nothing is relabeled optimal.

Report: docs/benchmarks/lp-external-baseline-native-return.md. Full machine rows:
docs/benchmarks/data/external-baseline-native-result-v1.json. Final accounting and
acceptance: external-baseline-native-accounting-v1.json and
external-baseline-native-acceptance-v1.json in the same directory. Total baseline
GPU charge is 3091.995889713 / 3600 seconds, including all prior failures.
The new CPU allocation is separately bounded at 32000; final settled charges are
in the accounting receipt. Historical CPU caps/charges remain closed and exact.

Nine new policy/export tests and one installed Solution API check pass. Prior
hardware/tests/certificates are reused; source/input/settings admission and final
metadata/documentation/cleanup checks are recorded in the delivery receipt.
Versions v1 through v5, their sources, partial native returns and all failed
reservations stay immutable. No old numerical gate/profile was rerun. The
historical 17438-event GPU ledger remains exact. No vendor installation, native
settings, checker mathematics or public solver defaults changed.

GPUP-BASELINE and its follow-up protocol are complete under the amended policy.
Next ready: GPUP-RESIDENT2, with explicit phase attribution and cold/prepared
model lifecycles before claims about faster arithmetic. No new scientific task
or spending is released by this handoff. GPUP-8 remains incomplete and GPUP-9
stays gated. No commit, publication or merge was requested.

## GPUP-BASELINE native-return continuation (2026-11-10)

Status: accepted continuation, now closed by the delivery above; the user requested
to complete the baseline and
accept cuOpt results without vendor-reported error while logging discrepancies.
ADR-0052 and SPEC-0023 supersede the CPU-only handoff and cuOpt certificate gate
for this separate v5 cohort. Strict mathematical certification remains unchanged
and separately reported; native success never becomes certified optimality.

Reuse all 123 settled screening trials and run only the 117 unexecuted cells.
Retain all original models, settings, deadlines, order, failures and charges.
Likely files: new policy/metadata adapter, versioned coordinator/worker/budget,
new focused tests and execution schema, frozen evidence, report and task state.
Acceptance: actual cuOpt error/status metadata, immutable prior bindings, full
240-cell disposition, separate native and strict-quality results, cleanup,
resource accounting and documentation. No historical solver check/profile rerun.

New continuation CPU ceiling: 32000 seconds (implementation 1600 including 128
preparation, screening 28080, reporting 1600, cleanup 720). This is a separate
allocation for the newly requested work; old CPU caps/charges remain historical.
Total baseline GPU cap remains 3600 seconds, including 1277.244626616 already
charged; v5 may reserve 2322 whole GPU seconds. Entire jobs must fit. Four CPUs,
one shared GPU lease and existing memory/output limits remain. No automatic
retry, new vendor installation, native parameter change or GPUP-9 execution.

## GPUP-BASELINE bounded implementation delivery (2026-11-10)

Implementation is delivered; the full scientific comparison remains incomplete.
Report: docs/benchmarks/lp-external-baseline-gpup-baseline.md. Machine summary:
docs/benchmarks/data/external-baseline-result-v1.json. Final accounting and
acceptance: docs/benchmarks/data/external-baseline-final-accounting-v1.json and
external-baseline-acceptance-v1.json in the same directory.

Six configurations/twelve admission suites pass. Of 240 planned screening cells,
123 execute and 108 certify; 96 are blocked by four cuOpt admission failures and
21 remain unexecuted after CPU reservation admission exhausts. Preserve cuOpt
numerical/postsolve refusals, the native failures and all unexecuted cells.
GPU charge is 1277.244626616 / 3600 seconds. CPU screening charges
9775.536859960 / 9860; total baseline CPU ceiling is 16000. ADR-0051's current
phase caps supersede the initial allocation below. Final CPU delivery totals
are in the accounting receipt. No unused phase or GPU headroom authorizes a retry.

Active implementation: tools/lp_baseline_study_v4.py and the buffered research
checker; v1 through v4 sources, artifacts, failed charges and source bridges stay
immutable. The active v4 reuses all admission outcomes and five small-model
blocks; its 33 large-model executions are separate from sixteen retained v3
transport timeouts. The lost-guardian v2 cancellation retains its full 240 CPU
charge and cleanup record. No passed numerical acceptance or historical profile
is rerun. Twenty-five new Python tests and one Rust writer test pass; scoped
format/lint/build and delivery checks are recorded in the report.

Next ready task: GPUP-BASELINE-FOLLOWUP, a CPU-only protocol using retained
records. Specify the exact 21 missing cells (5040 worker CPU / 720 GPU seconds
plus itemized overhead), per-path cuOpt postsolve/quality admission and native
missing-candidate error handling, and cold versus prepared model/evidence costs.
Do not launch those jobs, relax certification or silently transfer funds from
this handoff. GPUP-BASELINE stays in progress; RESIDENT2/MIXED2 remain gated on
its disposition. Historical GPUP-8 is incomplete with scientific stages closed;
GPUP-9 remains gated. The 17438-event historical GPU ledger and original numerical
sources remain exact. No commit, publication or merge is part of this delivery.

## GPUP-BASELINE initial implementation authorization (2026-11-10)

Status: accepted initial allocation, superseded by the delivery above and ADR-0051;
authorized by the user's instruction to implement GPUP-BASELINE
with 3600 additional GPU seconds. Implement separate vendor adapters, a neutral
Rust checker, immutable execution manifests, bounded admission and conditional
screening. Keep all ten lanes and 240 planned screening cells visible. Reuse the
retained numerical libraries and supervisor; do not reopen GPUP-8 or GPUP-9.

Bounds: new baseline GPU cap 3600 seconds (480 admission, 3120 screening),
charged separately without changing the historical ledger. CPU ceiling for this
new work is 16000 seconds, conservatively within the 18036.902496786 seconds below
the existing cumulative ceiling: 2400 implementation, 240 hardware, 2400 adapter
admission, 8960 screening, 1200 reporting and 800 reserved cleanup. Four CPUs,
one foreground job, 16 GiB sampled aggregate host RSS, 12 GiB sampled GPU memory.
This is an explicit allocation for the newly authorized baseline; no prior
failure is refunded or old stage retried. Whole-job reservations must fit before
launch; failed/unsettled jobs retain the full reservation. A partial grid is
reported as partial, never silently reduced to a favorable subset.

Acceptance: new checker/conversion/runner tests; pinned input readback and
min/max/offset/ranged dual mapping; nontrivial original-model certificates and
actual execution evidence; frozen dependencies; cleanup and immutable history.
Likely files: research/lp-external-baseline, new lp_baseline tools/tests/schemas,
ADR-0048, run artifacts/report and task state. No public solver defaults change.


## GPUP-BASELINE-SPEC: implement the external comparison contract (2026-11-10)

Status: complete; explicitly authorized by the user.
Objective: specify and validate canonical LP input, external endpoint/status and
comparison manifest contracts for project FP64, cuOpt 26.10.0 and COPT 8.0.6;
freeze timing, quality, comparison and admission rules; prepare a concrete future
resource proposal. Gurobi is unavailable and excluded from required execution.
Likely files: SPEC-0022, a protocol/decision record, versioned JSON schemas,
CPU-only contract validation and focused fixtures/tests, backlog and status docs.
Acceptance: new contract positive/negative checks, exact resource arithmetic,
documentation links, dependency consistency and preserved historical evidence.
Work bounds: CPU-only, no solver/model construction through vendor APIs, no GPU
jobs; each new test or documentation command has a 120-second wall limit, each
metadata inspection 30 seconds. Up to 600 process CPU seconds for new validation,
measured separately from historical campaign journals. No old scientific gate or
profile reruns. Future solver execution and resources are proposed, not reserved
by this specification task. GPUP-8 remains incomplete; GPUP-9 remains gated.

Delivered: SPEC-0022, comparison protocol, three schemas, CPU-only validator and
canonical CSC/CSR conversion, synthetic examples and local API provenance.
Twenty new focused CPU tests pass. The proposal contains ten lanes/eight models
and 240 screening cells, with phase A 6040 CPU / 480 GPU seconds and phase B
58600 CPU / 10080 GPU seconds. Resources are proposed only; execution remains
disabled. Next ready task is GPUP-BASELINE adapter/checker implementation.

Delivery checks pass: 178 documentation pages/internal links, 49 unique acyclic
backlog tasks, exact phase/shortfall arithmetic, proposal/model source bindings,
synthetic endpoint validation and diff hygiene. Fifteen retained evidence files
and twelve inspected source files remain hash-exact; historical numerical sources,
ADRs and model manifests are unchanged. Receipt:
docs/benchmarks/data/baseline-spec-acceptance-v1.json. No historical scientific
check or profile was rerun, and no full solver/native acceptance is claimed.

## System diagnosis, revised roadmap and cuOpt provisioning (2026-11-10)

Status: complete; authorized by the user's request to save the diagnosis,
make the roadmap concrete and install cuOpt if possible. Gurobi is unavailable.
Owner: numerical backend and experiment tooling.
Objective: record the actual GPUP-8 result and dominant costs, select explicit
next design steps, and provision an isolated optional cuOpt environment.
Likely files: diagnosis, a new ADR, the GPU LP roadmap, backlog, README, status,
changelog and solver setup documentation/receipts. Historical numerical sources,
ADRs, experiment artifacts, charges and ledger stay immutable.

Acceptance: documentation/internal links, task dependency consistency, scoped
diff/evidence preservation, and installation/package checks with GPUs hidden.
Operational limits: at most 900 wall seconds per package installation attempt,
30 seconds per import check and 120 seconds per documentation/check command;
single setup process, no GPU jobs. This is documentation/provisioning work under
the new request, not a draw on or reopening of historical scientific allocations.
No completed scientific gate is rerun. Solver measurements and new numerical
implementations require their own protocol and allocation. GPUP-8 remains
incomplete; GPUP-9 remains gated.

Delivered: [source-bound diagnosis](../docs/benchmarks/lp-system-diagnosis-2026-11-10.md),
[ADR-0047](../docs/decisions/ADR-0047-certified-performance-roadmap.md),
[current roadmap](../docs/plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10)
and aligned backlog/navigation. cuOpt 26.10.0 is installed in an isolated
environment; dependency and LP import checks pass with GPUs hidden. The
[setup record](../docs/operations/cuopt.md) includes a 56-package wheel-hash lock.
Next ready task: GPUP-BASELINE-SPEC, the comparison contract and resource proposal.
Gurobi is excluded from its dependencies. No solver execution was performed.

Validation: 176 documentation pages and internal links/anchors pass; 49 backlog
tasks have unique IDs and acyclic dependencies, with a ready successor and explicit
GPUP-9 gate. Retained profile/accounting/ledger hashes and setup-receipt bindings
pass. Historical numerical sources and ADR-0046 are unchanged; scoped diff hygiene
passes. Full native/device/scientific gates were not rerun for this delivery.

## GPUP-8 corrected proof and device acceptance pass; profile timeout (2026-10-24)

Final delivery passes 173 documentation pages/internal links, immutable evidence
checks and staged diff hygiene. Four exact hash-bound EOF blank-line exceptions
preserve historical/generated bytes; all other whitespace checks pass.
Cumulative CPU is 59603.097503214 / 77640 seconds; this recovery charges
8034.404049688. Timing and restricted-margin funds remain unused.
All coordinator/guardian cleanup receipts are empty. Final accounting:
docs/benchmarks/data/tensor-expanded/recovery-final-accounting-v1.json.
Final journal: artifacts/gpup-tensor-expanded-v1/recovery-hygiene-v1/cpu-journal-final-v21.json.

The corrected 7376-case proof, CPU/model/native gates and all six device jobs pass.
All twelve fixed-work/replay pairs are accounted for; twenty changed endpoints
independently verify once. Six small-model profiles complete. The first large-model
BF16 profile times out at its unchanged 18-second deadline without an endpoint.
Nine profiles and sixty timings remain unexecuted. Preserve the full 3200 CPU-second
profile failure charge and every source, image, receipt and historical charge.
No completed check/profile is rerun; no numerical or latency criterion changes.
GPU charge is 178.049776450 seconds; GPUP-8 1410.959187474/3000 and campaign
22770.545043263/25202.574545061. The 17438-event ledger
preserves the exact 17412-event prefix. Timing funds remain unused.
Report: docs/benchmarks/lp-tensor-expanded-recovery-gpup8.md.
Scientific stages are closed. GPUP-8 remains incomplete; GPUP-9 stays gated.

## GPUP-8 device acceptance passes; large-model profile deadline stop (2026-10-24)

The corrected proof, CPU model admission, native build and six device jobs pass.
Six small-model profiles complete and independently verify. The first large-model
BF16 profile reaches its unchanged 18-second worker deadline without an endpoint.
Preserve its timeout and full 3200-CPU-second profile reservation charge; no more
profiles, resource admission or timings follow. Timing funds remain unused.
CPU-only delivery uses existing reporting funds, with 488 CPU seconds for
120 work-wall seconds of reporting and 200 for documentation/evidence checks.
Active journal: artifacts/gpup-tensor-expanded-v1/recovery-delivery-v1/cpu-journal-v19.json.
GPUP-8 remains incomplete and all completion criteria remain unchanged.

## GPUP-8 corrected proof passes; freeze and bounded device continuation (2026-10-24)

The corrected 7376-case proof, new arithmetic/window checks, all twelve useful
400-update dense CPU configurations, four zero-spill CUDA modules and native
executor acceptance pass. Reuse every passed receipt and compiled image.
Transfer 400 unused implementation CPU seconds to artifact-adapter acceptance,
with 16 CPU seconds for bookkeeping. Active journal is artifacts/
gpup-tensor-expanded-v1/continuation-v1/cpu-journal-v18.json. Freeze all 76 study
cells, six device jobs and exact evidence bindings before device observations.
Then run acceptance, profiles and conditional timings in isolated existing
4000/3200/6400 CPU reservations. Preserve the 17412-event GPU prefix, 1760-second
cohort cap, all deadlines and completion criteria. No old check/profile rerun.

## GPUP-8 native integration passes; final profile instrumentation (2026-10-24)

Clippy, producer compilation and two new interface tests pass. Preserve their
source/binary receipts. Complete the required cumulative first-certificate,
final-assessment and execution timing fields before device freeze, using the
retained observation schedule and formula. Bind the actual executor and preserve
deadline status after final assessment. Arithmetic, window logic and images stay
exact; reuse all numerical/interface checks. Transfer 320 unused executor-recovery
CPU seconds to new telemetry acceptance, running only its one new contract test
and affected producer compilation/lint. Active journal: artifacts/
gpup-tensor-expanded-v1/telemetry-build-v1/cpu-journal-v17.json. No GPU work yet.

## GPUP-8 wrapper lint correction (2026-10-24)

The integration construction gate stops at two unused retained enclosure helpers
imported into the new library wrapper. No arithmetic/device test fails or runs.
Preserve the exact failed compiler inputs and full 1600-CPU-second charge. Under
the user's explicit harness-correction authority, add a scoped unused annotation
to that module; its numerical body remains exact. Transfer 700 unused primitive
compile seconds and 100 unused authority seconds to the new 800-second gate.
The formatter already passed and is not rerun. Continue only unpassed Clippy,
producer build and new interface tests. No GPU work or changed criteria.
Active journal: artifacts/gpup-tensor-expanded-v1/executor-recovery-v1/cpu-journal-v16.json.

## GPUP-8 executor integration gate (2026-10-24)

The new 32-byte argument test passes; all sixteen retained boundary tests were
filtered out. Preserve that exact source in its acceptance snapshot. A new event
module extends the same boundary for bounded CUDA-event observations; its added
module declaration leaves the accepted argument/launch bodies exact. The CPU
solver adapter preserves the complete passed solver body and adds probe access.

The isolated executor now binds canonical penultimate arrays to retained native
reference buffers, rejects stale generations and reuses the four compiled images.
Reserve 1600 unused CPU seconds (800 proof-retry, 800 CPU-model headroom) for
new executor build, new interface checks and artifact/source acceptance. No passed
numerical check or image compilation is rerun. Active journal: artifacts/
gpup-tensor-expanded-v1/executor-build-v1/cpu-journal-v15.json. Device acceptance
and the frozen study remain gated. Completion criteria and GPU caps are exact.

## GPUP-8 update enclosures pass; launch ABI integration (2026-10-24)

All 2400 new exact-rational update cases and 7200 inverse-magnitude enclosures
pass. The separate guard image uses at most 40 registers and zero spills. The
four compiled modules remain partial inventory until executor and acceptance
are complete. Reuse their images and all passed checks.

The new SoA kernels take 32-byte descriptors, whereas the retained safe launcher
owns only eight bytes per argument. Build a versioned research copy of the same
optimizer-cuda-sys boundary with aligned owned 32-byte argument storage. Preserve
the original crate and images; no new foreign API or unsafe owner is introduced.
Run only new argument-layout tests. Transfer 600 unused proof-retry CPU seconds
to this ABI stage; all numerical and study gates remain unchanged. The active
journal will be launch-abi-v1/cpu-journal-v14.json. No GPU work yet.

## GPUP-8 residual reconstruction inventory (2026-10-24)

The corrected assembly reader passes ten new opcode cases and admits the saved
seven-entry module without compilation or numerical reruns. Continue with a
separate residual/sparse reconstruction module, outward magnitude metadata and
original-unit product enclosures. Preserve all passed sources and images. Reserve
1200 unused implementation CPU seconds for this new compile-only stage, under
the unchanged 128-register/zero-spill requirement; retain all earlier charges.
The versioned journal will be residual-build-v1/cpu-journal-v12.json. This remains
CPU-only and partial: full device integration, reference-buffer binding, candidate
acceptance and all study gates remain prerequisites to any completion claim.

## GPUP-8 emitted-instruction scanner correction (2026-10-24)

The wider CUDA module compiles successfully: all seven entries use <=72 registers,
zero stack/spills, and all three Tensor entry points contain intended MMA.
The scanner falsely rejects `fma.rn.f32 ... %f64`: it mistakes a register name
for an FP64 type modifier. Preserve the exact successful image, assembly, original
refusal, sources and full 800-CPU-second failure charge. The user's explicit
harness-correction authorization permits an artifact-only corrected review.
Transfer 160 unused CPU-model seconds, with 16 for diagnosis/bookkeeping. Test
opcode parsing, re-read the existing assembly, and continue only if unchanged
requirements pass. Rerun no compiler, numerical check or profile.
Active journal: artifacts/gpup-tensor-expanded-v1/instruction-review-v1/cpu-journal-v11.json.
No GPU work or scientific criterion changes.

## GPUP-8 CPU matrix passes; wider CUDA component inventory (2026-10-24)

All five new recovery/controller tests pass. All 48 CPU cells are accounted for,
including eight retained tuned controls, 24 layout refusals and 16 new endpoint
verifications. All twelve required dense cells admit useful/eligible 400-update
trajectories; scaling-256's expected matched-control refusal remains. The CPU
stage charges 924.347221328 seconds. Preserve all source/binary/endpoint receipts.

Continue to one compile-only module for 8x10/14x16 Tensor main products, separate
u64 magnitudes/signs, Expansion64 reconstruction, warp-local packing and fused
primal/dual updates. Transfer 800 unused CPU-model seconds to compilation; charge
16 implementation seconds for source construction. Require intended Tensor
instructions, <=128 registers and zero spills. This is still a partial inventory:
residual/enclosure integration, complete CUDA executor and device acceptance
remain gated. Reuse every passed check/profile and existing primitive image.
Active journal: artifacts/gpup-tensor-expanded-v1/product-build-v1/cpu-journal-v10.json.
No GPU work, additional resources or changed completion criterion.

## GPUP-8 new CPU recovery checks and model admission (2026-10-24)

Three focused Rust window/preparation checks pass. Reuse their exact sources and
receipts. Run only five additional recovery/controller tests, then the inherited
48-cell CPU model matrix: new candidate and affected matched controls, with the
unchanged tuned control reused through its original bindings. Verify each new
endpoint once. Transfer the remaining 4000 native CPU seconds to this bounded
CPU-model stage (998 work-wall seconds). Keep all original-unit budgets, useful
400-update requirements, coverage and later GPU gates unchanged. This remains a
partial CPU admission; full Tensor/CUDA solver inventory is still pending.
Active journal: artifacts/gpup-tensor-expanded-v1/cpu-model-admission-v1/cpu-journal-v9.json.
No passed test/profile rerun and no GPU execution is authorized by this CPU stage.

## GPUP-8 new Rust window acceptance (2026-10-24)

The new Rust scalar path passes 11482 comparisons. Preserve its source-bound
evidence and the passed CUDA primitive image. New isolated CPU solver work adds
expanded windows, local update/conversion enclosures, separate wider counters,
generation-bound rollback, bounded preparation lookup tables, contiguous groups,
predecoded Gram coefficient parts and reusable assessment assignments.
Transfer 400 unused implementation CPU seconds to new Rust window/preparation
acceptance; charge 16 implementation seconds for construction bookkeeping.
Run only the new bin's three focused tests, including five window lengths and
canonical penultimate inputs. Full model admission and GPU implementation remain
pending; no complete solver/device/inventory claim follows these checks.
Active journal: artifacts/gpup-tensor-expanded-v1/rust-window-v1/cpu-journal-v8.json.
All completion criteria, historical evidence and GPU allocations remain exact.

## GPUP-8 new Rust arithmetic validation (2026-10-24)

The CUDA primitive module passes at 79 registers maximum and zero stack/spills.
Its image is retained for reuse. Add the isolated research Rust scalar path;
public solver registrations and dependencies remain unchanged. Transfer 600
unused implementation CPU seconds to the new Rust scalar acceptance reservation.
Compile only this new executable and compare it with the already verified scalar
outputs plus independent new codec/packing cases; do not rerun the C++ proof or
historical tests. This is new implementation validation, not another proof retry.
Active journal: artifacts/gpup-tensor-expanded-v1/rust-scalar-v1/cpu-journal-v7.json.
Full solver/window/model admission, Tensor inventory and GPU gates remain pending.

## GPUP-8 corrected proof passes; primitive CUDA admission (2026-10-24)

The one corrected proof passes 7376 scalar, 1400 conversion, 1400 exact split,
720 component product and 2400 projection cases. The new fixture/harness
preflight passes; the old 28 checks and every historical profile are reused.
Before full solver integration, compile the actual expanded scalar, projection
and boundary-conversion module once. This partial inventory makes no complete
candidate, Tensor, device or model-admission claim. Preserve the exact retained
arithmetic helpers and reuse this module if admitted. Transfer 800 unused native
CPU seconds to its compile reservation (198 work-wall seconds); retain 4000 for
the remaining native inventory. Charge 32 implementation CPU seconds for source
construction/bookkeeping. A failed 128-register/zero-spill gate stops science.

Active journal: artifacts/gpup-tensor-expanded-v1/primitive-build-v1/cpu-journal-v6.json.
No extra CPU/GPU funds, changed criteria, GPU execution or historical rerun.

## GPUP-8 authorized fixture correction and one proof retry (2026-10-24)

The user authorizes fixture/harness fixes, one corrected proof attempt and
conditional continuation from unused funds. This supersedes the earlier proof
stop only for this recovery. Transfer 100 unused authority CPU seconds to setup
and 1600 unused prototype seconds to the corrected proof reservation; add no
resources. Retain the full 5600-second failed proof charge and all original
sources, corpus, reports and journals. CPU ceiling remains 77640; GPU caps and
every completion criterion remain unchanged.

Active journal: artifacts/gpup-tensor-expanded-v1/proof-recovery-v1/cpu-journal-v5.json.
Authority: docs/benchmarks/data/tensor-expanded/proof-recovery-authorization-v1.json.
Implement versioned generator/harness adapters, canonical-input preflight and
indexed diagnostics. Reuse the source-bound 12 authority and 16 prototype passes;
rerun no passed checks or historical profiles. After the corrected proof passes,
continue the accepted ordered gates. No supervisor/bootstrap/host/container
change. A numerical or resource failure retains its charge and closes later
scientific stages. GPUP-8 remains incomplete until all criteria pass; GPUP-9 stays
gated. Expected writes: correction adapters, focused validation, new receipts,
accounting, and conditional candidate implementation under ADR-0046.

## GPUP-8 expanded-window proof stops on noncanonical fixture (2026-10-24)

Final CPU-only delivery passes source/evidence preservation, documentation/internal links,
syntax and diff checks. Cumulative CPU is 51568.693453526 / 77640;
continuation charge 5666.151624356 seconds. Reporting retains
761.762326424 seconds. All failure/delivery cleanup is empty.
Final journal: artifacts/gpup-tensor-expanded-v1/cpu-journal-final-v4.json.
Final report: docs/benchmarks/lp-tensor-expanded-final-gpup8.md.
Exact accounting: docs/benchmarks/data/tensor-expanded/final-cpu-accounting-v1.json.

ADR-0046 and the 24000-CPU-second / 1760-existing-GPU-second amendment are accepted.
Twelve authority/evidence and sixteen new CPU prototype checks pass. The new
scalar host harness compiles with UBSan, then rejects input 19: the generator
changes a short subnormal significand's exponent to -63 without normalization.
No scalar result was independently compared before the return-code refusal; no
arithmetic defect is inferred. Preserve the original corpus, sources and failure.

The full 5600 CPU-second proof reservation remains charged. Scientific stages
are closed; no correction/retry, implicit transfer or later scientific stage.
Implementation/native/device/profile/timing allocations remain unused. No old
passed check or profile is rerun and no GPU work or commit occurs. GPUP-8 stays
incomplete, GPUP-9 gated; cross-window persistence remains future work.
The exact 17412-event GPU ledger is unchanged. Both proof cleanup receipts are
empty. CPU-only delivery uses the separate reporting allocation.
Report: docs/benchmarks/lp-tensor-expanded-gpup8.md. Diagnosis:
docs/benchmarks/data/tensor-expanded/proof-fixture-diagnosis-v1.json.
Failed journal: artifacts/gpup-tensor-expanded-v1/cpu-journal-proof-stop-v2.json.

## GPUP-8 approved expanded-within-window continuation (2026-10-24)

The user accepts the expanded-window plan and its resource amendment: add 24000
CPU seconds, ceiling 77640, prospective allocation 31600; reallocate 1760 GPU
seconds inside the unchanged 3000-second GPUP-8 and campaign ceilings. Use the
new lp-tensor-expanded-v1 / gpup-tensor-expanded-v1 identities and journal
artifacts/gpup-tensor-expanded-v1/cpu-journal-v1.json. Preserve the exact 17412-event
ledger prefix, all prior sources, binaries, failures, profiles and charges.

Implement expanded working state within at-most-32-update windows, canonicalize
the shared penultimate audit input, and retain FP64 reference adoption and the
200-update host controller/certification boundaries. Scientific criteria stay
unchanged. New candidate gates run once in dependency order; retained passed
checks/profiles are not rerun. A failed formal gate closes scientific execution;
later funds remain unused. No automatic retry, transfer, bootstrap rerun, host or
container change. GPUP-8 remains incomplete and GPUP-9 gated. Cross-window state
persistence is documented future work with no allocation.

Likely additions: separate CPU/reference and CUDA candidate, artifact adapters,
new validation/evidence and ADR-0046. Authority and evidence admission precede
numerical execution. Starting CPU: 45902.541829170; authorization bookkeeping
charges 16 CPU seconds within the 400-second authority stage.

## GPUP-8 receipt correction passes; gain forecast refuses (2026-10-24)

Seventeen focused correction checks and exact source/provenance admission pass.
Sixteen separately stored corrected trial views bind the existing independent
verification receipts; every original trial retains its null link and exact hash.
No passed check, profile or retained numerical verification is rerun. The original
strict reader accepts the corrected views. All sixteen profiles and useful
integer/floating families satisfy the unchanged profile/forecast inputs.

The unchanged gain forecast now runs and refuses all six candidates. The best
small-model forecast is 0.642764297 s against the 0.415902600 s threshold; the best
large-model forecast is 8.977063370 s against 5.697919800 s. This is a forecast
refusal, not a measured primary timing comparison or numerical failure. No
resource-fit gate or timing worker follows. Preserve the corrected views,
original records, sources, reports, full historical charges and new forecast.

The forecast stage retains its full 400 CPU-second failure charge. The separate
6400-second timing reservation stays unused. The CPU-only scientific report
passes with original completion calculations and receipt reuse. Scientific stages
are closed; no automatic retry or implicit transfer follows. GPUP-8 remains
incomplete and GPUP-9 gated. There is no new GPU work: warp32 remains
369.700946478 / 1640, GPUP-8 1232.909411024 / 3000, and campaign
22592.495266813 / 25202.574545061. The exact 17412-event ledger remains unchanged.
Final CPU accounting is 45902.541829170 / 53640; this receipt recovery charges
843.323873964 CPU seconds entirely from unused funds. Reporting retains
315.762945624 CPU seconds. Delivery passes 168 documentation pages/internal
links, exact preservation of 637 original artifacts and sixteen corrected views,
source metadata and diff hygiene. All workload and guardian cleanup is empty.
Final closed journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-receipt-final-v31.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/receipt-final-cpu-accounting-v1.json. Cleanup is empty.
No host/container/supervisor change, bootstrap rerun, commit, publication or merge.
Report: docs/benchmarks/lp-tensor-warp32-receipt-recovery-gpup8.md.
Refusal: docs/benchmarks/data/tensor-warp32/receipt-forecast-refusal-v1.json.

## GPUP-8 approved receipt-link recovery (2026-10-24)

The user authorizes correcting receipt links in separate versioned records and
continuing GPUP-8 using unused funds. Preserve original trials/receipts, all
sources, failures and charges, and the exact 17412-event GPU prefix. Rerun no
passed checks or profiles. All scientific completion criteria remain unchanged.

Reallocated existing CPU headrooms: implementation 240, forecast 400, timings
6400, reporting 600 and restricted termination margin 400 seconds. No additional
CPU/GPU budget; CPU ceiling 53640 and warp32 GPU cap 1640 (330/320/990) remain.
Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-receipt-recovery-v29.json.
Write artifact-only correction/reader adapters, run focused correction acceptance,
then the interrupted forecast and conditional timing sequence. No automatic
retry, host/container/supervisor change, bootstrap rerun or GPUP-9. Likely writes:
new correction manifests, journal/receipts/report and state documentation.
Accepted plan: docs/plans/lp-tensor-warp32-receipt-recovery.md.

## GPUP-8 funded continuation stops at profile receipt binding (2026-10-24)

The approved 10400 CPU-second addition and 850 GPU-second reallocation are
recorded. Fourteen new adapter checks and exact source/provenance admission pass.
Initcheck and synccheck pass; full device acceptance reuses ordinary/project tests,
all twelve fixed-work/replay pairs and 24 verifications, memcheck and racecheck.
All sixteen profile workers complete with independent verification receipts.
The frozen writer captures artifact references before creating verification
receipts, leaving every trial's verification reference null. The strict forecast
reader refuses these links. No forecast or timing runs, and no numerical or gain
failure is inferred. Preserve every source, trial, receipt and the traceback.

The profile stage retains its full 2400 CPU-second failure charge. The separate
6400-second timing reservation remains unused. Scientific stages are closed;
there is no automatic repair/retry or implicit transfer. Four new post-stop
reader checks and the CPU-only report pass using sixteen profile, 24 acceptance
and 24 historical CPU verification receipts, with no numerical verification rerun.
Completion criteria are unchanged. GPUP-8 remains incomplete and GPUP-9 gated.

This continuation charges 113.279588268 GPU seconds; combined warp32 is
369.700946478 / 1640 (acceptance 261.200177856 / 330,
profiles 108.500768622 / 320, timings 0 / 990).
GPUP-8 is 1232.909411024 / 3000; campaign is
22592.495266813 / 25202.574545061. The exact 17412-event ledger
preserves the 17376-event prefix. Workload and guardian cleanup are empty.
Final CPU accounting is 45059.217955206 / 53640; this continuation charges
2664.409180444 CPU seconds. Reporting retains
466.729267256 seconds, unavailable for automatic retries. Delivery passes
166 documentation pages/internal links, exact source/evidence preservation and
diff hygiene. Every workload and guardian cleanup receipt is empty. Final closed
journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-funded-final-v28.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/funded-final-cpu-accounting-v1.json. No host/container
or supervisor change, bootstrap rerun, commit, publication or merge occurs.
Report: docs/benchmarks/lp-tensor-warp32-funded-gpup8.md.
Failure receipt: docs/benchmarks/data/tensor-warp32/funded-profile-refusal-v1.json.

## GPUP-8 approved fully funded continuation (2026-10-24)

The user approves 10400 additional CPU seconds and 850 GPU seconds reallocated
from GPUP-8's existing allowance. CPU ceiling 53640; warp32 GPU cap 1640,
including all prior charges, with acceptance/profiles/timings caps 330/320/990.
Prospective CPU allocations are implementation 200, sanitizers 1000, profiles
2400, timings 6400, reporting 600 and restricted termination margin 400.
Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-funded-continuation-v26.json.

Reuse all passed checks and exact verification receipts. Artifact-only adapters
must pass focused acceptance and exact source/provenance admission first. Run
only initcheck and synccheck, then the frozen sixteen profiles and conditional
sixty timings, in separate CPU reservations. Original scientific criteria,
source/image identities and every historical charge remain unchanged. Preserve
the exact 17376-event GPU prefix. No automatic retry, implicit transfer, host or
container change, supervisor change or bootstrap rerun. GPUP-9 remains gated.
Likely writes: artifact adapters/journal/receipts, new budget policy, reports and
task documentation. Accepted plan: docs/plans/lp-tensor-warp32-funded-continuation.md.

## GPUP-8 deadline recovery result (2026-10-24)

Final result: all twelve fixed-work/replay pairs and all 24 independent endpoint
verifications pass; ordinary/project-unit tests and software/inventory acceptance
were reused, not rerun. The resumed project and memcheck/racecheck pass. Initcheck
is refused before reservation because its required 36 GPU seconds exceed the
remaining 33.578641790 acceptance seconds. Synccheck and all 76 study
cells remain unexecuted. The full 3600-worker-CPU-second failure charge is retained.

The separately funded CPU report passes with no verification errors, and 164
documentation pages/internal links plus diff hygiene pass. All cleanup is empty.
This recovery adds 160.386137810 GPU seconds; combined warp32 consumption is
256.421358210 / 790, entirely within the 290-second acceptance cap.
GPUP-8 total is 1119.629822756 / 3000; campaign total is
22479.215678545 / 25202.574545061. The exact 17376-event ledger
preserves both the 17370-event and 17366-event prefixes. Final CPU is
42394.808774762 / 43240; this recovery charges 3663.609175120 CPU seconds.
Reporting retains 213.895961888 CPU seconds; worker headroom is zero.
Exact accounting: docs/benchmarks/data/tensor-warp32/deadline-final-cpu-accounting-v1.json.
Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-deadline-final-v25.json.
All historical sources, frozen requests, failures, images and charges remain.
No numerical/latency relaxation, automatic retry, implicit phase transfer or
local commit occurs. GPUP-8 remains incomplete; GPUP-9 stays gated.

The approved deadline continuation has finished its bounded attempt. See
 docs/benchmarks/lp-tensor-warp32-deadline-recovery-gpup8.md and the separate
machine report for exact status. All earlier failures/charges and passed checks
remain preserved; no full software or inventory rerun occurs. Scientific work
stops at the recorded failure/refusal or completed sequence; all original
completion criteria and the combined 790-GPU-second cap remain unchanged.
Final accounting follows supervisor finalization. GPUP-9 remains gated.

## GPUP-8 approved deadline recovery (2026-10-24)

The user approves 3600 additional CPU seconds and unused-fund reallocation.
Cumulative ceiling is 43240; continuation allocation including historical charges
is 13440. Prospective headrooms: implementation 100, workers 3600, reporting 248,
restricted termination margin 400 CPU seconds. All prior failures/charges remain.
Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-deadline-recovery-v23.json.
Eight implementation seconds cover preparation and authorization bookkeeping.

Use the accepted 180-second remaining-project deadline and 60-work-second final
report. Reuse passed software, inventory, ordinary/project-unit tests and seven
complete fixed-work/replay pairs. Finish one interrupted replay verification and
four unexecuted large-model pairs, then run all still-unexecuted sanitizers and
the existing conditional profile/forecast/timing sequence. Preserve twelve-pair
acceptance and all 76 study cells. Numerical sources, test/build inputs and the
verification helper remain byte-exact. Separate artifact-only adapters and exact
metadata source bridges must pass focused acceptance before resumed execution.
Likely writes: adapters/receipts/journal, authorization/task state and final report.

Preserve the old frozen source, all requests/failures and every ledger event.
Never relabel an old failed worker as passing. The 790 GPU seconds include the
already charged 96.035220400 seconds; phase caps remain 290/200/300. Per-job CPU,
GPU, forecast/resource-fit gates may refuse and do not authorize borrowing.
All completion criteria remain unchanged. No automatic retry, host/container or
supervisor change, bootstrap rerun, numerical/latency relaxation or GPUP-9.
Accepted plan: docs/plans/lp-tensor-warp32-deadline-recovery.md.

## GPUP-8 user-authorized deadline relaxation (2026-10-24)

Deadline amendment acceptance: retained timing/resource arithmetic, immutable
prior receipts and 17370-event ledger, 163 documentation pages/internal links and
diff hygiene pass. Amendment CPU charge is 20.382008576 seconds; cumulative
CPU is 38731.199599642 / 39640. No worker, compiler, numerical verification or
GPU job ran. Worker headroom remains zero. Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-deadline-amendment-final-v22.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/deadline-amendment-accounting-v1.json.
The 180-second remaining-project and 60-second reporting deadlines are selected;
the separate 3600-additional-CPU-second/reallocation proposal remains unaccepted.
All cleanup is empty and every prior charge is preserved.

The user authorizes choosing reasonable operational deadlines. Select 180 work
seconds for the remaining project acceptance actions and 60 work seconds for
final reporting. Preserve all prior failures/charges and passed checks; no
numerical or completion criterion changes. Record settings separately in
 docs/benchmarks/data/tensor-warp32/deadline-amendment-v1.json; never overwrite
the frozen request or reuse its failed identity.

The remaining work is one interrupted CPU replay verification and four unexecuted
large-model fixed-work/replay pairs. The completed large INT8 pair took about
27.423 wall seconds; 180 allows about 1.5 times the observed remaining-work
estimate. Forty-second individual action limits remain. A 60-work-second report
requires 248 CPU seconds under the unchanged supervisor's four-times-wall policy
and two-second work reserve.

Worker CPU headroom is zero after the retained full 3964-second failure charge.
Deadline authorization does not supply additional CPU funds or refund charges.
Use at most 32 existing implementation CPU seconds for this concrete amendment,
resource-fit proposal, documentation and receipt checks; active journal is
artifacts/gpup-tensor-warp32-v1/cpu-journal-deadline-amendment-v21.json.
Likely writes are the separate policy, diagnostic/resource proposal and task
state. No compilation, software-check rerun, numerical verification or GPU job.
Keep the 790-GPU-second cap, all phase caps, scientific gates and exact 17370-event
ledger. Reopen scientific execution only when its required CPU budget is funded.

## GPUP-8 inventory complete; project acceptance timed out (2026-10-24)

Final metadata delivery validates the inventory/composite, all fifteen completed
verification bindings, exact ledger/prefix and 162 documentation pages/internal
links plus diff hygiene. It does not replace either failed gate or complete the
sixteenth endpoint verification. Final CPU is 38710.817591066 / 39640;
this adapter recovery charges 4097.609224304 CPU seconds with all historical
charges preserved. Reporting retains 23.730196880 CPU seconds,
unavailable for automatic retries. Exact accounting:
 docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v5.json.
Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-device-final-v20.json.
All cleanup is empty. The exact 17370-event ledger and historical 17366-event
prefix verify unchanged after delivery. No local commit occurs.

The approved adapter correction and 36-worker-CPU-second transfer pass six new
focused checks and exact provenance admission. All four compile-only device
suites and explicit composite acceptance pass without rerunning passed software
checks. The frozen source/archive and all prior failed reservations remain exact.

All 66 ordinary device tests pass. The project unit suite passes 280 product
pairs, five controller comparisons and 32 warp32 bit/refusal witnesses, then
hits its unchanged 60-second deadline during fixed-work/replay acceptance.
Seven of twelve required pairs have complete host-verification receipts; an
eighth pair is retained with its replay verification incomplete. Sixteen
endpoints and fifteen completed verification receipts remain. No sanitizer,
profile or timing follows. The separate CPU-only final-report attempt also
reaches its deadline; no complete final verification report is claimed. Preserve
both failed sources/receipts and full charges: workers 3964, reporting 64 CPU
seconds. All workload/guardian cleanup is empty.

New GPU charge 96.035220400 / 790 seconds; GPUP-8 959.243684946 / 3000;
campaign 22318.829540735 / 25202.574545061. The 17370-event ledger SHA-256 is
2dac176a925a0bba6096eea8f57ed694465c0199625d120eeb32d468310dc4e4,
preserving the exact 17366-event prefix. CPU at worker stop is
38616.699832818 / 39640; at reporting stop 38684.699832818. Final metadata
accounting follows. Scientific stages are closed; no automatic retry, implicit
transfer or criterion relaxation. GPUP-8 remains incomplete; GPUP-9 stays gated.
Report: docs/benchmarks/lp-tensor-warp32-inventory-device-gpup8.md.

## GPUP-8 approved adapter correction and inventory recovery (2026-10-24)

The user explicitly approves the prepared adapter correction and transfers 36
unused worker CPU seconds to setup. Preserve the original failed adapter and its
full 64-second charge. No additional CPU funds: ceiling 39640, continuation
allocation 9840. New setup headroom 64 comprises 8 preparation, 32 corrected
admission and 24 composition CPU seconds; inventory retains 400, workers 3964,
reporting 117.847955128 and restricted termination margin 400 CPU seconds.
Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-adapter-recovery-v17.json.

Apply only the artifact adapter correction: validate locked crate archive hashes
and every extracted member, rejecting unexpected source files. Run focused new
checks for the correction and exact source/provenance admission once. Reuse all
passed software checks. Run the unchanged compile-only inventory once; after its
resource/cleanup pass, validate a separate composite acceptance, then freeze and
run the unchanged conditional device/profile/forecast/timing sequence. Likely
writes are artifact adapters, receipts/journal, authorization/task state and
post-execution delivery. No covered solver/test/build/harness source edits.

Keep all completion criteria and the 790-GPU-second cap (290 acceptance, 200
profiles, 300 timings). Preserve the exact 17366-event ledger prefix and all
historical evidence. No source edits after freeze, automatic retry, bootstrap
rerun, host/container or supervisor change, numerical/latency relaxation or
implicit transfer. GPUP-8 remains incomplete until every criterion passes;
GPUP-9 stays gated. The accepted proposal is
 docs/plans/lp-tensor-warp32-inventory-admission-recovery.md.

## GPUP-8 inventory admission stops before compilation (2026-10-24)

Final CPU-only delivery passes exact failure/source/receipt/budget checks,
161 documentation pages/internal links and diff hygiene. No passed software
check is rerun. Final cumulative CPU is 34613.208366762 / 39640;
this continuation charges 104.152044872 CPU seconds, retaining all
prior charges. Reporting retains 117.847955128 CPU seconds;
unused funds do not authorize an automatic retry. Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-admission-final-v16.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v4.json.
Workload/guardian cleanup and diagnostic/delivery cleanup are empty. Fresh hashing
confirms the unchanged exact 17366-event GPU ledger. No commit occurred.

The approved 2500 CPU-second increase and proposed reallocation are recorded:
cumulative ceiling 39640, continuation allocation 9840, unchanged 790 GPU cap
and completion criteria. All covered sources match the passed 1137-file archive;
only 15 exact metadata paths differ. Eleven new adapter checks pass, then
provenance admission fails on the adapter's assumption that extracted Cargo
packages contain .cargo-checksum.json. Charge the full 64 CPU seconds. This is
an adapter assumption error, not an observed dependency or numerical failure.
Post-stop CPU-only diagnosis verifies all 26 retained locked crate archives and
every extracted member; all 26 lack that metadata file. A separate correction
draft is unexecuted. No inventory command, composite acceptance, freeze or GPU
work occurs, and no passed software check is rerun. Both cleanup receipts are
empty; the exact 17366-event GPU ledger is unchanged. CPU at setup stop is
34581.056321890 / 39640; reporting charges follow separately.

Scientific stages are closed; no automatic retry or implicit transfer. GPUP-8
remains incomplete; GPUP-9 stays gated. Preserve all failed sources and charges.
Report: docs/benchmarks/lp-tensor-warp32-inventory-admission-gpup8.md. The separate
unaccepted recovery proposes a 36-worker-CPU-second transfer, no new CPU budget,
one corrected admission and the unchanged inventory/device/completion sequence.
See docs/plans/lp-tensor-warp32-inventory-admission-recovery.md.

## GPUP-8 approved inventory continuation (2026-10-24)

The user accepts docs/plans/lp-tensor-warp32-inventory-continuation.md: add
2500 CPU seconds and explicitly reallocate unused stage funds. The cumulative
ceiling is 39640 CPU seconds; continuation allocation including all historical
charges is 9840. Prospective headrooms are implementation 100, compile-only
inventory 400, workers 4000, reporting 150 and restricted termination margin 400.
All prior charges remain; 35.649492368 assigned seconds remain unused. Journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-continuation-v14.json.
Eight implementation CPU seconds conservatively cover authorization bookkeeping.

Validate exact source equivalence and retained provenance using an artifact-only
admission adapter with focused negative checks. Reuse the completed software
receipt and run the unchanged compile-only inventory once, separately supervised;
do not rerun passed checks. Then validate a separate composite acceptance record
and conditionally freeze/run the existing device/profile/forecast/timing sequence.
Likely writes: artifact-only adapter/receipts/journal, authorization and task state,
then separate report/accounting after workers. No covered behavior source edits.

Keep the 790-GPU-second cap (290 acceptance, 200 profiles, 300 timings), all
completion criteria and the exact 17366-event ledger prefix unchanged. No
bootstrap rerun, host/container change, supervisor change, numerical/latency
relaxation or automatic retry. Freeze all source during workers. Any failed gate
stops scientific work; GPUP-8 remains incomplete until every criterion passes;
GPUP-9 stays gated. Preserve all historical evidence and failed charges.

## GPUP-8 inventory-only continuation proposal (2026-10-24)

The user requests a CPU budget and a way to finish compile-only inventory without
rerunning passed checks. This task is documentation/source inspection only.
Reserve at most 24 existing reporting CPU seconds, including four conservative
setup/final-bookkeeping seconds; active planning journal is
artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-planning-v12.json.
Scientific stages stay closed. No compiler, tests of numerical behavior, device
reservation, new resources, implementation, bootstrap or host/container change
is authorized by this planning request.

Verify the completed check.sh receipt against its archived source, inspect the
inventory and resource-admission contracts, and propose exact prospective stage
headrooms with unchanged completion criteria and 790-second GPU cap. Likely
files are the new plan, planning/source-difference receipts and task state.
Acceptance is source/ledger preservation, exact budget arithmetic and a bounded
documentation/link check. Record the final planning charge and disposition.

The concrete proposal is docs/plans/lp-tensor-warp32-inventory-continuation.md:
2500 new CPU seconds, 5050 prospective headroom, proposed ceiling 39640, unchanged
790-GPU-second cap and completion criteria. No execution is authorized.

Planning acceptance: exact source comparison, integer budget arithmetic, the
unchanged 17366-event ledger, 159 documentation pages/internal links and diff
hygiene pass. Planning charges 16.264215568 CPU seconds; cumulative accounting
is 34509.056321890 / 37140. Reporting retains 9.043296760
CPU seconds. The final failed/closed planning journal is
artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-planning-final-v13.json;
receipt: docs/benchmarks/data/tensor-warp32/inventory-continuation-planning-v1.json.
The proposed 5050-second headroom would reach at most 39559.056321890
under the proposed 39640 ceiling. No compilation, GPU work, source implementation
or resource increase occurred; the proposal remains unaccepted.


## GPUP-8 availability fixed; inventory deadline stops recovery (2026-10-24)

The user-approved 1240 additional CPU seconds are recorded: cumulative ceiling
37140, continuation allocation 7340, unchanged 790-GPU-second cap. The CUDA
availability tests now distinguish initialization from version-query failures;
the actual availability test and four new mocked Rust cases pass. Eight source-
bridge checks pass. Production driver/numerical bytes and historical CPU evidence
remain exact through the separate test-only source bridge.

Every tools/check.sh command passes on source
267c5b7488482ea9005f359e367dcff2b97f363fe2e9ffd7b6008db5cb897138:
Clippy, Rust/native, 424 Python tests, dependencies, replay, 157 documentation
pages and CPU smoke. The complete source tree is archived. The supervisor then
reaches its 298-second work deadline before compile-only device inventory
completes. The combined native/resource gate is refused; its full 1200 CPU
seconds remain charged. No complete inventory, freeze, device acceptance,
sanitizer, profile or timing follows. No numerical failure is inferred.

Both workload and guardian cleanup are empty. The exact 17366-event GPU ledger
remains 9142829b3be8afdb1865425c83ca9122371284ca0e16f7bc8b18d303a5894426;
GPUP-8 remains 863.208464546 / 3000 GPU seconds. CPU at the native stop is
34458.336534342 / 37140; final CPU-only delivery is separately charged.
Scientific stages are closed. No automatic retry, implicit transfer, bootstrap
rerun, host/container change, supervisor change, numerical/latency relaxation,
commit or GPUP-9. Preserve every prior failure/source/image/journal/report.
See docs/benchmarks/lp-tensor-warp32-availability-recovery-gpup8.md and
 docs/benchmarks/data/tensor-warp32/native-refusal-v3.json.

Final CPU-only delivery passes exact failure/source-archive/ledger checks, 158
documentation pages/internal links, CPU smoke and diff hygiene. Cumulative CPU is
34492.792106322 / 37140; this availability recovery charges
1263.732468604 CPU seconds, retaining all prior charges.
Reporting retains 25.307512328 CPU seconds, unavailable for an
automatic retry. Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-availability-final-v11.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v3.json.
Native and delivery cleanup are empty. No new GPU work or commit occurred.


## GPUP-8 approved availability-test recovery (2026-10-24)

The user explicitly approves 1240 additional CPU seconds: 1200 native and 40
reporting. The cumulative CPU ceiling is 37140; continuation allocations including
all retained charges are implementation 258, proofs 800, native 3600, workers
2052, reporting 230 and margin 400, total 7340 CPU seconds. Prior native failures
remain exact and fully charged. The active journal is
artifacts/gpup-tensor-warp32-v1/cpu-journal-availability-recovery-v9.json.
Authorization and source inspection charge eight implementation CPU seconds.

Correct only the CUDA availability tests and add deterministic mocked coverage
for load, symbol, initialization and version-query failures. Preserve the
production driver and numerical bodies, admitted CPU evidence, images and
verification helper. Expected files are the CUDA-sys test module, separate
native/worker entry points, source receipts and recovery documentation.
Run one 1200-CPU-second full native gate and compile-only device inventory.
On success, freeze and run the existing conditional device sequence under the
2052-worker-CPU-second envelope and unchanged 790-GPU-second cap: 290 acceptance,
200 profiles, 300 timings. Select the active journal at runtime. Retain every
completion criterion, per-job admission, forecast and resource-fit gate.

No bootstrap rerun, host/container change, supervisor change, automatic retry,
numerical/latency relaxation, GPUP-9 or publication. A real failure ends this
recovery. Record acceptance or refusal with exact accounting and cleanup; all
prior sources, reports and the exact 17366-event GPU prefix remain preserved.

## GPUP-8 corrected native gate stops at driver availability (2026-10-24)

The approved 1200-native/40-reporting transfer is recorded and the one new
native gate runs once. Clippy passes, but the existing CUDA driver-availability
test rejects an error from driver_version while the native wrapper hides all
CUDA devices. Source inspection identifies an unhandled Driver error path;
the exact driver call/status is absent from the failure log. No numerical
failure is inferred. The full 1200 CPU seconds remain charged. No complete
native/Python integration gate or compile-only inventory passes, and no GPU
work, frozen study, bootstrap rerun, host access or container change occurs.
Cleanup is verified empty. Scientific stages are closed under ADR-0045; there
is no automatic retry or implicit transfer. GPUP-8 remains incomplete and
GPUP-9 stays gated. The exact 17366-event GPU ledger is unchanged.

At the native stop cumulative CPU accounting is 33196.332668818 / 35900.
Final CPU-only delivery passes exact failure-source/receipt checks, 156
documentation pages/internal links, repository CPU smoke and diff hygiene.
These checks do not replace the failed full native gate. Cumulative CPU is
33229.059637718 / 35900; continuation charge is
3474.353823460 CPU seconds. Reporting retains
19.763084308 CPU seconds, unavailable for automatic retries.
The final failed/closed journal is cpu-journal-native-stop-final-v8.json;
exact accounting is docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v2.json.
Both cleanup receipts are empty, and fresh hashing verifies the unchanged exact
17366-event GPU ledger. No new GPU work, host/container change or commit occurs.
 Failure receipt:
`docs/benchmarks/data/tensor-warp32/native-refusal-v2.json`. Preserve all prior
native failures, sources, journals, images, endpoints and reports.

## GPUP-8 approved native recovery (2026-10-24)

The user explicitly approves one new full native gate after the retained
one-line fixture correction, transferring 1200 unspent worker CPU seconds to
native acceptance and 40 to reporting. All prior failures and charges remain.
Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-native-recovery-v6.json.
Continuation allocations including charges are implementation 258, proofs 800,
native 2400, workers 2052, reporting 190 and margin 400 CPU seconds, total 6100.
Cumulative CPU accounting after bounded authorization bookkeeping is
31996.332668818 / 35900. Run the approved 1200-CPU-second native gate once.

If every native check and compile-only inventory passes, freeze all behavior
and run the existing conditional device sequence under the 2052-worker-CPU-
second envelope and 790-GPU-second cap (290 acceptance, 200 profiles, 300
timings). Select this active journal at runtime before worker admission; keep
the verification-cache helper source unchanged. Preserve the exact 17366-event
GPU prefix and every historical source, image, journal and report. Per-job
CPU/GPU admission and the frozen forecast/resource-fit rules can refuse early.
No host access, bootstrap rerun, supervisor change, unrelated-process signals,
container configuration change, numerical/latency relaxation or automatic retry.
GPUP-8 remains incomplete until every unchanged completion criterion passes;
GPUP-9 stays gated. The accepted plan is
[the native recovery](../docs/plans/lp-tensor-warp32-native-recovery.md).

## GPUP-8 warp32 native-gate final handoff (2026-10-24)

The corrected image passes 88-register/zero-spill admission and 592 independent
bit/refusal cases. All 48 eight-model CPU cells are retained, 24 endpoints
independently verify, and all twelve required dense configurations admit useful
400-update trajectories. Ten launcher/harness tests pass. The full native gate
fails Clippy on a redundant i32 cast in the new device fixture: charge all 1200
CPU seconds and retain the original source/failure. The one-line fix preserves
all admitted numerical-source hashes. Targeted format, 155 docs pages, CPU smoke
and diff checks pass; a full native pass remains unclaimed. No new GPU work,
resource-bootstrap rerun, host access, container change or commit occurs.

Final CPU accounting is 31980.332668818 / 35900; continuation charge is
2225.626854560. Reporting retains 12.490053208 CPU seconds. Exact receipt:
docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v1.json. Final
failed/closed journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-native-handoff-v5.json.
All cleanup is verified empty. The exact 17366-event GPU ledger stays unchanged.

The proposed native recovery transfers 1200 native and 40 reporting CPU seconds
from workers, leaving 2052 worker CPU seconds, under the unchanged 6100 total,
35900 ceiling, 790 GPU cap and completion criteria. It is unaccepted; no repeated
native gate or GPU reservation is authorized. GPUP-8 stays incomplete and GPUP-9
stays gated. See docs/plans/lp-tensor-warp32-native-recovery.md.

## GPUP-8 native Clippy stop; CPU delivery only (2026-10-24)

Warp32 compilation, 592 independent bit/refusal cases and complete eight-model
CPU admission pass. The full native gate fails on a redundant i32 cast in the
new device-test fixture. Preserve the full 1200-CPU-second charge, failed
journal, original fixture and verified empty cleanup. No GPU work ran.
At the gate stop CPU accounting is 31950.822722026 / 35900.

The one-line cast removal is prepared; all CPU-admitted numerical-source
hashes still match. No native retry or device gate is authorized. The new
[recovery proposal](../docs/plans/lp-tensor-warp32-native-recovery.md) requests
1200 native and 40 reporting CPU seconds from unspent workers, keeping every
charge, the 6100 allocation, 35900 ceiling and 790 GPU cap. It needs approval.
Scientific stages are closed; mandatory CPU refusal delivery uses only the
remaining 42 reporting CPU seconds, including four setup seconds already
charged. No implicit transfers, bootstrap rerun or host/container changes.

## GPUP-8 warp32 CPU admission passes (2026-10-24)

The explicitly approved corrected compiler launch passes: maximum 88 registers,
zero spills, required Tensor instructions/rounding and unchanged historical
numerical bodies. Its charge is 20.361500652 implementation CPU seconds.
Ten launcher/harness regressions pass. An optional provenance path lacking the
tools/ prefix refused before any reservation or child launch; correction is
separately journaled with four conservative CPU seconds, not a retried phase.

Independent actual-host/kernel-body comparison passes 592 bit/refusal cases.
The complete eight-model CPU cohort retains all 48 cells, including 24
independently verified endpoints and 22 eligible trajectories. All twelve
required dense-model configurations complete useful 400-update horizons.
Proof/admission charge is 696.176327576 / 800 CPU seconds, with a valid resource
receipt and verified cleanup. No GPU work or bootstrap rerun has occurred.

Run one full 1200-CPU-second pinned-native gate, with child PATH preserving
Python and adding the pinned Rust toolchain. Inventory device test binaries
without execution. After this gate, numerical/harness sources stay frozen;
the 3292-CPU-second worker envelope includes freeze, every lease, monitors,
independent endpoint verification and report calculation. All 790 GPU seconds,
their phase caps and completion criteria remain unchanged. Final reporting has
42 CPU seconds left; no implicit transfer or automatic real-failure retry.

## GPUP-8 approved compiler-launch recovery (2026-10-24)

The user explicitly approves the bounded launch recovery and transfer of 108
unspent worker CPU seconds to implementation. Carry all prior charges forward;
active journal is artifacts/gpup-tensor-warp32-v1/cpu-journal-recovery-v3.json.
Original continuation stage allocations, including charges, are implementation
258, proofs 800, native 1200, workers 3292, reporting 150 and margin 400 CPU
seconds, total 6100. Recovery setup charges four implementation CPU seconds;
cumulative accounting is 30012.459145450 / 35900. Implementation has
108.246668808 CPU seconds left; reporting has 42. No implicit borrowing.

Run exactly the approved corrected entry under the unchanged supervisor using
one 108-CPU-second reservation. It preserves PATH and uses the running Python
interpreter. If it passes, finish CPU oracle/harness, eight-model CPU admission,
one full native gate, freeze, device gates, profiles/forecast and conditional
timings. Preserve every historical artifact and the exact 17366-event prefix.
GPU aggregate caps remain 290 acceptance / 200 profiles / 300 timings, total
790; the tighter 3292-worker-CPU-second envelope can refuse earlier. No host
access, bootstrap rerun, supervisor change, criterion relaxation or study retry.

## GPUP-8 final warp32-launch handoff (2026-10-24)

GPUP-8 remains incomplete. The isolated correction is written but uncompiled.
Compiler launch fails because replaced PATH hides Python: charge 108 CPU seconds.
CPU-only delivery passes four mocked launch tests, exact historical preservation
and 153 docs pages; smoke then cannot find rustc: charge its full 100 CPU seconds.
No smoke retry, completed final gate or numerical acceptance is claimed. All
project cleanup is verified empty; no new GPU execution, bootstrap rerun, host
access, container configuration change or commit occurs. Final CPU accounting is
30008.459145450 / 35900. New continuation CPU charge is 253.753331192 seconds.
The final failed/closed accounting journal is
artifacts/gpup-tensor-warp32-v1/cpu-journal-accounting-v3.json; exact receipt is
docs/benchmarks/data/tensor-warp32/final-cpu-accounting.json. Reporting retains
42 CPU seconds, unavailable for automatic retries. The separate recovery plan
proposes one corrected compiler invocation and transfer of 108 unspent worker
CPU seconds to implementation, with all charges, criteria and the 790-GPU-second
cap preserved. It is unaccepted; scientific stages remain closed.

## GPUP-8 compiler-launch stop; mandatory CPU delivery (2026-10-24)

The authorized isolated source/config setup and historical numerical/17366-event
prefix checks pass. The prescribed warp32 body and test adapters are written,
but compilation never starts: the image-construction command replaces PATH and
hides Python. The supervisor returns command_failed/127, charges the full
108 CPU seconds and verifies empty cleanup. Preserve the failed execution
journal/receipt and all partial sources. No bootstrap rerun, host access,
container configuration change or GPU work ran. No automatic compiler retry.

At the compiler stop, CPU accounting is 29900.459145450 / 35900; implementation
has consumed 145.753331192 / 150 newly allocated CPU seconds. Close scientific
execution stages and finish only mandatory CPU reporting/checks from the already
reserved 150 reporting CPU seconds. The prepared corrected entry uses the
running interpreter and preserves PATH; mocked tests invoke no compiler.
The [launch recovery proposal](../docs/plans/lp-tensor-warp32-launch-recovery.md)
requires explicit approval for one corrected invocation and transfer of 108
unspent worker CPU seconds to implementation. All completion criteria/ceilings
and the 790-GPU-second cap remain unchanged. GPUP-8 is incomplete.

## GPUP-8 approved warp32 continuation (2026-10-24)

The user explicitly accepts ADR-0045 and reallocation of 6100 unspent CPU
seconds, and authorizes one isolated warp32 correction and continuation capped
at 790 GPU seconds. This supersedes the previous device stop only for this
new frozen cohort. No host access, bootstrap rerun, supervisor change or
numerical/latency criterion change. One serialized top-level phase at a time.

Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-v1.json. Carry every
old charge and add stage headrooms: implementation 150, proofs/admission 800,
native 1200, workers/verification 3400, reporting 150, termination margin 400
CPU seconds. Authorization setup charges four implementation CPU seconds.
Maximum cumulative CPU is 35854.705814258 / 35900. GPU caps are repeatability
290, profiles/ablations 200, timings 300; all GPU work uses the inherited exact
UUID and allocator, with the 17366-event prefix preserved. No implicit borrowing
or automatic retry after a real failure.

Implement only the reference reduction in a separate recovery source/image,
with strict source bridges and new request/study identities. Then independent
reduction checks, complete eight-model CPU admission, full pinned-native gate,
freeze and device correctness precede any study. Keep all 76 cells; profiles
must pass the existing gain forecast plus the new resource-fit check before
timings. Final changes are evidence/report/docs only, with targeted delivery
checks under the accepted native-check scheduling amendment. GPUP-8 remains
incomplete until every unchanged numerical/resource/latency gate passes.

## GPUP-8 warp32 recovery proposal (2026-10-24)

Current task is documentation only: propose one bounded correction of the
device reference reduction and a separately frozen continuation. Read the
retained failure, accepted ADR-0044 and known failures; preserve all historical
charges and evidence. No numerical implementation, compiler, bootstrap, study,
GPU reservation, host access or container configuration change is authorized
by this planning request. The existing device stop remains in force.

Planning reserves five reporting CPU seconds in total from the previously
remaining 5.193240856 seconds, including the first two-second read already
journaled. Acceptance is a concrete proposed contract with exact CPU/GPU
allocations, source-preservation rules, unchanged numerical/latency completion
criteria and explicit stop conditions. Execution and reopening the closed CPU
stages require acceptance of the new proposal; unused totals alone do not
authorize those stages. Record final planning accounting and evidence below.

Planning acceptance: [proposed ADR-0045](../docs/decisions/ADR-0045-warp32-tensor-reference-recovery.md)
specifies one isolated kernel correction, complete numerical/device gates/76-cell
roster, 6100 unspent CPU seconds reallocated across stages, and new aggregate
GPU caps of 290 repeatability / 200 profiles-ablations / 300 screening seconds.
All numerical and latency completion criteria and cumulative ceilings remain
unchanged. CPU limits are joint with GPU limits; profiles must pass the existing
gain forecast and a frozen resource-fit estimate before primary timings.
The proposed CPU schedule uses one full native gate on final behavioral sources
before device work, then targeted delivery checks, replacing the former second
full native run. No successful completion is promised by the allocation.

The [planning receipt](../docs/benchmarks/data/tensor-cost/warp32-plan-v1.json)
records exact integer budget arithmetic and hashes of the unchanged ADR-0044
and refusal report. Five planning CPU seconds are fully charged in
artifacts/gpup-tensor-cost-v1/cpu-journal-warp32-planning-v12.json; cumulative
accounting is 29754.705814258 / 35900, with 6145.117030904 allocated CPU seconds
and 2136.791535454 GPUP-8 GPU seconds unspent. The proposal's CPU maximum is
35854.705814258 / 35900. No GPU, compiler, workload, bootstrap, host access or
container configuration change ran. Documentation is unimplemented/unaccepted;
the previous stop and closed execution stages remain in force. No new full
test-suite or docs-suite pass is claimed for this planning-only edit.

Final handoff (2026-10-24): GPUP-8 is incomplete at the frozen device reference
gate. Final docs acceptance passes 150 pages plus smoke and diff hygiene; the
repeated combined integration gate remains partial after its deadline. Independent
review verifies 48 CPU records and five reader regressions pass. Final CPU upper
accounting is 29749.705814258 / 35900 seconds; new GPU charge is 38.094432271 s.
All project descendants are reaped. No retry, bootstrap rerun, host/container
configuration change, commit or GPUP-9 work follows. See
docs/benchmarks/data/tensor-cost/final-cpu-accounting.json and the device-stop
report. Preserve every source, image, worker, archive, failed journal and receipt.

## GPUP-8 final retained result (2026-10-23)

The separate posthoc reader and five regressions pass. Independent CPU review
verifies all 48 retained CPU records with originating and final frozen binaries.
The machine report and benchmark disposition are written. Controller differences
are at most 3 ulps in primal, dual and scaled primal, and 4 ulps in scaled dual.
New GPU charge is 38.094432271 s; GPUP-8 total 863.208464546 / 3000; campaign
22222.794320335 / 25202.574545061. Ledger has 17366 events, SHA-256
9142829b3be8afdb1865425c83ca9122371284ca0e16f7bc8b18d303a5894426,
retaining the exact 17362-event prefix and all earlier history.

Final schema verification passes. The repeated integration suite reaches the
remaining native wall deadline before completion: charge its full 530 CPU
seconds and preserve the valid resource/empty-cleanup receipt. No final combined
integration/docs/smoke pass is claimed. The earlier full pre-device 405-test
native pass remains the frozen numerical-source acceptance. A final docs/smoke
attempt may use only the remaining reporting allowance; no phase/resource
transfer, numerical edit, GPU retry or bootstrap rerun follows. All failed
journals and partial output remain retained. GPUP-8 is incomplete and changes
remain uncommitted after the device gate fails.

## GPUP-8 final CPU-only disposition acceptance (2026-10-23)

Device correctness has stopped the bounded continuation; no device identity is
retried. CPU delivery-v10 accounting preserves the failed v8/v9 journals and all
charges. The first posthoc reader mistook a traceback's quoted `SKIP` source for
a runtime skip; retain its full 250-reporting-CPU-second charge. The corrected
reader matches runtime skip lines and has five pure CPU regressions. Frozen
numerical sources/images are unchanged. Only CPU reporting and the existing
530.119959932 native CPU seconds remain enabled in delivery accounting.

Finish independent frozen-evidence/CPU-endpoint verification, machine report and
current status documentation. Final CPU acceptance uses at most 530 native CPU
seconds for report verification, Python integration, schemas, committed replay,
docs and smoke; CUDA is hidden. Rust/native numerical sources retain their
pre-device pass and have no post-device edits. A failure stops this final gate.
No local numerical commit after the failed hardware gate; GPUP-8 remains
incomplete and GPUP-9 stays gated.

## GPUP-8 frozen device correctness stop; CPU delivery only (2026-10-23)

The repaired-source full native gate passes 405 Python tests, Rust/native,
dependencies, historical replay, 149 documentation pages and smoke. Its valid
resource receipt charges 1069.880040068 native CPU seconds. Freeze preserves
all 76 study and six acceptance identities before any device work.

All 66 ordinary GPU tests pass. The project suite passes 280 product pairs and
range refusal, but its first controller comparison fails: INT8 endpoints differ
after 64 logical / 66 physical updates and two audits. The new reference kernel
uses a serial sparse sum; the host oracle requires its fixed warp32 reduction.
No LP fixed-work/replay pair, sanitizer, profile or primary timing follows. Stop
without retry or changing numerical/latency criteria. Preserve frozen source,
image, binaries, workers, request roster and ledger. GPUP-8 is incomplete.

The v8 journal is failed with the full 2050-worker-CPU-second phase charged.
Cleanup is verified empty, sampled peak RSS 450502656 bytes and maximum sample
gap 7296669 ns. Separate delivery-v9 accounting carries every charge and closes
implementation/proof/worker/margin stages. Only already funded CPU reporting and
remaining native CPU acceptance may run. No further GPU reservation, bootstrap,
device substitution, host access or shared-system change is authorized.

Complete CPU-only independent evidence verification, refusal report, status/docs
and appropriate final CPU/docs/smoke checks. Do not commit unaccepted numerical
behavior or claim a useful certified Tensor solve/latency gain from this cohort.

## GPUP-8 repaired resource/source admission passes (2026-10-23)

All 26 resource tests pass with bounded durable completion transport. The bridge
generator's allowlist omitted the explicitly approved historical-reader change;
its failed phase and full 100 CPU seconds remain preserved. Correct only that
approved scope entry and carry every charge into cpu-journal-resource-v8.json;
8 implementation CPU seconds are charged for this bookkeeping. No numerical or
device admission/study identity is retried. Separate source-preservation proof
passes all 26 tests, six exact source bridges, four PR-scope checks and six study
checks; charge 22.000298888 proof CPU seconds. Exact resource receipt is
docs/benchmarks/data/tensor-cost/resource-admission-v4.json. No bootstrap rerun.

The approved new full native gate uses the remaining 1600 native CPU seconds
under the accepted stage transfers. Refresh compile-only test inventory only
after that gate passes; then freeze sources/roster/rule before device admission.
Implementation has 22.940361676 CPU seconds left. Workers 7800, reporting 400 and
termination margin 400 remain reserved. No GPU execution or reservation has run.

## GPUP-8 approved transport recovery and stage transfers (2026-10-23)

The user explicitly approves the proposed transfers and recovery. Preserve all
charges and the failed v6 journal; active accounting is
artifacts/gpup-tensor-cost-v1/cpu-journal-resource-v7.json. Stage caps are now
implementation 1600, proofs 1600, native 3800, workers 7800, reporting 800 and
margin 400 CPU seconds: total 16000 under the unchanged 35900 cumulative ceiling.
Recovery setup charges 20 implementation seconds in full. No new CPU/GPU funds.

The exact previously accepted ADR and supervisor C3 are archived under
docs/benchmarks/data/tensor-cost/transport-recovery-prior. Accepted ADR-0044 now
appends only this resource reallocation; previous contract bytes remain an exact
prefix and numerical/latency criteria are unchanged. Source fixes and four new
tests remain unrun. Next: all 26 resource tests and separate source bridge, then
one new full native gate before device freeze. No bootstrap rerun, host access,
GPU study retry or shared-system changes. No GPU work has occurred.

## GPUP-8 native transport refusal and proposed recovery (2026-10-23)

The first native command ran: Rust/native and dependency checks passed, then
401 Python tests finished with one historical registration-scope failure. Docs
and smoke did not run. Separately, the guardian truncated its final coordinator
packet at 65536 bytes, losing the resource receipt and leaving an unsettled
reservation. The output's `refused_before_launch` label is inaccurate for this
case. All recorded supervisor/entry identities exited. Preserve the raw native
log and unsettled journal; charge all 2200 native CPU seconds. The current v6
journal is now failed and settled. Reporting's 400 seconds are fully charged.

Current CPU upper accounting: 25507.557917574 / 35900. No GPU execution or
reservation has occurred in this continuation. Full native acceptance is not
established. Bootstrap, component/norm proofs and final CPU trajectory admission
remain historical passes; they do not admit the repaired supervisor source.

A bounded durable completion-result file plus small length/hash control packet,
truncation detection and cleanup/settlement on malformed frames are prepared.
Four new regressions are prepared but unrun. The historical reader now checks a
chain of separate immutable source bridges; its new registration bridge generator
is also unrun. No acceptance or restart is implied by these source edits.

The proposed [recovery](../docs/plans/lp-tensor-cost-transport-recovery.md) transfers
1000 proof plus 600 worker CPU seconds to native acceptance, and 400 implementation
seconds to reporting. Total prospective CPU remains 16000, cumulative ceiling
35900, GPU maximum 1806. All numerical/latency criteria and no-host constraints
stay exact. Execution and transfers await explicit user approval. No bootstrap
or attempted device identity may be retried. Separate refusal evidence:
docs/benchmarks/data/tensor-cost/native-transport-refusal.json.

## GPUP-8 explicitly authorized bounded recovery (2026-10-23)

The user explicitly approves recovery after the retained development watchdog
stop, with every charge carried forward and no bootstrap or study retry. The
separate authorization and failed-journal copy are preserved under
artifacts/gpup-tensor-cost-v1/authorized-development-recovery-v6. Active accounting
is cpu-journal-resource-v6.json; historical failed journals stay exact. No host
access or shared container/cluster configuration changes. Use the approved four-
CPU mask, one top-level phase, existing memory stop and shared idle GPU lease.
Cleanup may signal only this task's recorded PID/start-time identities.

The focused harness checks pass six regressions and construct/schema-validate
all 76 prospective study requests. The tuned diagnostics retain their own CLI,
while research diagnostics retain sufficient charged physical-work budget for
2000 logical updates. The first full native gate now uses its reserved 2200 CPU
seconds, separately from implementation. All numerical/latency criteria and the
1806-second maximum GPU allocation remain unchanged. No device work has run.

## GPUP-8 development watchdog stop (2026-10-23)

The user-authorized workspace-read retry succeeded. The corrected bootstrap and
22 resource tests remain passed; do not rerun the bootstrap. Final CPU-v2,
component and interval-Gram admission remain passed. Isolated study tooling now
declares 76 cells, profile-first order, actual unchanged tuned diagnostics,
frozen requests and the conservative forecast; this tooling remains unaccepted.

A development invocation of the full integration suite was assigned only 160 CPU
seconds: 40 wall seconds less supervisor margins. The guardian stopped it at the
38-second work deadline and proved descendant cleanup empty. Retain the failed
receipt and full 160-second charge. Captured output was buffered and lost on
termination; no passing integration result is claimed. No full native gate,
device reservation or GPU execution has occurred in this continuation.

The current resource-v5 journal remains failed. No automatic restart is allowed.
Two earlier output-only inspection errors also retain their full 40-second charges
and separate conservative bookkeeping charges; all earlier journals remain exact.
The final refusal delivery charges 100 reporting CPU seconds in full. Cumulative
CPU upper accounting is 23020.213097770 / 35900 seconds. Remaining stage caps:
implementation 638.285181480; proofs 1041.324565912; native 2200; workers 8400;
reporting 200; margin 400. No implicit transfer or new allocation.

Recovery approval is requested for a separate journal carrying every charge
forward, finishing implementation and attempting the first full native gate
within those existing stage caps. Numerical, latency, GPU, no-host and no-study-
retry criteria remain unchanged. No recovery work begins before approval.
Evidence: docs/benchmarks/data/tensor-cost/development-watchdog-refusal.json.

## GPUP-8 authorized corrected supervisor bootstrap (2026-10-23)

The user explicitly authorizes one corrected bootstrap using 100 CPU seconds
from the existing implementation stage. Preserve the first refusal/source/journal;
use separate corrected sources, authorization, journal and receipt. The prior
200 CPU seconds remain charged. Corrected bootstrap reserves 100 of implementation's
1900 remaining; all other stage allocations and the 35900 cumulative ceiling stay
unchanged. No additional GPU allowance or host access. If corrected bootstrap
passes, continue the already authorized real supervisor tests and unchanged
numerical/device/cost gates. A further failure stops without automatic retry.
Acceptance: independent bootstrap entry/affinity/pidfd, orphan/session cleanup,
coordinator-death handling, stale journal and competing lock witnesses; no numerical
or device work in bootstrap. Likely changes: separate authorization/source receipt,
corrected journal and bootstrap output, then supervisor tests after a pass.

Progress: the authorized corrected bootstrap passes all five witnesses and charges
100 CPU seconds. Initial real supervisor acceptance passes 20 tests. Allocation
checkpoint tests expose a diagnostic race (guardian loss may first surface as a
broken pipe); retain resource-tests-v2.json and its full 100-second charge. A
narrow error-label repair within approved supervisor development preserves both
observations and quiescence; the final 22-test resource suite passes. This does
not rerun the bootstrap or any numerical/study identity. Current budget journal is
artifacts/gpup-tensor-cost-v1/cpu-journal-resource-v5.json; earlier journals remain
exact and all charges carry forward. Exact current resource admission is
docs/benchmarks/data/tensor-cost/resource-admission-v3.json.

Isolated tensor_cost host/CUDA/experiment modules implement compact preparation,
interval Gram/remainder/error norm, ordered device reference audit and strict
new evidence. Fraction checks pass 26 Gram cases, all eight canonical metadata
comparisons, 27164 component cases and 12288 original-unit product components.
The new image uses at most 88 registers, zero spills and actual INT8/FP16/BF16 MMA.
The first source-bound CPU cohort retains all 48 cells: 24 execute, 22 reach the
400-update horizon; the two scaling-256 native controls retain numerical failure.
All twelve required dense trajectories pass, with useful work for all four low
layouts. Every produced CPU endpoint verifies. Sources/image/records remain
separate under artifacts/gpup-tensor-cost-v1 and data/tensor-cost.

Diagnostic boundary timestamps/kernel phase scopes and numerical-worker allocation
acknowledgements are included in the rebuilt final CPU cohort. The separate
cpu-admission-v2, norm-proof-v2 and proofs-v2 receipts pass; retain both cohorts.
The user authorizes one further supervised workspace-read retry after two tool
approval timeouts; that read now succeeds. Do not rerun the bootstrap. Continue
the frozen study harness and full native gate using the existing resource-v3 CPU
journal, without host access. No GPU reservation or kernel execution has occurred.
Full pinned-native, device
correctness/sanitizers and the frozen forecast/timing gates remain unrun. Numerical
budgets, controller cadence, replay, host certification and latency criteria stay
unchanged. Do not edit numerical sources after the final CPU/device freeze.

## GPUP-8 accepted in-container continuation implementation (2026-10-23)

Status: active under explicit user acceptance of revised ADR-0044, 14300 new CPU
seconds and reallocation of the remaining 1700. Work remains inside this container.
Objective: implement and independently validate the cooperative supervisor first,
then the fixed Tensor cost package and its numerical/device/cost gates. Preserve
the exact numerical/latency criteria, old source snapshots and 17362-event ledger.

Resource admission: one coordinator/guardian, project-wide lock, four work slots,
same four-CPU affinity, 6-GiB sampled-RSS stop against the 8-GiB policy, atomic
launch/reservation journals and four-times-wall charges. Bootstrap is one attempt,
100 CPU seconds/25 wall seconds charged in full within implementation's 2000.
Further stage caps are proofs 2600, native 2200, workers/verification 8400,
reporting 400 and termination margin 400; total 16000. Prior CPU upper accounting
19899.822845162; cumulative ceiling now 35900. No implicit transfers or retries.
GPU maximum remains 1806 (990/320/496), exact UUID and existing allocator unchanged.
No GPU reservation before resource/numerical/full-native admission. Extra GPU
offer remains unreserved. No host access, namespace entry or cluster changes.
Likely files: new supervision/tests/journal, isolated tensor_cost host/CUDA/tool
modules and separate evidence. Acceptance is ADR-0044's complete unchanged gates;
any failed real admission is retained and stops this bounded continuation.

First bootstrap result: the Python 3.11.14 build lacks os.pidfd_open. Both fork
branches fail at that API before launching/releasing the workload command. The
recorded guardian exited and no supervisor/bootstrap process remains. Preserve
artifacts/gpup-tensor-cost-v1/bootstrap-failed-source, the original unsettled
journal, captured stderr and docs/benchmarks/data/tensor-cost/supervisor-bootstrap-refusal.json.
Settle the full bootstrap reservation, 100 CPU seconds, mark the journal failed
and stop under the accepted no-automatic-retry rule. No numerical/GPU work runs.

A portable Linux pidfd wrapper and pre-fork capability check are implemented in
the current source, separately from the frozen failed version. Four mocked
source-only regressions pass; real capability/guardian/resource acceptance remains
unrun. A corrected 100-CPU-second bootstrap has been requested using existing
implementation funds; it requires explicit authorization. Refusal delivery has
a separate 100-CPU-second reporting reservation, conservatively charged in full.
Cumulative CPU upper becomes 20099.822845162 / 35900; remaining approved stages:
implementation 1900, proofs 2600, native 2200, workers 8400, reporting 300,
margin 400 (15800 total). No stage transfer or new allowance is inferred.

## GPUP-8 in-container admission amendment design (2026-10-23)

Objective: revise ADR-0044 at the user's request with a practical in-container
CPU supervisor and the explicit CPU allocation needed to resume. Preserve every
numerical/latency criterion and measured artifact. Archive the exact accepted ADR
before editing its resource sections; the resource/budget amendment is proposed,
not execution approval or a new measurement cohort. No host access is permitted.

Acceptance: an implementable process/slot/memory/accounting/cleanup contract with
explicit limits versus cgroups; a stage budget derived from worst-case retained
job caps; immutable prior ADR binding and unchanged numerical/study/completion
sections; updated current guidance and a separate source/preservation receipt.
Likely files: ADR-0044, exact prior-ADR snapshot, task/status/known-failure/backlog
guidance and the amendment receipt. No workloads, compiler or full native gate.
This documentation turn conservatively charges 5 CPU seconds from the remaining
5.177154838 unallocated seconds; implementation needs the proposed allocation.
Static checks are sequential and short. Zero GPU seconds/reservations.

Result: ADR-0044 now contains the proposed cooperative coordinator/guardian,
explicit sampled-memory/swap/cleanup limitations, conservative four-times-wall
charging and a 16000-second prospective CPU allocation. It requests 14300 new
CPU seconds, explicitly reallocates the 1700 unspent and proposes a 35900-second
cumulative ceiling. Resource/budget acceptance remains pending; no implementation
or workload admission has run. The 1806-second GPU package is unchanged.
Static checks pass for nine exact prior-source snapshots, all four preserved
numerical/study/completion sections, local ADR links, CPU arithmetic, git diff
--check and the exact 17362-event ledger. No full native gate or runtime resource
acceptance is claimed. Separate receipt:
docs/benchmarks/data/tensor-cost/in-container-amendment.json. Prior CPU upper
accounting is 19899.822845162 / 21600, leaving 1700.177154838 overall; no old
receipt or charge is rewritten. No local commit before applicable acceptance.

## GPUP-8 Kubernetes constraint and plan revision (2026-10-23)

Objective: revise the continuation for the user's confirmed Kubernetes executor
and explicit prohibition on escaping this container. This is a documentation-only
disposition, not another resource-admission attempt. No host access, namespace
entry, privileged helper, Kubernetes API mutation or cgroup remount is authorized.
The existing read-only mount cannot provide ADR-0044's delegated task enclosure.
Do not substitute cooperative sampling for the accepted hard containment gate.

Acceptance: document the executable boundary, exhausted CPU stage reservations
and remaining resources; preserve the accepted ADR, all historical reports and
receipts, and exact GPU ledger. Likely files: separate constraint plan, current
task/backlog/status/known-failure guidance and changelog. No compiler, numerical
preparation, test cohort, full native gate, GPU reservation or experiment runs.
Only bounded repository reads/edits and static preservation checks are in scope.
Conservatively charge this planning turn 10 CPU seconds from the previously
unallocated 15.177154838 seconds under the original ceiling, separately from
ADR-0044's stage reservations. This does not replenish an exhausted compute stage
or claim admitted aggregate accounting. No GPU work is authorized by this slice.
The user's additional 3600-GPU-second offer does not resolve CPU admission; retain
it as an unreserved offer pending any explicit revised resource contract.

Result: docs/plans/lp-tensor-kubernetes-constraint.md records the container-only
boundary, unavailable enclosure, exhausted CPU stages and unchanged numerical
gates. Static local-link/budget checks, ADR/probe source bindings, exact 17362-event
ledger verification and git diff --check pass. No resource preflight, build,
numerical/device work or full native gate runs; no local commit is claimed.
Separate receipt: docs/benchmarks/data/tensor-cost/kubernetes-plan.json.
The 10-second conservative planning charge leaves CPU upper accounting
19894.822845162 / 21600; overall remaining 1705.177154838, including ADR-0044's
unchanged 1700. No GPU charge/reservation or historical receipt changes occur.

## GPUP-8 ADR-0044 resource admission (2026-10-23)

Status: CPU resource admission refused under explicit user approval of ADR-0044
and its bounded continuation; delegated host containment is unavailable.
Acceptance requires
the delegated cgroup v2 enclosure, aggregate four work slots/four CPUs/8 GiB,
complete CPU/memory accounting, shared coordination and the failure tests in
ADR-0044 before numerical preparation or a device reservation. If delegation is
unavailable, retain a source-bound refusal and stop before preparation, as the
accepted ADR requires. No per-tree sampler fallback or historical recertification.
Likely files: ADR acceptance, separate resource preflight/coordinator evidence,
task/report/status records and bounded tests if the host capability admits them.
Resources: at most 250 CPU seconds for admission/tooling/preflight and compilation,
within the accepted 2050-second continuation; reserve all subsequent mandatory
stage/delivery margins. Total prior accounting is 19534.822845162 / 21600 CPU s.
GPU reservations remain 990 screening/320 ablations/496 repeatability maximum,
1806 total; no device job until CPU resource/numerical admission passes.
Preserve the exact 17362-event ledger SHA-256
e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5,
the exact 17200/17132 prefixes, and every historical source/image/worker/report.
Local commit after applicable acceptance; no publication, merge, GPUP-9 or retry.

Result: the sole cgroup v2 mount is read-only, has no delegated child, and enforces
90 cores / 200 GiB rather than four cores / 8 GiB. Membership/freeze/kill/limit
controls are not writable. System/user manager probes fail and no checked host
management socket is exposed. The separate preflight receipt binds the accepted
ADR and preflight source: docs/benchmarks/data/tensor-cost/cpu-admission.json.
The accepted decision requires a retained refusal and stop before preparation;
no numerical implementation, compiler, full native gate or GPU reservation runs.
Seven bootstrap refusal tests pass; these do not certify a real coordinator.
Documentation/link validation passes 145 pages and git diff --check passes.
Delivery receipt: docs/benchmarks/data/tensor-cost/acceptance.json.
The initial write-only cgroup.kill read error is retained as a discovery limitation.
Charge full CPU admission/reporting reservations (250+100=350 CPU seconds) because
the capability/bootstrap observation cannot supply complete task aggregate
accounting. Cumulative GPUP-8 CPU upper accounting is 19884.822845162 / 21600;
the original CPU ceiling has 1715.177154838 seconds left, with no retry authority.
GPU charge remains 825.114032275 task / 22184.699888064 campaign seconds; all
17362 events and both prior prefixes remain exact. Report:
docs/benchmarks/lp-tensor-cost-gpup8.md. Full native acceptance and local commit
remain unperformed because the resource prerequisite failed. GPUP-8 stays
incomplete; the host must expose delegated containment before further admission.

## GPUP-8 latency diagnosis and bounded completion proposal (2026-10-23)

Status: CPU-only diagnosis/proposal complete; user requests diagnosis and a concrete bounded proposal,
including repaired CPU resource admission. This slice reads retained profiles
and sources on CPU, writes a separate diagnosis/proposed ADR, and runs applicable
CPU/native/docs/smoke acceptance. It authorizes no new GPU job or arithmetic.
Acceptance: reproducible phase/work accounting from frozen evidence, source-based
causal distinctions, exact task/phase/CPU headroom, enforceable prospective CPU
admission and explicit stop/completion gates. Preserve every historical receipt,
source/image/worker/report and the exact 17362-event ledger prefix.
Likely files: separate diagnosis tool/report/receipt, proposed ADR-0044, roadmap,
backlog, known failures and task status. Budget: at most 400 CPU seconds charged
conservatively in full against the 2465.177154838 CPU seconds remaining; zero
GPU seconds; four aggregate execution slots, 8 GiB RSS, 64 MiB new artifacts.
Heavy jobs run sequentially; Cargo/Rayon/native pools stay within four workers.
The proposal must fit the remaining resources after this diagnosis charge;
unused allowance does not authorize new cells, retries, GPUP-9 or publication.


Acceptance: separate diagnosis binds all 72 retained study LP endpoints, their
workers/trials and the exact settled ledger; no solve/device execution or fresh
numerical reverification runs. Counterexamples protect exclusive cost aggregation
and distinguish actual tuned controls from research-wrapper profiles. Full
pinned-native tools/check.sh passes 366 Python tests, Rust/native/dependencies,
historical replay, 144 documentation pages and smoke. Stable gate source hash:
b8d9d2fbd8a5242dfba4ffb21e45d4067b04c718d80fe7b3c4b31f6fd8617569.
Gate CPU time is 234.500760 s; sampled peak process-tree RSS 1650266112 bytes;
heavy jobs were sequential, affinity four CPUs, build slots four/test threads one.
This diagnostic gate does not establish ADR-0044 delegated-containment admission.
Charge the full 400-second diagnosis reservation; remaining CPU allowance is
2065.177154838 s. The proposed 2050 CPU / 1806 GPU-second continuation fits the
unchanged caps but remains unaccepted. Its CPU delegation prerequisite is absent
in this container. Preserve the historical overlap and all old evidence.
Receipt: docs/benchmarks/data/tensor-latency/acceptance.json. GPUP-8 stays incomplete;
no GPUP-9, new GPU cells, numerical implementation, publication or merge.

## GPUP-8 residual continuation result (2026-10-23)

CPU resource audit: initial CPU admission (four workers) overlapped the first
native build (four jobs). Aggregate active jobs/RSS were not recorded, so the
four-job preparation constraint is not certified. Record this additional
resource-acceptance limitation separately; later gates and GPU work are
sequential. Receipt: docs/benchmarks/data/tensor-residual/cpu-concurrency-limitation.json.


Status: incomplete on certified total-latency gain; bounded ADR-0043
implementation/evaluation finished under explicit user approval. The separate
[report](../docs/benchmarks/lp-tensor-residual-gpup8.md) retains all 75 cells:
60/60 timings certify, twelve profiles finish 2000 logical updates and three
product diagnostics pass. All thirty Tensor timings perform 2200 logical updates,
66 useful windows and no native promotion. Working integer/floating families now
qualify; all six multiplicity-adjusted gain comparisons fail. INT8 median seconds
are 0.614776 versus tuned 0.462114 at 1024 rows, and 10.390881 versus 6.331022 at
65536 rows. No preset or GPUP-9 progression follows.

CPU admission retains all eight models/six configurations, with complete useful
400-update trajectories on both dense models. Exact proofs pass 27164 cases,
12288 original-unit components, 961 BF16 products and 4608 lane addresses.
Device acceptance passes 280 product pairs, five controller pairs, twelve
fixed-work/replay pairs, all 66 ordinary GPU tests and four scoped sanitizers.
Independent verification accepts all 120 continuation LP records. All 1272
historical GPUP-8 inventory files remain byte-identical. Initial CPU acceptance
failures and their separate registration receipt remain visible; no measured
historical source/image/payload is changed or re-signed.

Continuation GPU charge is 588.257104641 s: timing 322.826798512,
profiles/diagnostics 67.444213966, acceptance
197.986092163, inside 1440/525/700 reservations. Combined
GPUP-8 charge is 825.114032275 / 3000 s; cumulative
22184.699888064 / 25202.574545061 s. Ledger 17362 events, SHA-256
e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5; exact 17200/17132-event prefixes preserved.
All sources/executables/images/workers/requests/endpoints/reports remain separate
under artifacts/gpup-tensor-residual-v1 and docs/benchmarks/data/tensor-residual.
Final CPU/native/docs/smoke delivery acceptance follows this measured result.
No new cells, retries, numerical relaxation, next-task allowance, publication or
merge. Local commit after applicable acceptance remains authorized.


Final software delivery acceptance (2026-10-23): stable-source pinned-native
tools/check.sh passes 363 Python tests, Rust/native/dependencies, historical
replay, 142 documentation pages and smoke. All 248 GPUP-8 LP records freshly
verify (120 continuation plus 128 historical); the historical machine report
reproduces exactly. Source-only portability passes 39 tests without study
artifacts/native dependencies. Final gate source SHA-256 is
ed68a106e072dfe19d568f32898d7f39aed1b4fe0eb14e4d6ff266939508511a.
Conservative continuation CPU accounting is 8797.192667 / 10000
seconds; combined GPUP-8 accounting is 19134.822845 / 21600.
Monitored process-tree RSS peaks at 2671681536 bytes;
combined task artifacts total 1818373856 bytes, below 32 GiB.
These measurements do not certify the unrecorded aggregate four-job/RSS bound
during the initial admission/build overlap. Software acceptance passes; task
completion and full preparation-resource acceptance remain unmet. Separate
delivery receipt: docs/benchmarks/data/tensor-residual/acceptance.json.
Subsequent edits only record acceptance metadata; numerical sources stay exact.

## GPUP-8 continuation diagnosis (2026-10-23)

Status: bounded continuation evaluated; see the result above. The user explicitly
approved ADR-0043 and its bounded
continuation using only the existing unspent allowance. First
bounded task: reproduce the range failure and prepare a concrete continuation
contract with CPU arithmetic/admission evidence. The ADR-0042 frozen study stays
exhausted; no historical cell, payload, image, report or ledger event is replaced
or retried. Completion still requires useful integer/floating Tensor solves and
a multiplicity-adjusted certified total-latency gain at unchanged tolerances.
ADR-0043 now admits revised arithmetic and a separate study: 1440 screening,
525 ablation and 700 repeatability seconds maximum reservation; no ceiling
increases. Independent arithmetic proofs and CPU admission precede device work. Acceptance: exact-real counterexamples and a reviewable bounded plan;
full CPU/native/docs/smoke gate for any committed changes. Likely files: separate
continuation diagnosis/tooling, proposed decision/plan, task state and evidence.
Diagnostic budget: 1800 CPU seconds, four jobs, 8 GiB RSS, 256 MiB new artifacts,
zero GPU seconds. Preserve all 17200 ledger events, SHA-256
5af7782a384ac73226f339d98d0b33e320518053c1accdf67c1339db36d0e0f1,
and the exact 17132-event prefix. This entry grants no additional resources,
GPUP-9 progression, publication or merge.

## GPUP-8 implementation (2026-10-23)

Status: incomplete; bounded implementation/evaluation finished under explicit
user approval of the GPUP-8 implementation
plan and 3000 GPU seconds from existing headroom. Implement research-only
lp-tensor-v1 INT8/FP16/BF16 component products on selected dense 32x32 tiles,
resident FP64 state, guarded original-unit arithmetic and fresh host authority.
Completion requires useful INT8 and floating Tensor Core certified nontrivial
solves plus a multiplicity-adjusted certified total-latency gain over tuned FP64.
A refusal or no gain leaves GPUP-8 incomplete and does not authorize GPUP-9.
Acceptance: independent integer/Fraction oracles and eight-model CPU admission;
full pinned-native tools/check.sh; instruction/register/spill gates; ordinary and
new device differentials, replay and four scoped sanitizers; independently
verified frozen study. Preserve all historical sources/images/workers/reports.
Resources: 21600 CPU seconds, four jobs, 8 GiB RSS, 2 GiB preparation, 1 GiB
device buffers, 32 GiB artifacts. GPU allocations: screening 1600, ablations 550,
repeatability 850 seconds; planned reservations 1560+540+816=2916 seconds.
No ceiling increase: cumulative 25202.574545061, independent campaign 28800,
phase ceilings baseline/screening/ablations/repeatability/finalists
1800/11800/8100/5300/9000 seconds. Starting consumption 21359.585855789 s.
Preserve exact 17132-event ledger prefix SHA-256
930de6771ab9bfbcb855bd05a07a58f6700aa1ade36bca09346790a94e7ff035.
Device GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 only, shared lease/activity
admission; no substitution or study retries. Separate artifacts/gpup-tensor-v1
and docs/benchmarks/data/tensor receipts. Local commit after applicable checks;
publication and merge are outside this task. The approved plan is ADR-0042.
Pre-device evidence: exact conversion/rounding (27091 cases), 12288 original-unit
components, 961 BF16 products and 4608 lane addresses pass. Four CPU cohorts retain
48 cells each, with the same useful-low refusals. Native gates pass up to 351
Python tests, Rust/native/dependencies, replay, 140 docs pages and smoke. The first
allocator preflight reserved no GPU job. The first leased device gate reproduces
a packing-index defect, retained with 2.105369475 GPU seconds; its repair has a
fresh CPU/image cohort before further device admission. All sources remain exact
in their archived cohorts; current numerical source matches the latest CPU cohort.


Final delivery acceptance: pinned-native tools/check.sh passes 353 Python tests,
Rust/native/dependency checks, historical replay, 140 documentation pages and
smoke, with zero GPU work. Independent verification accepts all 128 LP records.
Full-gate source SHA-256 is 2f98dce5bb37ec0e9b363ad2a33cffc1c735ce0dbcc5c96befc5737a7a5d154f.
Source-only portability passes 20 inherited plus nine Tensor tests with study
artifacts/native dependencies absent and only an empty scratch build directory.
Measured CPU jobs plus the conservative preparation/coordination allowance and
delivery reserve account for 10337.630178 / 21600 CPU seconds; sampled process-tree RSS
is 3535245312 bytes and retained task artifacts approximately 1.166 GiB, within caps.
The delivery receipt is docs/benchmarks/data/tensor/acceptance.json. Subsequent
edits only record acceptance metadata; measured numerical sources remain exact.

GPUP-8 result: all 75 planned cells are retained: 27 execute and 48 are CPU-refused.
All 20 admitted FP64 timings certify (20/60 planned); four profiles finish 2000
logical updates. Matched profiles use 2070 physical updates and remain unclosed;
tuned profiles use 2000 and first certify at 1400. Correct INT8/FP16/BF16 operators
pass 260 CPU/device product pairs, five controller comparisons, four fixed-work/
replay pairs, 66 ordinary GPU tests and all four scoped sanitizers. No useful
component window passes CPU admission on either dense model, so working-family
solve and certified latency-gain requirements remain unmet. GPUP-9 is not started.
Fresh independent CPU verification accepts all 128 LP records: 96 from four CPU
cohorts, eight device/replay and 24 study records, without normalization/re-signing.
Separate report and receipts: docs/benchmarks/lp-tensor-gpup8.md and
 docs/benchmarks/data/tensor. Final CPU/docs/smoke delivery gate follows this result.
GPU charge is 236.856927634 / 3000 s (timing 92.278436607, profiles 22.601859333,
acceptance 121.976631694, including the failed first 2.105369475-second device gate).
Cumulative is 21596.442783423 / 25202.574545061 s. The 17200-event ledger SHA-256
is 5af7782a384ac73226f339d98d0b33e320518053c1accdf67c1339db36d0e0f1,
with the exact 17132-event prefix and all previous sources/images/workers/reports
preserved. The authority preflight reserved no GPU identity. No completed identity
was retried. Local evidence commit follows applicable acceptance; no publication,
merge, replacement study cells, tolerance relaxation or next-task allowance.

## GPUP-7/7R PR review and integration (2026-10-23)

Status: in progress. The user explicitly authorizes opening a PR, repeated review
and fixes, protected merge and safe cleanup. This supersedes prior local-only
delivery restrictions for GPUP-7/7R. Main lacks the completed GPUP-7 prerequisite;
the PR includes its preserved implementation, the resident plan and GPUP-7R.
Objective: review the complete main-to-branch diff against accepted ADR-0040/0041
and specifications; fix reproduced findings; preserve every measured source,
executable, image, endpoint, report and ledger prefix. Use separate CPU-only PR
source bridges/reports if verifier or reader changes are needed.
Acceptance: regression counterexamples, full pinned-native bash tools/check.sh,
independent retained-endpoint verification, clean-checkout CPU portability,
all cpu/docs/smoke test commands and no unresolved actionable findings. GitHub
Actions cannot start because its account budget is exhausted. The user reports
disabling branch protection, explicitly requires every test, and authorizes
integration after local acceptance. Verify effective remote rules before merging.
Resources: CPU-only review, at most 21600 CPU seconds/four build jobs and 8 GiB
RSS; zero GPU execution or additional allowance. Preserve 17132 ledger events,
SHA-256 930de6771ab9bfbcb855bd05a07a58f6700aa1ade36bca09346790a94e7ff035,
and all historical artifacts. Publication is authorized only through this PR;
merge with ancestry preserved, then remove merged task branches after verifying
ancestry. Retain native dependencies and all research artifacts.

Review acceptance (2026-10-23): two passes reproduce and repair mutable prepared
operators, partial promotion on invalid IDs, malformed window counters, JSON
shape aliases, inconsistent promotion histories, physical counter validation and
interrupted-profile/report-output eligibility. Full pinned-native acceptance
passes 344 Python tests plus Rust/native, dependencies, historical replay, 138
documentation pages and smoke; 20 quantization tests pass without ignored
artifacts/dependencies. Fresh CPU verification accepts 495 LP plus 21 operator
endpoints: rebuilt verifiers cover 423 LP/21 operator endpoints, and the original
frozen verifier covers 72 initial resident CPU endpoints predating the required
first-certification field. No payload/schema is normalized or re-signed.
Separate report/receipts: docs/benchmarks/lp-quant-pr-review.md and
docs/benchmarks/data/quant-resident/pr-{review-source,native-acceptance,retained-verification}.json.
Original reports, workers, archives, kernels, mathematical authority and all
17132 ledger events remain exact. PR #22 contains the preserved three prerequisite
commits; the review commit follows acceptance. Merge and cleanup remain pending
remote admission; the effective Protect main ruleset is still active despite the
user's reported branch-protection change. No new GPU work or allowance.

## GPUP-7R implementation (2026-10-22)

Status: complete (2026-10-23), under the user's explicit ADR-0041/allocation approval.
Acceptance evidence: full pinned-native gates pass 338 Python tests, Rust/native,
dependencies, historical replay, 137 documentation pages and smoke. All 66 ordinary
GPU tests, inherited/new quantization suites, 628 product/bound differentials,
six CPU/device controller comparisons, 29 fixed-work endpoint/replay pairs and
all four scoped sanitizers pass. A pre-sanitizer source bridge broadens the filter
to include resident updates/windows; completed jobs are preserved without retry.
The invalid project interpreter preflight reserved no GPU identity and remains.
Independent final verification accepts 313 LP endpoints (39 study, 58 acceptance/
replay, 216 CPU cohorts) plus 21 operator endpoints. Three CPU cohorts remain exact.
The separate report is docs/benchmarks/lp-quant-resident-gpup7r.md, with acceptance
and machine results under docs/benchmarks/data/quant-resident. All 36 admitted
fresh timings certify (36/108 planned); 78 quantized timing/profile cells retain
CPU useful-low refusals. Three FP64 profiles finish 2000 logical updates. Resident
matched FP64 irregular-32768 median is 4.799867 s versus tuned FP64 2.564014 s;
quantization remains inadmissible on actual trajectories. No preset follows.
Task GPU charge is 245.686586823 / 3600 s: timing 69.376705845 / 2300,
profiles 69.783306098 / 450 and acceptance 106.526574880 / 850. Cumulative
21359.585855789 / 25202.574545061 s, with unchanged phase/campaign ceilings.
The 17132-event ledger SHA-256 is
930de6771ab9bfbcb855bd05a07a58f6700aa1ade36bca09346790a94e7ff035,
preserving the exact 17036-event prefix and all historical evidence. CPU upper
accounting (major measured jobs plus preparation/final-gate allowances) is below
21600 s; RSS 3234975744 B and new artifacts approximately 2.12 GB stay within caps.
Final CPU-only gate/log: artifacts/gpup-quant-resident-v1/delivery-native-resources.log.
Local commit follows acceptance; no push, publication or merge. GPUP-8 is next
for a conditional disposition/contract, with no allowance reserved.
Objective: lp-quant-resident-v1 GPU-resident FP64 updates, compact sparse layout,
two-level conservative device guards and the frozen bridge/matched comparison.
Retain the existing numerical budgets, norm/step, promotion/recovery rules and
original-model host authority. CPU admission precedes all device execution.
Acceptance: exact guard/format oracles and eight-model CPU admission; full pinned
native bash tools/check.sh; ordinary/new device differentials, fixed-work replay,
four scoped sanitizers; independently verified bounded study and separate report.
Likely files: new resident host/CUDA/experiment modules and image, strict schemas,
tools and tests; accepted ADR-0041/spec mappings and state/evidence documents.
Resources: 21600 CPU seconds/four build jobs, 8 GiB RSS, 1 GiB device buffers,
2 GiB preparation, 32 GiB artifacts. Allocate 3600 GPU seconds from existing
authority: timing 2300 screening, profiles 450 ablations, acceptance 850
repeatability; planned reservations 2268/432/816 seconds. Additional GPU allowance
is zero; cumulative ceiling remains 25202.574545061 and campaign cap 28800 s.
Phase ceilings remain 1800/11800/8100/5300/9000 seconds. Prior consumption is
21113.899268966 s. Preserve the exact 17036-event ledger prefix SHA-256
861c90d8d82a20ff9655173742db37a5047d315e8cc4c983e0d6b2e6fa09bb97 and all prior
artifacts/identities. Execute only on GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48
under shared host lease/activity admission, without retry/substitution. Retain
CPU-refused dependent cells without replacement. Store new evidence separately
under artifacts/gpup-quant-resident-v1. Commit locally after acceptance; no push,
publication or merge. This approval supersedes the historical planning-only
handoff below.

## GPUP-7R follow-up planning (2026-10-22)

Status: planning complete at the user's request. Specify a bounded resident
quantized executor, cheaper conservative guards, matched controls and a proposed
resource allocation before implementation. This task authorizes documentation
and CPU validation only; no runtime changes or GPU execution.
Acceptance: reviewed plan and draft superseding ADR; consistent roadmap/backlog;
checked reservation arithmetic and historical ledger identity; full pinned-native
bash tools/check.sh with zero GPU work. Likely files: new plan and ADR-0041,
state/active-task.md, state/backlog.yaml, roadmap and wiki/status.md.
Planning resources: at most 900 CPU seconds, four build jobs, 8 GiB host RSS,
256 MiB new planning receipts and zero GPU seconds. Preserve the 17036-event
ledger SHA-256 861c90d8d82a20ff9655173742db37a5047d315e8cc4c983e0d6b2e6fa09bb97,
all GPUP-7 sources/images/reports and all earlier evidence. Proposed execution
allocation remains unaccepted until separately authorized by the user.

Acceptance evidence: full pinned-native bash tools/check.sh passes 329 Python
tests plus Rust/native/dependency, historical replay, 136 documentation pages
and smoke, with zero project GPU work. Stable gate source SHA-256 is
6373f11b118a630f2da38f0b30a10a883e8f6cab14f84e44d83680f0be81dcec;
124.909852223 elapsed / 160.555184 CPU seconds and 1662705664 bytes sampled
process-tree RSS. Planning arithmetic verifies 3516 seconds of reservations
inside the proposed 3600-second allocation and all unchanged campaign/phase caps.
Receipts: artifacts/gpup-quant-resident-plan-20261022/native-acceptance.json and
planning-arithmetic.json. Subsequent edits only clarify planning/handoff text
and record this acceptance; recheck their links and the unchanged ledger before
the local documentation commit. No numerical/runtime/tooling behavior changes.

## GPUP-7 implementation (2026-10-22)

Status: complete; final pinned-native acceptance passed. Delivery is a local
commit only. All 104 attempts remain:
34 study endpoints verify and 33/96 timings certify. New modes and matched FP64
only certify initial host-only small-4; tuned FP64 certifies 12/12. No preset or
useful low-product solve benefit follows. All eight profile horizons are censored
(seven timeouts; tuned FP64 early success at 1400/2000). Final CPU admission retains
56 cases/7 scaling refusals, 162015 format and 3072 product components. All 66
ordinary/three new device tests, 384 vector comparisons, six CPU/device controller
comparisons, 18 fixed-work endpoints/18 bitwise replays and four sanitizers pass.
Fresh host verification accepts all 182 retained endpoints. Exact CPU admission
and report-reader source bridges retain both cohorts and reports. Final GPU task
charge is 1382.959456122 s (1109.904216936 timing, 215.675211186 profiles,
57.380028000 acceptance); cumulative 21113.899268966/25202.574545061 s.
Ledger 17036 events, SHA-256
861c90d8d82a20ff9655173742db37a5047d315e8cc4c983e0d6b2e6fa09bb97.
Preserve the exact original 16816-event prefix and all artifacts. CPU review adds
zero GPU work. Final source/gate receipts are under docs/benchmarks/data/quant. Final tools/check.sh
passes 329 Python tests, Rust/native/dependency, committed replay, 134 docs pages
and smoke. Gate source is stable; 122.521477555 elapsed / 141.162757 CPU seconds,
1661800448 bytes sampled process-tree RSS and zero GPU work.
Objective: lp-quant-v1 matrix-only uniform/selective binary16, E4M3 and E5M2,
FP64 state and original-model host authority. CPU admission precedes CUDA work.
Acceptance: independent exact format/error oracle; CPU preparation on eight frozen
models; full pinned-native tools/check.sh; ordinary/new device differentials,
fixed-work replay and four scoped sanitizers; frozen development study and report.
Likely files: new quant modules in optimizer-lp/optimizer-lp-cuda and experiment,
separate CUDA image, strict schemas and tools, ADR-0040 and SPEC-0012/0021.
Resources: 21600 CPU seconds/four jobs, 8 GiB RSS, 1 GiB device buffers, 2 GiB
preparation, 32 GiB artifacts. GPU cap 3600 seconds: timing 2300 screening,
profiles 450 ablations, acceptance 850 repeatability. New cumulative ceiling
25202.574545061 seconds; phase caps 1800/11800/8100/5300/9000 and independent
28800-second overall cap. Preserve the exact 16816-event prefix SHA-256
dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c
and prior 19730.939812844 GPU seconds. Use only
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 under the shared host lease/activity
admission, without automatic substitution or retries. Record artifacts under
artifacts/gpup-quant-v1. Deliver a local commit after acceptance; no publication.
This authorization supersedes the historical instruction below not to start GPUP-7.

## GPUP-ASSESS review and integration (2026-10-22)

Status: PR 21 review and local acceptance complete; final publication/checks precede
protected merge. All review counterexamples are repaired.
Checkpoints reject transfer to a fresh same-engine session; evidence rejects
inconsistent failure metadata/oversized counters; incomplete profile pairs cannot
borrow discovery from a longer policy horizon. Targeted CPU regressions pass.
Full pinned-native tools/check.sh passes 323 Python tests plus Rust/native,
dependency, historical replay, 132 documentation pages and smoke. Gate resources:
128.427299756 elapsed / 180.294952 CPU seconds, 1658880000 bytes sampled process-tree
RSS, zero GPU work. All 1468 frozen artifacts remain byte-identical and the rebuilt
report preserves every numerical result, outcome and charge. Exact PR source
receipts and native acceptance are docs/benchmarks/data/assess/pr-*.json. Final
retained-endpoint verification and reviewed-head CI precede merge.

Final review intercepts and repairs the report default overwriting the earlier
CPU-review report. Protect both historical reports/aliases and write to a separate
PR path. The first PR source/gate/report cohort remains exact; final source and
native receipts use separate filenames. The final full pinned-native gate passes
324 Python tests plus Rust/native/dependency, historical replay, docs and smoke:
116.991061611 elapsed / 144.139803 CPU seconds, 1663926272 bytes sampled process-tree
RSS. The rebuilt verifier accepts all 97 retained endpoints (57 study, 12 device
acceptance, 12 replays, 16 CPU traces), using 1669.733762 CPU seconds and 512024576
bytes sampled process-tree RSS. All numerical results and charges remain exact;
zero GPU work is added. Required CI must pass on the final published head, with
integration/cleanup receipts in the review artifact directory.

The user authorizes a draft PR, careful review and repairs, merge after required
checks, and safe cleanup, superseding the local-only scope below. Review the
scheduler/controller lifecycle, final witness authority, strict evidence and
experiment accounting; retain counterexamples for any repairs. Run focused CPU
regressions and full pinned-native tools/check.sh on the reviewed source before
integration. Do not start GPUP-7.

Resources: at most 7200 CPU seconds, four build jobs, 8 GiB host RSS and 2 GiB new
review artifacts. No GPU execution or additional allowance. Preserve all of
artifacts/gpup-assess-v1, frozen source/executable/image identities, original and
reviewed reports, and the exact 16816-event ledger SHA-256
dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c.
Record review, acceptance, CI, merge ancestry and cleanup receipts under
artifacts/gpup-assess-pr-review-20261022. Merge through the PR after successful
checks without bypassing repository rules; remove only the verified merged task
branch and explicitly disposable scratch files. Retain native dependencies and
all research evidence.

## GPUP-ASSESS (2026-10-22)

Status: complete; final pinned-native acceptance passed, local commit follows.
All 60 attempts are retained; 57 endpoints verify and 24/48 timings certify.
Task charge is 523.674592721 GPU seconds, with 16816 ledger events and SHA-256
dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c.
Review strengthens signed-zero replay comparison and unverified-profile handling.
All twelve retained replays already match bitwise; preserve measured sources,
executables, images and report with exact review source bridges. No further GPU
execution or allowance is admitted.
The original and reviewed reports have identical numerical results and charges.
Six GPU profile pairs match bitwise; FP64 irregular-32768 gains 1.0272x in three
screening repetitions, with unchanged coverage and no supported preset.
CPU admission used 545.510899 seconds, 493043712 bytes maximum child RSS and
zero GPU time. All 66 ordinary/three new device tests, six fixed-work pairs,
twelve actual bitwise replays and four scoped sanitizers passed on the selected
5090. The reviewed host verifier accepts all 57 available endpoints on CPU.
Final full pinned-native tools/check.sh passes 322 Python tests, Rust/native and
dependency checks, committed-record replay, 132 documentation pages and smoke.
Native coverage was enabled; no GPU work ran. Gate resources are 123.223139896
elapsed / 163.805355 CPU seconds, 1662132224 bytes sampled process-tree RSS and
1663143936 bytes maximum child RSS. Only subsequent documentation records these
results and the retained checksum inventory; measured numerical sources remain
exact. Reviewed acceptance is docs/benchmarks/data/assess/native-acceptance.json.
Preserve artifacts/gpup-assess-v1 in full, including original/CPU-review sources,
executables, images, endpoints, first launch failure, report versions and receipts.
GPUP-7's numerical/resource contract is the handoff; do not start it here.
Objective: compare fixed_200 and bounded_800 original-model assessment scheduling
on tuned FP64 and existing accumulation FP32, preserving every 200-update
restart/weight decision. CPU common-trajectory admission precedes device work.
No other task, numerical mode, default, promotion or recovery policy is admitted.
Acceptance: independent CPU replay over the eight GPUP-EXEC models at up to 4000
updates, strict requests/evidence and complete scheduler/controller checkpoints;
full pinned-native tools/check.sh; all 66 ordinary device tests; six fixed-work
policy pairs and twelve replays; four scoped sanitizers; 48 fresh timings and
12 separate 2000-update diagnostic profiles with independent host endpoints.
Likely files: optimizer-lp/optimizer-lp-cuda assessment modules, experiment example
and strict evidence; CPU oracle/admission, bounded protocol/runner/report/tests;
ADR-0039, SPEC-0021, reports and handoff documents.
Resources: 21600 CPU seconds/four build jobs, 8 GiB host RSS, 1 GiB device buffers,
32 GiB new artifacts; at most 2300 GPU seconds (1300 screening timing, 450 ablation
profiles, 550 repeatability acceptance). Frozen reservations are 1248/432/516 s.
Use only GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 under the shared host lease and
selected-device activity admission. Retain failed/refused attempts without retry
or substitution. Preserve the 16684-event prefix SHA-256
e83d07792fb0775fc26d8d2cca8a2411f59fcbc94f742cafd8f6b844ffb60535
and 19207.265220123 / 21602.574545061 cumulative GPU seconds, all phase ceilings
and every historical artifact. No added campaign allowance or later reservation.
Record new evidence under artifacts/gpup-assess-v1. Commit locally after acceptance;
publication, push and merge are outside this task.


## GPUP-REFINE review and integration (2026-10-22)

The user authorizes opening the PR, careful review and fixes, protected merge and
safe cleanup, superseding the prior local-only delivery scope below. Review the
numerical/controller, checkpoint and evidence boundaries locally before one
publication of the reviewed head; keep GitHub CI runs to the required minimum.
Preserve every measured source/ELF/image, raw attempt, failure and ledger prefix.
Resources: 7200 CPU seconds, four build jobs, 8 GiB host RSS, 2 GiB new review
receipts; no GPU work is planned. Any newly required device acceptance must use
a new scoped identity inside the existing task/campaign allowance, never rerun
primary identities. Record review findings, targeted regressions, full pinned-native
acceptance and exact measured/reviewed identities under
artifacts/gpup-refine-review-20261022. Local review reproduces and fixes stale
checkpoint logical metadata, candidate-free trace claims, skipped final assessment
after refresh/promotion offsets and incomplete generated-instruction parsing.
The rebuilt host verifier accepts all 39 available refinement endpoints; all
1088 original artifacts and the byte-identical historical report are retained.
Exact source bridges bind every changed implementation/tool file. No GPU work
ran and cumulative charge/16684-event ledger remain unchanged. Full pinned-native
acceptance passes 310 Python tests, Rust/native/dependency checks, historical
replay, 130 documentation pages and smoke: 126.882339225 elapsed / 178.747286 CPU
seconds, 1631154176 bytes sampled process-tree RSS, 1663311872 bytes maximum child
RSS. Reviewed-source receipts are docs/benchmarks/data/refine/review-*.json.
Publish the reviewed head once and use the PR's required CI checks, cancelling
only redundant push-triggered runs for that same head. Merge through the protected PR without
bypassing checks, synchronize main and remove only the merged task branch and
explicitly disposable caches; retain evidence and native dependencies. Hand off
GPUP-ASSESS without starting it or reserving its allowance.

## GPUP-REFINE implementation (2026-10-22)

Status: complete; final native acceptance passed, local commit follows.
Implemented on codex/gpup-refine under
accepted ADR-0037 / native-FP64-outer SPEC-0021 and ADR-0038's selected-device
telemetry repair. The original implementation objective/budget was recorded here
before runtime work; the user explicitly authorized this bounded slice and its
3600-second allocation within the existing ceiling. No other task is started.

Result: equality-plus-box correction LPs, host FP64 state/controller, GPU FP64 or
FP32 sparse products, directly maintained guarded anchors, charged sticky native
promotion, complete in-memory checkpoints and strict solve/verify/replay.
Original-model host certification remains authoritative. The
[report](../docs/benchmarks/lp-refinement-gpup-refine.md) retains all 108 attempts,
48 verified endpoints and 30/96 certified timings. Only small-4 certifies in the
new modes, at the initial host point before any device work. Scaling-256 refuses
numerical budgets; other new timing cells expire. No sparse-product benefit,
general convergence result or preset is admitted. Host guards/FP64 recurrences
are expensive, and every refresh, failed correction and recovery remains charged.

Acceptance evidence: Fraction admission covers 240 general models/1200 correction
maps; independent sparse endpoint checks cover 21 endpoints, 93 merit enclosures
and 39 exact contractions. The subnormal rounded-step counterexample is retained
and refused. All 66 ordinary device tests, three refinement tests/1920 bitwise
product checks, nine fixed-work solve/verify/replay pairs and memcheck, racecheck,
initcheck and synccheck pass. New image uses 40 registers and zero stack/spills.
The pretrial exact-source full pinned-native tools/check.sh gate passes (299
Python tests, Rust/native/dependency checks, committed replay, docs and smoke).
Final full pinned-native gate passes all 304 Python tests, Rust/native/dependency
checks, committed-record replay, 130 documentation pages and smoke. It used
116.036960146 elapsed / 140.362833 CPU seconds, 1644863488 bytes peak sampled
process-tree RSS and 1663217664 bytes maximum child RSS. No GPU job ran in that
gate; native coverage was enabled. The only post-gate changes record these CPU
results and refresh the artifact inventory; measured numerical sources remain exact.

Preserve the v1 activity refusal before child launch (0.125948387 GPU seconds),
all unexecuted v1 cells, and the separately frozen v2 continuation on the same
5090. No attempt identity is repeated or device substituted. Original source
4e8af4e8fc3a197af2c5d8e31f7e25c798833588c7e8ae4986db487c80f294d6;
measured v2 source b6a462fb9b43a168e2da890a75e70abd345d929dcfc1ae2dfcad173838f6d3a2.
Numerical Rust/CUDA/ELFs/images are unchanged between cohorts. The first CPU final
report failed to decode a compact control wrapper; its failure log and exact
reader/test correction hashes are retained with no reexecution. Local artifacts
are artifacts/gpup-refine-v1 and artifacts/gpup-refine-v2; reviewed summaries are
under docs/benchmarks/data/refine. Final native log/resources remain in v2.

Task GPU charges: timing 1275.123297404/2300, profiles 217.195487188/450,
acceptance including refusal 49.400351920/850; total 1541.719136512/3600 s.
V2 uses 1541.593188125/3599 s. Cumulative 19207.265220123/21602.574545061 s.
Final 16684-event ledger SHA-256:
e83d07792fb0775fc26d8d2cca8a2411f59fcbc94f742cafd8f6b844ffb60535.
Original 16452-event prefix:
24949150272600fe58364f25ebbf7bf892f7454da342edc268d50684568c5f18.
Intermediate 16454-event prefix:
900bbaed980f273db069819028e48ee8c896024e4492ade21382199b78ae8e6e.
Every earlier prefix and phase ceiling is preserved; no campaign allowance added.
All GPU work used the shared host lease and activity admission on
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48. CPU allocation 21600 seconds/four build
jobs, host RSS 8 GiB, device resident/preparation 1/2 GiB, new artifacts 32 GiB.
Observed primary RSS peaks at 835399680 bytes; retained cohort artifacts are well
below the artifact cap. Shape/memory bounds include up to 131072 transformed
variables and the implicit activity block; in-range shapes may still refuse.

Hand off GPUP-ASSESS under its own bounded contract/allocation, without starting
policy work or reserving unused headroom. Preserve expansion/alternative gates,
original-model authority, defaults and all historical evidence. Final acceptance
is followed by a local commit only; no push, publication or merge is authorized.


## PR 19 integration and evidence retention (2026-10-13)

The user has now authorized merging PR 19 and safe cleanup, superseding the
earlier no-merge delivery scope below. Implementation, device validation and
publication are complete; CPU/docs/smoke CI passed at 2320e32.
Finish through the protected PR with a merge commit preserving evidence ancestry,
then synchronize main and remove only the merged task branch and disposable build
caches. Preserve all historical research artifacts, failed attempts, frozen source,
executables, images, raw endpoints, native dependencies and the canonical ledger.
Record a checksum inventory, merge/CI receipts and cleanup verification under
artifacts/gpup-state-integration-20261013. Bound this administrative task to 1200
CPU seconds/four jobs, 8 GiB RSS, 64 MiB new receipts and zero GPU jobs. Verify the
retained reports and unchanged 16452-event ledger after cleanup. No subsequent
numerical task or resource reservation is started by this handoff.

## PR 19 device validation and publication (2026-10-13)

Status: implementation, device experiments and final native acceptance complete;
publication in PR 19 is authorized and is the final delivery step.
The first frozen cohort was refused before child launch by external GPU activity;
retain its 3.002084480-second charge and all 41 unexecuted cells. The user then
explicitly requested another idle GPU if available. Discovery found idle sm_120
RTX PRO 6000 GPU-6721b13a-30f9-83ec-dace-ba2d9738556f; both 5090s were busy.
Run a separately frozen gpup-state-device-v2 cohort on that device, under the same
shared host lock. Its cap is 1096 seconds (496 acceptance/600 timing), so both
cohorts together remain below the original 1100/500/600 limits. Preserve the
16368-event prefix a97630527900a1a11cfd612bd3f96d55a86c211555bb0adc7de3ab52adebfc96
and 17638.434099818 cumulative seconds. Do not retry either cohort's identities.
V2's two ordinary device checks passed. Memcheck exited zero with an exact
endpoint and its zero-error summary in stdout; the verifier incorrectly read
only stderr. Repair receipt reading on CPU, preserve the original failed
classification, bind a reviewed classification and continuation source archive,
and resume only unattempted cells. No device/executable/input/protocol change or
GPU retry is authorized by this evidence repair.
Objective: validate the compact full-range FMA on the selected device, measure
bounded primitive behavior, and publish the review commits and revised PR scope.
Acceptance: exact independent corpus differentials at multiple block sizes,
fresh-process repeatability, four scoped sanitizers, instruction/resource audit,
frozen primitive timings with independent endpoints and complete cost accounting,
full pinned-native gate, evidence/ledger verification and PR checks. No merge.
Likely files: a safe Rust diagnostic example using optimizer-cuda-sys, separate
CUDA probe, bounded protocol/runner/report/tests, ADR-0036 and handoff documents.
Resources: 14400 CPU seconds/four jobs, 8 GiB host RSS, 64 MiB device allocation,
4 GiB new artifacts; at most 1100 GPU seconds, comprising 600 screening timing
and 500 repeatability acceptance, within the existing 2300/850 GPUP-STATE caps.
Frozen roster: two 30-second device checks, four 90-second sanitizer checks and
36 ten-second timing attempts; deadline+6 reservations total 1032 seconds.
Use only GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 under the shared host lease and
existing supervised ledger. Retain all failures without primary retries.
Preserve the 16366-event prefix SHA-256
4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b and inherited
17635.432015338 / 21602.574545061 GPU seconds. No added campaign/phase allowance.
Keep all prior evidence immutable; new receipts belong in
artifacts/gpup-state-device-v1. Full controller, solver timings, runtime selectors
and GPUP-REFINE remain outside this bounded extension. Push the completed changes
to codex/gpup-state and update PR 19 after acceptance; do not merge it.

## PR 19 numerical and experiment review (2026-10-13)

Status: review and targeted repairs complete; full pinned-native acceptance passed.
Objective: independently challenge the primitive arithmetic, oracle coverage,
resource evidence and conclusions of GPUP-STATE; reproduce and repair actionable
defects while preserving the frozen first construction and all historical evidence.
Acceptance: focused independent CPU regressions and compile-only checks where
needed, strict evidence re-verification, full pinned-native `bash tools/check.sh`,
and a final complete PR diff review with recorded findings and limitations.
Likely files: state admission/candidate/oracle/diagnostic tooling and tests, report,
accepted contract clarifications and this record. Resources: 7200 CPU seconds,
four build jobs, 8 GiB host RSS, 4 GiB new artifacts and zero GPU jobs.
Keep original artifacts/gpup-state-v1 immutable; new review receipts belong in
artifacts/gpup-state-pr-review-20261013. Preserve all 16366 ledger events, SHA-256
4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b and cumulative
17635.432015338 / 21602.574545061 GPU seconds. No controller or subsequent
GPUP task is admitted by this review. Commit accepted repairs locally; publication
and merge are outside this request.

Acceptance evidence: the original refusal is reproducible but does not establish
an unavoidable scalar resource obstacle. A separately contracted full-range FMA
uses compact alignment and an odd low bit for discarded tails, with a written
rounding proof. Both formats compile to 40 registers and zero stack/spills under
the original gate, versus the retained full-bin construction's 255 registers and
296/152 spill-store/load bytes. Both constructions match 5900 supplementary
Fraction cases each and the 270 historical FMA cases each. All 11800 supplementary
comparisons also pass host UBSan; the focused suite checks all 12340 comparisons
with UBSan. These are CPU/compile-only results, with no device/controller or
performance promotion. The original seed-17004 fixture and evidence stay exact.

Two reproduced verifier defects are repaired: uniform-predicated instructions
could bypass the FP64/call audit, and the frozen transcendental candidate was
never executed during archive verification. Every addressed instruction is now
parsed or refused, the complete file inventory is required, and all 48 archived
log/exp results are checked by executing the frozen candidate in isolated Python.
Corruption and isolated-archive tests pass; the original archive re-verifies.
The preliminary compact-v1 freeze omitted verifier-only import dependencies and
is retained. The self-contained compact-reviewed freeze retains the same kernels
and inputs and independently re-verifies in isolated Python. Its receipt hash is
79a1b572f6cf73906d3e1632f8833c368dba7365d9e6fb8760e5e8f2c9fe0d44;
the reviewed summary is docs/benchmarks/data/state/fma-review-v1.json.

All 21 focused tests and the full `CARGO_BUILD_JOBS=4 bash tools/check.sh` pass:
280 Python tests, Rust/native/dependency checks, committed-record replay,
127 documentation pages and smoke. Native coverage is enabled; no GPU workload
ran. The full gate used 125.078377860 elapsed / 152.458983 CPU seconds and
1663545344 bytes maximum child RSS. Logs, resource receipts and final ledger/
artifact audits remain in artifacts/gpup-state-pr-review-20261013. The unchanged
16366-event ledger has the exact hash and cumulative consumption above. All
current reports/handoffs distinguish the compact scalar pass from open full
state/controller gates. Final documentation/whitespace checks precede the local
review commit; no remote publication or merge is authorized by this review.

## GPUP-STATE draft PR preparation (2026-10-13)

Status: source preparation accepted; user authorized opening a separate draft PR.
Objective: publish the completed bounded admission-refusal result for review,
without waiting for GPUP-REFINE or starting another numerical task.
Acceptance: inspect the complete diff and remote base, preserve the frozen
construction and evidence identities, renew the full pinned-native gate before
publication, and verify the draft PR's base and head after creation.
Likely files: this record and documentation consistency corrections only.
Resources: 1800 CPU seconds, four build jobs, 8 GiB host RSS and zero GPU jobs.
The accepted implementation is dd93b82; its full pinned-native gate passes
272 Python tests, Rust/native/dependency checks, committed-record replay,
127 documentation pages and smoke. PR preparation corrects the stale wiki
handoff and makes the final test count explicit in the report. Gate and
publication receipts belong in artifacts/gpup-state-pr-20261013.
Preserve the 16366-event ledger and cumulative GPU consumption of
17635.432015338 / 21602.574545061 seconds. This request authorizes publishing
the task branch and creating a draft PR; it does not authorize merging or
starting GPUP-REFINE. Keep all historical artifacts and the source branch.

## GPUP-STATE (2026-10-13)

Status: complete as the user-authorized bounded resource admission refusal.
Objective: investigate persistent compensated and 64-significand-bit expansion
state with a full expansion controller, stable formulas, complete checkpoints and
independent original-model certification. Follow the user-accepted implementation
plan; a demonstrated numerical/resource admission refusal is a valid bounded result.
Acceptance: ADR-0036/SPEC-0020 subset; independent integer/rational primitive and
transcendental oracles; complete operation inventory and state/replay contracts;
checked layouts; full pinned-native gate. Only admitted device behavior proceeds
to instruction/register/spill audit, device differentials, four sanitizers and the
frozen 96-timing/12-profile development study. Preserve every failure and all costs.
Likely files: ADR/spec/report and admission tooling/tests first; research modules
in optimizer-lp, optimizer-lp-cuda and optimizer-experiment plus a separate CUDA
image/protocol only after CPU admission. Resources: CPU 21600 seconds, four build
jobs, 8 GiB host RSS, device resident/peak 1/2 GiB, new artifacts 32 GiB. The user
explicitly allocated 3600 GPU seconds within existing authority: timing 2300
screening, profiles 450 ablations, acceptance 850 repeatability. No increased
campaign or phase ceiling. Use GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 under the
shared host lease with deadline+6 reservation; no primary retries. Preserve
17635.432015338 / 21602.574545061 cumulative GPU seconds and all 16366 events,
ledger SHA-256 4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b.
Original-model host authority and every historical identity remain. Commit locally
after acceptance; do not push or start GPUP-REFINE. Retain evidence under
artifacts/gpup-state-v1 and reviewed summaries under docs/benchmarks/data/state.

Admission evidence: the independent seed-17004 fixture checks 192 integer
operations, 270 full-range FMA cases, 64 unprojected update graphs and 48 log/exp
cases. All 13 CPU admission regressions pass. The first direct exact-bin full-FMA
construction in both formats uses 255 registers, a 152-byte stack and 296/152
spill-store/load bytes, exceeding the 128-register/zero-spill gate. Bounded
integer/update probes fit at 62/76 registers with no spills; no full controller,
state/replay, runtime selector or 96-timing/12-profile study is admitted.
The verified construction's source SHA-256 is
ae7eedf7e53d2a6e5b5ec70333a7a1cd72146431dde9ca676f9e8236644eb3b7;
image SHA-256 is
14bdccf1e246b6966bafc4d33a3aa59925a50a567b643d31c58f1052e1781c8d.
All frozen CPU/source/image/resource files independently reverify. GPU charge
is zero and the exact ledger above remains. Alternative guard/sticky or explicit
scratch constructions are not proved impossible and retain separate gates.
Initial full pinned-native `CARGO_BUILD_JOBS=4 bash tools/check.sh` passes all Rust/native,
dependency and committed-record replay gates, 270 Python tests, 127 documentation
pages and smoke. GPU opt-in was unset and native acceptance was not skipped.
The measured gate took 128.209268496 elapsed seconds and 175.761509 CPU seconds;
maximum recorded child RSS was 1663467520 bytes.
The log/resource receipts are under artifacts/gpup-state-v1. The optional
/usr/bin/time launcher was absent; that failure is preserved and Python's standard
resource accounting was used without provisioning another dependency.
Documentation/acceptance completion is followed by a final exact-source native
gate and artifact/ledger audit before the local commit. The next task is
GPUP-REFINE under its own accepted contract/allocation; it is not started here.
Final CPU-only review rejects duplicate/boolean evidence fields before private
archive access and includes every probed kernel in the aggregate resource gate.
The frozen construction, image, numerical results and refusal are unchanged.
Both added source-only regressions pass; final source acceptance is retained in
artifacts/gpup-state-v1/native-reviewed.log and native-reviewed-resources.json.

## GPUP-EXEC PR 18 review and integration (2026-10-13)

Status: self-review, repairs and local acceptance complete; user authorized
protected merge after final GitHub checks. Integration/cleanup receipts are retained
under artifacts/gpup-exec-pr-review-20261013.
Objective: open the completed bounded executor as its own PR, reproduce and fix
any actionable review findings, and preserve useful raw evidence and recovery
references during safe cleanup. Merge the reviewed PR after required checks pass,
then verify main ancestry before removing the integrated task branch.
Acceptance: numerical, lifecycle and independent evidence review; focused
regressions for any defects; full pinned-native `bash tools/check.sh`; final diff,
GitHub checks and clean published branch; verified artifact inventory and recovery
bundle. Preserve the measured study and its negative result, including failures.
Likely files: executor runtime/tests/tooling and report if review requires changes,
plus this task record. Resources: two CPU-hours, four build jobs, zero GPU jobs and
no added allowance. Preserve cumulative 17635.432015338 / 21602.574545061 GPU
seconds and the 16366-event ledger SHA-256
4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b.
Keep artifacts/gpup-exec-v1, all historical evidence and unrelated worktrees.
Review receipts and recovery material belong in artifacts/gpup-exec-pr-review-20261013.
Do not start GPUP-STATE. Delete the task branch only after verified integration
and a checked source-recovery bundle; preserve unrelated worktrees.


Acceptance evidence: [PR 18](https://github.com/liuyumou/OptForge/pull/18) was opened
as a bounded GPUP-EXEC change. Self-review reproduced five missing acceptance
checks (image directory, attempt key, executable, selected device and regular-test
counts), rejection of complete recovered endpoints, and a recovered-reservation
promotion gap. Six CPU regression tests now cover these cases plus the closed
source-correction scope. No remaining actionable finding was identified within
the admitted cold-solve contract. All 166 measured Rust/CUDA files remain exact.

The full pinned-native gate passes 259 Python tests, Rust/native and dependency
checks, committed-record replay, 125 documentation pages and smoke. All 16 executor
tooling tests also pass in an isolated source copy with hash-checked input fixtures
and no campaign artifacts. The hardened independent report is byte-for-byte equal
to the completed report: all 108 attempts, 94 verified endpoints and 58/96 certified
timings remain, with all failures and negative results preserved. The retained
regular device log has 14 driver + 6 scheduling + 46 LP tests; the earlier prose
count of 58 is corrected to 66. No new GPU work ran; the complete ledger and its
historical prefix retain the hashes and consumption above.

Every one of the 1153 original artifact references verifies. A compressed recovery
copy preserves 1198 files / 360328297 uncompressed bytes, including the original
source archives, executables, images, endpoints, failures, logs, ledgers and reviewed
summaries. Its 80793840-byte archive has SHA-256
c807b6ac2074d5377d86408b164c38991f9b813613d6d21be68cb979229823e3.
The original bfe88c3 source bundle is verified; final source, CI, merge ancestry and
owned-scratch cleanup receipts are kept beside it. Original raw artifacts and
unrelated worktrees remain in place. The user explicitly approved finishing these
repository commands outside the sandbox after automatic approval review timed out;
the ordinary sandbox could not create a process namespace.

## GPUP-EXEC (2026-10-13)

Status: complete; bounded implementation, device acceptance, frozen study and
final pinned-native acceptance passed.
Objective: an isolated binary64 exact-dot CUDA executor with cached/uncached
vector decoding, FP64 solver state and original-model host certification.
Acceptance: independent integer/Fraction CPU oracle; range, transpose, cache,
memory and failure contracts; generated-instruction/register/spill inventory;
full pinned-native gate; regular device/differential/replay/four sanitizer gates;
96 frozen fresh timing attempts and 12 fixed-work profiles; independently verified
endpoints, retained refusals/timeouts and total-cost report. No supported preset.
Likely files: ADR-0035/SPEC-0020, research modules in optimizer-lp/lp-cuda/experiment,
a separate CUDA image, bounded study protocol/schema/tools/tests and handoff docs.
Resources: CPU 21600 seconds, four jobs, 8 GiB host RSS; operator resident/peak
1/2 GiB, 32 GiB new artifacts. GPU task cap 3600 seconds: timing 2300 screening,
profile 450 ablations, acceptance 850 repeatability. User explicitly authorized
cumulative ceiling 21602.574545061 seconds and phase ceilings screening 9500,
ablations 7650, repeatability 4450; baseline 1800/finalists 9000 and total 28800
remain. Every GPU job requires the shared host lease and deadline+6 reservation.
Preserve prior 17115.274617853 seconds and the 16134-event prefix SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823.
Use GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48. Commit locally after acceptance;
preserve all existing artifacts and unrelated worktrees. Next GPUP-STATE only
when this task's gates pass. The retained first oracle gate passed its then-two
device tests and charged 0.774594710 seconds. The resumed three-test suite and
all subsequent device gates passed. The resume point was 16136 events and cumulative
17116.049212563 seconds, ledger SHA-256
7cc4544de557c68daa72fc44837627222d6ea27e11ea83d85e653428d6271d93.
Keep that attempt and every earlier ledger byte; do not retry its identity.

Acceptance evidence: [ADR-0035](../docs/decisions/ADR-0035-bounded-exact-executor.md)
and the bounded SPEC-0020 subset implement exact binary64 sparse products with
cached/uncached vector decoding, FP64 state and original-model host authority.
The [report](../docs/benchmarks/lp-exact-executor-gpup-exec.md) retains all 108
attempts, independently verifies 94 endpoints and certifies 58/96 timings. All
27 cached/uncached timing/profile pairs match bitwise. Eighteen exact timings
refuse the exponent window; six mixed FP64 controls time out. Fourteen initial
controls failed discovery because the frozen archive omitted schedule_eval.cubin;
the unchanged dependency was restored with a receipt, without retrying identities.
No fresh-solve improvement over tuned FP64 or supported preset is selected.

The 2347-case independent Fraction fixture reproduces byte-for-byte. Full
pre-device native acceptance passes 250 Python contracts and all Rust/native,
dependency, committed-record, documentation and smoke checks. The device oracle
checks 2346 shape-admitted cases in both cache modes. All 66 regular device tests,
three new device tests, three fixed-work cache pairs, six same-device replays and
four scoped sanitizers pass. Decode/sparse paths use 14/39 registers, zero spills
and no native FP64 arithmetic. Measured source SHA-256 is
03df0db2362dee7284deb7d10d08dda60b36eb14607164f71a3ab1e818c1350e;
image SHA-256 is
ec3c6c03387c742ccac83742d905616f6ca4160026e00c4c8dfc36c2eb21a0c6.

CPU-only review repairs require the discovery image before future freezes,
classify nonzero child exits, reject malformed budgets without private artifacts,
and bind complete acceptance identities. All ten final source-only contracts
pass in an isolated source copy. The hardened independent report re-verifies all
six acceptance endpoints and six replays; every original report result/statistic
is unchanged. Measured runtime/CUDA sources, executables, numerical settings and
primary receipts remain unchanged. Logs and raw archives are under
artifacts/gpup-exec-v1; reviewed summaries and hashes are under
docs/benchmarks/data/exec. Historical gaps stay open; GPUP-STATE is not started.
Final `CARGO_BUILD_JOBS=4 bash tools/check.sh` passes 253 Python tests, all
Rust/native/dependency gates, committed-record replay, 125 documentation pages
and smoke. Log: artifacts/gpup-exec-v1/native-final.log. The final artifact audit
checks all 1153 exported references and the exact historical ledger prefix.
Maximum sampled worker RSS is 1178767360 bytes; cataloged artifacts total
359546004 bytes, within the 8 GiB / 32 GiB limits. Final documentation links and
new-file whitespace checks pass. Commit locally after this acceptance record.

Task GPU charge is 520.157397485 seconds: timing 431.684266725/2300, profiles
36.003675982/450 and acceptance 52.469454778/850. Cumulative consumption is
17635.432015338 / 21602.574545061 seconds. The complete 16366-event ledger
SHA-256 is 4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b,
with the 16134-event prefix above intact and every task/phase cap enforced.

## PR 17 review and integration (2026-10-13)

Status: review and repairs complete; protected merge and safe cleanup receipts
are retained under artifacts/pr17-review-20261013.
Objective: review GPUP-REP and the unmerged design prerequisites needed to land it
on main, repair actionable defects, preserve useful artifacts and results, and
integrate only after the required checks pass. Preserve the newer main-branch
convergence-review fixes and all historical evidence.
Acceptance: independent numerical and malformed-input regressions, reproducible
oracle/design fixtures, full pinned-native `bash tools/check.sh`, final diff and
GitHub checks, verified merge ancestry, and recoverable branch/artifact cleanup.
Likely files: expansion candidate/oracle/tests, their accepted contract/report,
design documents where review requires corrections, and this task record.
Resources: at most two CPU-hours, four build jobs, zero GPU workloads and no new
allowance. Preserve the 16134-event ledger SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823 and cumulative
17115.274617853 / 18002.574545061 GPU seconds. Do not start GPUP-EXEC.
Keep existing ignored artifacts and unrelated worktrees; retain review logs and
source-recovery references before deleting any integrated task branch.

Acceptance evidence: self-review reproduced shared 2-norm/square-root overflow,
noncanonical underflowed zero, FMA zero-sign loss, permissive malformed codecs,
nonfinite projection acceptance, stale operator/vector receipts and late resource
admission. Thirteen added regression tests cover these defects and exhaustive
small-format rounding boundaries independently of both arithmetic models. All
24 expansion tests pass, including byte-identical original fixture reproduction.
The 57429-pattern design artifact also reproduces without changes.

The full pinned-native `CARGO_BUILD_JOBS=4 bash tools/check.sh` gate passes:
243 Python tests, all Rust/native gates, dependency policy, committed-record replay,
123 documentation pages and smoke. AI_OPTIMIZER_GPU was unset; no project GPU job
ran. The ledger retains exactly the preserved 16134 events and SHA-256 above.
Logs, original native receipt, original implementation/design acceptance logs,
failing regressions and frozen-artifact hashes are in the review directory.

The sole open PR was stacked on an unmerged design branch. PR 17 includes the
reviewed research/design prerequisites when retargeted to main. Current main was
merged into the published PR branch to preserve shared history and its convergence
acceptance-binding repairs; both task histories survive the conflict resolution.
No runtime, CUDA, schema, benchmark input, dependency or historical result differs
from current main. Final GitHub checks, merge identity, verified source bundle and
ancestry-checked branch cleanup are recorded in the review directory before ending
this task. Existing artifact directories and unrelated worktrees remain intact.

## GPUP-REP (2026-10-12)

Status: complete; CPU-only contract, proof, oracle and layout validation accepted.
Objective: validate and accept a bounded SPEC-0020 subset for exact binary64 input
storage, correctly rounded binary64 reference primitives and separately identified
64-significand-bit expansion primitives. Cover conversion, arithmetic, reductions,
norms, comparisons and projection without changing solver behavior.
Acceptance: independent integer and exact-rational oracles; reproducible fixtures;
codec canonicality, range/rounding/error proofs and actual layout/peak-memory
analysis; fault/refusal tests; accepted ADR/spec subset; full pinned-native
`bash tools/check.sh` gate.
Likely files: SPEC-0020 and a new ADR/report, CPU tools and integration tests,
reproducible fixture, backlog/status/known-failures/changelog and this task record.
Resources: one CPU-hour, four build jobs, 2 GiB validator RSS, zero GPU workloads
and no new GPU allowance. Shape analysis is bounded to 65536 rows/columns and
2^23 nonzeros, with 1 GiB resident and 2 GiB peak admission limits. Preserve all
16134 ledger events, SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823, and cumulative
17115.274617853 / 18002.574545061 GPU seconds. Existing runtime, certification
authority, identities, defaults, benchmark inputs and historical evidence remain
unchanged. Commit locally after acceptance; do not push or start GPUP-EXEC.

Acceptance evidence: [ADR-0034](../docs/decisions/ADR-0034-lp-expansion-cpu-contract.md)
and the bounded accepted [SPEC-0020](../docs/specifications/SPEC-0020-lp-expansion-arithmetic.md)
subset define the exact input codec, direct binary64 and 64-significand-bit
24/24/16 expansion reference semantics, primitive errors/exceptions and bounded
preparation interfaces. The [report](../docs/benchmarks/lp-expansion-gpup-rep.md)
records proofs, layouts and limitations. No runtime or device behavior changed.

The seed-17004 independent fixture contains 32852 codec cases, 1058 primitives,
40 reductions, 40 comparisons and 80 projections; the integer-only candidate
agrees throughout. It covers all binary64 exponents/signs, every q in [-8,8],
ties, carries, gradual underflow, overflow-safe FMA, division/sqrt, cancellation
and 65536-term reductions. Fixture SHA-256 is
0a7203554c7f15ccded04d5cac00504119851611205c4566969468848bd08760. Eleven
integration tests cover corrupt/understated evidence, malformed tuples, explicit
exceptions, cancellation, canonical transpose, dimensions, stale generations,
aliasing and memory refusal. At 65536 by 65536 and 2^23 nonzeros, resident/peak
receipts are 295960592/532414480 bytes under the 1/2 GiB caps.

The earlier 57429-pattern design artifact reproduces. Full pinned-native
`bash tools/check.sh` passed with four build jobs and GPU opt-in unset: Rust gates,
dependency policy, all 228 Python tests, committed-record replay, 123 documentation
pages and smoke. Final log: `/tmp/ai-optimizer-gpup-rep-check.log`. Final docs
and whitespace checks pass. The preserved ledger still has 16134 events and SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823; GPU use
remains 17115.274617853 / 18002.574545061 seconds. Next: GPUP-EXEC under its own
active task, accepted subset and device reservation; it is not started here.

## Precision architecture and experiment redesign (2026-10-12)

Status: complete; user-requested design/documentation and CPU mathematical artifacts only.
Objective: turn the first-principles review into component designs, mathematical
obligations, a dependency-ordered roadmap and experiments that distinguish exact
storage, arithmetic accuracy, algorithmic convergence and certified total cost.
Include compact mixed-format expansions, integer decoding, persistent expansion
state, refinement/anchoring, selective precision, stable formulas, executor and
assessment costs, and conditional alternative solver/Tensor Core directions.
Acceptance: trace each proposal to motivation/evidence, state unproved assumptions
and rejection gates, reconcile specs/backlog/navigation, preserve historical
contracts and artifacts, and pass the full pinned-native tools/check.sh gate.
Likely files: new design/specification/decision/experiment documents, roadmap,
candidate register, backlog, known failures, status, README, AGENTS and changelog.
Resources: at most one CPU-hour, four build jobs, zero GPU workloads; no new GPU
allowance, runtime implementation, dependency provisioning, push or publication.
Preserve cumulative 17115.274617853 / 18002.574545061 GPU seconds and the
16134-event ledger SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823.
New numerical contracts remain proposed until their bounded acceptance gates;
this task may revise future planning order, as requested, but authorizes no new
solver behavior, measurement, preset, seed, tolerance or benchmark split.

Acceptance evidence: [ADR-0033](../docs/decisions/ADR-0033-lp-precision-design-order.md)
records planning-only priority. The [architecture](../docs/plans/lp-precision-architecture-2026-10-12.md)
maps measured failure mechanisms to component motivations and rejection gates;
draft SPEC-0020 gives the normalized exact-tail proof, integer decoding, layouts,
primitive/kernel construction and range/error obligations; draft SPEC-0021 derives
the general equality/activity-variable correction, dual scaling and anchored-error
identities. The [experiment design](../docs/benchmarks/lp-precision-design-experiments.md)
separates component effects, small factorial interactions, full costs, coverage and
frozen held-out selection. Existing SPEC-0012/0013 requirements remain unchanged;
only navigation/current study metadata is updated there. Roadmap, candidate
register, backlog, README, status, AGENTS and limitations are reconciled.

CPU evidence: tools/check_lp_precision_design.py writes and byte-for-byte reproduces
[data/lp-precision-design-examples.json](../docs/plans/data/lp-precision-design-examples.json).
All 57429 finite patterns round-trip, covering every normal exponent and both
signs plus subnormal/tie/carry samples; all 17 integer tails are exercised.
Fifty rational correction/dual-scale cases and 353 proximal cases pass, with
anchored/residual/gap identities, actual ABI sizes and preserved counterexamples.
This finite sample supports the written derivations; it is not production
primitive, convergence or device acceptance. Artifact SHA-256:
bde0c7bb271a888403179c4a8ee2bf5b29da713fba45b41ed2a3a6a90e020e5c.

Full pinned-native tools/check.sh passed with four build jobs and GPU opt-in unset:
Rust formatting/clippy/build/tests/docs, dependency policy, all 217 Python tests,
committed-record replay, 121 documentation pages and smoke. The log is
/tmp/ai-optimizer-precision-design-check.log; target/lp-native-gate.json was written.
Device tests were not enabled and no GPU workload/sanitizer was run. Final prose
and task-state updates pass the documentation/whitespace check. The backlog
has 40 unique tasks, no dependency cycle and dependency-ready GPUP-REP.
The actual campaign ledger still has 16134 events and exactly the preserved hash
above; tracked runtime, kernels, schemas, benchmark inputs and historical reports/
data remain unchanged. No implementation, measurement campaign, preset, new GPU
allowance or external publication. Next: GPUP-REP CPU validation/acceptance of a
bounded draft subset, with its own active task before work. Commit locally after
these gates; do not start that next task as part of this design request.

## Persist low-precision research analysis (2026-09-30)

Status: complete; documentation only, explicitly requested by the user.
Objective: save the complete preceding evidence review and research proposals in
repository documentation so later sessions can discover and evaluate them.
Acceptance: preserve measured-versus-proposed distinctions, equations and numerical
caveats, primary sources, hardware applicability, experiment order and rejection
gates; link from the roadmap, candidate register and session entry points; full
pinned-native tools/check.sh and documentation/link validation.
Likely files: docs/plans/lp-low-precision-research-2026-09-30.md, precision roadmap
and candidate register, AGENTS.md, wiki/status.md and this task record.
Resources: at most one CPU-hour, four build jobs, zero GPU workloads and no new
allowance. Preserve runtime, accepted contracts, backlog order and all evidence.
Campaign remains 17115.274617853 / 18002.574545061 GPU seconds; preserve the
16134-event ledger SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823.
GPUP-7's accepted quantization/resource contract remains the implementation handoff.
Commit documentation locally after acceptance; no push or publication.

Acceptance evidence: the complete
[research note](../docs/plans/lp-low-precision-research-2026-09-30.md) records the
measured failure mechanisms, all six primary proposals and supporting/speculative
ideas, correction-LP and anchored-error equations, hardware/source qualifications,
range/conditioning/authority caveats, falsifiable experiment sequence and resource
handoff. AGENTS.md, wiki/status.md, roadmap and candidate register link to it.
The register distinguishes completed investigations from unimplemented hypotheses.
Independent numerical and hardware reviews found no blocking issues; minor scale,
conservative-bound and cuOpt-mode clarifications were applied.
Full pinned-native `bash tools/check.sh` passed: native/Rust gates, 217 Python
tests, committed-record replay, 116 documentation pages and smoke. Log:
`/tmp/ai-optimizer-low-precision-notes-check.log`. Final documentation links and
whitespace checks pass. No GPU workload or runtime change; all campaign evidence,
accepted contracts, defaults and backlog order remain unchanged.

## Low-precision performance research review (2026-09-30)

Status: complete; user-requested research and recommendations only.
Objective: reconcile the completed LP studies with hardware documentation and
numerical-method literature; propose bounded routes to faster FP32/FP16/FP8
computation at the unchanged original-model 1e-9 acceptance criteria.
Acceptance: trace findings to repository evidence and primary external sources;
distinguish measured results from hypotheses, explain sm_120 applicability and
failure conditions, and prioritize falsifiable follow-up experiments.
Likely files: this task record only; recommendations are delivered in chat.
Resources: at most one CPU-hour for research and required CPU/native validation,
with at most four build jobs; zero GPU jobs or new campaign allowance.
No runtime, accepted-contract, backlog or ledger changes.
Preserve cumulative 17115.274617853 / 18002.574545061 GPU seconds and the
16134-event ledger SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823.
GPUP-7's accepted quantization/resource contract remains the next implementation
prerequisite; this review does not accept or implement new numerical behavior.

Acceptance evidence: reviewed the roadmap, candidate register, rounding analysis,
FP64-pipe/GPUP-5C reports, adaptive host-cost report and latest convergence study.
Cross-checked NVIDIA RTX Blackwell, PTX/CUTLASS and cuBLAS documentation, LP
iterative refinement (Gleixner/Steffy/Wolter), mixed-precision linear-system
refinement (Haidar et al.) and Ozaki-II primary sources. Recommendations delivered
in chat distinguish established techniques, repository measurements and proposed
adaptations: scaled correction LPs with anchored products; a lean precision
executor; scaled double-float; selective operator-error budgets; active-face
polishing; and layout-appropriate Tensor Core/integer emulation. End-to-end
Amdahl limits and failed-convergence costs govern the proposed experiment order.
No new performance result or accepted numerical behavior is claimed.
Full pinned-native `bash tools/check.sh` passed: native/Rust gates, 217 Python
tests, committed-record replay, 115 documentation pages and smoke. Log:
`/tmp/ai-optimizer-low-precision-review-check.log`. No GPU workload ran.
Only this task record changed; recommendations do not reorder the backlog.

## GPUP-CONVERGENCE PR integration (2026-09-30)

Status: implementing the user's explicit authorization to publish a PR, self-review,
fix substantiated problems, merge through required checks and clean up safely.
Objective: integrate the completed bounded diagnosis and verified evidence without
changing measured workers, numerical behavior, runtime defaults or campaign history.
Acceptance: labeled self-review; full pinned-native tools/check.sh; source-only and
artifact/provenance checks; current-head GitHub CPU/docs/smoke success, resolved
conversations and merge without policy bypass. Preserve the separate research-docs
branch at 62516e8cef59104442fa359a2e2440af8a59f033 and restore its checkout afterward.
Likely files: this task record and substantiated review corrections only.
Resources: four build jobs, at most one additional CPU-hour for integration checks,
zero GPU jobs and no new allowance. Preserve cumulative 17115.274617853 /
18002.574545061 GPU seconds and the 16134-event ledger SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823.
Starting source: ce72e80572fdd9eea88a33d31d5c92299903b9c5. This authorization
supersedes the implementation-phase no-push scope below for this branch only.
Keep integration receipts under artifacts/gpup-convergence-integration-20260930.

Local self-review reproduced acceptance-label substitution with unchanged, valid
retained endpoints. The independent report now binds claimed model/configuration,
work limits, profile flags, code images, COPT parameters/dependencies and exact
min/max offset-seven models, and rechecks state/work equality. Measured workers,
schemas, protocols, endpoints and ledger bytes are unchanged. Twelve source-only
contracts pass in an artifact-free copy; the full pinned-native gate passes
514 Rust tests, 219 Python tests, record replay, 115 documentation pages and smoke.
The original PR head passes required GitHub CPU/docs/smoke checks. Independent
report re-verification and current-head remote checks must pass before merging.
Self-review is explicitly labeled; no independent approval is claimed. Final
verification, merge and safe-cleanup receipts are retained in the integration
directory above; no additional GPU execution is authorized or needed.

## GPUP-CONVERGENCE (2026-09-30)

Status: complete; bounded study, independent verification and all required gates pass.
ADR-0032/protocol were frozen before GPU execution. Local commit follows.
Objective: diagnose fresh-solve convergence/work amplification after host repairs,
including fresh scalar COPT CPU/GPU PDLP controls, with unchanged runtime arithmetic,
kernels, settings, defaults and historical evidence. Freeze 176 study attempts.
Acceptance: full pinned-native tools/check.sh before GPU admission and at completion;
source-only schedule/provenance/accounting/recovery tests, regular device gate,
twelve project fixed-work profile pairs and replays, COPT min/max/profile checks,
independent endpoint verification, reproducible report/exports and preserved ledger.
Likely files: dedicated convergence tools, study/trial schemas, protocol, ADR-0032,
benchmark report/data/figures and task/status documentation. Runtime changes excluded.
Resources: four build jobs; 14400 CPU seconds; timing 800 GPU seconds (ablations),
profiles 800 and acceptance 300 (repeatability); combined 1900, no borrowing or
additional allowance. Preserve 15776 events and SHA-256
2b99b615dc77da07fb078e1cefc188d2131db5ca671fe9b86f989a6d660606f0;
15804.186067059 / 18002.574545061 cumulative GPU seconds and every phase cap.
Every GPU job uses the shared host lease and complete reservations. Retain failures,
partial artifacts and interruptions; never retry an admitted study identity.
Starting revision: c10d212. Commit locally after acceptance; no push/publication.
Handoff after completion: GPUP-7 contract work, without implementing GPUP-7.

Acceptance evidence (2026-09-30):

GPUP-CONVERGENCE is complete under accepted ADR-0032/SPEC-0013. Its
[report](../docs/benchmarks/lp-convergence.md) retains all 176 frozen attempts,
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
Next is GPUP-7's accepted quantization/FP8 interface and resource contract,
before any new numerical behavior.

Final full pinned-native gate passes 217 Python tests, native Rust/exact-rational
regressions, committed-record replay, documentation and smoke. Source-only review
reproductions and exact measured/reviewed hashes are retained. The resource catalog
records metered child CPU within 14400 seconds and four build jobs. Existing scoped
sanitizer receipts carry forward because runtime/kernel bytes are unchanged.

## GPUP-COPT-ADAPTER protected integration (2026-09-30)

Status: user authorized PR publication, self-review, protected merge and safe
branch cleanup. This supersedes the implementation-phase no-push scope below.
Objective: review the isolated study and its evidence, retain the faster existing
scalar COPT wrapper as the ordinary COPT construction path, and leave runtime
solver defaults unchanged. The bulk adapter stays explicitly experimental.
Acceptance: full pinned-native gate, current-head GitHub cpu/docs/smoke checks,
resolved conversations, merge preserving source ancestry without bypass, and
clean synchronized main. Self-review is labeled; no independent approval is claimed.
Likely files: this task state and any substantiated review corrections.
Resources: four build jobs, at most one CPU-hour for integration validation,
zero GPU jobs and no new campaign allowance. Preserve every study artifact and
the 15776-event ledger SHA-256
2b99b615dc77da07fb078e1cefc188d2131db5ca671fe9b86f989a6d660606f0;
cumulative consumption remains 15804.186067059 / 18002.574545061 GPU seconds.
Starting source: 5c77323. Integration receipts will be retained under
artifacts/gpup-copt-adapter-integration-20260930. GPUP-CONVERGENCE is not started.

Local self-review and CPU acceptance pass. The reproduced interruption defect and
fix are covered by partial-output, surviving-receipt, conservative-charge and
no-promotion regressions. All eleven adapter tests pass in a clean source-only
checkout. The full pinned-native gate passes 514 Rust tests, 207 Python tests,
committed-record replay, 113 documentation pages and smoke. No checks were waived.
The source audit binds three declared CPU coordinator/report/export corrections,
359 unchanged measured files and 382 unchanged historical authority files. All
1159 archived artifact references match. Both solver workers, CSC builder, native
binaries, schemas, protocol and measured endpoints remain byte-identical; the
ordinary scalar COPT path and runtime solver defaults remain unchanged.
Independent report re-verification and current-head remote checks must pass before
merging. Their outcomes, self-review, protected merge and cleanup receipts are
retained in the integration directory above. No additional GPU execution is needed.

## GPUP-COPT-ADAPTER (2026-09-29)

Status: complete; implementation, device acceptance, frozen study, independent
report and final full native gate pass under SPEC-0019/ADR-0031. Local commit follows.
Objective: a separately identified COPT bulk matrix adapter, exact import/readback
and fresh independent certification; compare three methods against fresh scalar
controls in one new isolated environment. Archive baseline 8fdec89451c07ffea46a3d8630aa184b14e072c5.
Acceptance: full pinned-native gate before GPU admission and at completion;
dependency-free contracts, real CPU readback, 24 min/max/profile endpoints,
72 timings and 12 profiles with independent verification and strict provenance.
Likely files: new Python study/provisioning/acceptance/report tools, schemas,
protocol, tests, contract and evidence/state documents. No runtime or kernel edits.
Resources: four build jobs, four CPU-hours; timing 900 GPU seconds in ablations,
profiles 200 and acceptance 400 in repeatability, combined 1500; no added allowance.
All device jobs require the shared host lease and full reservations. Preserve
15606 ledger events, SHA-256 ad3d84354f0b74ae62fcc019ee4dcbf29b0a3251d066f1e0f2df11ccb107230b,
and 15632.281207415 / 18002.574545061 cumulative GPU seconds and all phase caps.
Retain every failed attempt, never retry admitted study identities. Commit locally
after acceptance; no push. Handoff: GPUP-CONVERGENCE without starting it.

Acceptance evidence: [report](../docs/benchmarks/lp-copt-adapter.md). All 84 attempts
independently verify; 42/72 timings and 10/12 profiles certify. Twelve native
readbacks and all 24 min/max/profile acceptance endpoints pass with both
certifiers. All 27 completed timing pairs match; nine interrupted CPU-default
pairs differ in native work. Ten profiles match timing state/work; the two
CPU-default interruptions differ. Bulk is slower in every certified cell, with
CSC preparation and cold SciPy import exceeding native loading savings.
Full pre-study native gate passes 514 Rust/205 Python tests, record replay,
112 documentation pages and smoke; source-only new contracts also pass.
Initial CPU schema/readback failures are retained and corrected. No failed GPU
acceptance or retried study identity. No runtime/kernel/default change or preset.
Task charge 171.904859644 GPU seconds (timing 142.395630328/900, profiles
22.026636414/200, acceptance 7.482592902/400), cumulative
15804.186067059 / 18002.574545061. The 15776-event ledger SHA-256
2b99b615dc77da07fb078e1cefc188d2131db5ca671fe9b86f989a6d660606f0 preserves the
15606-event prefix above and all phase caps. Evidence remains under the
gpup-copt-adapter baseline, acceptance, environment and v1 artifact directories.

Final full pinned-native tools/check.sh passes 514 Rust tests, 205 Python tests,
committed-record replay, 113 documentation pages and smoke. The source audit
checks 362 measured files and preserves all 382 historical code/authority files.
Metered child CPU remains within 14400 seconds; the final resource catalog records
the exact total and each receipt. No new GPU job is needed after acceptance.
Local commit only; GPUP-CONVERGENCE is the next handoff and is not begun.

## GPUP-SETUP protected integration (2026-09-29)

Status: user authorized PR publication, self-review, fixes, protected merge and
safe branch cleanup. The current instruction supersedes the implementation-phase
no-push scope below. Review the completed runtime, evidence and study tooling,
fix any findings, pass full pinned-native validation and current-head cpu/docs/smoke
checks, resolve all conversations, merge preserving source ancestry, and synchronize
local main. No release or subsequent research task is included.
Resources: four build jobs, at most one CPU-hour for integration validation,
zero GPU jobs and no new campaign allowance. Preserve all archived artifacts and
the 15606-event ledger SHA-256
ad3d84354f0b74ae62fcc019ee4dcbf29b0a3251d066f1e0f2df11ccb107230b; cumulative consumption
remains 15632.281207415 / 18002.574545061 GPU seconds. Initial source head:
62c625f81892004b2cb0aa90fb2bf8f84c4b771c. Likely changes: this state and any review
corrections. Self-review is explicitly labeled; no independent approval is claimed.
Final review, checks, merge and cleanup receipts are retained under
artifacts/gpup-setup-integration-20260929.

PR #14 is open. Self-review found and fixed two validation gaps: setup replay
accepted a missing required nullable error field or more than 4096 events; the
report verifier checked artifact hashes without binding filenames to their attempt.
Retained failing regressions reproduce both defects, and the corrected tests pass.
The CPU-only parser/report corrections are declared with old/new hashes in
setup-review-corrections.json. All 488 historical artifact references, 340 unchanged
measured files and 190 historical authority files verify. All 56 retained setup
receipts pass the corrected parser on CPU. Archived timings, binaries and the ledger
are unchanged. The final full pinned-native gate passes 514 Rust tests, 196 Python
integration tests, committed-record replay, 110 documentation pages and smoke.
Independent report re-verification and current-head remote checks precede merging;
their outcomes and final merge/cleanup receipts are retained in the integration
artifact directory above. No further runtime change or GPU execution is required.

## GPUP-SETUP (2026-09-29)

Status: complete; implementation, device acceptance, bounded study and final native
gate pass. Diagnosed fresh discovery, driver,
context/module and teardown costs before testing one experimental primary-context
lifecycle. SPEC-0018 and ADR-0030 record the contract before runtime edits.
Baseline 9bf8e8d5d6f6e4fd3b2eb60ae494506ed620323e is archived in
artifacts/gpup-setup-baseline. Changes: CUDA boundary and safe study plumbing,
opt-in cost scopes, strict setup study/schema/budget/replay/report tooling and tests.
Acceptance: full pinned-native tools/check.sh, lifecycle fault tests, regular device
gates, four primary-context sanitizers, twelve fixed-work pairs and twelve replays,
and independently verified 24 timings plus eight profiles. Four user-context profiles
must precede primary-context implementation. Negative results are complete evidence.
Resources: four build jobs, four CPU-hours; timing 900 GPU seconds in ablations,
profiles 300 and acceptance 600 in repeatability, combined 1800; no new allowance.
Preserve cumulative 15407.672759957 / 18002.574545061 GPU seconds and all phase caps,
15528 events and prefix cb0dc57f9f92546f4cc2d93b0de3c8556d6b24517f71b7a6efaa91fa96afedb6.
All GPU jobs use the shared lease and full reservations; retain every failure and
never retry attempted study identities. Record evidence and commit locally after
acceptance; no push. Handoff: optional GPUP-COPT-ADAPTER, without beginning it.

Acceptance evidence: [report](../docs/benchmarks/lp-fresh-setup.md), strict protocol,
three source/binary archives and hash-bound repository data. All 32 attempts verify,
24 timings certify and all 16 numerical/work pairs match. Control attribution was
completed before the primary implementation; no consistent latency benefit follows.
Full native pre-study gate passes 514 Rust and 195 Python tests; 58 candidate device
tests and all four primary-context sanitizers pass. Twelve fixed-work pairs and
setup-bound replays match, with both binaries verifying all 36 acceptance endpoints.
The source-only synthetic-budget tests pass without campaign artifacts. No GPU
attempt failed or was retried. The initial test-order lint receipt is retained.
The audit preserves 342 measured and 190 historical authority files. Task charge
224.608447458 GPU seconds: timing 47.100554150/900,
profiles 15.598178240/300, acceptance 161.909715068/600.
Cumulative 15632.281207415 / 18002.574545061 seconds; 15606 ledger events,
SHA-256 ad3d84354f0b74ae62fcc019ee4dcbf29b0a3251d066f1e0f2df11ccb107230b; the 15528-event prefix and
all phase caps remain intact. Final full pinned-native tools/check.sh passes 514 Rust
tests, 195 Python integration tests, committed-record replay, 110 documentation
pages and smoke. Metered child CPU totals 2085.569504 seconds within four hours;
small source-edit/catalog actions are outside that meter. Final source/ledger audits
and all 488 artifact references pass. Local commit follows. No push; optional
GPUP-COPT-ADAPTER is the next handoff and is not begun.

## GPUP-ADAPTIVE-COST protected integration (2026-09-29)

Status: user authorized PR publication, self-review and protected merge after checks.
Objective: review the completed slice and evidence, address any findings, publish
its PR, require current-head cpu/docs/smoke checks and resolved conversations,
merge without bypass while preserving source ancestry, and synchronize local main.
The latest user authorization supersedes the implementation-phase no-push scope
below. No release, additional experiment or GPUP-SETUP work is included.
Acceptance: existing full pinned-native/device/sanitizer receipts, independent
source and provenance review, required remote checks, protected merge, and clean
synchronized main. Likely files: this task state and any review corrections.
Resources: four build jobs, at most one CPU-hour for integration validation,
zero GPU jobs and no new campaign allowance. Preserve all artifacts and the
15528-event ledger SHA-256
cb0dc57f9f92546f4cc2d93b0de3c8556d6b24517f71b7a6efaa91fa96afedb6;
cumulative consumption remains 15407.672759957 / 18002.574545061 GPU seconds.
Initial source head: 400d575a4bc0bc2f80fa9b1b76c9d199cc404eed; current main:
5b9a9d083b27547e8bcb3ee4c9d265dde1a40bbb. Final review/check/merge outcomes
are retained in artifacts/gpup-adaptive-cost-integration-20260929/integration.json
and sibling receipts. Self-review is explicitly labeled; no independent human
approval is claimed or required by the current branch rules.

Integration preflight: self-review found no blocking issue in runtime, tests,
frozen study, strict identity/accounting tools or report claims. All 468 artifact
references and the complete ledger/prefix match their recorded hashes; measured
runtime, tooling, schemas and protocol match the archived source. The small-4
direct slowdown and historical coverage gaps remain explicit. The fresh full
pinned-native gate passes 505 Rust tests, 187 Python tests, committed-record replay,
107 documentation pages and smoke. GitHub requires current-head cpu/docs/smoke
and resolved conversations; no protection bypass or independent approval is claimed.
Only integration state changed after the implementation commit. Remote check,
self-review comment and merge receipts will be retained in the directory above.

## GPUP-ADAPTIVE-COST (2026-09-29)

Status: complete; implementation, bounded study and final repository gate passed.
Objective: share adaptive operators by matrix width, stream original-unit audits,
and borrow probe state when working-state narrowing is not needed. Preserve all
arithmetic, guards, recovery and physical-work accounting. User accepted the full
plan before implementation; SPEC-0017 and ADR-0029 record it.
Acceptance: full pinned-native tools/check.sh; all-ladder/legacy host differentials;
strict study provenance and clean-checkout synthetic budgets; regular device tests,
four adaptive sanitizers, twelve 200-update old/new pairs and twelve replays;
24 fresh timings and eight profiles independently verified by both executables.
Baseline: 5b9a9d083b27547e8bcb3ee4c9d265dde1a40bbb, archived before runtime edits.
Likely files: host adaptive runtime/tests, separate study/schema/budget/report
and acceptance tooling, specification/decision and state documentation.
Resources: four build jobs, four CPU-hours; timing 1000 GPU seconds in ablations,
profiles 300 and acceptance 500 in repeatability, combined 1800. No added allowance.
All GPU work requires the shared host lease and full conservative reservations.
Preserve 15452 ledger events, SHA-256
90dab78c269b74f511416ddd73cf05e123555ae006b9ad75fc896933a35f9cd2,
and 15205.782575335 / 18002.574545061 charged GPU seconds. Retain failed attempts.
Commit locally after acceptance; no push or publication. Handoff: GPUP-SETUP only.

Acceptance evidence: [report](../docs/benchmarks/lp-adaptive-host-cost.md), strict
protocol/schemas and hash-bound data. All 32 attempts verify with both binaries,
all 24 timings certify and all 16 numerical/work pairs match. Twelve 200-update
old/new pairs and twelve baseline replays match bitwise; both binaries accept all
36 endpoints. Full native (187 Python integration tests), 55 regular device tests
and all four adaptive sanitizers pass. All sixteen ladders and independent old
probe/audit implementations match; exact-rational regressions remain intact.
A 255-file source audit preserves old runtime/schema/protocol/kernel/decision data.
Only adaptive.rs changes runtime behavior. Initial test-only Clippy and clean-source
fixture failures are fixed; failed and passing CPU receipts are retained.
No failed GPU trial or retry. Historical racecheck/session/mixed-65536 gaps remain.

Task charge 201.890184622 GPU seconds: timing 62.784243449/1000,
profiles 20.927881994/300 and acceptance
118.178059179/500. Cumulative 15407.672759957 /
18002.574545061 seconds, no added allowance. The 15528-event ledger SHA-256
cb0dc57f9f92546f4cc2d93b0de3c8556d6b24517f71b7a6efaa91fa96afedb6 preserves the 15452-event prefix and every phase cap.
Final full pinned-native tools/check.sh passes 505 Rust tests, 187 Python tests,
record replay, 107 documentation pages and smoke. Metered child CPU is
1430.901302 seconds within four hours; small edits/catalog checks are outside that
metered child total. Four build jobs; no additional GPU work. Final source audit
and immutable ledger prefix pass. Local commit follows; no push.

Raw source/executables, endpoints, receipts and analysis remain under
artifacts/gpup-adaptive-cost-baseline, artifacts/gpup-adaptive-cost-acceptance and
artifacts/gpup-adaptive-cost-v1. GPUP-SETUP is the next handoff; no work on it begins.

## GPUP-HOST protected integration (2026-09-29)

Status: local acceptance complete; PR publication and protected merge authorized.
The user authorized opening the GPUP-HOST PR and merging after the recommended
checks. Scope: publish the completed slice, inspect required CI and review
conversations, merge with preserved source ancestry, and synchronize local main.
Acceptance: existing full pinned-native and device receipts, current branch,
required GitHub cpu/docs/smoke checks on the final head, resolved review threads,
protected merge without bypass, and clean synchronized main.
Resources: four build jobs, at most one CPU-hour for integration validation,
zero GPU jobs and no added campaign allowance. Preserve all artifacts and the
15452-event ledger SHA-256
90dab78c269b74f511416ddd73cf05e123555ae006b9ad75fc896933a35f9cd2;
cumulative consumption remains 15205.782575335 / 18002.574545061 GPU seconds.
Initial source head: af8e60f9c400968f8a8c66c4986ef3a6bb7a86e8; origin/main:
1818cdb5405fe466728c9cfb1719c67e22f660a5. The branch is current with main.
The recorded no-push scope below describes the completed implementation phase;
this later user authorization permits its PR and merge. GPUP-ADAPTIVE-COST
remains the next task and is not begun. Final check/merge outcomes are retained
in artifacts/gpup-host-integration-20260929/integration.json and sibling receipts.

Integration preflight: runtime review found no blocking issue; the pinned-native
and regular device receipts pass, the 15452-event ledger hash is unchanged, and
all 104 documentation pages pass link/anchor validation. Dependencies and CI
workflows are unchanged. GitHub's effective rules require current-branch
cpu/docs/smoke checks and resolved conversations; no mandatory approval or
protection bypass is used. Remote outcomes follow in the integration receipt.

## GPUP-HOST immutable model reuse (2026-09-29)

Status: complete; implementation, bounded study and final repository gate passed.
Objective: remove one duplicate model parse/structural validation within fresh
solve evidence construction, retaining fresh LP reconstruction and assessments.
Contract: SPEC-0016 and ADR-0028, accepted by the user before runtime work.
Likely files: optimizer-experiment LP input, CLI solve, host study/schema/tooling,
contract tests, report and state documentation.
Acceptance: full pinned-native tools/check.sh, exact-rational regressions, v1-v5
constructor/identity checks, CPU reconstruction counts, regular device acceptance,
fixed-work old/new comparisons/replay, and independently verified 24 timings plus
four profiles. Archive baseline HEAD 1818cdb5405fe466728c9cfb1719c67e22f660a5.
Resources: four build jobs, four CPU-hours; timing 900 GPU seconds in ablations,
profiles 200 and acceptance 300 in repeatability, combined 1400. No added allowance.
Every device job uses the shared host lease and conservative reservation accounting.
Preserve cumulative 15071.710156489 / 18002.574545061 GPU seconds, all phase caps,
15392 events and ledger SHA-256
6a30c1954ff9bc80c733364d8e8a7c0fc4c4439d70b959d2c10996d71993e518.
Retain every failed attempt; no retries, numerical/default/kernel changes or
cross-solve reuse. Commit locally after acceptance; no push. Handoff after completion
is GPUP-ADAPTIVE-COST, which this task does not begin.

Acceptance evidence: [report](../docs/benchmarks/lp-immutable-host-input.md), accepted
SPEC-0016/ADR-0028 and hash-bound repository data. The full pinned-native pre-study
gate passes 502 Rust and 183 Python tests, exact-rational regressions, record replay,
103 documentation pages and smoke. All 55 regular device tests pass; six old/new
fixed-work pairs and six compact replays match bitwise, with both executables
independently accepting all 18 endpoints. CPU old/new checks retain every assessment.

All 28/28 admitted study attempts independently verify and 24/24 primary timings
certify. All 14 timing/profile numerical/work pairs match. Profiles demonstrate
parse/validation counts 2 to 1, sparse construction remaining 2 and unchanged
candidate/certificate/gap counts. Scoped large-model improvements and smaller-cell
uncertainty are reported; no preset follows. No failed or retried GPU identity.
The first final gate caught one broken relative report link after all numerical
and integration checks passed; the link is corrected and the failure receipt retained.
Only two runtime files change; 121 historical files and both source archives pass
the independent audit. Kernels, old schemas/protocols and mathematical authority
are unchanged; historical session, racecheck and mixed-65536 gaps remain open.

Task charge 134.072418846 GPU seconds: timing 91.461934760/900, profiles
19.113062965/200 and acceptance 23.497421121/300. Cumulative
15205.782575335 / 18002.574545061 seconds, no added allowance. The 15452-event
ledger SHA-256 is
90dab78c269b74f511416ddd73cf05e123555ae006b9ad75fc896933a35f9cd2;
the 15392-event prefix above and all phase caps remain intact. Source, native/device
receipts, CPU metering, raw outputs and independently verified analysis are retained
under artifacts/gpup-host-baseline, artifacts/gpup-host-acceptance and
artifacts/gpup-host-v1. Handoff is GPUP-ADAPTIVE-COST; no work on it or push occurs.

Final repository acceptance: corrected full pinned-native tools/check.sh passes
502 Rust tests, 183 Python tests, record replay, 104 documentation pages and smoke.
The first documentation-link failure and corrected passing receipts are retained.
Metered child CPU across builds, focused/full gates, device acceptance, study,
independent reporting and source audit is 1297.465518 seconds within four hours;
small source-edit/catalog checks are not included in that metered child total.
Four build jobs; no additional GPU work. The published artifact catalog verifies
all 335 retained references. Local commit follows; no push.

## GPUP-EVIDENCE protected integration (2026-09-27)

Status: local acceptance passed; protected integration authorized; remote outcomes
are recorded in the integration receipt.
The user explicitly authorized opening the PR, merging after required checks and
review, synchronizing main, and cleaning up its corresponding branch.
Scope: publish the completed GPUP-EVIDENCE slice and its preceding follow-up
ordering; inspect reviewable changes and CI, preserve measured commit ancestry
with a merge commit, and delete only the merged compact-evidence branch after
checking main ancestry and worktree ownership. No release or hosting change.
Acceptance: full pinned-native tools/check.sh, local diff review, required GitHub
cpu/docs/smoke checks on the final head, resolved review threads, protected merge,
clean synchronized main and verified local/remote branch deletion. No bypass.
Resources: four build jobs, at most one CPU-hour for integration, zero GPU jobs.
Preserve all campaign evidence and the 15392-event ledger SHA-256
6a30c1954ff9bc80c733364d8e8a7c0fc4c4439d70b959d2c10996d71993e518;
cumulative 15071.710156489 / 18002.574545061 GPU seconds, no added allowance.
Initial source head: 99f2abb1f08df67d74263d1ad5ca982bd41c269c; origin/main:
15dd5c8d7bf47ea9dfb530cb2051f66b5971562c. The branch is current with main.
Final PR/check/merge/cleanup outcomes and acceptance logs are retained in
artifacts/gpup-evidence-integration-20260927/integration.json and sibling files.

Local acceptance: full pinned-native tools/check.sh passes (500 Rust tests, 179
Python tests, 101 documentation pages, committed-record replay and smoke). The
local review found no blocking issue in codec/CLI verification or accounting.
The read-only evidence audit checks 391 retained references, the unchanged ledger
prefix and numerical/kernel sources; all pass. Integration uses 124.719736 metered
child CPU seconds and no GPU work. Remote cpu/docs/smoke and unresolved review
threads are checked on the PR head before merge; no protection bypass is allowed.

## GPUP-EVIDENCE compact LP output (2026-09-27)

Status: complete; implementation, bounded study and final repository acceptance passed.
Objective: study-only compact evidence with independently reconstructed validation,
legacy identity/replay, CPU size/write/verification evidence and 24 fresh paired timings.
Contract: SPEC-0015 and ADR-0027, recorded before implementation. Preserve every
numerical setting, original-model certification, existing output default and kernel.
Likely files: optimizer-experiment compact codec, optimizer-cli study/solve output,
schemas, CPU/device contracts, bounded evidence protocol/runner/report and task docs.
Acceptance: full pinned-native tools/check.sh; strict versions 1–5, bitwise codec
round trips and rejection tests; four extension fixtures; regular device and fixed-work
format/replay equivalence; independent report retaining every failure and timing gap.
Resources: four build jobs, four CPU validation hours; 900 GPU seconds ablations for
24 timing attempts (864 seconds total reservation), 300 repeatability for acceptance.
No added allowance: cumulative 14766.435441716 / 18002.574545061 seconds; retain all
phase caps and the 15340-event prefix SHA-256
5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b. Serialize GPU jobs
under the shared host lease. No failed identity is retried. Local commit after
acceptance; advance to GPUP-HOST only when this bounded slice passes. No push.

Acceptance evidence: [SPEC-0015](../docs/specifications/SPEC-0015-compact-lp-evidence.md)
and ADR-0027 were accepted before implementation. The study-only compact codec,
assessment stdout, auto-detect verification/replay and verified transcode preserve
legacy defaults and v1-v5 payload hashes. Full pinned-native pre-study gate passes
500 Rust and 179 Python tests; 55 regular device tests, six fixed-work format pairs
and six compact replays pass with all 18 endpoints independently verified and
bitwise equal. Four extension CPU fixtures fit below 32 MiB and preserve exact
legacy serialization through round trips. Two fixtures are explicitly synthetic;
retained conversions never become new or recovered historical timing samples.

The [report](../docs/benchmarks/lp-compact-evidence.md) and hash-bound repository data
retain all 24 fresh attempts: 15 verified endpoints and 12 certified timings.
Compact certifies 9/12 and verifies 12/12; legacy certifies/verifies 3/12. All nine
legacy partials hit 32 MiB. Compact mixed-65536 outputs verify interrupted outcomes
but remain timeouts. The three qualifying irregular-32768 pairs have identical
numerical bits and median legacy/compact ratio 1.046264 (95% paired interval
1.022637–1.049929); no general preset follows. Kernels and numerical settings are
unchanged; prior sanitizer receipts retain their original scope, and the historical
racecheck/session gaps remain explicit. The initial historical-schema test failure
and subsequent corrected passing gates are retained; no GPU identity was retried.

Task charge: 305.274714773 GPU s (283.019581049/900 ablations timing and
22.255133724/300 repeatability acceptance). Cumulative 15071.710156489 /
18002.574545061 s; every phase cap and the original output binding are intact.
The 15392-event ledger SHA-256 is
6a30c1954ff9bc80c733364d8e8a7c0fc4c4439d70b959d2c10996d71993e518;
its 15340-event prefix retains the hash above. CPU resource receipts and full logs
are under artifacts/gpup-evidence-acceptance. Advance to GPUP-HOST for one bounded
immutable-host reconstruction repair; no additional GPU allowance is implied.


Final repository gate: full pinned-native tools/check.sh passes again after report
publication (500 Rust tests, 179 Python tests, 101 documentation pages, native
committed-record replay and smoke). Metered child CPU use across full gates, build,
CPU study, device checks, fresh study and analysis is 1277.511807 seconds; earlier
focused checks retain duration logs without child CPU receipts. Four build jobs
and the four-hour CPU bound are retained. Final artifact/reference and ledger-prefix
checks pass, including assessment-only compact stdout and unchanged numerical/kernel
sources and code images. The report, compatibility tutorial, all 24 trial summaries
and acceptance/provenance data are repository files. Local commit follows; no push.

## GPUP follow-up ordering (2026-09-27)

Status: complete; documentation-only ordering and acceptance recorded.
Objective: reconcile the merged GPUP-6/COPT state and order the remaining COPT
repairs and precision slices by coverage, measured cost and actual dependencies.
Scope: backlog, roadmap and current handoff pointers; preserve benchmark reports,
accepted contracts, raw evidence, numerical settings and historical task receipts.
The next implementation starts with its own bounded contract; this review does
not accept new numerical behavior or allocate GPU time.
Acceptance: consistent ordered tasks and dependency-ready next handoff, unchanged
campaign ledger, documentation links and full pinned-native `bash tools/check.sh`.
Resources: four build jobs, at most one CPU-hour for validation, zero GPU jobs.
Baseline: clean local main at 15dd5c8d7bf47ea9dfb530cb2051f66b5971562c;
GPUP-6 and COPT are merged according to the retained integration receipt.
Preserve 14766.435441716 cumulative GPU seconds, the 18002.574545061 current
ceiling, all phase caps and the 15340-event ledger SHA-256
5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b.
Likely files: state/backlog.yaml, docs/plans/gpu-lp-precision-roadmap.md,
wiki/status.md, AGENTS.md and this record. Local commit after acceptance; no push.

Acceptance evidence: full pinned-native `bash tools/check.sh` passed, including
495 Rust tests, 170 Python integration tests, archived-record replay, 97-page
link/anchor validation and bootstrap smoke. A separate planning check confirms
34 unique tasks, an acyclic dependency graph, completed prerequisites for
GPUP-EVIDENCE and matching roadmap/backlog priority. Receipts are retained in
artifacts/gpup-followup-order-20260927. Only five planning/state documents changed;
the COPT report, accepted specifications, runtime and historical evidence remain
unchanged. The ledger still has exactly 15340 events and the SHA-256 above after
the gate; no GPU job or allowance was added. The next task begins with the
GPUP-EVIDENCE contract, not a new solve campaign. Setup and optional COPT adapter
investigations retain their priority without becoming quantization prerequisites.

## GPUP-6 and COPT protected integration (2026-09-27)

Status: acceptance complete; protected integration and safe cleanup authorized.
Final merge/check/cleanup outcomes are retained in the integration receipt below.
The user explicitly authorized two PRs, ordered merges and safe branch cleanup.
Merge GPUP-6 first, then its dependent COPT comparison, preserving measured
commit ancestry with merge commits.
Scope: inspect reviewable changes and existing acceptance, publish both branches,
wait for required cpu/docs/smoke checks and resolve actionable review findings,
merge through protected PRs, synchronize local main, and delete only branches
whose tips are ancestors of merged main and have no other worktrees.
Acceptance: required checks pass on current PR heads, no unresolved review
threads, both PRs merged, original measured commits retained, clean synchronized
main, only the merged task branches removed. No protection bypass or force push.
Resources: four build jobs and one CPU-hour for integration checks; no new GPU
work or campaign allowance. Preserve the 15340-event ledger and all artifacts:
14766.435441716 cumulative GPU seconds, SHA-256
5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b.
Initial code acceptance is the full pinned-native GPUP-6/COPT gates and recorded
device/sanitizer scope. Initial remote main is 1dff5a9; both task branches form a
linear stack above it. Integration receipts remain under
artifacts/gpup6-copt-integration-20260927. No release or hosting publication.

Acceptance evidence: [PR #9](https://github.com/liuyumou/OptForge/pull/9) passed
all required cpu/docs/smoke checks, had no unresolved review threads, and merged
without bypass as 5aca01d. The dependent branch includes that merge with no source
conflict or numerical change. Its existing full native gate passes 495 Rust and
170 Python tests, with 55 device tests and the documented sanitizer scope; the
additional GitHub checks must pass on its current head before merging.
Local review covers adaptive rollback/work/reference authority, COPT method and
model identity, bounded admission, nested timing and compatibility; no unresolved
local finding remains. The final integration.json receipt records both merged PR
URLs/commits, the required-check snapshots, preserved measured ancestry, clean
main and the exact local/remote branch deletions. Only documentation and merge
ancestry change in this integration; the campaign ledger and raw evidence stay
unchanged.

## COPT comparison and component-cost diagnosis (2026-09-26)

Status: implementation and study complete; final acceptance recorded below.
The maintainer accepted the complete plan before behavior.
Objective: fresh certified LP comparison and component-cost diagnosis against local
COPT 8.0.6 under ADR-0026/SPEC-0013, identity gpup-copt-comparison-v1.
Scope: 17 configurations, 16 development models through 65536 rows, 1140 planned
attempts; separate timing, hierarchical profiles, bounded-work runs and CUDA traces.
Likely files: study CLI/input bounds; core optional profiling; LP/CUDA phase scopes;
external witnesses; v6 study and cost schemas; comparison/budget/report tooling;
acceptance tests and repository report. Numerical methods and kernel bytes unchanged.
Acceptance: full pinned-native tools/check.sh; regular device and profile equivalence;
strict external/cost evidence; clean-checkout synthetic budgets; independently verified
report retaining all failures and incomplete blocks. Existing sanitizer receipts are
carried forward only for unchanged arithmetic; historical gaps remain explicit.
Resources: four build jobs and four CPU validation hours. GPU: timings 4800 s in
ablations; profiles/short work 3000 s in repeatability; traces 600 s in baseline;
acceptance 300 s in repeatability; combined 8700 s. No cross-category borrowing.
Starting consumption 8912.494084146 s; 13056 events; prefix SHA-256
6db55153153e66ed5c2398417d008e4edd278e11153cf87b975345f1a574d34d.
Additional ceiling authority 3600 s gives 18002.574545061 s cumulative. Preserve all
campaign phase caps, 28800 s total, existing output binding, and every prior prefix.
All device jobs use the shared host lease. Commit locally after acceptance; no push.

Acceptance evidence: full pinned-native tools/check.sh (495 Rust and 170 Python
tests), 55 regular device tests, six fixed-work bitwise profile pairs, six COPT
min/max method fixtures, clean-source synthetic budget/admission tests and 948
independently verified endpoints from all 1140 frozen attempts. Final metadata
checks cover all 1140 worker receipts and collector envelopes. Existing four
adaptive sanitizer receipts are carried forward for unchanged kernels/arithmetic.
See the [comparison report](../docs/benchmarks/lp-copt-comparison.md) and its
hash-bound data catalog for precise scope, initial failures and corrected readers.
The first verifier omitted the explicit study allowance for endpoint reads;
88 unchanged endpoints reverify, recovering 21 primary certified samples. The
primary comparison still certifies only 402/816, with large-output/time-limit
failures retained. All 20 traces export; COPT graph internals remain unavailable.
No solver optimization, retries, preset, tolerance change or publication occurred.

Task GPU charge 5853.941357570/8700 s: timings 3848.867383594/4800,
profiles/short work 1717.984545181/3000, traces 267.901220613/600,
acceptance 19.188208182/300. Cumulative 14766.435441716/18002.574545061 s;
15340 events; ledger SHA-256
5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b.
The original 13056-event prefix and all phase caps remain intact. Raw evidence is
in artifacts/gpup-copt-comparison-v1 and artifacts/gpup-copt-acceptance. Four build
jobs; measured validation CPU stays below four hours. Commit locally after the
final gate. GPUP-7 still requires its bounded contract; the report ranks separate
host/evidence repair experiments without implementing them.

## GPUP-6 adaptive precision recovery (2026-09-26)

Status: complete; bounded plan accepted before implementation; correctness gates passed and comparison gaps retained.
Objective: implement opt-in FP32/FP64 audits, complete-window rollback, direct and
gradual promotion, sticky/guarded demotion, independent v5 evidence and replay,
and the frozen 2376-attempt development policy comparison under ADR-0025.
Likely files: optimizer-core settings/records; optimizer-lp adaptive control;
optimizer-lp-cuda executor/backend; CLI/evidence; schemas; study/budget tooling;
CPU/device tests and documentation. Existing kernels and old protocols stay intact.
Acceptance: full pinned-native tools/check.sh; injected rollback/guard/work/cancel
contracts; legacy wire/replay compatibility; device differentials and four adaptive
sanitizers; independently verified study report with all missing/failing trials.
Resources: four build jobs and four CPU-hours; 5400 GPU seconds in ablations and
900 in repeatability, combined 6300, under the one-device shared host lease.
Starting consumption 7015.920961503 s; 8278 events; prefix SHA-256
c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a.
New cumulative ceiling 14402.574545061 s; preserve campaign 28800 s, every phase
cap, prior output binding and ledger prefix. No remote publication is authorized.
The preceding throughput integration completed at 1dff5a9; the retained completion
receipt supersedes the historical pre-merge wording below.

GPUP-6 is complete under accepted ADR-0025 and SPEC-0012: explicit lp-adaptive-v1
ladders/audits, whole-window rollback and charged replay, direct/gradual promotion,
sticky or probed demotion, fresh-single v5 evidence and replay. Original-model
host certification remains authoritative; old kernels, records and defaults remain.
Its [report](../docs/benchmarks/lp-adaptive-gpup6.md) independently verifies
2086 endpoints from 2376 admitted of 2376 planned attempts.
Failed archive-discovery attempts and comparison gaps remain visible; no preset
is selected. Native, regular device and four adaptive sanitizer gates pass.
Campaign consumption is 8912.494084146 s inside the 14402.574545061 s ceiling;
GPUP-6 study 1826.094392481/5400 s, acceptance 70.478730162/900 s.
The 13056-event ledger SHA-256 is
6db55153153e66ed5c2398417d008e4edd278e11153cf87b975345f1a574d34d, preserving the 8278-event prefix
c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a and every earlier prefix.
GPUP-7 follows and needs its bounded quantization/FP8 interface and resource
contract before behavior. Adaptive sessions, persistent checkpoints and supported
presets remain outside GPUP-6; old 65536-row and tuned_cases racecheck gaps remain.

Acceptance evidence: full pinned-native tools/check.sh, clean-checkout synthetic
budget/admission tests, regular device suites, CLI v5 verification/replay, and
memcheck/racecheck/initcheck/synccheck on adaptive_. Receipts are retained in
artifacts/gpup6-acceptance; the measured source/executable and all attempted trial
records remain in artifacts/gpup6-adaptive-v1. The report records exact test
counts, costs, retained failed initial acceptance and harness preflight/discovery
failures. Final verifier/archive checks change no numerical path. Local commit
after acceptance only; no push or publication.

## GPUP-THROUGHPUT integration and branch cleanup (2026-09-22)

Integration follow-up: PR #8 is open, but both initial CPU workflows fail in
`test_ledger_for_enforces_the_v3_ceiling_authority`: the test reads the ignored
local campaign ledger absent from a clean checkout. Before merging, repair this
one test with a temporary root, checked source/decision/authority files and a
valid synthetic CPU-only ledger; retain ceiling, reference-hash, prefix and
output-binding rejection checks. Validate the budget tests in a clean source
checkout and rerun the complete native gate. No production budget code, frozen
protocol, numerical settings, device work or live ledger changes. The CI logs
are retained in artifacts/gpupt-integration-20260922.
Repair evidence: all three budget-authority tests now pass in a fresh local clone
with no campaign artifacts. The fixture uses actual temporary ledger/reference
files and preserves all refusal cases; the live 8278-event ledger is unchanged.
Only test code and integration documentation change. The complete native gate
and new GitHub checks remain the final integration gates.


Status: implementation acceptance complete; prepared for protected integration.
The PR status and retained integration receipt record the final remote outcome.
The user explicitly authorized opening a PR, merging when appropriate, and
cleaning up the merged branch. Scope: verify the branch against
current origin/main, inspect the reviewed changes and existing acceptance,
run the pinned-native integration gate, publish the branch and a reviewable PR,
wait for all required GitHub checks and review conversations, merge without
bypassing protection, then fast-forward local main and delete only this merged
local/remote feature branch. Preserve all benchmark artifacts and GPU ledgers.
No release tag, hosting change, protection change or new GPU job is included.

Resources: four build jobs, one CPU-hour, read-only GitHub inspection plus the
explicitly authorized PR/push/merge/branch deletion. Existing numerical/device
acceptance and the 7015.920961503-second campaign total are unchanged. Acceptance:
full tools/check.sh, no unresolved new findings, current main ancestry, required
cpu/docs/smoke checks on the PR, merged head ancestry, synchronized clean main,
feature branch removed and all experiment evidence retained. The PR and local
artifacts/gpupt-integration-20260922 receipt record the final remote outcome.



Readiness evidence: origin/main remains 0e7811a, an ancestor of the five reviewed
implementation/specification commits ending at cd1e958; no rebase is needed.
All four review findings are fixed. Existing full native acceptance is 481 Rust
results and 150 Python tests; fresh controls validate 360/360 variant comparisons,
and both old/new verifiers validate 16/16 optimized diagnostic solve identities.
The effective main rules require current cpu/docs/smoke checks and resolved
conversations, with no mandatory approving review and no bypass. Merge commits
are allowed and preserve archived source ancestry. No lockfile/dependency changes
or raw experiment artifacts are included in the source diff. The 65536-row
coverage and historical tuned_cases racecheck limitations remain explicit;
experimental opt-in behavior and unchanged defaults make them documented scope
limits rather than newly concealed supported-backend guarantees.


## GPUP-THROUGHPUT validated host input reuse (2026-09-22)

Status: complete after the review corrections committed as 2848b0d.
Objective: remove repeated JSON parsing, canonical model serialization and sparse
LP reconstruction from research evidence generation and verification. Reuse only
independently validated immutable host inputs, with freshly materialized bounds
for variants; every candidate evaluation, certificate and gap check remains per
solve. Existing SPEC-0014 requirements 5, 8-10 and 15-17 govern this internal
optimization; no public schema, numerical method, kernel or default changes.

Acceptance: byte-identical raw/materialized evidence, stale assessment and model
identity mutation rejection, historical v1/v2 mode/tier compatibility, paired
CPU timings against the correction executable, full pinned-native tools/check.sh.
If CPU evidence justifies it, at most two existing 32768-row N=8 fused-FP64 short
batch cells (repeat and variant) may be rerun as explicitly scoped diagnostic
acceptance of the producer path, with all original numerical settings and
independent bitwise comparison. Freeze inputs/source before device admission;
use one 48-second worker plus six-second reservation in the original study pool.
No new campaign or allowance. Changes: experiment host assessment/evidence code,
contract tests and performance report. Four build jobs and four CPU-hours.
GPU start: 6982.408046756 s, 8276 events, hash b3451186b7a5fc0029fbbd612b07e795072476ab76137a78a375b1d97866c236.
Remaining study 54.022860302 s; acceptance 58.328048581 s; combined 112.350908883 s.
Preserve every prior prefix and the cumulative 8102.574545061-second ceiling.


Acceptance evidence: full pinned-native tools/check.sh passed (481 Rust test
results, 150 Python tests, 93 documentation pages and all other gates). New
regression proves byte-identical raw/prepared evidence, fresh variant assessment,
LP rebuild equality and wrong model hash/stale assessment refusal. Seventeen
archived research-v1/v2 single endpoints across all twelve modes and three tiers
reverify. Three paired CPU repetitions accept unchanged N=8 evidence and reduce
verification medians 0.656→0.186 s (2048 repeat), 12.821→3.484 s (32768 repeat),
12.832→7.344 s (32768 variant), versus the corrected operator-cache baseline.

The two admitted large-batch producer diagnostics complete and are independently
verified by both original and optimized executables: 16/16 per-solve bitwise
identities match, with identical work-limit statuses. Whole process times are
10.746/22.484 s versus historical 48.679/49.444 s (repeat/variant), one new
repetition each; these are historical unpaired diagnostics, not single-solve
latency, statistical claims or a supported preset. See the
[host-input report](../docs/benchmarks/lp-throughput-host-input.md).

New device charge 33.512914747 s; cumulative 7015.920961503 s. Study
2679.490054445/2700, acceptance 541.671951419/600, combined 3221.162005864/3300.
The 8278-event ledger SHA-256 is c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a;
its 8276-event prefix b3451186b7a5fc0029fbbd612b07e795072476ab76137a78a375b1d97866c236
and every earlier prefix remain intact. No GPU allowance was added; no kernels
changed. Exact measured source 97a77c12e52a87d185442a168a5211dbba0019ebe46284f58c1b91aaf9cbb362
and all receipts are in artifacts/gpupt-host-input-20260922. The earlier
65536-row coverage and tuned_cases racecheck limitations remain explicit.


## GPUP-THROUGHPUT review corrections (2026-09-22)

Status: complete at the user's explicit request to fix the review findings.
Objective: one bounded corrective slice for outcome identity, common session
identity, actual binary64 comparisons and ordinary fresh-variant controls.
Preserve the original study and ledger; then select a separate bounded host
performance optimization if measurements justify one. GPUP-6 remains deferred.

Contract: SPEC-0014 requirements 6, 13-17 and the accepted corrective addendum;
ADR-0024 records the new follow-up protocol and shared (not additional) budget.
Acceptance: targeted CPU regression/mutation tests, full pinned-native
`bash tools/check.sh`, scoped device acceptance and corrected fresh controls
under the existing shared lease and caps, independent endpoint verification,
corrected analysis in a new artifact directory, updated report and task state.
Files: tuned backend/session identity, batch verifier, study planner/analyzer,
regression tests, corrective protocol, specifications and report.
Resources: four build jobs, four CPU-hours. At start: campaign 6951.059845871 s,
8178 events, SHA-256 dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6.
Remaining GPUP-THROUGHPUT study 82.070540459 s, acceptance 61.628569309 s;
combined 143.699109768 s, cumulative ceiling 8102.574545061 s unchanged.
All admitted GPU work retains prefix gpupt and old phase/combined caps; no new
allowance, prefix reset, kernel arithmetic or default change.

Acceptance evidence: full pinned-native tools/check.sh passes, including the
new Rust outcome/session-identity regressions and 150 Python tests. All 48
ordinary fresh-variant controls completed, independently verified and certified;
360/360 retained batch variants match their binary64 numerical/work identities.
The original-study reanalysis independently verifies 687/705 endpoints, with
4425/4425 ordinary-single repeat pairs, 360/360 historical N=1-session pairs
and 2451/2451 cross-mode pairs; partner labels remain explicit. The cancellation endpoint regression passes on the device and
under all four scoped sanitizers with zero errors/hazards; this does not close
the earlier tuned_cases racecheck gap. See the
[correction report](../docs/benchmarks/lp-throughput-corrections.md).

New study work: 28.047680157 s; acceptance: 3.300520728 s. Cumulative campaign:
6982.408046756 s; study 2645.977139698/2700, acceptance 541.671951419/600,
combined 3187.649091117/3300. The 8276-event ledger SHA-256 is
b3451186b7a5fc0029fbbd612b07e795072476ab76137a78a375b1d97866c236;
the original 8178-event prefix remains dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6.
Measured controls source identity: 73936de19b351cc4f89328355c49fbcba7acf38024854067b0c004809bcaca6b.
Artifacts: artifacts/gpup-throughput-controls-v1 (archived source, protocol,
binaries, models, controls, comparisons and original reanalysis) and
artifacts/gpup-throughput-review-acceptance (scoped device receipts). Original
study artifacts and numerical kernels are unchanged.

## GPUP-THROUGHPUT branch review and bounded performance repair (2026-09-22)

Status: complete. Reviewed feat/gpup-throughput at 14a1a88 against main at
0e7811a; [PR findings and CPU measurements](../docs/benchmarks/lp-throughput-review.md)
recommend request changes for four unresolved correctness/evidence findings.
One bounded host verification performance repair is implemented and accepted;
this is a review of the completed slice, not GPUP-6 implementation.

Objective: identify reproducible PR findings and, if supported by measurements,
complete one bounded host-side performance repair within SPEC-0014. Preserve
numerical behavior, protocol, frozen artifacts and the GPU ledger.

Acceptance: focused CPU regressions and performance evidence for any repair,
then full pinned-native `bash tools/check.sh`; PR review references verified lines
and distinguishes archived GPU receipts from checks run during this review.
Likely files: session/batch evidence paths in optimizer-lp, optimizer-lp-cuda,
optimizer-experiment and optimizer-cli, relevant contract tests and documentation.
Resources: at most four build jobs, four CPU-hours; initially zero GPU jobs.
Any device validation must use the shared lease and existing phase/campaign caps;
no allowance or ledger reset is authorized by this review.

Acceptance evidence: full pinned-native `bash tools/check.sh` passed on the
repair (477 Rust test results, 148 Python integration tests, 90 documentation
pages, schema/provenance/replay/smoke and static checks). Three added CPU tests
cover byte-identical cached/uncached evidence, fresh bound-dependent assessment,
provenance mutation, matrix/method/mode invalidation and one independent metadata
preparation across producer and final directory checks. All 11 research evidence
tests pass; 17 archived single endpoints covering all twelve modes, v1/v2 and
three tolerance tiers reverify. Two temporary CPU tests reproduced invalid
failure endpoint identity and acceptance of mixed code-object identities; a
Python probe reproduced signed-zero equality. These are review findings, not
newly injected GPU faults.

CPU-only N=8 archived batch verification, three paired repetitions: 0.970→0.638 s
(irregular-2048 repeat), 18.905→12.732 s (irregular-32768 repeat), and
19.366→12.737 s (irregular-32768 variant), 1.48–1.52x faster. All 18 timed calls
accepted unchanged evidence. No end-to-end GPU throughput claim. Raw timing,
compatibility, reproductions, measured candidate and acceptance logs are retained
in artifacts/gpupt-review-cpu-20260922; tools/benchmark_lp_batch_verify.py
reproduces the CPU endpoint. Zero GPU jobs ran: the 8178-event campaign ledger
retains 6951.059845871 seconds and SHA-256
dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6.
Original protocols, measured archives and code objects remain unchanged.

## GPUP-THROUGHPUT: specification, ADR and budget before behavior (2026-09-20)

Status: complete. Phase A is committed as 0d5d713 with its full pinned-native
gate receipt; Phases B-E are the implementation commit on top of it. The
[repeated-solve report](../docs/benchmarks/lp-repeated-solve-throughput.md)
holds the Phase E evidence; GPUP-6 is next_ready_task and requires its bounded
adaptive contract before behavior. The working tree carried the optimizer-lp
PreparedMatrix/Engine::from_prepared refactor, TunedSession and
ResearchSession with residency bound rebinding, solve-batch/materialize/verify-batch
CLI, lp_batch and research batch documents, both frozen schemas, lp_variants.py,
benchmark_lp_throughput.py (705 planned attempts) and the session_ device cases. The
backlog reorder record below stays as the history of how this slice was selected.

Objective: implement GPUP-THROUGHPUT (state/backlog.yaml next_ready_task) in phases,
beginning with its accepted bounded contract: SPEC-0014 (repeated-solve sessions for
cuda-lp-tuned and the research executable), ADR-0023 (two opt-in paths, variant rule,
bitwise-identity rule, frozen resources) and the frozen protocol
benchmarks/configs/lp-throughput-v1.json carrying its own ceiling authority. A batch
fixes one matrix, objective and row bounds; solves are identical repeats or per-solve
variable-bound variants tightened around the instance's frozen witness. The
fresh-process single-solve endpoint, protocol, defaults and archived evidence stay
unchanged; amortized throughput is a separately labeled endpoint, never substituted
(ADR-0013, SPEC-0013 requirements 10-13).

Acceptance gate per phase: Phase A (this record) — full pinned-native
bash tools/check.sh with zero GPU work, committed as documentation only. Phases B-D —
full gate plus Python integration tests; device session_ cases and all four scoped
sanitizers under the shared lease. Phase E — frozen study under identity
gpup-throughput-v1, independent verification of every admitted attempt, bitwise
identity counts, report and final gate.

Likely files: docs/specifications/SPEC-0014-lp-repeated-solve-throughput.md,
docs/decisions/ADR-0023-repeated-solve-throughput.md,
benchmarks/configs/lp-throughput-v1.json, crates/optimizer-lp (problem.rs, pdhg.rs),
crates/optimizer-lp-cuda (residency.rs, backend.rs, session.rs, research.rs),
crates/optimizer-experiment (lp_batch.rs, lp_research.rs, example), crates/optimizer-cli
(batch.rs, lp_study.rs, main.rs), schemas/lp-batch-request-v1/lp-batch-endpoint-v1,
tools (lp_variants.py, benchmark_lp_throughput.py, analyze_lp_throughput.py,
lp_research_budget.py), tests, and the documentation set named in SPEC-0014.

Resource budget: four build jobs; four-hour CPU validation ceiling. GPU only after
ADR-0023 is accepted: study 2700 s plus acceptance 600 s (combined 3300 s) under
identity gpup-throughput-v1, inside a cumulative ceiling of 8102.574545061 seconds
(4502.574545061 + 3600). Preserve the 6722-event ledger prefix SHA-256
ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b and 3794.758955639
consumed seconds; campaign 28800 s and phase caps unchanged. Phase A runs zero GPU work.

Evidence: full pinned-native bash tools/check.sh passed on the Phase A tree
(source identity 1620d714af9b4f84e41303b7d1c17ae47dbcd1481d7993c873dde5901036035;
441 Rust tests, 131 Python tests, 88 documentation pages with valid links/anchors,
artifact schemas and committed-record replay). SPEC-0014, ADR-0023 and the frozen
lp-throughput-v1 protocol (planned 705 attempts, ceiling 8102574545061 ns embedding
source campaign hash b40217f3... and decision hash 06f28fbf...) are committed as
documentation. No GPU job ran; the campaign ledger is untouched.

Phase B-D evidence (2026-09-20): full pinned-native bash tools/check.sh passed on the
implementation tree (source identity 3a10d41228d2e70b8ce1a544b21c7657a58935e870c33985b185041273df6f36;
146 Python tests including 15 throughput grid/variant/budget/analysis gates, 88
documentation pages with valid links/anchors, artifact schemas and committed-record
replay; log /tmp/gpupt-gate-b2.log). Resumed work added tools/analyze_lp_throughput.py
(separate-endpoint labeling, bitwise identity counts), the lp_gpu_cli_check.py
solve-batch/verify-batch section, the v3 acceptance ledger authority in
lp_research_budget.py's main, the CHANGELOG behavior entry and SPEC-0014
implementation/test mappings. The Rust workspace test suite passes across 54
binaries with zero failures; the eight session_ device cases compile and await
their leased acceptance run. No GPU job has run; the campaign ledger is untouched.

Phase E evidence (2026-09-21): the frozen gpup-throughput-v1 study admitted all 705
planned attempts; 687 verified independently with the archived executables and 18
(the 65536-row N=8 short batches, both kinds, three repetitions) stopped at their
58-second reservations without endpoints, charged and retained. Batch solves are
bitwise identical to fresh singles on 4785/4785 compared pairs; fused and intguard
research trajectories agree on 2451/2451 numerical comparisons (launch counts
differ by construction). Study 2617.929459541/2700, acceptance 538.371430691/600,
combined 3156.300890232/3300, cumulative 6951.059845871/8102.574545061 GPU seconds;
the 8178-event ledger SHA-256 dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6
preserves the 6722-event prefix ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b,
with all 728 new reservations settled. Device acceptance passed on
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48: regular suites on both binaries, all
session_ cases under all four scoped sanitizers with zero errors/hazards, the
research_ cases under all four, the study_observation/matched_control/tuned_cases
filters under memcheck/initcheck/synccheck, and the CLI evidence check including
solve-batch, materialize, verify-batch and the pinned fallback. Retained failures:
one stale-binary launch, one three-defect session-test run and two CLI-check
failures (all fixed before final evidence), one session-racecheck reservation
timeout (retried, passed 116.8 s), and the pre-existing-filters racecheck that
timed out after study_observation and matched_control passed clean; tuned_cases
lacks a racecheck receipt because the frozen acceptance cap left 61.6 seconds, and
the gap is recorded in the report and known failures, not relabeled. The measured
source tree 6343d622025803e6e9637612c8fd05d30832b138788ab652fe5ed791f245b1ea
(optimizer 6498e4f3e126cd24d3bb2587dadd792857a4819ec44ac5f6ddbd3f009e087676,
research ec778ceeba80bc072525c4447863a46e892d72bc11fc94d151c088a4ab776e1e, code
object 6a743e1e745159f304168124800eec86891c641dfe9f18a91c0aa11d0555b7a2 unchanged
from GPUP-5C) is archived in artifacts/gpup-throughput-v1 with protocol, jobs,
ledger snapshot and analysis.json (analysis tool
2916421b148e70ebb676a6e353fdf745fd1af8c9768fbcc66463070b3de40448). The
[report](../docs/benchmarks/lp-repeated-solve-throughput.md) keeps the amortized
endpoint separate and records the N=1 and 32768-row negative results. The
post-measurement changes are the analysis-tool tuple fix and cross-mode
launch-count exclusion (each with a regression test), documentation and state
records; measured kernels, sessions and frozen evidence are unchanged.

## GPUP-THROUGHPUT pulled ahead of GPUP-6; GPUP-5/5B/5C integrated (2026-09-20)

Status: ready; no behavior implemented. PR #6 merged branch
codex/gpup5b-exact-products into main as merge commit 8e768247 after the cpu, docs
and smoke checks passed; the recorded full pinned-native gate receipt
(target/lp-native-gate.json) matched the merged source identity
e8055b7e8158f5919c0d4b82e08e1af1b388aa1dcfb7577e48e7c98a8ea8f758. GitHub refuses
self-approval, and the main ruleset requires zero approving reviews, so the merge
rests on the recorded gate and the required status checks.

Objective: reorder the backlog only. The user pulled GPUP-THROUGHPUT ahead of
GPUP-6 because the GPUP-5C report shows the remaining cost is outside arithmetic:
paired certified-latency ratios stay within 0.92-1.11 of tuned for every mode and
tier, context creation (208-330 ms) and fixed host phases dominate 400-600 ms solves
at study size, and at 65536 rows preconditioning (about 940 ms) and research
preparation (about 1020 ms) each exceed the 19-30 ms total kernel time of a
200-proposal run. GPUP-THROUGHPUT becomes next_ready_task with status ready and
depends_on GPUP-5C; GPUP-6 now also depends on it. Its acceptance keeps the ADR-0013
separation: an accepted specification, API and resource budget before any behavior;
the fresh-process single-solve endpoint, protocol, defaults and archived evidence
unchanged; amortized throughput never reported as single-solve latency.

Acceptance gate: bash tools/check.sh (documentation build and policy checks cover
the edited pages); no solver, protocol, seed, tolerance, artifact or ledger changes.
Likely files: state/backlog.yaml, AGENTS.md, docs/plans/gpu-lp-precision-roadmap.md,
docs/plans/lp-precision-candidates.md, wiki/status.md and this record.
Resource budget: documentation-only; at most four build jobs for the gate; zero
project GPU work. The slice's own CPU/GPU budget is set by its specification, which
is the first deliverable of GPUP-THROUGHPUT and must be accepted before behavior.

Evidence: full pinned-native bash tools/check.sh passed on the edited tree (source
identity 38d6a626c4a32e44668d280d31fbdbe23e0c0ca9ecc9f3610f094cab374d3248; 131
Python tests, 86 documentation pages, committed records re-executed, bootstrap
smoke). No GPU job ran; the campaign ledger is untouched.

## GPUP-5C: FP64-pipe execution, tolerance tiers and corpus extension (2026-09-19)

Status: complete under [ADR-0022](../docs/decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md);
see the [report](../docs/benchmarks/lp-fp64-pipe-gpup5c.md). Evidence below.
Objective: act on the [root-cause note](../docs/benchmarks/lp-fp64-pipe-root-cause.md)
without changing runtime selectors, defaults, existing code objects, archived
evidence or the nine GPUP-5B modes. Add feature-gated research modes
intguard-fp64 (integer-pipe guards), fused-fp64 (two launches per proposal) and
doublefloat-fp32 (FP32 hi/lo pairs, no FP64 in the sparse loop) with CPU oracles;
research-v2 requests/evidence; explicit tolerance tiers 1e-9/1e-6/1e-4 recorded
per configuration; a frozen development-extension manifest under lp-manifest-v2
with instances up to 65536 rows and a new mixed family; a protocol-driven research
harness with byte-identical v1 behavior; committed diagnostic microbenchmarks.

Acceptance gate: full pinned-native tools/check.sh; CPU rational fixtures for
double-float products; strict v1/v2 evidence tests; device differential over all
twelve modes across controller boundaries, fault/admission tests, and all four
scoped sanitizers sequentially; frozen lp-research-v2.json attempts all admitted
through the shared lease and the preserved ledger; independent revalidation of
every endpoint; report with coverage per tier, paired latency, equal work, traces.

Likely files: crates/optimizer-lp/src/research.rs and tests; cuda/lp_pdhg_research;
crates/optimizer-lp-cuda/src/research.rs and tests/device/research.rs;
crates/optimizer-experiment/src/lp_research.rs; schemas/lp-manifest-v2.schema.json;
tools/lp_generate.py, lp_protocol.py, lp_research_budget.py, benchmark_lp_research.py,
analyze_lp_research.py, lp_research_oracle.py; cuda/diagnostics; benchmarks/configs/
lp-research-v2.json; benchmarks/manifests/lp-development-extension-v1.json; docs.

Resource budget: four build jobs; CPU validation within four hours; GPU study
1500 s and acceptance 300 s (combined 1800 s) charged to the preserved
gpup-baseline-v1 ledger under identity gpup5c-v1. Preserve the 4996-event prefix
SHA-256 737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f and
2235.353878971 cumulative seconds inside the 4502.574545061-second ceiling.
Uncharged 2026-09-19 investigation work is recorded, not repeated silently.

Evidence: artifacts/gpup5c-v1 (850 admitted of 874 planned attempts, 806 verified,
24 missing at the study cap, 44 without endpoints: 34 CLI 16 MiB refusals and 10
mixed-65536 timeouts) and artifacts/gpup5c-acceptance (two regular device runs of
33 cases, all four sanitizers twice with zero errors/hazards, three charged
microbenchmark runs). All twelve modes match the CPU oracle bitwise over 40 steps;
intguard/fused endpoints are identical to the FP64 control on all 114 pairs.
Full pinned-native tools/check.sh passed on the measured source
5e1e0ff1dd6604c54667356fa75d665c451d1e37b7f794039783acc982833e68 (131 Python
tests, 85 documentation pages) and again on the final source. Study
1493.313474227/1500 plus acceptance 66.091602441/300 seconds; cumulative
3794.758955639/4502.574545061. Ledger 6722 events, SHA-256
ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b, 4996-event prefix
intact. The initial fused kernels serialized their update tail on lane 0 and were
restructured before the study; both microbenchmark results are retained. Every GPU
job used the shared lease; no push or publication. Next ready task: GPUP-6.

## GPUP-5B: exact scaling and component sparse products (2026-09-16–17)

Status: complete; all 840 attempts and required acceptance gates passed. The
maintainer accepted ADR-0021 and SPEC-0012/0013 amendments before behavior.
Feature-gated host scaling, separate research code object/executable and strict
research-v1 evidence implement power-of-two/factored exact storage and two/three
components with matched reconstructed-FP64/FP32-cross-product controls. Ordinary
runtime schemas, selectors, code objects, replay and original-model authority
remain. No correction, adaptive recovery or supported preset was added.

The [report](../docs/benchmarks/lp-exact-components-gpup5b.md) retains all results:
432 timings, 48 profiles, 336 equal-work runs and 24 Systems traces. All 840
endpoints independently verify; all traces decode offline and match 1200 launches.
Timing coverage is 27/36 for every new mode versus 12/36 for plain FP32 storage.
Three-component cross-products recover convergence but cost 2.69x/2.67x native
research update time on irregular-2048/dense_block-1024. Failures remain visible;
no held-out/validation measurement or supported preset. The prior diagnosis is
unchanged. The [rounding note](../docs/benchmarks/lp-fp32-rounding-analysis.md)
reproduces every CPU claim and archived witness/hash; the
[candidate register](../docs/plans/lp-precision-candidates.md) preserves future work.

Acceptance: full pinned-native tools/check.sh on measured and final code, with
435 Rust tests, 126 Python integration tests and 83 documentation pages on final
source, plus format/clippy/dependency/replay/smoke checks. Independent Fraction
fixtures cover reconstruction/products/sparse cancellation/transpose; CPU/device
differentials cover all nine modes and controller boundaries. Memory refusal,
cancellation, exhausted physical work, range/fault accounting and strict evidence
mutations pass. All 51 regular device cases pass; all four scoped sanitizers run
sequentially with zero errors/race warnings. All nine research modes pass the
end-to-end preflight; the hardened final reader revalidates all 630 research
endpoints. Evidence: artifacts/gpup5b-v1, artifacts/gpup5b-rounding-v1 and
artifacts/gpup5b-acceptance (native-final.log, canonical device/sanitizer logs,
final-verification.json, exact source/code identities and artifact indexes).
Preliminary compile/CPU launcher/debug-audit records are retained. Post-measurement
changes only strengthen CPU evidence checks, rational fixtures and reporting;
measured numerical kernels/executor/controller are unchanged.

Resources: four build jobs, CPU validation within four hours; GPU measurements and
CPU acceptance run separately. New study 697.211414922/900 plus acceptance
70.875589353/300 = 768.087004275/1200 screening seconds. Preserve prior
1467.266874696 seconds: cumulative 2235.353878971/4502.574545061, with all original
campaign/phase caps. All 854 new reservations settled. The 3288-event prefix SHA
b3ca2739b1108a552b0423606ddd0cd94a8ed2323da1506098fa0150ba42bfef is intact;
4996-event final ledger SHA
737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f.
Historical artifact indexes and all their referenced files verify. GPUP-5's
80.458622460 acceptance seconds remain separate and unchanged. Every GPU job used
the shared host lease. No push/publication. Next ready task: GPUP-6; accept its
bounded adaptive interface/contract before implementation.

## Standalone pelican bicycle animation (2026-09-16)

Status: complete. User-requested creative artifact, separate from the optimizer
capability backlog. Objective: one self-contained `pelican-bicycle.html` containing
an original 2D SVG pelican riding a bicycle, synchronized pedaling/wheels, a moving
seaside scene, responsive layout, pause/speed controls and reduced-motion support.
Likely files: the HTML artifact and this task record. Acceptance: inspect the SVG
and script, browser checks if a local browser is available, and `bash tools/check.sh`.
Resource budget: 20 minutes CPU wall time, at most four build jobs; zero project
GPU work. CONTRIBUTING and relevant task state were read before implementation.

Acceptance evidence: the self-contained SVG parses with unique IDs and resolved
references; JavaScript syntax passes. Chromium desktop (1440px) and mobile (390px)
previews were visually inspected. Browser checks passed for moving pedals,
pause/resume, exclusive pace selection, reduced motion, keyboard activation,
no horizontal mobile overflow and no script errors. Temporary browser dependencies
were extracted under /tmp; no system package or project dependency changed.
Full pinned-native `bash tools/check.sh` passed, including 121 Python tests,
79 documentation pages, policy checks, committed replay and bootstrap smoke.
Evidence is retained under artifacts/pelican-bicycle. No optimizer behavior,
research backlog, GPU campaign ledger or archived study evidence changed.

## GPUP-5 follow-up: diagnose FP32 latency (2026-09-16)

Status: complete; diagnostic evidence and full pinned-native acceptance passed.
The requested investigation preserves runtime behavior, all 480 original trials,
code objects, guards, controller, original-model authority and defaults. No GPUP-6
behavior or supported preset was introduced. See
[diagnosis report](../docs/benchmarks/lp-fp32-slowdown-diagnosis.md) and ADR-0020.

All 213 frozen GPU jobs ran under the shared lease: 196 equal-update repetitions,
14 Nsight Systems traces and three unsuccessful Nsight Compute counter attempts.
Every endpoint independently verifies and records exactly 200 proposals (206
physical steps with correction). Every decoded trace matches 1200 launches. Raw
traces initially failed automatic import; existing private libdw decoded them offline.
All counter attempts retain ERR_NVGPUCTRPERM; no driver permission was changed.
No retry, timeout, fallback or missing endpoint. Hardware bottleneck counters remain
unavailable, and first-200-update timings do not establish late convergence behavior.

Exact rational representation analysis covers 72 archived witnesses across all
twelve development models. All 166292 original coefficients are exactly FP32;
only 18 scaled values are. Concrete original-row violations exceed allowances by
34.2x/15.8x while meeting the implied represented-operator allowance. Other failures
also retain represented residuals, so quantization alone is not asserted for every
model. Equal-work FP32 savings are small or instance-dependent; extra iterations,
generic guarded execution, state readback and fixed correction dominate large losses.

Full pinned-native tools/check.sh passed before measurement (422 Rust tests,
119 Python tests, 78 pages) and on final tooling/documentation (422 Rust tests,
121 Python tests, 79 pages), including formatting, clippy, native HiGHS,
dependency policy, committed replay and smoke gates. Final log:
artifacts/gpup5-diagnosis-v1/native-final.log. Five new diagnostic tests cover schedule,
exact arithmetic, historical totals, phase/counter status and work-limit eligibility.
All 480 old endpoints reverify in a temporary copy; old report/index bytes and all
original indexed artifacts are unchanged. No runtime/device changes required another
sanitizer run; GPUP-5 device evidence remains intact.

Resources: four build jobs within the two-hour CPU validation ceiling; GPU jobs and
CPU acceptance sequential. Diagnostics consume 143.056235443 of their 300-second
cap, charged to screening, plus the preserved 1324.210639253 = 1467.266874696 total
GPU seconds, within 4502.574545061 and global/phase caps. GPUP-5 acceptance remains
80.458622460/900 seconds, unused here. All 213 reservations settled; complete
2862-event old prefix SHA-256
66d8c2b0ee24ce050ee051c6dbea2184361abe2c2fc4a57b8ee202c001479ff0 is preserved.
New 3288-event ledger SHA-256:
b3ca2739b1108a552b0423606ddd0cd94a8ed2323da1506098fa0150ba42bfef.

Evidence: artifacts/gpup5-diagnosis-v1 (frozen protocol/source/executable, raw runs,
traces/decoder commands, counter failures, disassembly, exact row diagnostics,
paired analysis and artifact hashes). Post-measurement changes affect only read-only
analysis/reporting/tests/documentation. No old report or evidence was rewritten.
Known failures and CONTRIBUTING were read first. GPUP-6 remains next, requiring its
bounded contract. No push or publication.

## GPUP-5: explicit FP32 comparisons and COPT baselines (2026-09-16)

Status: complete; full native, device, sanitizer and frozen-study gates passed.
Next ready task: GPUP-6, bounded adaptive contract before implementation.
The maintainer accepted the complete plan before behavior (ADR-0019 and
SPEC-0012/0013 amendments). cuda-lp-tuned now has strict lp-precision-v1, v4
records/replay, canonical FP32 storage/products/accumulation/state and charged fixed
FP64 correction. Original-model authority, prior behavior/code objects and unsafe
boundaries remain. COPT 8.0.6 CPU/GPU PDLP uses isolated ignored Python 3.11 bindings;
licenses remain in /root/copt80. No adaptive recovery or preset was introduced.

Evidence: [GPUP-5 report](../docs/benchmarks/lp-fp32-gpup5.md),
artifacts/gpup5-fp32-v1 and artifacts/gpup5-acceptance. All 480 attempts have verified
endpoints, exact schedule/provenance and settled ledger entries. No missing/invalid
endpoint, fallback or lease failure. Lower-precision failures remain in coverage.
Full pinned-native final gate: 422 Rust tests, 116 Python tests, 77 documentation
pages plus format/clippy/dependency/replay/smoke gates; native-final.log records the
pass. The exact measured source also passed its pre-study gate (421/115/76).
Final device suites: 47 cases.
All six precision cases pass memcheck/racecheck/initcheck/synccheck sequentially on
the original RTX 5090 with zero errors/race warnings. Six CLI/replay pairs and
missing-code pinned HiGHS fallback pass. Native COPT original-model min/max,
ranged-row and objective-constant fixtures pass; actual GPU preflight certifies.
Initial callback/log-wording preflight failures are retained. Final source adds an
independent device subnormal/tie/guard fixture and refuses COPT input coefficients
at or below its native discard threshold; every frozen model is above it.

Resources: four build jobs within a four-hour CPU validation ceiling. All GPU work
used the shared one-device lease. Acceptance used 80.458622460 of its separate 900
seconds. Study added 421.636094192 screening seconds to the preserved
902.574545061 seconds, totaling 1324.210639253 of 4502.574545061 allowed seconds.
The full 1902-event prefix SHA-256 remains
35b58ef0b0d58637288801bac2bdaa32b65b97b42b429debcffc615768c7c543;
final ledger SHA-256 is 66d8c2b0ee24ce050ee051c6dbea2184361abe2c2fc4a57b8ee202c001479ff0.
Global 28800-second and original phase caps remain. No ledger, archive, seeds,
thresholds, defaults or partitions were reset. Validation/held-out remain untouched.
Known failures/CONTRIBUTING were read before work. No push or publication.

## GitHub main protection (2026-09-16)

Status: complete; main protection is active and independently verified.
The user explicitly authorized protecting main on GitHub.
Follow release operations: require CPU, documentation and smoke checks; prevent
force pushes and deletion. Inspect existing rules and actual check identities
before configuring protection. Require pull requests with current checks, while
retaining the documented autonomous workflow without mandatory human approval.
No administrator bypass is planned. Preserve repository visibility, source history,
existing permissions and GPU/study evidence.

Acceptance: validate the concrete ruleset request, read back active rules and their
application to main, and record the final settings or any hosting-plan limitation.
CPU administration/documentation only, bounded to 15 minutes; no GPU work.
Evidence: artifacts/main-protection. Read release operations and known failures.

Created active [ruleset 23515452](https://github.com/liuyumou/OptForge/rules/23515452),
then independently read it back and checked the effective rules on main. GitHub
reports main protected and current_user_can_bypass=never. Required cpu/docs/smoke
contexts are bound to the observed GitHub Actions application ID 15368. PRs must
be up to date and have resolved review conversations. Approving-review count is
zero; no bypass actors, force pushes or branch deletion are allowed. Existing
merge methods remain available. Main's source commit was unchanged by configuration.

The exact request, response, verified ruleset and effective branch rules are saved
under artifacts/main-protection. Updated release operations and resolved the stale
main-protection blocker in known failures. Documentation uses a PR under the active
rules; do not push completion records directly to main or disable protection.

Full pinned-native acceptance passed in 18.739547708 seconds: 411 Rust tests,
110 Python tests, 74 documentation pages and all policy/replay checks. No source,
solver behavior, GPU work or study ledger changed. The documentation commit follows
the newly enforced PR and hosted-check requirements; integration receipts are
retained with the configuration evidence under artifacts/main-protection.

## GPUP-4 integration follow-up: supervisor timing fixture (2026-09-16)

Status: complete; fixture repair reviewed, merged and its branch removed.
PR #3 and branch cleanup completed after all six pre-merge
checks passed. The subsequent completion-documentation commit's CPU CI run
35041476887 found a pre-existing fixture timing assumption: coordinator-loss
supervision correctly reported timeout, but 1.340948131 leased seconds exceeded
an arbitrary one-second assertion. Preserve its failed hosted log and receipts in
artifacts/gpup4-pr-integration. Inspect the supervisor contract before changing tests.

Objective: make the coordinator-loss fixture assert independent timeout, complete
lease accounting and released ownership within its existing three-second outer
wait. Keep solve/cleanup limits, production supervisor and all GPU/study behavior
unchanged. Acceptance: targeted repeated fixture runs, full pinned-native gate,
reviewed follow-up PR with hosted CPU/docs/smoke checks, main synchronization and
branch cleanup. CPU only within the remaining integration budget; four build jobs.
No new study or GPU work. GPUP-5 interface handoff remains the next feature task.

Ten consecutive targeted coordinator-loss cases passed in 7.123434293 seconds.
The full pinned-native gate passed in 18.939487085 seconds: 411 Rust tests,
110 Python tests and 74 documentation pages, including all policy/replay checks.
Review confirms this changes only test assertions and documentation. The existing
three-second completion wait and 0.1-second solve/cleanup settings remain. Timeout
signal timing, negative child status, complete lease timing and nonblocking lock
reacquisition now establish the intended contract without assuming CI scheduling
or durable output always fits an additional one-second ceiling.

[PR #4](https://github.com/liuyumou/OptForge/pull/4) merged as
1b8e33d13138dcb2da751bd113d5560976c2c073. All six hosted CPU/docs/smoke checks passed for
reviewed head 8ced5d85e879a6191251ede1904e8bcb3246f792. The
[author review](https://github.com/liuyumou/OptForge/pull/4#pullrequestreview-5217393475)
verified the four file blobs and reports no blocking finding. The merge required
that SHA and preserved its exact tree. Main was synchronized and the local/remote
codex/gpup4-supervisor-fixture branches were deleted after ancestry verification,
with expected-head protection for remote deletion. The failed prior main run is
retained; its failure is not relabeled as a pass. New hosted receipts are in
artifacts/gpup4-pr-integration/hosted-fixture-pr.json. Final completion updates are
documentation only and pass the documentation/link gate. All study artifacts and
902.574545061 campaign GPU seconds remain unchanged. GPUP-5 is next.

## GPUP-4 PR integration and GPUP-5 interface handoff (2026-09-16)

Status: complete. The user authorized publishing the completed GPUP-4 branch,
reviewing and merging its PR after required checks, synchronizing main, and deleting
the completed feature branch. Preserve reference commits, ignored study archives,
code objects and the canonical 902.574545061-second campaign ledger.

Record the backend-interface recommendation in the GPUP-5 handoff and discovery
paths. This is planning guidance: GPUP-5 precision behavior and any interface
migration still require accepted contracts before implementation. No new study.
Read CONTRIBUTING, release operations and known failures before work.
Acceptance: complete diff/unsafe/dependency review, fresh full pinned-native gate,
hosted CPU/docs/smoke checks for the reviewed head, verified merge ancestry and
synchronized main before branch cleanup. Budget: 30 CPU wall minutes with four
build jobs; at most five GPU acceptance minutes only if a runtime review repair
requires them, sequentially under the shared lease. Existing device/sanitizer
results apply to unchanged runtime. Integration receipts: artifacts/gpup4-pr-integration.

Local review, acceptance, publication, hosted checks, merge and branch cleanup
are complete.
Full pinned-native tools/check.sh passed in 18.889058079 seconds: 411 Rust tests,
110 Python tests, 74 documentation pages, formatting/Clippy/rustdoc, dependency and
license policy, artifact checks and recorded replay. No runtime change or additional
GPU job was needed. Existing 41 regular device cases and eight scoped cases under
each of all four sanitizers remain applicable, with the documented device limitation.

Review covered the complete implementation diff, resident/restored state, bounded
cancellation and physical work, padded memory admission, deterministic reductions
and fusion, legacy schemas and code, strict execution/replay/provenance, fallback,
ledger reservations/admission, pairing/coverage and report limitations. No blocking
finding remains. The lockfile adds only a dev-dependency on existing serde_json;
SHA-256 moved unchanged into core and no new unsafe boundary was introduced.

Fresh read-only evidence verification checked all 640 trial records, 616 available
endpoints and 5530 indexed files across the preserved original and correction rounds.
The canonical ledger hash remains 35b58ef0b0d58637288801bac2bdaa32b65b97b42b429debcffc615768c7c543;
study consumption is unchanged at 902.574545061 seconds. GitHub sign-in was restored
with the maintainer's device authorization. At pre-merge review, remote main was
still the reference 722e0b01aecc5875b44ae0a7124f7c1b41eeeeed, so no rebase was needed.

The [GPUP-5 interface handoff](../docs/plans/gpup5-interface-handoff.md) recommends
versioned experimental precision settings, preserving existing backend identities
and replay, and revisiting the reserved quantized selector before behavior. It is
linked from AGENTS, the roadmap, SPEC-0012 and the GPUP-5 backlog entry; the interface
decision remains pending. This documentation does not begin GPUP-5 implementation.

[PR #3](https://github.com/liuyumou/OptForge/pull/3) merged as
1982bbf8f4522f604f899983990ec0a7e849a10e. All six hosted CPU CI, Documentation and
Benchmark Smoke push/pull-request runs passed for reviewed head
7820ccf688bb759107386120505dee38cb3288c2. All 59 PR file blobs matched the reviewed
local tree. The [author review](https://github.com/liuyumou/OptForge/pull/3#pullrequestreview-5217348891)
is a self-review comment, not independent peer approval. The merge API required the
reviewed SHA; the resulting tree matches it exactly and retains 4bca1a0, 722e0b0
and e415918 ancestry.

Local main was fast-forwarded to the merge. Remote feature-branch deletion required
its expected head, then the merged local codex/gpup4-fp64-execution branch was
removed. Study archives, reference code objects, ignored artifacts and the canonical
ledger remain intact. No new GPU work, ruleset change or release tag was introduced.
Machine-readable merge, review, hosted-run and preservation receipts are retained
in artifacts/gpup4-pr-integration. This completion record follows the merge; GPUP-5
remains the next bounded task, beginning with its pending interface decision.

The completion documentation passed the full pinned-native gate in 30.104146154
seconds (411 Rust tests, 110 Python tests, 74 documentation pages). Both local
gate receipts are retained; no additional GPU time was consumed.

## GPUP-4: tuned FP64 execution (2026-09-15)

Status: complete; all required gates and study evidence passed, ready for local
commit. GPUP-5 is next_ready_task; no GPUP-5 behavior is implemented.
Objective: explicit cuda-lp-tuned under accepted SPEC-0012/ADR-0017; resident
allocation, necessary uploads, deterministic warp32 and two-kernel fusion, with
recorded execution settings/provenance. Legacy/matched behavior and host authority
remain. Runtime and reference source/code were archived before measurement.

The [reviewed report](../docs/benchmarks/lp-tuned-fp64-gpup4.md) retains 640 attempts:
320 original plus the separately frozen ADR-0018 correction, each 280 GPU/40 CPU.
The original remains interim after 24 archived-reference execute-permission failures;
its source/binary bytes, failed attempts and charges are preserved. The full
correction has 248 certified endpoints, 66 work limits and six host timeouts, with
no process/invalid/missing evidence or unsettled reservations. Each configuration
certifies 27/36 timings. All 36 GPU endpoint pairs preserve bits and iteration/restart
counts across ablations. Matched remains the general reference; fused warp32 is a
provisional comparison on three named development instances only. No preset,
held-out solve, lower precision, dispatch, publication or push is introduced.

Study charges: prior 445.988045904; original round 219.094449232; correction
237.492049925; GPUP-4 total 456.586499157 of 900 additional GPU seconds. Cumulative
902.574545061, below the exact 1345.988045904 ceiling, 1800-second baseline phase
and 28800-second campaign. Original authority/output binding and the exact 622-event
prior prefix are preserved. Final study ledger SHA-256:
35b58ef0b0d58637288801bac2bdaa32b65b97b42b429debcffc615768c7c543.
Correction raw index SHA-256:
9b560b44b74f2035525a2d0c86ea5438f03097fdb203e2fb33723b3023a98b77.
Correction source/archive/executable/code identities are in the report and immutable
artifacts/gpup4-tuned-fp64-correction-v1. Native-freeze receipt binds measured source
8307df2ecb105552551058d93d885d10e93063695b188889fe520705ccdaef86.

Acceptance budget: 60 CPU wall minutes, four build jobs; 30 GPU minutes, sequential
with CPU gates. The measured source passed all 410 Rust/110 Python tests and 73 doc
pages in 19.140472299 seconds. All 41 regular device cases passed on RTX 5090 and
PRO 6000. Eight scoped cases passed each of all four sanitizers on PRO 6000, zero
errors/racecheck warnings. RTX 5090 lacked memcheck memory (797 MiB free); both
failed attempts remain recorded. The final parser-only schema repair was reproduced
by a failing regression and passes afterward; measured iteration code/settings/code
object are unchanged, and its untimed status is explicit in the report. Final
41-case RTX 5090 acceptance plus CLI evidence/fallback/replay/altered-code rejection
passed in 16.587609922 seconds. Total acceptance GPU use including failures:
479.537579339 seconds of 1800. Complete receipts/logs: artifacts/gpup4-acceptance.

Review fixes cover peak observations on early stops, cached launch configuration,
executor/residency agreement, GPU overflow, signed bits in both vectors/anchors,
strict enum shapes, complete ledger/trial coverage, torn-ledger read refusal,
immutable pre-campaign history and archive execution permission. GPUP-1 independent
rational authority and matched trajectory regressions remain. Only a dev-dependency
edge to existing serde_json was added; no external package version or unsafe boundary
changed. Read CONTRIBUTING and known failures before implementation.

Final full pinned-native acceptance passed in 35.965244998 seconds: 411 Rust tests,
110 Python tests, 73 documentation pages, formatting/Clippy/rustdoc, dependency and
license policy, artifact/provenance checks and recorded-run replay. Native and
focused schema-regression receipts total 177.027801669 CPU wall seconds; builds
used four workers and remained within the 60-minute acceptance allocation. Final
GPU acceptance including failed attempts totals 479.537579339 seconds of 1800.
The post-measurement parser-only change has a failed-before/passed-after fixture,
full native acceptance and fresh 41-case/CLI RTX 5090 acceptance. The report names
its measurement limitation. The complete diff, legacy schema/source preservation,
unsafe boundaries and lockfile were reviewed. Commit locally; no push authorized.


## GPUP-2/3 PR review and integration (2026-09-15)

Objective: publish the completed branch, review its full diff, merge after acceptance
and hosted checks, synchronize main, and delete the completed branches. The user
explicitly authorized PR creation, self-review, merge and cleanup. Preserve the five
bounded implementation/diagnosis commits, source archives, model hashes and the
445.988045904-second cumulative study ledger; no new experiment or GPUP-4 work.

Status: complete. [PR #2](https://github.com/liuyumou/OptForge/pull/2) is merged
as 3c8d1ffba2b79e527a1dd32bcea2e695eb34ae80. Local main is synchronized; the
remote and local codex/gpup2-lp-measurement branches were removed after merged
ancestry verification. The five bounded commits and e415918 reference are retained.
Reviewed CONTRIBUTING, known failures and accepted contracts.
Gate: full pinned-native tools/check.sh; full branch/unsafe/dependency/CI review;
successful remote CPU/docs/smoke checks; verified merged ancestry before cleanup.
Budget: 30 minutes CPU review/acceptance with four build jobs; up to five minutes
GPU acceptance only if a runtime review fix requires it, sequential with CPU gates
and under the shared lease. Existing device/sanitizer evidence remains applicable
to unchanged runtime. GitHub authentication is restored with the maintainer's sign-in; Git SSH access
works. Two review findings are fixed: CI now fetches full history for the archived
e415918 schema comparison, and the lease test observes worker readiness before
measuring queue wait. The initial full native gate caught the latter race (40.380
ms observed against its 50 ms requirement); this was fixture startup timing, not
a lease exclusion failure. The corrected fixture retained its threshold, gained
an assertion that no child output opens under the held lease, and passed ten
consecutive runs (2.553 seconds). No runtime, kernel or measurement artifact changed.

Fresh full pinned-native acceptance passed in 19.144629400 seconds: 405 Rust tests,
103 Python tests, dependency/license checks, committed-record replay and 69 doc pages.
Logs and the failed first run are retained in artifacts/gpup-pr-review. No additional
GPU work was necessary; prior 38 regular device tests and five scoped cases under
each of four sanitizers remain applicable. Review checked the complete branch:
native row multipliers and sense/order normalization, independent endpoint authority,
matched checkpoints/work/cancellation, legacy compatibility, outward reduction
ordering and signed zeros, frozen generation, schema strictness and provenance,
ledger/crash recovery, lease/activity/process cleanup, report pairing/censoring,
CI and the lockfile's single internal dependency addition. No blocking review finding
remains after the two integration fixes. Preserve the original commit history on
merge because the accepted reference source is named by its commit.

Hosted acceptance: CPU CI, Documentation and Benchmark Smoke all passed for both
push and pull-request runs of reviewed head faf4a9075fe218872d2d85563cb3406f665f0f9c.
The [self-review](https://github.com/liuyumou/OptForge/pull/2#pullrequestreview-5206719687)
is recorded as an author comment review, not independent peer approval. GitHub
confirmed the merge at 2026-09-15T07:13:44Z. The merge API required the reviewed SHA;
remote deletion used an expected-head lease. No branch protection or hosting
configuration was changed. Machine-readable run IDs, review URL and merge receipt
are retained in artifacts/gpup-pr-review/integration.json. Completion documentation
is committed after integration; GPUP-4 remains next with campaign use unchanged.

## GPUP-3: shared resumable matched FP64 control (2026-09-15)

Status: complete; acceptance passed, ready for local commit. SPEC-0012 accepted before implementation; ADR-0016 freezes
the opt-in FP64 contract and comparative protocol. Prerequisites committed separately
as 18fe686 (schema/activity) and 223ee6c (bit-preserving certification), each after
its full native gate. No legacy controller/default, numerical target or frozen
baseline artifact changed. GPUP-4 is the next dependency-ready task.

The [reviewed report](../docs/benchmarks/lp-matched-fp64-gpup3.md) retains all 160
attempts: 144 primary timings and 16 profiles, all development-only, in one
468.090-second invocation. Matched CUDA and current host certified 27/36 timing
trials; both legacy CUDA builds certified 6/36. Three scheduling instances remain
infeasible at the matched iteration limit. No invalid/missing evidence, device
failure or fallback occurred. All 33 mutually completed reference/current legacy
pairs and 27 mutually certified host/matched pairs agree on candidate, witness,
objective, bound and gap bits. The report includes paired intervals and limitations.

Budget: 251.845179881 additional GPU seconds from the allocated 600; prior
194.142866023 carried forward through the original authority. Cumulative is
445.988045904 of 900, preserving the 1,800-second baseline phase, 28,800-second
campaign and remaining allocations. All 160 distinct attempts settled, no pending
crash reservation. Pre-reservation waits total 55.605846414 seconds, lease queue
0.002241305 seconds; no study restart. Original baseline summary and ledger hashes
are unchanged. Current ledger SHA-256:
49ea15fc24a24fcabb4e677d6a684ea8a8d0d6c5fc1d1a52dba7b098c827a8f3.
Raw source/binary/schema identities and indexed artifacts are in the report.

Acceptance uses the separate 60-minute CPU/four-build-job and 30-minute GPU budgets.
Premeasurement full pinned-native gate passed: 405 Rust, 103 Python and 68 doc pages,
18.273888354 seconds. CPU gates/builds and device workloads were sequential.
The 38 regular GPU cases and five scoped cases under each of memcheck, racecheck,
initcheck and synccheck passed with zero errors; racecheck zero warnings. The first
combined job then caught a missing controller phase in endpoint-v2's schema.
Schema/parser parity and a CPU regression fixed it; a full native gate and targeted
leased CLI evidence/fallback/replay rerun passed. Runtime/controller/kernel output
was unchanged. Both attempts are retained. Total GPU acceptance was
77.351226566 + 2.322113705 = 79.673340271 leased seconds, within 1,800.

Logs: /tmp/gpup3-measurement-ready.log/.json, /tmp/gpup3-acceptance and
/tmp/gpup3-cli-acceptance. Durable copies are indexed under
artifacts/gpup3-matched-fp64-v1 along with raw trials and independent verification.
No precision work, persistent checkpoint format, preset, general runner or
publication is included.

Final gate: full pinned-native bash tools/check.sh passed in 18.284103359 seconds,
405 Rust tests, 103 Python tests and 69 documentation pages, with dependency/license
checks, unchanged-record replay and smoke verification. Evidence is retained in
artifacts/gpup3-final-acceptance/native.log and native.json. Native log SHA-256:
8601cc1a629acab78d33c6661d7ddea10d00d35b7603f8d5be827f7832ec5f90.
Only completion-state documentation and backlog selection changed afterward;
the source/kernel/device acceptance and measured artifacts remain intact.
GPUP-3's required gates are satisfied; GPUP-4 is ready, with no new work authorized
by merely selecting that backlog item. Local commit includes all bounded GPUP-3
implementation, acceptance and handoff documentation.

## GPUP-3 prerequisite: bit-preserving certification cost (2026-09-15)

Status: accepted for local commit. Full pinned-native gate passed in 22.844
seconds: 398 Rust tests, 98 Python tests and 68 documentation pages. New tests
compare 138 length/input combinations bit-for-bit with the retained padded reducer
and verify exactly n-1 live enclosure additions across segment boundaries. All
independent exact-rational certificate/gap fixtures pass. No GPU work occurred.
Logs: /tmp/gpup3-cert-tests.log and /tmp/gpup3-cert-gate.log/.json.

Optimize only outward reduction padding under ADR-0016.
Keep the partition, meaningful addition order, rounded/enclosure bits, signed zeros
and conservative refusals. Keep the literal padded differential oracle and GPUP-1
exact-rational authority. Acceptance: signed-zero/subnormal/cancellation/overflow
and segment-boundary differential cases, meaningful operation counts, full native
gate. CPU only, four build jobs, charged to the combined 60-minute acceptance cap.
No GPU work or campaign consumption; runtime reduction/controller settings unchanged.

## GPUP-2 follow-up: schema reuse and activity admission (2026-09-15)

Acceptance: completed. Full pinned-native tools/check.sh passed in 18.026 seconds,
396 Rust tests, 98 Python tests and 68 documentation pages. The targeted study
suite passed 26 tests in 2.172 seconds, including schema reuse/strictness, immutable
refresh, residual activity, process exclusion, telemetry refusal, exact wait limits
and a simulated post-lease race that launches no child. No GPU work occurred.
Reference executable SHA-256 remains 9538f9b16f1fdf3e224674a9c2e4f76f5e797022f730f858eaf63d2080b048fb.
Evidence: /tmp/gpup3-harness-gate.log and .json; /tmp/gpup3-harness-tests.log.

Status: accepted for local commit. First bounded change in the maintainer-approved matched FP64
plan, followed by bit-preserving certification and GPUP-3. Read CONTRIBUTING,
known failures and accepted contracts. Accept SPEC-0012 with later requirements
explicitly deferred; ADR-0016 freezes implementation and supplementary measurements.
Preserve original artifacts, legacy behavior and 194.142866023 seconds of campaign
consumption. Objective: immutable reusable schema registries and cancellable,
accounted GPU admission. Acceptance: strictness/activity/lease simulations and the
full pinned-native tools/check.sh gate. Combined acceptance budget across changes:
60 CPU wall minutes, four build jobs; 30 GPU minutes sequential with CPU gates.
Supplementary study cap: 600 additional GPU seconds, cumulative 900, baseline
1,800 and campaign 28,800 unchanged. Record exact evidence before local commits.

## GPUP-2 follow-up: Diagnose slow GPU study (2026-09-15)

Objective: measure and carefully explain solver latency, convergence, GPU setup,
certification and study orchestration costs requested by the maintainer. This is
bounded diagnosis of the existing FP64 baseline, not GPUP-3 implementation.
Status: complete; accepted for local commit. GPUP-3 remains next.
Read accepted contracts and known failures first. Preserve
all frozen trials, original solver settings and exact-rational regressions.
Budget: 30 minutes CPU diagnostic/acceptance wall time, four build jobs; at most
120 additional GPU study seconds within the existing 900-second Slice 2 allowance
and 1,800-second baseline phase. Prior campaign spending is 173.148261443 seconds.
GPU jobs use the same RTX 5090 UUID and shared host lease; CPU gates and device
jobs run sequentially. If device acceptance is needed, separately cap it at five
minutes. No publication or later-slice algorithm changes.

Plan: audit phase accounting and implementation; time original-model evaluation,
certification and reductions independently; replay fixed GPU control on the host;
profile Python schema/analysis overhead; use bounded driver/kernel traces on
selected development cases. Freeze supplementary diagnostic choices and ledger
extension before GPU launches. Retain raw profiles under ignored artifacts and
write a reviewed diagnosis with uncertainty, reproduction and resource accounting.
Acceptance: useful component/trajectory consistency checks, full pinned-native
tools/check.sh for committed tooling, and independently verified device endpoints.

Evidence: CPU component/replay diagnostics completed in 15.27 seconds. Both
50,000-step fixed CPU replays matched every primal/dual bit of the archived GPU
endpoints. The first full pinned-native gate passed in 41.317 seconds, with
396 Rust tests, 91 Python tests and 66 documentation pages. Seven supplementary
GPU jobs completed with independent endpoint checks, using 20.994604580 seconds;
canonical cumulative consumption is 194.142866023 seconds. No additional GPU
acceptance job was required. Four activity pauses resumed only unattempted jobs.

Both Nsight traces retained raw qdstrm files despite automatic importer failure.
A missing libdw.so.1 was supplied from a pinned Ubuntu package extracted privately
to /tmp; offline import/export then succeeded, without new GPU work. Both traces
contain exactly 1,200 kernels for 200 iterations. A reviewed report and strict
raw-prefix/hash/ledger/count analysis are in
[the diagnosis](../docs/benchmarks/lp-gpu-slowdown-diagnosis.md). Main findings:
fixed-controller convergence, repeated padded host certification, setup/launch
costs and redundant schema construction. GPU transfers are small on these cases.
No solver/controller/kernel/default changed.

Final acceptance: full pinned-native bash tools/check.sh passed in
39.866 seconds, with 396 Rust tests, 91 Python tests, 67 documentation pages,
dependency/license checks, committed-record replay and smoke verification. The
native gates total 81.184 seconds; CPU component/replay measurement used 15.271
seconds; four recorded resume invocations plus intervening waits used 174.924
seconds, dominated by repeated ledger/schema validation. The initial invocation,
Python profiling, builds, provisioning and offline trace analysis also remained
within the declared 30-minute CPU allocation. Final log/summary:
/tmp/gpup2-diagnosis-final.log and /tmp/gpup2-diagnosis-final.json. No CPU gate
ran concurrently with GPU jobs. All indexed raw artifact hashes were rechecked;
original baseline evidence is unchanged.

Cumulative ledger SHA-256:
9a1bed26e90ad69bc641355c68ca6edff055268a3971f948df69cc89abeb254f.
Diagnosis SHA-256:
0c79e7bb322df44fdcaa7cc8679d0a6c7347138d721562822638eb44b570a7cb.
Remaining original Slice 2 allowance: 705.857133977 seconds; remaining baseline
phase: 1,605.857133977 seconds; remaining total campaign: 28,605.857133977 seconds.
No budget reset, repeated attempt, changed numerical threshold or publication.

## GPUP-2: LP measurement infrastructure (2026-09-15)

Objective: implement the maintainer-approved Slice 2 plan: accepted contract,
frozen repository/generated workloads, independent host-lp/cuda-lp/HiGHS
endpoints, strict artifacts, crash-safe accounting and a baseline cost report.
Status: complete; accepted for local commit. GPUP-3 is the next ready task.
Known failures have been read. Preserve GPUP-1 rational
regressions and existing host/GPU controller differences; no later slice.
Acceptance: full pinned-native bash tools/check.sh; adversarial artifact,
endpoint, budget/crash/lease/cleanup and analysis tests; regular device suites
and relevant new cases under all four sanitizers; development measurements.
Budget: 60 minutes CPU acceptance wall time, four Cargo jobs; 30 minutes GPU
acceptance sequential with CPU gates. Study cap 900 GPU seconds from the 1,800
baseline phase within the 28,800 campaign total. Device is exclusively
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 under the shared host lease.
Likely files: diagnostic backend APIs, CLI solve/study, experiment types/schemas,
Python tooling/tests, frozen manifests/configs, SPEC-0013, ADR-0014 and task/docs.
No publication. Evidence and actual consumption follow below.

Pre-measurement acceptance: two full pinned-native gates passed (50.974 and
39.336 seconds), each with 396 Rust tests, 89 Python tests and 64 documentation
pages. Release solver/device-test preparation took 10.299 seconds. Additional
CPU orchestration checks exercised one complete trial and an interim report with
source archive/raw-reference validation, with no GPU work. The second gate
includes a correction preventing --output from creating a fresh campaign ledger.

Device acceptance: all 35 regular device cases passed on the pinned RTX 5090.
Both new study_observation cases passed under memcheck, racecheck, initcheck and
synccheck, with zero errors; racecheck also reported zero warnings. The first
combined invocation exited 1 only at the CLI fallback fixture: it hid the
scheduling code object required to open a session, before LP fallback was reachable.
The corrected fixture preserves that object and hides only lp_pdhg.cubin.
The targeted CLI rerun passed device evidence and pinned fallback verification.
No runtime code changed for this fixture correction. Total GPU acceptance was
27.249 + 1.266 = 28.515 seconds, well within 1,800. Logs and timing JSON are in
/tmp/gpup2-gpu-acceptance.* and /tmp/gpup2-gpu-cli.*. This is the declared scoped
sanitizer acceptance, not a claim of running the historical broad sanitizer suite.

The third full pre-measurement native gate passed in 39.966 seconds with the
same coverage. All 144 development attempts then completed: 108 timing trials,
36 separate profiles, 48 GPU jobs. The canonical campaign ledger charged exactly
173.148261443 GPU seconds; CPU-only jobs used 202.666858567 seconds and additional
standalone host verification used 24.459310130 seconds. Two activity pauses resumed
on the same device/ledger without repeated trials. No validation/held-out solves.

The [reviewed baseline](../docs/benchmarks/lp-baseline-gpup2.md) records medians,
paired intervals, coverage, work, phases, memory, certificate quality and raw hashes.
CUDA certified 6/36 timing trials (two small witness cases), host LP 27/36 and
HiGHS 30/36. No fallback or malformed evidence occurred in the campaign. Failure,
work-limit and deadline evidence is retained. No solver default, seed, split or
numerical threshold moved; the exact-rational GPUP-1 regressions are unchanged.

Raw artifacts: artifacts/gpup-baseline-v1, with canonical budget storage in
artifacts/lp-campaign-ledgers/gpup-baseline-v1. Ledger SHA-256 is
aee3f1398725fedf8ad37d644c8960156b897b3a11478839359def4619eb8e37;
summary SHA-256 is c57de898e75b5c422efd09ed3590e8e9d39f97f2b50ce99535f63d1c41a6cc63.
The measured dirty source is archived and hashed in the report. Preserve spending
when a later slice introduces a recorded campaign migration. Remaining baseline
phase is 1,626.851738557 seconds; remaining total is 28,626.851738557 seconds.

Final review tightened the supervisor after measurement: persist SIGINT intent
before escalation, reap orphaned process-group children before releasing the lease,
and stream artifact hashes after checking model size. Fifteen targeted study tests
passed, including exact simulated deadline boundaries and orphan cleanup. Existing
raw measurements and their source archive remain intact; these tooling-only edits
introduce no solver, kernel, controller or protocol-setting change.

Final acceptance: bash tools/check.sh passed with pinned native HiGHS 1.11.0,
396 Rust tests, 91 Python tests, 65 documentation pages, dependency/license checks,
committed-record replay and smoke verification (39.666 seconds). The four full
native gates total 169.942 CPU wall seconds; release preparation was 10.299 seconds,
the last focused study tests 5.891 seconds, and explicit Rust validation of all
32 frozen models plus 24 planted primal witnesses was 1.215 seconds. Earlier
bounded orchestration/interim-report checks added approximately 4.17 seconds;
acceptance remained below the 3,600-second CPU allocation with four build jobs.
Logs: /tmp/gpup2-cpu-final.log and timing JSON; /tmp/gpup2-partition-validation.*.

The final supervised GPU CLI/evidence/fallback check passed in 1.467 seconds
(leased job 1.308638432 seconds). Signal history was empty for the successful job;
forced-signal and orphan-reaping cases passed the CPU simulation tests. Including
the prior regular suites, all four scoped sanitizers and failed fixture attempt,
GPU acceptance totals 29.981850548 seconds of 1,800. Its machine-readable worker
record is /tmp/gpup2-final-supervisor/acceptance.worker.json; summary is
/tmp/gpup2-gpu-final.json. No CPU gate overlapped device acceptance.

Slice 2's gate is satisfied. Preserve the accepted source/records, exact-rational
regressions, frozen splits/settings, unsuccessful trials and cumulative campaign
spending. GPUP-3 must accept SPEC-0012 before implementing shared resumable FP64
control. No mixed precision, C10 runner, supported preset or publication is included.

## GPUP-0/1 PR Review and Integration (2026-09-14)

Objective: review the roadmap and certification repair, publish one PR preserving
both slice commits, record the review, merge through GitHub after acceptance,
synchronize local main, and remove the two completed branches. The maintainer
explicitly authorized publication, self-review, merge, and branch cleanup.

Status: complete. PR #1 is merged, main is synchronized, and both completed
local branches plus the published feature branch have been removed. Base main is ee2d4fe; reviewed implementation is 61c53f4,
which includes roadmap commit f28bf0e. No later precision slice is in scope.

Acceptance gate: numerical proof and caller review; full pinned-native CPU gate;
finish the previously incomplete broad GPU sanitizer coverage if the bounded
integration allocation permits, otherwise explicitly assess the existing scoped
coverage; successful PR CI; remote merge confirmation and clean synchronized main
before branch deletion. GitHub author self-approval restrictions must be respected;
record the review without changing branch protections if formal approval is refused.

Resource budget: at most 30 minutes CPU gate wall time with four Cargo build jobs
and 30 minutes additional GPU acceptance on one device under the shared host lease,
sequentially with the CPU gate. Profiling and performance trials remain out of scope;
the eight GPU-hour research campaign is unspent. Likely files: active task, known
failures/publication state, and review evidence; runtime changes only for review
findings, with a fresh gate before publication.


Review evidence: checked the finite enclosure primitives, concave variable-bound
contributions, row repair, objective-sense conversion, conservative tolerance
arithmetic, both backend callers, and the shared reduction tree. The independent
Fraction oracle evaluates the stored coefficients without copying the interval
algorithm. No blocking numerical or contract finding was identified. Original-model
feasibility remains tolerance-based, and interval dependency can weaken/refuse a
certificate; neither limitation is hidden by the gap result. No runtime edit was
needed. The two original slice commits remain separate.

The fresh full CPU gate passed (23.30 seconds, pinned native HiGHS covered), with
390 Rust tests, 76 Python tests and 62 documentation pages. A GPU launch without
the provisioned Rust PATH failed before device work (0.08 seconds). The next run
failed from CUDA context allocation on the busy RTX 5090 (4.31 seconds); both
5090s had approximately 30 GiB allocated by other activity. Those processes were
left untouched. Remaining acceptance moved to the idle RTX PRO 6000 Blackwell,
UUID GPU-6721b13a-30f9-83ec-dace-ba2d9738556f, under the same host-wide lock and
remaining total budget. A temporary sanitizer wrapper adds --error-exitcode 99;
no test counts, timeouts inside tests, or numerical thresholds were reduced.

Publication readiness: the reviewed slice commits were pushed to
codex/fix-lp-certification through SSH. The maintainer completed GitHub CLI browser
login, enabling API access as liuyumou. Main was unprotected; merge settings and
protections remained unchanged. [PR #1](https://github.com/liuyumou/OptForge/pull/1)
was opened as a draft with its review prepared locally. Documentation and benchmark
smoke CI passed first; CPU CI initially hit the tooling-cache finding below.

Integration finding: the first remote CPU CI run failed before acceptance during
cargo-deny installation (run 34859538269, job 104027791392). The Cargo cache restores
bin/ but not Cargo installation metadata, so reinstalling reports "binary
cargo-deny already exists in destination". Bounded correction: verify the cached
binary reports exactly cargo-deny 0.19.0; reuse that version, otherwise install the
same pinned locked package with --force. No toolchain or dependency version changes.
The final local gate and remote CI must pass after this workflow edit.

Sanitizer scope decision before the remaining runs: the broad PRO 6000 job was
stopped after 1,294.10 seconds during the existing atomic-reduction negative-control
stress case under racecheck. The 20,000-iteration publication test had completed
successfully under racecheck; the original Slice 1 coverage gap at that case is
therefore narrowed. The entire broad job is still not a completed gate. Use the
remaining total allocation for all three full initcheck and synccheck suites,
both non-LP full racecheck suites, and the 11 other LP racecheck cases (excluding
the already-observed publication case and the unfinished atomic stress case).
Keep error-exitcode 99 and every test's internal settings unchanged. Review accepts
this explicit sanitizer coverage for a host-only arithmetic repair with unchanged
kernels and prior scoped coverage on RTX 5090; it does not waive a known numerical
failure or claim the entire broad sanitizer gate passed.

Final device evidence: the nine supplemental invocations all passed with exit 0
in 251.97 seconds. Full initcheck and synccheck each ran 13 LP, six scheduling,
and 14 CUDA tests with zero errors. The completed racecheck invocations ran 11 LP,
six scheduling, and 14 CUDA tests with zero errors and warnings; only the LP
invocation filtered the two explicitly named cases above. Together with all
regular device suites, all three full memcheck suites, the observed long publication
test completion under racecheck, and the prior RTX 5090 scoped checks, this is the
accepted coverage. The unfinished atomic negative-control racecheck remains a
known acceptance limit, not a full broad-gate pass. No device test silently skipped.

Total additional GPU acceptance: 1,550.46 seconds including both failed launches,
the stopped broad job, and supplemental checks; within 1,800 seconds. No CPU gate
overlapped GPU acceptance, and the performance campaign remains unspent. Logs:
/tmp/gpup-pr-cpu.log, /tmp/gpup-pr-gpu-launch-failure.log,
/tmp/gpup-pr-gpu-5090-oom.log, /tmp/gpup-pr-gpu.log, and
/tmp/gpup-pr-remaining-sanitizers.log, with timing summary JSON siblings. These are
ephemeral acceptance diagnostics. Reproduction and scope are recorded in
[LP certification arithmetic](../docs/architecture/lp-certification.md).

Final local acceptance after the CI/documentation edits: bash tools/check.sh passed
with pinned native HiGHS 1.11.0, 390 Rust tests, 76 Python tests, and 62 documentation
pages (23.53 seconds; /tmp/gpup-pr-cpu-final.log and its timing summary). The CI setup
shell passed bash syntax validation, and the cached-tool guard's version string was
checked against the actual pinned binary. The original runtime and CUDA files are
unchanged from 61c53f4. PR CI, review publication, merge, and cleanup follow this
accepted local tree. Final integration evidence follows.

Integration evidence: both push and pull-request CPU, documentation, and benchmark
smoke CI passed on PR head 1930a0b09c4b0c0f9c8009111480203c0592fc12. CPU workflow
runs 34862464456 and 34862468896 passed; manual-only GPU discovery was skipped as
configured and is not GPU acceptance evidence. GitHub rejected a formal author
APPROVE review ("Can not approve your own pull request"). The completed technical
approval, including acceptance of the sanitizer scope, is published as a
[COMMENT review](https://github.com/liuyumou/OptForge/pull/1#pullrequestreview-5199671767).
This is the requested agent self-review, not an independent human review or a
formal GitHub approval event. No branch protection or merge setting was changed.

GitHub confirmed PR #1 merged at 2026-09-14T15:32:28Z, merge commit
2c84a95e8580bb51ac74dff6bfe4535b2edbb282. The rebase check was a no-op against
unchanged main ee2d4fe. A merge commit preserves the original roadmap, numerical
repair, and review-evidence commit identities and their documentation references.
The merged tree exactly matches the CI-tested PR head. Local main fast-forwarded;
both former branch tips were verified as ancestors before deletion. The remote
feature branch was deleted with an expected-head guard, both local branches were
removed with git branch -d, and remote references were pruned. The roadmap branch
had never been published.

Post-merge audit acceptance: bash tools/check.sh passed on synchronized main
with the completed task/publication records (33.46 seconds), again covering pinned
native HiGHS, 390 Rust tests, 76 Python tests and 62 documentation pages. The log is
/tmp/gpup-pr-main-audit.log with its timing summary. Total local CPU gate wall time
for integration was 80.29 seconds, within the declared 30-minute allocation.

This post-merge audit changes task/publication records only. Follow-up remains
GPUP-2: finalize and accept SPEC-0013 before the LP experiment harness. No later
slice, performance experiment, or supported low-precision recipe was introduced.

## GPU LP Precision Slice 1: Conservative Certification (2026-09-14)

Objective: reproduce and repair the zero-reduced-cost cancellation defect, bound
rounding uncertainty conservatively through certification, and review objective/gap
arithmetic and minimization/maximization termination in both first-order backends.

Status: complete. GPUP-0 is complete; this is GPUP-1 only.

Acceptance gate: independent exact-arithmetic regressions, the full
`bash tools/check.sh` gate with pinned native HiGHS, and the device acceptance and
sanitizer gate if the shared host-side change reaches device integration. Resource
budget: up to 60 minutes CPU gate/test wall time with four Cargo build jobs; up to
15 minutes GPU acceptance under the shared host lease on one device, sequentially
with the CPU gate. No performance study jobs; the eight-hour campaign remains
unspent. No GPU kernel or iteration arithmetic change is planned.

Likely files: optimizer-lp certification, a private outward-arithmetic helper,
shared objective/gap assessment, host/device backend integration, regression
fixtures and exact validation tooling, SPEC-0011, numerical documentation,
changelog, known failures, roadmap and backlog. No new runtime dependency or
unsafe boundary is authorized. Existing caller tolerances remain unchanged.

Evidence (2026-09-14): the rounded-zero and free-variable regressions both failed
against the old certifier, which returned bound 0 and allowance 0. The separate
maximization gap regression also failed before repair. All now pass. The rational
oracle covers 1,083 primitive arithmetic cases, five fixed-tree sums (including a
multi-segment sum), 26 certificate cases, and 18 objective/gap cases; the Python
integration gate independently regenerates the fixture from exact Fractions.

The final `bash tools/check.sh` passed, exit 0: pinned native HiGHS 1.11.0,
390 Rust tests, 76 Python tests, artifact/provenance validation, committed-record
re-execution, and 62 documentation pages. The final gate took 27.46 seconds; both full CPU gates stayed within the
declared allocation and ran sequentially with GPU acceptance.
No runtime dependency, GPU kernel, original-model coefficient, caller tolerance,
experiment seed/split, or solver default changed.

Device evidence: RTX 5090, UUID GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48,
driver 580.105.08, provisioned CUDA 13.0 code objects. All three regular device
suites passed, including the new maximization case and existing bitwise iteration
comparisons. All three full memcheck runs reported zero errors. The broad
`tools/gpu_check.sh` sanitizer invocation was explicitly stopped during the
existing 20,000-iteration publication test under racecheck; **the full broad
sanitizer gate did not complete and is not claimed as passed**.

Bounded replacement coverage: memcheck, racecheck, initcheck, and synccheck each
ran the new one-iteration maximization integration, the existing 400-iteration
CPU/GPU bitwise comparison, and the wide-row differential case. All 12 scoped
runs reported one executed passing test and zero errors, with no skips. The
scoped commands set `--error-exitcode 99` and retained the existing test iteration
counts/thresholds. This is the relevant sanitizer coverage for unchanged kernels
with repaired host-side certification/gap arithmetic; reproduction commands are
in docs/architecture/lp-certification.md.

The stopped broad job consumed 499.99 seconds and the scoped checks 59.74 seconds:
559.73 seconds total acceptance wall time, within the 900-second allocation,
on one device under the shared host lease. Performance campaign consumption is
zero. Local logs and machine-readable timing summaries are in
`/tmp/gpup-1-cpu-final.log`, `/tmp/gpup-1-gpu-acceptance.log`, and
`/tmp/gpup-1-scoped-sanitizers.log` with sibling summary JSON files. These are
ephemeral acceptance diagnostics, not retained performance artifacts.

Resolution: certification carries outward enclosures through original-model
products, reductions, reduced costs, variable contributions, and the final sum.
Both LP backends use the shared outward objective/gap check, including sense
conversion and conservative finite tolerance arithmetic. Certificate fields stay
compatible; LP record gaps remain absolute objective-unit diagnostics, now
nonnegative conservative upper bounds. Feasibility and reported objective values
retain their existing tolerance-based meanings. Interval dependency and overflow
can weaken or prevent a certificate, as the numerical documentation records.

Follow-up: GPUP-2 is ready. Complete and accept draft SPEC-0013 before implementing
the LP-only measurement harness; freeze its concrete manifests, artifacts,
analysis and campaign accounting before performance trials. This repair satisfies
the certification prerequisite and does not implement mixed precision, select a
recipe, or complete C7/C9/C10.

## GPU LP Precision Slice 0: Roadmap and Contracts (2026-09-14)

Objective: persist the user-approved GPU LP performance roadmap as a separate,
dependency-ordered research track, draft its numerical and experiment contracts,
and record the prerequisites before any new arithmetic is implemented.

Status: complete. This slice changes documentation and task state only.

Acceptance gate: `bash tools/check.sh` with the pinned native HiGHS build,
documentation link/anchor validation, and a manual requirement-to-test and backlog
dependency review. Resource budget: CPU only, at most 30 minutes of gate wall time
with four Cargo build jobs; zero GPU work. The first later experiment campaign has
an eight GPU-hour cap, not a budget consumed by this documentation slice.

Likely files: the new roadmap under `docs/plans/`, two draft specifications,
arithmetic/reproducibility and experiment ADRs, project navigation, benchmark
protocol, changelog, backlog, and known failures. Existing runtime behavior,
experiment seeds, splits, thresholds, and solver defaults remain unchanged.

Acceptance evidence (2026-09-14): `bash tools/check.sh` passed, exit 0, with
pinned native HiGHS 1.11.0, 380 Rust tests, 72 Python tests, artifact/provenance
validation, committed-record re-execution, and 61 documentation pages with valid
local links/anchors. The gate completed within the 30-minute CPU wall-time budget;
GPU jobs and GPU campaign consumption: zero. The full local gate log is
`/tmp/gpup-0-acceptance.log` (ephemeral, not a retained benchmark artifact).

Supplemental review checked all 38 SPEC-0012 and 35 SPEC-0013 numbered requirements
against their planned acceptance mappings, unique backlog identities and ordered
dependencies, the campaign allocation sum (28,800 GPU seconds), and the exact
rational objective in the cancellation counterexample. These are documentation
and planning checks; none is recorded as runtime precision or performance evidence.
No runtime source, schema, dependency, experiment manifest, seed, threshold, or
default changed. ADR-0012 and ADR-0013 accept design decisions; SPEC-0012 and
SPEC-0013 remain drafts requiring completion before their implementation slices.

Follow-up: GPUP-1 is ready under the existing SPEC-0011 certification contract.
Reproduce the recorded cancellation case with an independent exact-arithmetic
fixture; repair conservative reduced-cost/contribution handling including uncertain
signs and infinite bounds; review objective/gap rounding and objective-sense
conversion; run the full gate and record evidence before any lower precision.
The known-failure entry remains open. GPUP-2 then finalizes and accepts the LP
experiment contract before implementing measurement. C7/C9/C10 remain planned,
and repeated-solve throughput and full MILP performance are separate future tasks.

## C6 Clean-Checkout Verification and Local Integration (2026-09-13)

Objective: verify C6 from a checkout with nothing prebuilt before integrating it, as
the C4, C8 and Track B branches each were, and as this branch already was at `6dbaf8c`
when only SPEC-0010 was implemented.

Status: complete. The branch is integrated into local `main` by fast-forward.

Acceptance gate: `bash tools/check.sh` passes in an independent clone with no `target/`
directory, no provisioned HiGHS library, no provisioned device code object, and no CUDA
toolkit on `PATH`. Resource budget: CPU only, no GPU workloads — which is itself part of
what is being verified.

The earlier verification at `6dbaf8c` no longer covered the tree. Eight commits since
then added two crates, a schema, two examples, a step to the acceptance gate itself and
a second code object, and every one of those is surface a clean clone exercises and a
warm working tree does not. Re-running it was the point of having the ritual.

What the clone establishes that a local run cannot. The build script's warning fired
four times, so `cuda_native` was unset throughout and every device path compiled to its
unsupported form: ADR-0009's "nvcc is a provisioning dependency, never a build
dependency" observed rather than asserted, and now covering the linear-programming
kernels as well as the integer ones. `nvcc` was absent from `PATH` deliberately. The
pinned HiGHS library was built from source inside the clone, so native acceptance was
covered rather than skipped — the loud banner did not print and the differential test
against the standalone reference ran. And the twelve device tests reported their skips
rather than failing, which is what keeps a host with no GPU a full gate pass.

Evidence (2026-09-13): cloned with `--no-hardlinks` at `d7c2118` with no `target/`
present; `bash tools/check.sh` passed there, exit 0, with 380 Rust tests, 72 Python
tests and 56 documentation pages — the same counts as the working tree.

`Cargo.lock` gained three workspace entries across this branch: `optimizer-cuda-sys`
from the device work, and `optimizer-lp` and `optimizer-lp-cuda` from the
linear-programming work. No third-party crate was added — the diff contains no new
`source` line — so the workspace still resolves the same eighteen external packages,
which is what `cargo deny --locked check` confirms on every gate run. No code object,
native library or other build output is tracked; `git ls-files` finds no `.cubin`,
`.ptx`, `.so`, `.a` or `.o`.

Integration was a fast-forward. `main` had not moved, so the branch was already linear
on top of it and the rebase CONTRIBUTING.md asks for before integration was a no-op;
this repository's history carries no merge commits and that is preserved.

Not pushed. Everything after `dfdc245` remains local, as `state/known-failures.md`
records, and publishing needs authorization this task does not carry.

Follow-up: C6 is complete and integrated. C7 is next and has no specification; it needs
one before any behavior.

## C6 Evidence and the Limits It Carries (2026-09-13)

Objective: reach SPEC-0011 requirements 17, 20, 21, 22 and 23 — the two tests ADR-0010
names as the ones that can fail, the fallback, and the rule that no acceptance artifact
records a timing — and record what C6 does not establish.

Status: complete. C6 is complete: both its contracts are implemented with evidence, and
the backlog line closes.

Acceptance gate: `bash tools/check.sh` plus
`bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh`. Resource budget: one GPU under
the shared host lease, for the device runs only.

Requirement 22 needed an early-stopped iterate to mean anything. At convergence the
certified bound and the pinned backend's can round to the same `f64` — that backend
sets its bound equal to its objective for a continuous LP — so a converged instance
would have made "strictly weaker" turn on rounding rather than on the procedure. Three
iterations produce a bound that is valid and visibly weaker, which is what ADR-0010
asks for: a certificate that only ever agrees has not been shown to be a certificate.

The other able-to-fail test asserts three things because the hazard has three parts. A
point outside the row bound looks better than the optimum, `Model::evaluate` refuses it,
and no multiplier — including two scaled by 1e9 — turns into a bound below the true
optimum. A wrong kernel's most dangerous output is a plausible number better than the
truth, and two independent host computations stand in its way.

Requirement 20's fallback is provoked by a code object that is not there, which is a
real availability failure rather than a simulated one, and the test asserts the failure
fired before asserting the agreement. Without that ordering the agreement would hold
just as well if the device had quietly succeeded.

One gap was found by running the end-to-end command rather than by reading the
contract. The device backend ran to its iteration limit and assessed once, so the
recorded check interval changed nothing — requirement 10 exists precisely to stop an
interval being a number that is recorded and ignored. It now assesses at each interval,
and a test asserts both halves: that the interval is consulted, and that changing it
leaves the iterates bit for bit identical. The second half is the one that could have
gone wrong quietly, because the Halpern coefficient sequence has to continue across an
interval boundary rather than restart at it.

Seven entries were added to `state/known-failures.md` rather than left implied: no
dispatch threshold for either contract, a fallback that cannot be verified field for
field, the difference between a device that cannot be opened and one that fails after
opening, tolerances reused as an optimality-gap policy, bitwise CPU/GPU identity being
this project's property rather than the contract's, the third device suite not running
in CI either, and the two candidate explanations any weak bound on a scheduling
instance would have.

Evidence (2026-09-13, RTX 5090, driver 580.105.08, CUDA 13.0):
`bash tools/check.sh` passed, exit 0, 380 Rust tests, 72 Python tests, 56 documentation
pages, every device test reporting an explicit skip.
`bash tools/gpu_job.sh GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 bash tools/gpu_check.sh`
passed, exit 0: three device suites, twelve sanitizer runs across memcheck, racecheck,
initcheck and synccheck, zero errors.
End to end, `optimizer solve --backend cuda-lp --device GPU-...` writes a record naming
`cuda-lp`, carrying the settings that produced it, an objective the host recomputed and
a bound below the true optimum, and terminating as `iteration_limit` rather than
claiming a proof it did not have at the caller's tolerance.

One observation worth carrying: `tools/check.sh` is CPU-only but not independent of
device activity. `test_a_named_device_is_refused_rather_than_run_on_the_cpu` blocked for
the lease's full timeout while a device gate held it, and the gate failed on a timeout
rather than on a defect. That is the lease behaving as SPEC-0006 specifies, not a new
fault, but running both gates at once on one host does not work.

Follow-up: C6 is complete. C7 is next and has no specification; it needs one before any
behavior.

## C6 First-Order LP Kernels on a Device (2026-09-13)

Objective: reach the device halves of SPEC-0011 requirements 5 to 8 — the iteration's
kernels in `f64` on a leased device, with the reduction order fixed so a result cannot
depend on how the hardware scheduled it.

Status: complete. This is the last implementation slice of SPEC-0011 and therefore of
C6.

Acceptance gate: `bash tools/check.sh` on the CPU, where every device test reports an
explicit skip, plus `bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` on hardware.
Resource budget: one GPU under the shared host lease, for the device runs only.

`optimizer-lp-cuda` is a separate crate rather than a module in `optimizer-cuda`. That
crate is what every existing GPU consumer depends on, so putting the LP engine there
would force `optimizer-cuda` to depend on `optimizer-lp` and make the CLI and the
scheduling examples compile an engine none of them calls. It would also put a `Backend`
implementation in the crate that owns discovery and the lease. The new crate inherits
the workspace lints, so it forbids unsafe and opens no second boundary: it reaches
hardware only through `optimizer-cuda-sys`, which is the one ADR-0009 authorizes. The
single change to that boundary is an `F64` kernel argument, which requirement 5 makes
unavoidable.

A real defect was caught before it could hide. The first kernel accumulated per-segment
partials left to right while the host reduces them by the same tree. Those orders agree
for any line of at most `SEGMENT` entries and disagree for every wider one, so the
models this project currently produces would all have passed and the defect would have
surfaced later as an unexplained disagreement on a large instance. The kernel now
performs the same two-level recursion, and a test builds a deliberately wide row to
exercise the second level — without it the agreement tests would only ever cover the
single-segment path.

The able-to-fail instrument for determinism substitutes the atomic reduction *inside*
`spmv_row` rather than adding a second kernel beside it. A separate kernel could drift
from the real one and leave the instrument measuring something else; substituting into
the production path is also literally what the specification's acceptance section asks
for. The first attempt did add a separate kernel, reached by hand-written launch code in
the test, and that code faulted — which is its own argument for exercising the machinery
the other tests use.

Bitwise CPU/GPU identity holds and is asserted, but it is this project's property rather
than the contract's. Requirement 8 asks only for same-device reproducibility. The
identity needs `-fmad=false` on the device, Rust never contracting on the host, and the
`log`, `exp` and `sqrt` staying host-side; the test re-verifies it on every run instead
of assuming it. A tolerance was rejected because a tolerance on an iterative method is
nearly untestable: loose enough to pass at iteration ten thousand, it hides a real
defect at iteration ten.

`tools/check.sh` gains a grep for atomic accumulation outside the guarded build. It is
CPU-only and it is the sole guard on a host with no GPU, where the device suite reports
a skip. Its first version flagged the file's own documentation of the prohibition and
was tightened to match the call rather than the name; both directions were then checked.

Evidence (2026-09-13, RTX 5090, driver 580.105.08, CUDA 13.0):
`bash tools/check.sh` passed, exit 0, 372 Rust tests, 72 Python tests, 56 documentation
pages, with all ten device tests reporting explicit skips.
`bash tools/gpu_job.sh GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 bash tools/gpu_check.sh`
passed, exit 0: three device suites and twelve sanitizer runs, three binaries under each
of memcheck, racecheck, initcheck and synccheck, zero errors.

Follow-up: the evidence record and the limits that must be carried rather than hidden.

## C6 Backend Selection at the Run Surface (2026-09-13)

Objective: reach SPEC-0011 requirements 18 and 25 — the first-order backend
reachable by explicit caller configuration, with the pinned CPU backend still the
default, and the settings document a caller supplies validated by both authorities.

Status: complete for the host backends. Requirement 20's fallback and requirement 17's
relaxation forfeiture belong to the device backend and are not reached yet.

Acceptance gate: `bash tools/check.sh` with the pinned HiGHS library present.
Resource budget: CPU only, no GPU workloads.

`optimizer solve` gains `--backend` and `--lp-settings`. The default is the pinned
backend, and it is the default in the strongest available sense: there is no threshold
anywhere that could promote a solve to another backend, so nothing could say otherwise.
That is deliberate rather than unfinished. Requirements 18 and 19 make a dispatch
threshold a recorded measurement, and `state/known-failures.md` already records for
SPEC-0010 requirement 22 that this project commits no such number without an ADR and
held-out evidence. The same entry now covers two specifications.

Settings are required rather than defaulted when the first-order backend is named, and
`--lp-settings` is refused outright for a backend that has none. A caller who thinks
they configured something is told they did not, rather than having the flag ignored.

`lp-settings-v1` is its own schema rather than a block inside the record. It is a
document a caller passes on the command line, so it needs to be checkable on its own,
and the record `$ref`s it exactly as it already `$ref`s the solve configuration. Both
authorities are asserted to refuse the same documents: the Rust parser and the JSON
Schema each reject a settings document missing any recorded field, and a record
embedding an incomplete block is rejected too.

`examples/lp-model-v1.json` is new because the existing example model is discrete, so
the specification's own worked example would have refused. Both examples are now
validated by `tools/validate_artifacts.py`, so a committed example cannot drift from
the schema a record embeds it under.

Evidence (2026-09-13): `bash tools/check.sh` passed, exit 0, with 362 Rust tests, 72
Python tests and 56 documentation pages. Eleven tests are new. The default reaching the
pinned backend is asserted positively, on the backend named in the record rather than
by observing that nothing else happened. Both backends are shown to agree on the
example model, which is what makes naming one a choice of implementation rather than a
choice of answer. The discrete refusal is asserted end to end at the run surface, not
only in a unit test: exit 2, `unsupported`, and the record still names the backend that
refused.

Follow-up: the device kernels, then the evidence record and the honest limits.

## C6 Host First-Order Engine and Backend (2026-09-13)

Objective: reach SPEC-0011 requirements 3, 5, 8, 10, 14 to 16, 21 and 24 to 26 — the
restarted primal-dual method on the host, a backend that claims only what two
independent computations support, and a record that states the settings it ran under.

Status: complete. Requirements 9 and 10's recording half lands here as
`solve-record-v2`. Requirements 17 to 20 (relaxation forfeiture, dispatch and
fallback) belong to the CLI surface and are not reached yet.

Acceptance gate: `bash tools/check.sh` with the pinned HiGHS library present.
Resource budget: CPU only, no GPU workloads.

Two version constants now exist where one did. `SOLVE_SCHEMA_VERSION` keeps its value
and its meaning narrows to the configuration; `SOLVE_RECORD_SCHEMA_VERSION` is 2. That
split is what confines the bump: the configuration is embedded in `search-config-v3`,
so bumping it would have moved the search configuration, the search record and the run
record as well — four documents to record something no configuration carries. Nothing
embeds a solve record, so the record moves alone. The settings are constructor state,
which is what SPEC-0011's own `open(residency, settings)` interface already implied.

The settings documents live in `optimizer-core` for the same reason `ProblemClass`
does: a record carries them, records are core types, and a second copy in the
implementing crate would be the drift SPEC-0008 requirement 8 exists to prevent. The
method stays in `optimizer-lp`.

A sign convention was wrong on the first attempt and the test caught it. The method
converged to an infeasible point with objective -2 on an instance whose optimum is
-1.5, because the dual update used the saddle function with the opposite sign of the
one the certification assumes. The fix is not cosmetic: this module takes
`cᵀx − yᵀAx + h(y)` so that the reduced cost is `c − Aᵀy`, the ordinary linear
programming convention and the one the certification recomputes. Under the other
convention the multipliers come out negated, certification stays *valid* — it is valid
for any vector — and every bound is uselessly weak. That is a much harder defect to
notice than a wrong answer, which is why the convention is now stated where the update
is written. With it right, the engine's own dual on the worked instance is exactly
-1.0, the true optimal dual, and the certified bound sits one rounding allowance below
the optimum.

Two departures from the published method, both made for determinism and both
recorded rather than absorbed. The step size is fixed rather than line-searched,
because an adaptive step retries an input-dependent number of times and the trial
count would then depend on rounding. The power iteration count is fixed for the same
reason. The cost is convergence rate, which requirement 23 forbids claiming anything
about in either direction.

The KKT residuals this module computes steer the algorithm and justify nothing. No
bound, status or proof reads them. A device computing them badly converges badly and
cannot produce a wrong answer — a distinction easy to lose at a glance, so it is
written where the residuals are.

Evidence (2026-09-13): `bash tools/check.sh` passed, exit 0, with 355 Rust tests, 68
Python tests and 56 documentation pages. Twenty-three tests are new. Agreement with
the pinned backend is asserted over the same four LP shapes its own differential
acceptance uses, with a mutated instance shown to disagree so the comparison is known
able to fail. All four fixtures reach optimality with a certified bound, which is
asserted rather than assumed: without that assertion the closure test would pass by
taking its other branch if certification ever regressed.

Follow-up: the CLI surface, dispatch and fallback, then the device kernels.

## C6 Host Certification of a Dual Bound (2026-09-13)

Objective: reach SPEC-0011 requirements 11, 12 and 13 — a bound produced only by a
host-side procedure that does not assume the device computed anything correctly, and
that is valid even when the iterate is far from optimal.

Status: complete. This is the piece ADR-0010 calls load-bearing in a way little else
in the project is, and it is tested for validity far from optimality rather than only
near it.

Acceptance gate: `bash tools/check.sh` with the pinned HiGHS library present.
Resource budget: CPU only, no GPU workloads.

Nothing here reads a residual, a norm or an objective any device computed. The only
device-produced numbers the procedure touches are the row multipliers, and they enter
inequalities that hold for every real number. That is what makes the result a
certification rather than a check: the reduced costs are recomputed from the model's
own coefficients, so `z = c − Aᵀŷ` is true by construction rather than claimed.

The two sides of the repair are not symmetric, and the asymmetry is the reason
ADR-0010's wording was corrected in `fde1d82`. A row multiplier with the sign whose
bound is infinite can be zeroed, because projecting it breaks no identity. A reduced
cost cannot, because it is determined by the multipliers, and adjusting one alone
would falsify the identity the bound rests on. Where a variable's bound is infinite on
the side its reduced cost needs, the infimum really is negative infinity and the
honest answer is no bound, naming the variable. Clamping to a large finite number
would fabricate one and is the most dangerous shortcut available in this module.

Both mechanisms were checked to be load-bearing rather than assumed to be. Removing
the repair fails three tests including the central validity one. Removing the rounding
allowance fails the test written for it.

Finding an instance where the allowance matters took a search, and the search is worth
recording because the first attempt produced a test that proved nothing. A violation is
pure `f64` rounding, so it only appears where the margin is zero: at the optimal dual,
where complementary slackness makes every bounded term tight. Away from it the slack is
of order the reduced costs, and rounding at 1e-16 cannot reach across — half a million
random multipliers produced no violation at all. With the multiplier set to the one that
zeroes a variable's reduced cost, an instance appeared whose raw sum exceeds the true
optimum by 6.6e-14. The first version of this test used an instance where the raw sum
landed exactly on the optimum, and asserted only that the allowance was positive and the
bound weaker; that would have passed with the subtraction deleted.

Evidence (2026-09-13): `bash tools/check.sh` passed, exit 0, with 332 Rust tests, 68
Python tests and 56 documentation pages. Eight tests are new. Validity is asserted
against every feasible point on a grid rather than against an optimum, because weak
duality claims the bound is below the objective everywhere feasible — testing the claim
itself needs no second solver and no optimum. The multipliers include zero, a
sign-flipped one and two scaled by 1e18, none near optimal.

Follow-up: the host PDHG engine and the settings document, which is where requirements
9 and 10 are recorded and where `solve-record-v2` lands.

## C6 Canonical LP Form and Fixed Reduction Order (2026-09-13)

Objective: reach SPEC-0011 requirements 6, 7 and 27 — the constraint matrix in both
orientations, one reduction order both engines share, and a recorded preconditioner.

Status: complete. Requirement 9's recording half waits on the settings document; what
lands here is the preconditioner itself and the proof that it is a pure function of
its parameters, which is what makes recording them sufficient.

Acceptance gate: `bash tools/check.sh` with the pinned HiGHS library present.
Resource budget: CPU only, no GPU workloads — deliberately, because this crate is the
oracle the device kernels will be checked against and must not need one.

The new `optimizer-lp` crate takes no device dependency and adds no third-party crate,
so `cargo deny` still resolves the same eighteen external packages. It inherits the
workspace lints, so it forbids unsafe; ADR-0009's single new boundary is untouched.

Holding the matrix twice is the requirement that most looks like a performance choice
and is not. Each product reads the orientation whose major axis it writes, so every
output element is owned by exactly one accumulation and no atomic is needed anywhere.
The column-major form is built from the same triples transposed rather than derived
from the row-major one, because deriving it would make a defect in the first invisible
in the second, and the two exist to be an independent pair.

`SEGMENT`, the tree, and the `+0.0` padding are one definition rather than a rule the
kernel will restate. Padding is what removes the length from the tree shape, and it
changes no bit because adding `+0.0` is an exact identity.

The reduction has two orders on purpose. `DeviceMirror` is the kernel's own, so a host
and device result can be compared bit for bit and a drifted index shows immediately.
`Sequential` shares no order with the kernel, so agreement with it is evidence about
the method rather than about a copied summation. One number could not establish both.

Two tests earned their place by being rewritten. The first version of the partition
test compared `tree_sum` with itself, which asserts only determinism — a much weaker
claim than the one its name made, and one the repeatability test already covers. It
now checks a literal transcription of the documented steps, written separately, bit
for bit across seven lengths including the segment boundary. And
`a_tree_sum_differs_from_a_left_to_right_sum_on_a_catastrophic_input` exists because
without it every later determinism assertion would be vacuous: if no input
distinguished the two orders, any order would satisfy them.

Evidence (2026-09-13): `bash tools/check.sh` passed, exit 0, with 324 Rust tests, 68
Python tests and 56 documentation pages. Fifteen tests are new, covering both
orientations holding the same nonzeros, infinite bounds surviving conversion, a
maximization negated once and reported back in the caller's direction, a discrete
model refused rather than relaxed, the documented reduction rule, the two orders being
distinguishable, padding changing no bit, and the preconditioner being a pure function
of its recorded parameters.

Follow-up: the host certification, which is the load-bearing piece.

## C6 Backend Capability Declaration (2026-09-13)

Objective: reach SPEC-0011 requirements 1, 2 and 4 — a declaration a caller can read
without knowing which implementation it holds, and which that caller cannot widen.

Status: complete. Requirement 3's refusal is not reached here, because it needs a
backend that refuses something, and the pinned adapter accepts every class.

Acceptance gate: `bash tools/check.sh` with the pinned HiGHS library present.
Resource budget: CPU only, no GPU workloads.

`ProblemClass` moved from `optimizer-extension` to `optimizer-core` and is re-exported
from its old path. It is a relocation rather than a redesign: its only constructor
already read nothing but `Model` and `Domain`, both core types, and the serde
implementation was carried verbatim. The alternative was a second enum on the solve
contract with the same two variants and the same wire form, which is the drift
SPEC-0008 requirement 8 exists to prevent arriving from a new direction — a registry
entry claiming `continuous` and a backend declaring `continuous` would have become two
unrelated facts. Every `optimizer_extension::ProblemClass` path still compiles, and the
unchanged extension contract tests and `tests/integration/test_registry.py` are the
evidence that no wire byte moved.

Requirement 4 is carried by three mechanisms rather than one, because the obvious one
is the weakest. Private fields stop a caller mutating a declaration; `capabilities`
takes no argument, so there is no request-shaped input to influence it with; and a
backend consults its own declaration inside `solve`, which is what makes a caller
holding a widened copy still refused. The requirement is about authority, and only the
third mechanism establishes it.

The specification's printed interface could not be implemented and was corrected in
`fde1d82` first. `version` is a `String`: the adapter reports the version it actually
linked and `unavailable` when it linked nothing, and a `&'static str` would have forced
it to name a version it may never have called.

What the widening test does and does not establish. The `compile_fail` doctest is the
first in this workspace. It was verified to fail with `E0616`, the private-field error,
by compiling the same snippet directly. But the `E0616` annotation is **not enforced**:
substituting `E0308` was tried and the doctest still passed, so stable rustdoc accepts
any compilation failure. On its own the block would therefore keep passing if the field
were renamed rather than kept private. A positive test reads the same field through its
accessor so a rename cannot leave both green, and the doc comment records the
limitation rather than implying the annotation checks anything.

Evidence (2026-09-13): `bash tools/check.sh` passed, exit 0, with 309 Rust tests, 68
Python tests and 56 documentation pages. Nine tests are new: four on declaration
validation, one pairing with the doctest, three on the pinned adapter's declaration,
and the doctest itself. `the_pinned_adapter_accepts_every_class_it_declares` solves a
model of each declared class and requires a real outcome rather than `Unsupported`,
so a declaration cannot drift from behavior and the test cannot pass by refusing
everything.

Follow-up: the canonical LP form and the fixed reduction order, then the host
certification.

## C6 SPEC-0011 Corrections Before Implementation (2026-09-13)

Objective: settle two requirements of SPEC-0011 that cannot be satisfied as written,
before any of the GPU linear-programming backend is implemented against them.

Status: complete. Documents only; no behavior changes, so no changelog entry, as
the C2, C5 and C8 specification commits each recorded.

Acceptance gate: `bash tools/check.sh` passes unchanged, with the same 300 Rust and
68 Python tests, because nothing executable changed. Resource budget: CPU only, no
GPU workloads.

Three corrections, each a conflict found by reading the contract against the tree
rather than a preference.

Requirements 9 and 10 require the preconditioner and the termination check interval
to be recorded "as part of the settings that produced a record", and the acceptance
section requires a record missing either to be refused. Compatibility freezes
`solve-record-v1`, and that document is closed: `deny_unknown_fields` on the Rust side
and `additionalProperties: false` in the schema. Both cannot hold. The correction
permits `solve-record-v2` and keeps `solve-config-v1` at version 1, which is what the
specification's own `CudaLpBackend::open(residency, settings)` interface already
implies: settings are constructor-time state, not per-solve options. Nothing embeds
`solve-record`, so this is a leaf bump with no cascade into `search-config-v3`,
`search-record-v3` or `run-record-v2` — checked before choosing it. The rejected
alternative was a sidecar settings document, which obeys the frozen version literally
but leaves a `SolveRecord` unable to reproduce its own solve, contradicting the
doc comment on that type and weakening SPEC-0005's reproducibility spine.

The Interfaces block cannot be implemented as printed. `version: &'static str` cannot
hold the HiGHS version, which is a runtime `String` and is `UNAVAILABLE_VERSION` when
nothing was linked, so a `&'static str` would force the adapter to name a version it
may never have called. And public fields make widening a declaration a mutation the
compiler permits, which contradicts requirement 4 and its acceptance line that a
caller attempting to widen one does not compile.

The host first-order method is the oracle the device kernels are checked against,
which `state/backlog.yaml` requires be built first. Shipping it as a selectable
backend rather than as test scaffolding makes it a public feature, and CONTRIBUTING.md
requires an accepted specification for one. Requirements are added here rather than
the surface being introduced without a contract.

ADR-0010's "which is finite wherever the repair needs it" is true of every model this
project currently produces and false of `model-v1` in general: a free variable admits
no finite repair on the column side, because the reduced cost is determined by the
dual iterate and repairing it alone falsifies the identity the bound rests on. The
behavior there is a refusal rather than a wrong bound, so this is a scope statement,
but the sentence reads as a theorem and is narrowed to the models it is a theorem
about.

Follow-up: the implementation slices, in order — the capability declaration on the
solve contract, the canonical LP form and fixed reduction order, the host
certification, the host engine with dispatch, the device kernels, and the evidence
record.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS library
present, exit 0, 300 Rust tests, 68 Python tests and 56 documentation pages — the same
counts as before this change, which is what a specification-only commit should
produce. The advisory database fetch failed and fell back to the cached copy, which
`state/known-failures.md` already records as intermittent.

## C6 Clean-Checkout Verification (2026-09-13)

Objective: verify the C6 branch from a checkout with nothing prebuilt, before any
integration, as the C4, C8 and Track B branches each were.

Status: complete; the branch passes from a fresh clone and one environment-dependent
test was found and fixed by doing so.

Acceptance gate: `bash tools/check.sh` passes in an independent clone with no
`target/` directory, no provisioned HiGHS library and no provisioned device code
object. Resource budget: CPU only, no GPU workloads — which is itself part of what
is being verified.

The verification earned its place. `a_device_no_registered_extension_needs_is_refused`
passed locally and failed in the clone. With a code object present the refusal is
"no extension requires one" and names the device; without one the session fails
earlier with "no device code object at <path>", which names a path. The test was
environment-dependent, and the message was genuinely worse than the test: a caller
who asked for a device and got a message about a file cannot tell which device was
refused. Fixed by making every refusal name the device rather than by weakening the
assertion.

What the clone establishes that a local run cannot. The build script's warning fired
four times, so `cuda_native` was unset throughout and every device path compiled to
its unsupported form: this is SPEC-0010 requirement 37 and ADR-0009's "nvcc is a
provisioning dependency, never a build dependency", observed rather than asserted.
The pinned HiGHS library was built inside the clone from scratch. And the twenty
device tests reported their skips rather than failing, which is what keeps a CPU-only
host a full gate pass.

Evidence (2026-09-13): cloned with `--no-hardlinks` at `6dbaf8c` with no `target/`
present; `bash tools/check.sh` passed there in 1 minute 35 seconds, exit 0, with 300
Rust tests, 68 Python tests and 56 documentation pages — the same counts as the
working tree.

`Cargo.lock` did change across the branch, and the earlier wording here said it had
not. What it gained is the `optimizer-cuda-sys` entry, its one dependency edge on
`libc`, and the edges naming the new crate from `optimizer-cuda` and
`optimizer-schedule-examples`. No third-party crate was added: `libc` was already in
the lockfile transitively, so the workspace still resolves the same eighteen
external packages it did before, which is what `cargo deny --locked check` confirms
on every gate run.

Follow-up: the branch is ready to integrate. C6 itself is not complete: SPEC-0011's
GPU linear-programming backend is accepted and unimplemented, so the backlog line
stays open.

## C6 Bounded Launch Chunks and Host Fallback (2026-09-13)

Objective: reach SPEC-0010 requirements 27 to 30 — bounded launch chunks with a
cancellation check between them, a poisoned context that is not launched into again,
and a device fault that never becomes a solver outcome.

Status: complete. Requirement 29 takes its fall-back-for-the-run option rather than
rebuilding a context, which the specification permits and which is recorded as the
choice it is.

Acceptance gate: a 500-job neighbourhood takes four launches rather than one,
asserted against a counter; the chunked result is identical to the host's; a
pre-cancelled call launches nothing and reports cancellation; a cancelled residency
is still usable afterwards; an input error touches the device at all; the host
fallback produces byte-identical proposals; `bash tools/check.sh` passes with native
acceptance covered. Resource budget: **GPU, one device under the shared host lease**.

What had to be bounded is work, not calls, and the two chunk sizes differ for a
reason worth recording. The batch kernel is one thread per permutation, so 4,096
permutations is 4.1e7 integer operations at the largest supported shape. The
neighbourhood kernel is one block per removed job and each block's recurrence is
serial, so the same block count buys far less parallelism and takes longer; 128 jobs
is 2.6e6 dependent operations. Picking one constant for both would have made one of
them either uselessly small or unboundedly large.

Synchronizing per chunk is what makes the cancellation check mean anything, and that
is not free. Without it the launches queue and the loop finishes before any of them
has run, so the check would test a token nothing had waited on. It is also where a
kernel fault surfaces, which is why the sticky check wraps the synchronize rather
than the launch.

The measurement did not move: a 500-job neighbourhood still runs in the same time it
did as a single launch, because four synchronizes at this size cost microseconds
against milliseconds of work. That is the expected result and it is worth stating,
because a chunking change that *did* move it would mean the chunks were too small.

Requirement 29 offers two responses to a sticky fault and this takes the second.
Rebuilding a context would mean replacing one that the residency's buffers hold
through an `Rc`, which is a lifetime problem rather than a driver one; falling back
for the remainder of the run is permitted, simpler, and loses only a transient
fault's device. The cost is recorded in [known failures](known-failures.md) along
with the honest gap: the decision logic is unit-tested, and recovery from a real
sticky fault is not, because provoking one means corrupting a device.

The producer's fallback closes requirement 24's recorded gap, and the assertion is
the one that matters. The fallback is `optimizer_schedule::insertion_neighborhood`
— the CPU path this project already treats as authoritative, not a second
implementation written to match the kernel — so the two cannot drift, and the
contract asserts the proposals are *identical* rather than equally good. A caller
cannot tell which path ran, which is the definition of a fallback; the `fallbacks()`
counter is how a test can.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the twenty device tests**, exit 0.
Rust tests rose from 295 to 300 and Python remains 68; documentation remains 56
pages. `Cargo.lock` is unchanged; `optimizer-cuda` gained an `optimizer-core` edge
for `CancellationToken`, which requirement 27 names explicitly. Separately,
`bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` passed both device suites —
fourteen kernel contracts and six producer contracts — and all four sanitizers over
both binaries, with zero errors and zero hazards.

Follow-up: none blocking. What remains open on SPEC-0010 is requirement 22's
threshold, which is deliberately not implemented because a dispatch threshold is an
acceptance-shaped number that the benchmark protocol requires an ADR and an
experiment record to commit.

## C6 Device-Backed Candidate Producer (2026-09-13)

Objective: make a search reach a device. Until now the device path existed and was
verified, and nothing outside a test could use it — the same gap C8 closed for
extensions, open again for hardware.

Status: complete; `optimizer schedule solve` with a device named and
`flow-shop-neh-gpu` registered runs the neighbourhood on the device, writes a record
whose provenance names the hardware, and that record re-executes and agrees.

Acceptance gate: every device-produced candidate is feasible by `Model::evaluate`;
the producer applies exactly the best single insertion move by the host's own
computation; repeated proposals are identical; a `gpu` registry entry resolves with
a device and is refused without one, still before construction; a configuration
naming a device that no registered extension needs is refused and writes no record;
`bash tools/check.sh` passes with native acceptance covered. Resource budget:
**GPU, one device under the shared host lease**.

Where the enforcement lives took the most thought. Requirement 6 says a record must
not claim a device the run did not use, and it has two halves that cannot live in
one place. The executive can see that a device is named and no extension is
registered at all, which makes the device certainly unused — that check is
necessary and it is not sufficient, and the code says so rather than implying
otherwise. Whether a *particular* registration uses a device needs the hardware
requirement, which SPEC-0004 deliberately keeps out of an extension's declaration
and SPEC-0009 puts in the registry. So the sufficient half belongs to the surface
that resolved the registry. Splitting it felt like a smell until the alternative was
written down: putting both in the executive would mean teaching it to read registry
entries, which is exactly the coupling ADR-0008 avoided.

The registry's condition is a UUID, not a device handle, so optimizer-registry stays
free of the driver boundary. That is sound because of where the UUID comes from: the
only way to obtain one is `DeviceSession::open`, which leases the host lock, creates
a context and reads the identity back. A caller cannot fabricate `Some` without
having done all three, so "a device is selected" and "a device is held" are the same
statement.

A refactor was needed and is worth recording because it improved the code rather
than merely enabling it. The driver handles borrowed their context with a lifetime,
which a producer cannot satisfy: a `Box<dyn CandidateProducer>` has no lifetime to
borrow from. They now hold `Rc<Context>`, so a context outlives its modules, streams
and allocations by refcount rather than by the borrow checker. That is strictly more
robust — the old arrangement was correct only because every holder happened to be
borrowed from the same scope.

Two mistakes the work caught, both mine.

The first was a wrong test. I asserted the device producer is never worse than
`SchedulingProducer` and it failed on `ta051`, 4059 against 4040. The producer was
right and the test was wrong: the CPU producer runs a full sequential pass, up to one
accepted move per job with each visible to the next, while this one applies a single
best move. Comparing them compares two algorithms, and neither promises to beat the
other. The test now asserts what is actually promised — that the move applied is the
best single move, checked against `insertion_neighborhood` on the host — and the
old assertion is recorded in its doc comment so the next reader does not reinstate
it.

The second was a wrong diagnostic, found by a test helper making the obvious error.
It chose a device from the host inventory, and under `tools/gpu_job.sh` the inventory
and the driver disagree: the wrapper restricts the process to one device, so the
inventory's first entry is usually one the driver cannot see. The message was "no
device with UUID", which is true and sends a reader to check a UUID that is already
correct. There is now a separate `HiddenFromDriver` refusal naming
`CUDA_VISIBLE_DEVICES`, and `visible_uuids()` reports what the driver can actually
see, which is the list a consumer must choose from.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the fifteen device tests**, exit 0.
Rust tests rose from 286 to 295 and Python remains 68; documentation remains 56
pages. `Cargo.lock` is unchanged and one `Cargo.toml` gained one intra-workspace
edge. Separately, `bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` passed both
device suites — eleven kernel contracts and four producer contracts — and all four
sanitizers over both binaries, with zero errors and zero hazards, on an RTX 5090.

End to end on an RTX PRO 6000: a scheduling search with the device producer
registered proved optimality, recorded `gpu_uuid`, `gpu_name` and driver 580.105.08
in its provenance, and `optimizer verify` re-executed it on the same device and
agreed on every compared field.

Follow-up: bounded launch chunks with a cancellation check between them, which is
the part of requirements 27 to 30 an interrupted long device run would notice.

## C6 Device Probe and Driver Version (2026-09-13)

Objective: give the driver version a producer, under SPEC-0006 requirement 1a, and
add `optimizer gpu probe` so a caller can find out whether this build can use a
device without running a search on one.

Status: complete; discovery reports four fields, and a probe creates a real context
under the lease and reports what the driver and the code object actually provide.

Acceptance gate: discovery refuses a row without a driver version rather than
accepting a hole; a probe reads the requested UUID back through the context it
created and reports both; it resolves every kernel this build expects without
launching one; a UUID no device carries, a missing device flag, a repeated flag, an
unknown lease mode and an out-of-range timeout are each refused with exit 2 and no
report; `bash tools/check.sh` passes with native acceptance covered. Resource
budget: **GPU, one device under the shared host lease** for the device-gated tests;
the CPU gate is unchanged and still runs none of them.

Why a probe is a separate command from discovery. Discovery asks management tooling
what hardware exists and never touches the driver, which is why it needs no lease
and runs anywhere. A probe asks the driver, so it creates a context and therefore
must hold the lease. Collapsing the two would have made the cheap question expensive
and the expensive one look free.

The report keeps `requested` and `observed` as separate fields, and that is the
point of it rather than a detail. Requirement 3's check is that they are equal; a
single field would have recorded the answer while recording nothing about whether
anything was compared. The same reasoning put the kernel list in the report: the
probe resolves every entry point this build expects without launching any of them,
so a code object that loads but is missing a kernel is found here rather than by a
first launch.

Two arguments were refused where a lenient reading was available. `--lease` accepts
only `acquire` and `inherited`, and a repeated `--device` is an error rather than
last-one-wins, because a caller who named two devices did not mean either of them
and the lock permits one holder anyway.

The unsafe prohibition caught a design mistake, which is worth recording because it
was mine. The first version of the probe command set the inherited-lease environment
variable so the library would see it. `optimizer-cli` forbids unsafe and
`env::set_var` is unsafe under edition 2024, so it would not compile. The
prohibition was right on the merits, not merely in the way: a command that mutates
its own environment to signal a library is harder to follow than one that passes an
argument. The lease decision is now a `LeaseRequest` parameter, and `LeaseRequest`
is deliberately distinct from the `LeaseMode` the report carries — one is what the
caller asked for, the other is what happened, and `Auto` can produce either.

`--lease acquire` inside a wrapped job is now a bounded refusal rather than a hang.
It waits on the lock its own parent holds and gives up at the timeout, which is the
deadlock requirement 8 exists to prevent, made visible in a test run instead of a
stuck job.

What this does not do, stated because it is easy to read as further along than it
is: `Hardware::driver` in a run record is still null. That is correct rather than
outstanding. Every search this build performs is a CPU search, and SPEC-0007
requirement 9 forbids a CPU record claiming GPU execution; the field takes a value
when a search runs on a device, which is the device-backed producer's work.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the eleven device tests**, exit 0.
Rust tests rose from 277 to 286 and Python remains 68; documentation remains 56
pages. `Cargo.lock` and every `Cargo.toml` are untouched. Separately,
`bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` passed all eleven device
tests and all four sanitizers — memcheck, racecheck, initcheck and synccheck — with
zero errors and zero hazards, on an RTX 5090. A probe on the RTX PRO 6000 reported
compute capability 12.0, 188 multiprocessors, 101,376 bytes of shared memory per
block and driver 580.105.08, with both kernels resolved.

Follow-up: the device-backed candidate producer. It is what would make the
registry's unconditional refusal of a `gpu` hardware requirement worth narrowing,
and the measured crossover worth consulting; until it exists, no search reaches a
device.

## C6 Device Selection Schema Cascade (2026-09-13)

Objective: put the selected device on the search configuration, under SPEC-0010
requirements 40 and 41, so that a device run is describable by a record that
verification can re-execute — and pay the three version bumps that forces rather
than avoiding them by putting the device somewhere verification never reads.

Status: complete; `search-config-v3`, `search-record-v3` and `run-record-v2` are in
both authorities, and a configuration naming a device is refused rather than run on
the CPU.

Acceptance gate: both the Rust parsers and the JSON Schemas accept exactly the same
documents and are asserted to refuse the same four mutations; an earlier version is
refused rather than migrated; a configuration naming a GPU is refused with the
device named and writes no record; the three committed example records still
re-execute and agree; `bash tools/check.sh` passes with native acceptance covered.
Resource budget: CPU only, no GPU workloads.

Why the field is in the configuration and not in provenance. Provenance was the
cheaper answer by a wide margin: `Hardware` already has three nullable GPU fields
and no version would have moved at all. It is the wrong answer because SPEC-0005
verification re-runs a search using only the record's embedded configuration, on
purpose, so that a record cannot confirm its own result. A device recorded only in
provenance is therefore invisible to the thing that repeats the run, and a record
naming a device would be re-executed without one. The cascade is what it costs to
keep the device where a re-execution can see it.

One field moved three versions because the documents nest: a search record embeds
its configuration, and a run record embeds that search record. The solve
configuration deliberately did not move. A relaxation inherits the search's device
because SPEC-0006 requirement 6 permits one lease holder across device selections,
so a search cannot use two devices and a per-solve field could express a
configuration the lease forbids.

Nothing is migrated, and the reason is not conservatism. A version-2 configuration
is exactly a version-3 one with the `device` line deleted, so defaulting an absent
device to `cpu` looks free. It is not: a version-2 record of a device run and a
version-2 record of a CPU run are byte-identical, so a migration would have to
invent the fact that tells them apart. Both authorities refuse, and a test asserts
they refuse the same documents rather than each refusing separately.

The refusal that matters most is the one that looks like an omission. The executive
rejects a configuration naming a GPU, because no search path dispatches to a device
yet. Honouring it by quietly running on the CPU would not have been a smaller
version of the feature; it would have been a false record that *passes*
verification, because verification re-runs from the same configuration, also lands
on the CPU, and agrees — and that agreement would certify a hardware claim nothing
ever checked. The refusal names the device it refused, and the CPU configuration
differing only in that field still runs, so it is discriminating rather than a
blanket failure.

One thing nearly went wrong and is worth recording. The three committed example
records are synthetic: an all-zero revision, `dirty: false`, a fixed identifier and
a warning saying they are not measurement evidence. Regenerating them with
`optimizer search` was the obvious way to move them to the new version and would
have silently replaced all four of those properties with real ones from a dirty
working tree. They were version-bumped in place instead, with only their
configuration input's path and checksum updated, and all three still re-execute and
agree.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the eight device tests**, exit 0.
Rust tests rose from 273 to 277 and Python from 63 to 68. Documentation remains 56
pages. `Cargo.lock` and every `Cargo.toml` are untouched.

Follow-up: the surfaces that make the field do something — `optimizer gpu probe`,
the driver version SPEC-0006 requirement 1a needs, a device-backed candidate
producer, and narrowing the registry's unconditional refusal of a `gpu` hardware
requirement. Until one of those lands, the device field is honoured only by being
refused.

## C6 Device Boundary and Batched Schedule Evaluation (2026-09-13)

Objective: implement SPEC-0010's device path far enough to answer the question the
whole capability exists for — whether a device agrees with the host exactly, and
where the crossover is — without granting the device any authority.

Status: complete for the boundary, the kernels and the evidence; incomplete for the
surfaces that would let anything outside a test reach a device. Both halves are
recorded in [known failures](known-failures.md) rather than one of them implied.

Acceptance gate: device makespans equal `optimizer_schedule::makespan` exactly, at
tolerance zero, over the whole ADR-0011 sweep; the device neighborhood equals both
the accelerated CPU path and a full recomputation; a repeated evaluation is bitwise
identical; a residency uploads once, asserted against a counter; a nonexistent UUID
and an absent code object are each refused by name; the ordinary gate stays CPU-only
and green with no device. Resource budget: **GPU, one device under the shared host
lease**, which is the first task in this project whose budget is not CPU only.

The boundary is `dlopen`, not a link. `optimizer-cuda-sys` opens `libcuda.so.1` and
resolves about twenty entry points, so `cargo build --workspace --all-features` keeps
working on a host with no toolkit and no device, and an absent driver is a typed
`DriverUnavailable` rather than a link error. That is what makes requirement 37
reachable rather than aspirational, and it added no third-party crate: `libc` was
already in the lockfile transitively. `optimizer-cuda` keeps `unsafe_code = "forbid"`
and keeps discovery, the lease and residency, so the crate every GPU consumer already
depends on did not become unsafe.

Both kernels are pure `unsigned int`, and that choice is forced twice over. The
hardware runs FP64 at one sixty-fourth of FP32 and issues integer and
floating-point instructions on one pipeline, so integer code runs at the full lane
rate. And the head and tail tables are 80,000 bytes at 500 jobs by 20 machines,
inside the 99 KB a block may address at compute capability 12.0, where 64-bit tables
would be 160,000 and would not fit on any block of this hardware. Both numbers were
checked rather than assumed: the driver reports the 99 KB limit and `ptxas -v`
reports 31 registers with zero spill for the batch kernel, inside the 42 that 48
resident warps allow.

Agreement is exact. Not "within a tolerance" — the assertion is `assert_eq!` on
`u32` values, over 64 permutations of each of the twelve instances and over every
job of every instance's neighborhood, plus a full cubic recomputation on the
twenty-job instances so the two head-and-tail implementations cannot share a wrong
idea of what an insertion costs. This is the strongest form of the CPU/GPU agreement
evidence Stage 4 asks for, and it is available only because the arithmetic is
integer; SPEC-0011's floating-point path will not have it.

The crossover is measured and both of its findings are inconvenient. The device
loses at twenty jobs by a factor of four, crosses over at roughly fifty, peaks at
16x on 200x20 — and then falls back to 9.5x at 500x20, because the 80 KB tables
leave one block resident per multiprocessor and two threads build the recurrence
while 254 wait. Context creation costs about 148 ms, which dwarfs every other number
in the table including the largest CPU time. The losing row and the falling tail are
both why the table is believable: SPEC-0010 names the first as the expected outcome,
and a sweep stopping at 200 jobs would have reported a monotonic trend that does not
hold. The full table is in [known failures](known-failures.md).

What is deliberately not done: the max-plus scan that would parallelise the
recurrence across machines. It is named in the kernel comment and left undone,
because correctness came first and an unmeasured optimisation would have had no
baseline to be measured against. Now it has one.

Device tests are opt-in behind `AI_OPTIMIZER_GPU=1`. Every earlier task record in
this project states "CPU only, no GPU workloads", and a suite that silently took the
host lease and ran kernels would have made those records false; it would also contend
on a lock that permits one holder for the whole host. The ordinary gate therefore
reports eight explicit skips naming the variable, which is the same shape as the
native-library skip and is never counted as coverage.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the eight device tests**, exit 0.
Rust tests rose from 253 to 273 and Python remains 63; documentation remains 56
pages. `Cargo.lock` gained `libc` as a direct dependency of the new crate and nothing
else. Separately, `AI_OPTIMIZER_GPU=1 bash tools/gpu_job.sh <uuid> cargo test
--release -p optimizer-cuda --test device` passed all eight on both an RTX 5090 and
the RTX PRO 6000, under an inherited lease. No device test has run in CI, because the
labeled runner is still not provisioned, and that is recorded rather than glossed.

Sanitizers (2026-09-13, added after the boundary landed): `bash tools/gpu_check.sh`
under the wrapper runs the device suite and then all four `compute-sanitizer` tools.
memcheck 0 errors, racecheck 0 hazards, initcheck 0 errors, synccheck 0 errors on an
RTX 5090. Racecheck was the one worth having: the neighborhood kernel has two threads
writing disjoint halves of one dynamically sized shared array while 254 others wait on
a barrier, which is exactly the shape a reviewer cannot check by reading. The script
refuses to run without an inherited lease rather than taking one, so it cannot escape
the wrapper that names a single device.

Follow-up: the schema cascade — `device` on the search configuration, and the
`search-config-v3`, `search-record-v3`, `run-record-v2` versions it forces — then the
CLI probe and the device-backed producer, then `compute-sanitizer`. Nothing reaches a
device from outside Rust test code yet, which is the same gap C8 closed for
extensions and is open again here.

## C6 Scale Split (2026-09-13)

Objective: add a frozen flow-shop split that spans published instance shapes, so the
crossover SPEC-0010 requirement 22 makes the CPU default depend on can be located
rather than merely bounded from below.

Status: complete; ADR-0011 is accepted, twelve instances are committed with their
derivations, and the manifest validates under both authorities.

Acceptance gate: the manifest validates against the SPEC-0007 schema; every committed
document is reproduced from its recorded seed by an independently written generator
and matches its checksum; the reproduction check is shown to fail for a wrong seed
and for a transposed loop order; the development subset is byte-identical to before;
`bash tools/check.sh` passes with native acceptance covered. Resource budget: CPU
only, no GPU workloads.

Why a new split rather than a larger one: SPEC-0008 requirement 24 and the benchmark
protocol both require a decision record before a split changes, and the development
subset's own documentation says enlarging it is such a change. Enlarging it would
also have altered the split a completed capability's evidence cites, for a reason
that has nothing to do with that capability. ADR-0011 therefore adds a split and
leaves C5's untouched.

Why one instance per shape rather than ten: the two splits answer different
questions. C5 asks whether an encoding and a recurrence are correct, and correctness
does not vary with shape, so ten instances of one shape exercise the same paths ten
times and that is the right sample. C6 asks how cost grows with shape, so the sample
has to move along the axis that varies. Ten per class would have committed twelve
times the bytes to answer a question about within-shape variance that nothing in C6
asks — and would have invited averages over a split never designed to support them.

The smallest shape is in the split deliberately. Twenty jobs by five machines is
where a device is expected to lose, so it is the crossover measurement's own
falsification check: a report showing the device winning everywhere is evidence the
measurement excluded transfers, not evidence the device is fast. A sweep starting at
the large end could not produce that signal.

One property of the source caught a wrong assertion before it was written. Taillard
reuses time seeds across classes — `ta051` and `ta071` are both 1539989115 — so the
development subset's "seeds must be unique" assertion is true only within one shape.
Carrying it over would have failed on the published table itself rather than on a
mistake. Both the Rust and the Python contracts now assert uniqueness of the seed
together with its shape, and the reason is recorded beside them.

The seed table was transcribed from the same OR-Library source the development subset
cites, and the ten seeds already in the repository matched it exactly, which is a
cross-check on both rather than on neither.

With the split in place the Phase 1 measurement was retaken over all twelve
instances, replacing the earlier table that reported shapes without naming instances.
The numbers are materially unchanged, which is the expected result — processing times
are drawn from the same distribution regardless of seed — but the rows now name
instances that exist. The full table is in [known failures](known-failures.md).

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips**, exit 0. Rust tests rose from 252 to 253 and
Python tests from 60 to 63; documentation rose from 55 to 56 pages, which is ADR-0011
and nothing else. `Cargo.lock` and every `Cargo.toml` are untouched. The tracked
instance documents add roughly 280 KB, which is the cost of checkable provenance.

Follow-up: SPEC-0010's device phases. The next is the CUDA driver boundary and the
provisioning script, which must leave an ordinary `cargo build` working on a host
with no toolkit and no device.

## C6 Tuned Flow-Shop Baseline (2026-09-13)

Objective: implement Taillard's exact head and tail acceleration inside `neh` and
`insertion` so that Stage 4's entry condition — baselines are tuned before any
intervention is measured — holds before any device work is measured against them.

Status: complete; both heuristics score insertion positions from head and tail
arrays, the returned permutations are asserted identical to the pre-change
algorithm's, and the measurement is recorded.

Acceptance gate: every existing SPEC-0008 contract passes unchanged; a new contract
test compares both heuristics against the pre-change algorithm over the fixed grid
and all ten frozen Taillard instances and requires the same permutation rather than
the same makespan; that test is confirmed able to fail; `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, no GPU workloads.

Why this first, before any kernel: the pass being replaced was `Theta(n^3 m)`, and a
device measured against it would have been measured against the clone-and-re-evaluate
loop rather than against the algorithm. That is the failure mode Stage 4's entry
condition exists to prevent, and it would have been invisible in the result: a large
speedup is exactly what a strawman baseline produces.

Where the acceleration lives is a contract question rather than a style one. The
value it computes is a makespan, and SPEC-0008 requirement 8 makes the recurrence
module the sole authority on what a schedule costs by keeping it architecturally
independent of everything that proposes one. Putting head and tail arrays in
`heuristic` would have given a heuristic its own cost model that happens to agree,
which is the shape of argument requirement 8 exists to refuse. They are in
`evaluate`, and `head[i]` is by construction the row `partial_completion_times`
would leave after `i` jobs.

The assertion is on permutations, not costs, and the difference is load-bearing.
Requirement 17 fixes which of several tied permutations a caller receives, so two
implementations can return different sequences of equal makespan and a
cost comparison would pass. The test therefore compares sequences, and it was
confirmed able to fail by relaxing the insertion tie-break from strictly-less to
less-or-equal — the exact mistake this rewrite invites, because it is the rewrite
that moves that comparison. Under that mutation the new test fails and
`construction_is_deterministic_including_under_ties` still passes, which is the
evidence that the existing suite could not have caught it: a deterministic wrong
answer is still deterministic.

`insertion` stays sequential. An accepted move is visible to the next job, so the
jobs cannot be scored independently of one another, and only the scoring of one
job's positions is accelerated. This is worth stating because the obvious next
optimization — evaluate all removals in parallel — would silently change which moves
the pass accepts, and it is the reason the device workload SPEC-0010 specifies is a
new producer rather than a faster `insertion`.

Measured on the development host, release build, best of three after a warmup, with a
0.41% noise floor from an identical binary. The full table is in
[known failures](known-failures.md). A 100-job, 20-machine improvement pass falls
from 32.66 ms to 0.92 ms, and a 200-job, 10-machine pass from 98.87 ms to 1.88 ms;
the ratio grows from roughly 3x at 20 jobs to roughly 50x at 200, which is what an
`O(n)` factor should do. The smallest instance is in the table on purpose: a single
large instance would have supported almost any claim about the shape of the
improvement.

What the numbers are not: a benchmark result or evidence. They are a development
diagnostic on one host, comparable only against another run of themselves, and
SPEC-0008 requirement 26 continues to forbid this slice recording a performance
claim. What they do change is C6's starting position, and not in a convenient
direction: a device now has to beat 23.86 ms of tuned single-threaded CPU work at 500
jobs rather than the several seconds the naive pass would have taken, so the
crossover will sit further out than it would have.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips**, exit 0. Rust tests rose from 251 to 252, the
one new test being the naive-comparison contract; Python tests remain 60 and
documentation remains 55 pages. `Cargo.lock` and every `Cargo.toml` are untouched: no
crate was added and no dependency edge changed.

Follow-up: SPEC-0010's remaining phases. The next dependency-ready one is the scaled
workload, because a crossover measured only on the frozen 20-by-5 subset would report
that the CPU wins and would establish nothing about where the crossover lies.

## C6 Heterogeneous Computation Specification (2026-09-13)

Objective: write and accept the C6 contracts before any public GPU or
backend-selection API exists, as required by AGENTS.md, CONTRIBUTING.md and the
Stage 4 scope. No C6 behavior is implemented by this change.

Status: complete; SPEC-0010, SPEC-0011, ADR-0009 and ADR-0010 are accepted and the
project records that reference C6 are synchronized.

Acceptance gate: each specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation and link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and **unchanged test counts**, because no behavior
changes. Had either count moved, this change would be doing something it claims not
to. Resource budget: CPU only, no GPU workloads; the device inventory was read once
through `nvidia-smi` for the hardware table below, which creates no CUDA context and
needs no lease.

Scope decided before implementation: C6's backlog line bundles two distinct
contracts, and CONTRIBUTING.md mandates one complete vertical slice, so they are
separated. SPEC-0010 owns heterogeneous computation itself — device selection,
residency, batching, transfer timing, arithmetic width, lease ownership, fallback,
cancellation, reset recovery and equivalence — and the batched integer schedule
evaluator that is its first workload. SPEC-0011 owns the GPU linear-programming
backend, which needs a capability concept on the solve contract that nothing in C1
through C8 required. Both are C6; neither is complete without the other, and the
first can be accepted, implemented and measured while the second is still a draft.

Why two decision records: they authorize different things. ADR-0009 amends
ADR-0003's single-unsafe-boundary rule, which is a workspace-wide structural change
and the same blocker C3, C8 and C9 each recorded rather than crossed. ADR-0010
decides that an approximate first-order solution never carries mathematical
authority, which is a numerical-authority decision that would still be needed if the
device were a CPU. Bundling them would let approval of the second imply approval of
the first.

The development host was observed with three Blackwell devices, compute capability
12.0, under driver 580.105.08 and CUDA 13.0.88: two GeForce RTX 5090 with 32,607 MiB
each and one RTX PRO 6000 Blackwell Server Edition with 97,887 MiB. This is recorded
because four properties of that compute capability are load-bearing in SPEC-0010's
requirements rather than incidental to them, and a reader checking the requirements
on sm_100 hardware would find different numbers: FP64 runs at one sixty-fourth of
FP32; INT32 and FP32 share one execution pipeline, so integer code runs at the full
lane rate; a thread block may address at most 99 KB of shared memory; and thread
block clusters are accepted by the assembler while `cluster.sync` degenerates to a
no-op, which is a silent-failure mode rather than a missing feature.

Three decisions inverted what the roadmap paragraph assumed, and each is recorded in
the contract that made it rather than only here. The first workload is integer
because of that FP64 ratio and that shared pipeline, which also means its CPU/GPU
equivalence is an exact identity at tolerance zero rather than an agreement within a
tolerance — the strongest form of the agreement evidence Stage 4 asks for, available
only because the arithmetic is integer. The same ratio does *not* disqualify GPU
linear programming, which is the opposite of what a peak-throughput reading suggests:
a sparse matrix-vector product is bounded by memory bandwidth at this intensity, with
roughly fivefold headroom before the FP64 rate could bind, so first-order methods are
viable here and factorizing ones are not. And "approximate results remain candidates
or warm starts until justified bounds exist" is met by constructing the justification
rather than by deferring it, because the justification is short and deferring it would
have left the backend's value impossible to evaluate except on throughput.

Two prerequisites were found while reading the code and are recorded in
[known failures](known-failures.md) rather than absorbed. The flow-shop heuristics
evaluate every insertion position by cloning the sequence and re-running the whole
recurrence, which is Theta(n^3 m) where Taillard's head/tail acceleration is
Theta(n^2 m); that was the right choice for C5, which forbids performance claims, and
it becomes a strawman the moment a device is measured against it, so Stage 4's entry
condition requires it be tuned first. And the frozen C5 subset is 20 jobs by 5
machines, roughly 1.3e4 integer operations for a full construction, so a crossover
measured only there would report that the CPU wins and would have established
nothing about where the crossover lies.

One correction was made during drafting and is worth recording because it nearly
shipped. An early draft claimed the contract needed no schema version, on the grounds
that a `device` field already existed. It does — in `run-config-v1`, which is the
benchmark manifest's configuration, not the search configuration a run record embeds.
A device recorded only in provenance would describe a run that `optimizer verify`
could not repeat, because SPEC-0005 verification reads only the record's embedded
configuration. SPEC-0010 requirements 40 and 41 therefore accept the version cascade
this actually costs: `search-config-v3`, `search-record-v3` and `run-record-v2`. The
solve configuration stays at version 1, because SPEC-0006 requirement 6 permits one
lease holder across device selections, so a search cannot use two devices and a
per-solve device would be a configuration able to express something the lease forbids.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips**, exit 0, in 29 seconds. Rust tests remain 251
and Python tests remain 60, which is the acceptance gate for a contract with no
behavior: had either moved, this change would be doing something it claims not to.
Documentation moved from 51 to 55 pages, which is the four new contract documents and
nothing else. `cargo deny` reports advisories, bans, licenses and sources ok with no
lockfile change, because no crate was added; `optimizer-cuda-sys` and its `libc`
dependency arrive with the implementation, not with the contract.

Expected changes: docs/specifications/SPEC-0010-heterogeneous-computation.md,
docs/specifications/SPEC-0011-gpu-lp-backend.md,
docs/decisions/ADR-0009-cuda-driver-boundary.md,
docs/decisions/ADR-0010-certified-gpu-lp.md, state/backlog.yaml, AGENTS.md,
state/known-failures.md, implementation-plan.md, wiki/status.md, README.md,
docs/architecture/overview.md, docs/architecture/testing.md, docs/operations/gpu.md,
cuda/schedule_eval/README.md, the forward references in SPEC-0006 and SPEC-0009, and
this record. No CHANGELOG.md entry: the changelog records user-visible changes and an
accepted contract with zero behavior is not one, matching the C2, C5 and C8
specification commits.

Also corrected here rather than left to be decoded: SPEC-0006, `docs/operations/gpu.md`
and `cuda/schedule_eval/README.md` deferred kernel work to a milestone named M5, which
the roadmap later renamed C6. Nothing else in the repository uses that name, so those
references pointed at a milestone a reader could not look up.

Follow-up: SPEC-0010's implementation phases, beginning with the tuned CPU baseline
that Stage 4's entry condition requires before any intervention is measured.

## Local Track B Integration (2026-09-12)

Objective: verify the Track B node-path branch from a clean checkout, integrate it
into local main, and delete the feature branch after confirming its commits are
retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip e8fcd7b; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-12): the branch was cloned with `--no-hardlinks` and no `target/`
directory present, and `bash tools/check.sh` passed there in 2 minutes 3 seconds
with **zero test skips**, building the pinned HiGHS 1.11.0 library inside the clone
and running 251 Rust and 60 Python tests. main fast-forwarded from 5beccfd to
e8fcd7b with no conflicts and no history rewriting; `git diff e8fcd7b main` is
empty, `git merge-base --is-ancestor` confirms the reviewed tip is retained, and
`git branch -d` removed the fully merged branch. The bootstrap smoke was rerun on
the integrated revision, recording e8fcd7b with `dirty: false`.

`Cargo.lock` and `Cargo.toml` are untouched by the whole branch. No crate was
added and no dependency edge changed, which is why this integration did not need
the stronger justification the C4 and C8 clean-checkout runs did — it was run
anyway, because `Model::rebound` is new public API and the branch rewrote a path
every search takes.

One item was found and fixed before integration rather than carried onto main.
SPEC-0001 gained requirement 2a in 5fe8ba3, but its review marker still named
9e6dc86 — a GitHub synchronization record that never touched the file — so the
specification claimed review at a revision predating a normative requirement it
now contains. This is the same staleness 95c1d81 and f0af453 corrected for C8 and
C5. Worth recording is how nearly it was missed: an audit comparing every marker
against its file's last-change commit reported all eighteen specifications and
ADRs as stale, which is a useless answer, because the commit that sets a marker is
itself a change to the file and no correct marker can ever match. The check was
discarded and the one real case identified by reading the history instead.

No remote refs were changed. main is now 13 commits ahead of origin/main and
remains unpushed pending the maintainer's authorization; the publication state is
recorded in [known failures](known-failures.md).

Follow-up: C6, heterogeneous computation and GPU feasibility, is the next
dependency-ready capability and still has no accepted specification. Write one
before introducing any public GPU or backend-selection API. The two deferred
per-node items — the constraint clone in `node::relaxation` and cross-node `Highs`
instance reuse — are recorded in [known failures](known-failures.md) with the
measurement each would need.

## Track B: Node-Path Measurement and Waste Removal (2026-09-12)

Objective: make solver timing measurable, then remove work the branch-and-bound
node path does and discards, without changing any conclusion.

Status: complete; the harness, all five removals and the multi-node gate fixture
are in place and gated. Every item this track set out to do is done, and the two
it declined are recorded below with their reasons.

Acceptance gate: every compared field and node counter is identical before and
after each change, asserted by the harness rather than by eye; every diagnostic
whose text is touched is pinned byte-exactly by a test written against unmodified
code; and `bash tools/check.sh` passes with native acceptance covered after each
commit. Resource budget: CPU only, no GPU workloads.

There was no way to measure a solver change before this. `benches/` held a
placeholder and `tools/benchmark_smoke.py` times `optimizer hello`. The bottleneck
ranking recorded in the plan was therefore static analysis, and the first task was
to replace it with numbers.

The unit of work is a fixed node budget with `time_limit_ms` null, over ta001 to
ta003 from the frozen Taillard set. A time limit would couple the outcome to host
speed, so before and after would explore different trees — the comparison would be
meaningless and the ten fields SPEC-0005 requirement 11 compares would
legitimately move. A node budget holds the work constant, and every run terminates
at the limit and claims nothing.

Measured, minimum of three runs after a warmup, release build, same host:

| change | ta001 | ta002 | ta003 |
| --- | --- | --- | --- |
| baseline | 8028.9 ms | 4186.1 ms | 5369.7 ms |
| basis extracted only on request | -5.8% | -10.4% | -8.9% |
| evaluation diagnostics built lazily | -11.5% | -22.5% | -17.3% |
| structural diagnostics built lazily | -1.0% | -3.5% | -2.4% |
| candidate borrowed when already canonical | -1.3% | -2.3% | -1.8% |
| node relaxation rebounded, not rebuilt | -0.3% | -0.7% | -0.4% |
| **cumulative** | **-18.8%** | **-35.0%** | **-28.1%** |
| *noise floor, identical binary* | *0.1%* | *0.2%* | *0.1%* |

The noise floor is in that table on purpose. The last row of real work is
-0.3% to -0.7% against a repeat-measurement spread of 0.1% to 0.2%, so it is
roughly two to three times noise and no more. Reporting it alone would overstate
it; reporting it beside the floor lets a reader judge it. The first three items
are large enough that the distinction does not arise.

What the numbers are not: they are a development diagnostic, not evidence. The
tool records `"claim": "none"`, defines no threshold, and is comparable only
against another run of itself on the same host. Nothing here is a benchmark result
and no performance property is claimed of the engine.

The largest single item was pure waste. Node relaxations are always continuous, so
the backend extracted an LP basis on every node; extraction computes the model's
canonical fingerprint, which serializes the entire model with
`serde_json::to_string_pretty`. The encoded ta001 model is 567,565 bytes, so a
256-node search serialized and discarded roughly 145 MB — to build a value
`Backend::solve` dropped on the next line and that SPEC-0003 requirement 23
forbids reusing anyway.

The second was diagnostics nobody reads. `checked` took `&str`, so `expression`
formatted about four `String`s per matrix nonzero on the success path and
`check_bound` two to three per call. At 5,175 nonzeros and two to three
evaluations per node that is tens of thousands of allocations per node for text a
valid model never produces. `Model::new`'s per-nonzero context had the same shape
and is on the same path, because `node::relaxation` rebuilds and revalidates a
model per node.

The last two were the smallest and are worth recording for what they cost rather
than for what they saved. `Candidate::canonical` cloned and re-sorted a candidate
a backend had just built by iterating the model's own sorted variables; it now
returns `Cow` and borrows when the input is already canonical. `node::relaxation`
went through `Model::new`, which re-sorted and revalidated every row and the
objective once per node for data the node did not touch; it now goes through
`Model::rebound`, which validates the supplied bounds and refuses any variable
list that is not the original's IDs.

That refusal is the whole basis for skipping the row checks, and it is stated as
SPEC-0001 requirement 2a rather than left implicit in code. The skipped checks
decide two things — coefficients are finite, and every term names a variable the
model has — and the first is carried from a document that already passed while the
second is exactly what the ID requirement preserves. This follows how SPEC-0003
requirement 12a and SPEC-0004 requirement 9a were recorded when implementation
found a rule the contract had not stated. No ADR: the change is strictly narrowing
and reverses nothing accepted.

Method worth keeping: characterization first. Eleven tests pinning the byte-exact
text of every diagnostic these commits touch were written and passed against
unmodified code before any of it moved, and the two candidate-canonicalization
contracts were written the same way, against the clone-always implementation. Three
of the eleven were wrong on the first attempt in an instructive way — the fixtures
aimed at a constraint-level message and hit the variable-level one, because
variables are checked first. Discovering that from a failing characterization test
is the cheap version of discovering it from a changed error message in production.

Every behavior change here was also verified by reinstating the defect rather than
by assertion alone. An unconditional canonical fast path fails the signed-zero
contract with bits 9223372036854775808 against 0 and takes three pre-existing
contracts with it; disabling `rebound`'s ID refusal fails the refusal contract.

Two traps avoided rather than survived. `checked` returns `zero(value)`, not
`value`, and that negative-zero normalization is observable through
`VariableCheck.value` and therefore every serialized validation report; a lazy
rewrite that returned the raw product would have changed committed records. The
same trap reappeared in the candidate fast path, where borrowing a candidate
holding `-0.0` would publish a different number than the owned path does, which is
why the fast path tests for negative zero and not merely for sorted-and-distinct.
And the harness compares conclusions itself and fails outright if any moved, so a
timing win accompanied by a counter change is reported as a bug rather than a
speedup.

A blind spot found while closing the track, and the reason the last commit is a
test rather than a removal: both committed run records reported `nodes_explored:
1`. `tools/verify_committed_record.py` is the only check that re-executes a record
against a later build, and it had therefore never descended past the root node —
while every change on this branch was on the per-node path. A generated 5x3
instance exploring 37 nodes, pruning 23 by bound and proving optimality now closes
that. Its counters are asserted against the committed record rather than the
verdict, which does not carry them, so swapping in a single-node record fails
loudly instead of passing quietly.

Not attempted, and why: reusing the `Highs` object across nodes is legal under
requirement 23, which forbids reusing a *basis* rather than the instance, and is
the obvious next item — deferred pending the measurement that now exists. The
constraint and objective clone in `node::relaxation` also remains and is now
likely the dominant per-node cost, since `rebound` removed the validation beside
it but not the copy; eliminating it needs shared ownership inside `ModelDocument`,
which is a public type change with a wide ripple and belongs behind its own
measurement. Cross-node warm start and any parallelism remain out of scope; both
are forbidden by accepted contracts (SPEC-0003 requirement 23, SPEC-0002
requirement 5) and need their own decision records.

Evidence (2026-09-12): `bash tools/check.sh` passed after each of the three
commits with the pinned HiGHS 1.11.0 library linked and **zero test skips**, exit
0. Rust tests rose from 247 to 251 — two candidate-canonicalization contracts and
two `rebound` contracts — while Python tests remain 60 and documentation 51 pages.
The last commit adds a gate step and fixtures rather than contracts, so it moves
neither count, which is the expected result for what it claims to do.

Follow-up: Track B is closed. C6, heterogeneous computation and GPU feasibility,
is the next dependency-ready capability and still has no accepted specification;
write one before introducing any public GPU or backend-selection API. The two
deferred per-node items above are recorded in
[known failures](known-failures.md) rather than carried as intentions.

## Local Track A Integration (2026-09-12)

Objective: verify the C8 follow-up branch from a clean checkout, integrate it into
local main, and delete the feature branch after confirming its commits are
retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 8cddb44; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-12): the branch was cloned with `--no-hardlinks` and no `target/`
directory present, and `bash tools/check.sh` passed there in 1 minute 33 seconds
with **zero test skips**, building the pinned HiGHS 1.11.0 library inside the clone
and running 234 Rust and 60 Python tests. main fast-forwarded from dfdc245 to
8cddb44 with no conflicts and no history rewriting; `git diff 8cddb44 main` is
empty, `git merge-base --is-ancestor` confirms the reviewed tip is retained, and
`git branch -d` removed the fully merged branch. The bootstrap smoke was rerun on
the integrated revision, recording 8cddb44 with `dirty: false`.

One process note worth recording rather than hiding: the first commit on this
branch used `git add -A` and captured all of Track A under a message describing
only the review-marker fix. It was split into two honest commits before anything
was integrated. The branch was local and unpushed, so no shared history was
rewritten.

Publication state changed outside this work. The maintainer pushed the work
through `dfdc245` to origin, so every milestone up to and including C8 is now
published. Records dated before that push describe main as unpushed pending
authorization; they were accurate when written and are left as written rather than
backdated. [Known failures](known-failures.md) now carries the current state. The
two Track A commits are local and unpushed, and remain so pending the maintainer's
own push.

Follow-up: Track B, the measurement harness and the behaviour-preserving waste
removal on the per-node path, is next. C6 still has no accepted specification.

## C8 Follow-Up Items (2026-09-12)

Objective: close the three items the C8 integration record left open — SPEC-0009
requirement 14's overstated wording, requirement 20's possibly-unreachable
verification branch, and the stale C5 review markers.

Status: complete; the full gate passes with native acceptance covered.

Acceptance gate: requirement 14 is narrowed to what the implementation can
actually guarantee; requirement 20's branch is either reached by a test or
recorded as unreachable with a decision; the C5 markers name the implementing
revision; and `bash tools/check.sh` passes with native acceptance covered.
Resource budget: CPU only, no GPU workloads.

Requirement 20's branch is reachable, and the earlier doubt came from testing it
the wrong way round. Restamping the *registry* is refused by the declaration check
first, because the extension still reports the version it always did — the existing
test's own comment says so. The rule the requirement describes runs the other
direction: a record naming a version the current build no longer declares, which is
what happens when a record outlives the build that produced it and the extension's
version has since moved. A new contract restates the version in the record's
extension summary, leaves the registry alone so resolution succeeds, and reaches
the comparison. Disabling the branch makes it fail, so it is not vacuous. Nothing
was deleted.

That diagnosis found a second defect, in the acceptance gate itself.
`tools/verify_committed_record.py` restamped the registry and then asserted only
that `9.9.9` appeared in stderr. Resolution's declaration-mismatch message contains
that string too, so the check passed on the wrong error and never reached
requirement 20 — while its comment claimed to "isolate the version refusal". The
gate now covers both rules separately, each asserting the message its own rule
produces, and the requirement 20 case is checked across a commit boundary as
SPEC-0009's acceptance section says it is. Verified by disabling the branch: the
gate step now fails where it previously passed. This is the same class of defect
the C8 clean-checkout run found — a check passing for a reason other than the one
it names — and it is worth recording that it was found by pulling on a thread
about a *different* requirement.

Requirement 14 was wrong as written rather than under-implemented. It claimed
resolution never constructs a refused extension, but `Extension::declare` is the
authority a declaration mismatch compares against and the provider is what supplies
the role, so both mismatches are necessarily decided after construction. The rule is
now split: requirement 14 governs invocation and holds everywhere; requirement 14a
governs construction and names the refusals decided before it — a gpu hardware
requirement, an unsatisfied data requirement, an unpermitted experimental entry and
a failed promotion check are all decided before the provider is consulted, while an
unprovided identity consults the provider but constructs nothing. The
implementation did not change, and the acceptance mapping now says which refusals
can be asserted against a construction counter and why the others cannot.

Evidence (2026-09-12): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0. Rust tests
rose from 233 to 234, the requirement 20 contract. Python tests remain 60 and
documentation 51 pages.

Follow-up: C6 remains the next capability and still has no accepted specification.
The remaining thin spots in SPEC-0009's acceptance mapping — requirement 20's
nondeterministic-record case, requirement 21's positive diagnostic case,
requirement 22's forfeited registry-backed record, `optimizer search --registry`
with a non-empty policy, and the document-level parse cases — stay recorded in
[known failures](known-failures.md); each needs a fixture this build does not have.

## Local C8 Integration (2026-09-12)

Objective: verify the feat/extension-registry branch from a clean checkout,
integrate it into local main, and delete the feature branch after confirming its
commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 7757af6; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-12): the branch was cloned with `--no-hardlinks` and no `target/`
directory present, and `bash tools/check.sh` passed there in 2 minutes 2 seconds
with **zero test skips**. That run built the pinned HiGHS 1.11.0 library from the
checksum-verified upstream archive inside the clone, producing `libhighs.a` at
10,186,956 bytes, ran 233 Rust and 60 Python tests, re-executed the committed run
records against the freshly built binary, validated 51 documentation pages, and
passed cargo-deny, artifact validation and bootstrap smoke.

This clean-checkout pass is the acceptance evidence for the integration, and it was
not a formality. The first attempt **failed**, at
`a_registry_does_not_change_a_search_that_names_no_extension`, and the cause was a
record identifier derived from measured elapsed time rather than anything the
registry does. Every warm-tree gate run during C8 had passed because both searches
finished in the same millisecond. That defect, its fix and the reasoning are
recorded above under the C8 verification follow-up. C8 adds a crate, a dependency
edge and a lockfile change, which is the case the C4 record identifies as the one
where a clean checkout earns its cost; this time it earned it for a different
reason than a stale lockfile.

main was fast-forwarded from 08ed424 to 7757af6 without conflicts or history
rewriting, so the integrated tree is byte-identical to the verified revision, which
`git diff 7757af6 main` confirms as empty. `git merge-base --is-ancestor` confirmed
the reviewed tip is retained, and `git branch -d` removed the fully merged
feat/extension-registry branch, which refuses a branch whose commits are not
reachable. The worktree is clean and the bootstrap smoke was rerun on the integrated
revision, recording 7757af6 with `dirty: false` for clean revision-bound provenance.

The branch held five commits: d48ce11 specifying the registry, 6cf6d5e implementing
it, 95c1d81 correcting the two review markers to name the implementing revision,
bb13f67 narrowing the requirement 17 contract when the clean checkout failed, and
7757af6 fixing the identifier derivation and restoring that contract to a whole
record comparison. bb13f67 is partly superseded by 7757af6 and was kept rather than
rewritten, because the intermediate state is what motivated the fix and shared
history is not rewritten.

No remote refs were changed. main is now 5 commits ahead of origin/main and remains
unpushed pending separate authorization; the origin remote and its outstanding
protection settings are recorded in [known failures](known-failures.md).

Follow-up: C6, heterogeneous computation and GPU feasibility, is the next
dependency-ready task and has no accepted specification. Write one before
introducing any public GPU or backend-selection API. Two items recorded during C8
are worth picking up with it or before it: SPEC-0009 requirement 14's "MUST NOT
construct" is narrower in practice than it reads and wants a wording correction, and
the requirement 20 version comparison at verification may be unreachable and should
be diagnosed rather than deleted on inspection. SPEC-0008 and ADR-0007 also still
name 5157786, the C5 specification commit, rather than its implementing commit
08ed424, which is the same marker staleness 95c1d81 fixed for C8.

## C8 Verification Follow-up: Clock-Derived Record Identifier (2026-09-12)

Objective: remove measured elapsed time from a run record's identifier, and specify
what the identifier is so the derivation cannot regress.

Status: complete; the full gate passes with native acceptance covered, and the
clean-checkout verification that found the defect now passes.

Acceptance gate: two runs of the same model and configuration produce the same
identifier; a changed configuration and a changed model each produce a different
one; the SPEC-0009 requirement 17 contract compares whole records again with only
elapsed time normalized; the contract fails with the old derivation reinstated; and
`bash tools/check.sh` passes with native acceptance covered. Resource budget: CPU
only, no GPU workloads.

How it was found, because the method is the point: every gate run during C8 used a
warm `target/` and passed. The clean-checkout verification, run before integrating
the branch, failed at
`a_registry_does_not_change_a_search_that_names_no_extension`. The registry was not
the cause. `record_id` was built as `run-{model_id}-{elapsed_ms}`, both searches
finished in 0 ms on the warm tree so their identifiers matched, and in the
independent clone one took 0 ms and the other 1 ms. The contract had been failing
on the clock since it was written and passing by luck.

The defect is older than C8. `search.rs` and `schedule.rs` have derived the
identifier this way since C4 and C5 respectively; the C8 contract was simply the
first thing to compare two whole records produced by separate invocations. A record
identifier that moves with the clock makes a record's identity a property of how
busy the machine was, which SPEC-0005 requirement 12 already excludes from meaning,
and it collides for unrelated searches that happen to take equally long.

What was decided rather than assumed: the identifier now derives from the SHA-256
digests of the input documents the record already carries. Two runs of the same
model and configuration therefore share an identifier, and that is the intended
reading rather than a residual collision — the identifier names the inputs a record
describes, and whether two such runs agree is what `optimizer verify` exists to
answer. `revision` and `model_fingerprint` stay separate fields, so the identifier
does not duplicate the build or the model dimension. The rule is now SPEC-0005
requirement 1a, added rather than left implicit, matching how SPEC-0003 requirement
12a and SPEC-0004 requirement 9a were recorded when implementation found a rule the
contract had not stated.

Why this needed no record version and no ADR: `record_id` is not among the ten
fields requirement 11 compares, so agreement is untouched and SPEC-0005's rule that
a change to the compared fields is breaking does not apply. The field, its type and
its schema constraint are unchanged, no exit code or stderr category moved, and the
committed example records carry hand-written identifiers rather than generated
ones, so none of them changed. The schema gains a description only.

Evidence (2026-09-12): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0. Rust tests
rose from 232 to 233, the new identifier contract. Python tests remain 60 and
documentation 51 pages. The fix is verified by reinstating the defect rather than by
assertion alone: with `run-{model_id}-{elapsed_ms}` restored the new contract fails
at the changed-configuration assertion, and with the fix it passes. Restoring the
requirement 17 contract to a whole-record comparison is the second check, since it
now compares `record_id` like every other field.

## C8 Extension Registry Implementation (2026-09-12)

Objective: implement C8 under the accepted SPEC-0009 and ADR-0008: the registry
document and its strict parser, resolution with each refusal path in its own
category, the reusable conformance suite and its record, the CLI provider table and
`registry` subcommands, registry integration in `search`, `verify` and
`schedule solve`, the two JSON Schemas with committed examples, and a gate step
re-executing a committed registry-backed scheduling record.

Status: complete; the specification preceded the implementation, and the full gate
passes with native acceptance covered.

Acceptance gate: each resolution refusal is asserted separately in its own
`ErrorKind` category; a promoted entry is refused when its conformance record is
absent, tampered with, failing or naming another version; a scheduling run
registering the NEH producer writes a record that verifies by re-execution, both in
Rust and across a commit boundary in the gate; a registry supplied to a search
naming no extension changes nothing; the conformance suite runs and its committed
record regenerates; and `bash tools/check.sh` passes with native acceptance
covered. Resource budget: CPU only, no GPU workloads.

Evidence (2026-09-12): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0, with no
native-uncovered warning. Rust tests rose from 191 to 232 and Python tests from 45
to 60. Documentation rose from 48 to 51 pages: SPEC-0009, ADR-0008 and the
register-an-extension tutorial. No checks were waived; the RustSec advisory fetch
recovered through the cached database as already recorded.

`Cargo.lock` changed only by adding the new optimizer-registry crate and local
dependency edges. No external package version changed and no new external
dependency was introduced. The registry crate depends on the published core,
extension and executive APIs and on no crate supplying a concrete extension, so the
provider seam is enforced by the build rather than asserted: the concrete table
lives in optimizer-cli.

Correctness evidence, stated as what was actually checked:

- Every refusal path is asserted in its own `ErrorKind` category: an unprovided
  identity; a declaration disagreeing with its entry on version, category, host
  contract version, problem class, determinism and limits, each individually; a
  provider returning the wrong role; an authority not implied by the category; the
  transformation category; an unmet data requirement; a gpu hardware requirement;
  an absent required identity; a declared conflicting pair; a promoted entry whose
  record is absent, tampered with, failing, or names another extension or version;
  and an experimental entry without permission.
- Refusal is total. A two-entry registry in which one entry is refused refuses the
  whole set, and the CLI writes no record for such a run.
- The refusals decided before construction are asserted against the provider's own
  construction counter, so neither can pass because nothing was ever built.
- A scheduling run registering the NEH producer through a registry writes a record
  that verifies by re-execution and exits 0. The gate re-executes such a record
  committed at an earlier revision, which is the property no in-process test can
  establish.
- A registry whose entry names a different producer version is refused at
  verification as unsupported rather than reported as divergence, so the verifier
  does not blame a record for a property of its own inputs.
- An experimental entry is refused without `--allow-experimental` and, with it,
  the written record carries a warning naming it.

Findings during implementation, each recorded rather than patched silently:

The conformance suite had no test at all. `conformance::run` and
`optimizer registry check` had exactly one caller between them, the production code
path, so requirements 23 to 25 had no evidence and the committed
`examples/conformance-record-v1.json` was a frozen artifact that was internally
consistent and correctly checksummed but never re-derived. That is the specific
failure the suite exists to prevent: `examples/extension-registry-v1.json` promotes
`flow-shop-neh` by citing that file's SHA-256, so a producer that regressed would
have kept citing a passing record while every check still agreed with it. New CLI
contracts now regenerate the record through `registry check` and compare it byte for
byte, and the assertion was shown to fail by perturbing the committed file. The
suite's own invariance comparison is unit-tested against each of the six fields it
compares, because SPEC-0004's containment means no extension reachable through the
host can move them — a broken comparison would otherwise be indistinguishable from
a conforming extension.

`entry_order_does_not_affect_resolution` was vacuous. Its adviser entry recorded an
identity its declaration did not match, so both orders were refused on the first
policy and the test asserted only that two identical errors were identical; it
passed with both identity sorts deleted. It now resolves two entries successfully in
both orders and asserts the identity and role sequences the host receives, and it
was shown to fail with the sort removed. The refusal-determinism case it used to
cover is kept as a separate test, because a test that only ever observes refusals
cannot see the ordering it claims to check.

Requirement 17 had no test. An empty extension policy with a registry supplied must
still take the extension-free entry point, which is the compatibility claim the
whole slice rests on, and it was asserted only in a code comment. A run surface
contract now compares the two records field by field apart from elapsed time.

`docs/architecture/testing.md` claimed that every refusal test asserts the
extension's own construction or invocation counter. Two did, and the invocation
counter was written and never read. The claim is now accurate, the dead
instrumentation is removed, and the reason the declaration-mismatch paths cannot
assert it is stated: resolution has to construct the extension and call `declare`
to discover the disagreement, which means requirement 14's "MUST NOT construct" is
narrower in practice than it reads. That narrowing is recorded in
[known failures](known-failures.md) as a specification correction to make, not a
code change to sneak in.

Recorded and not closed, because each needs a decision rather than a patch:
requirement 20's nondeterministic-record refusal has no fixture that can produce
one; requirement 20's version comparison at verification may be unreachable, since
resolution has already equated the declaration with the entry, and the branch is
left in place rather than deleted on inspection alone; requirement 21's positive
diagnostic case, requirement 22's forfeited registry-backed record, and
`optimizer search --registry` with a non-empty policy are all untested, the last
because both provided extensions are flow-shop producers that cannot be built from
a bare model. All are in [known failures](known-failures.md).

Scope boundary held: no schema version changed anywhere, no existing document
gained or lost a field, and the compared fields stay the ten SPEC-0005 fixed. The
committed C4 example record still re-executes and verifies inside the gate. An
extension summary difference is a diagnostic note that does not change an exit code,
matching the existing environment-difference rule.

What is deliberately not claimed: no performance, runtime or solution-quality
result. Promotion means the contract conformance suite passed, never that the
extension improves a search, which stays C7's question. The conformance record
carries no timing field, and a test asserts its absence so one cannot arrive
quietly.

Follow-up: C6, heterogeneous computation and GPU feasibility, is the next
dependency-ready task and has no accepted specification; write one before any
public GPU or backend-selection API. C9 and C10 are also unblocked now that C8 is
complete, and both keep their recorded blockers.

## C8 Extension Registry Specification (2026-09-12)

Objective: write and accept the C8 contract before any public registry API exists,
as required by AGENTS.md, CONTRIBUTING.md and the Stage 3 scope. No C8 behavior is
implemented by this change.

Status: complete; SPEC-0009 and ADR-0008 are accepted and the project records that
reference C8 are synchronized.

Acceptance gate: the specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation and link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and **unchanged test counts**, because no behavior
changes. Had either count moved, this change would be doing something it claims not
to. Resource budget: CPU only, no GPU workloads.

Why C8 and not C6: Stage 4's entry condition is that Stage 3 provides reproducible
workflows, and C8 is Stage 3's last open item. It is also the seam two recorded
known-failures point at, so it blocks rather than merely precedes: the registry does
not exist, and a C5 scheduling run performed with the NEH producer is not verifiable
by re-execution at all. C6's dependencies are met, but starting it would leave
Stage 3's reproducibility claim partial.

Scope decided before implementation: the registry alone. C8's backlog line bundled
three deliverables and CONTRIBUTING.md mandates one complete vertical slice, so the
Python SDK becomes C9 with its pyo3/ADR-0003 blocker unchanged and the comparative
experiment runner becomes C10. Existing references to "C8's registry" stay accurate
because C8 keeps the registry.

Two contract decisions worth recording, because both are the kind a later
implementation could get quietly wrong:

The registry resolves; it does not load. An entry names an extension the build
already provides through a caller-owned `Provider` seam, which is the same pattern
as `&dyn Backend` and `&[Registration]`. Dynamic native loading needs a second
unsafe boundary ADR-0003 prohibits, so it stays deferred; the registry now makes
that absence more visible rather than closing it.

No document version changes and agreement is untouched. An extension is identified
in a record by the `extension_id` and `version` its `ExtensionSummary` already
embeds verbatim, so a record naming an extension is re-resolvable without a new
field. Adding the registry to the compared fields would change what agreement means
for every existing record, which SPEC-0005 reserves for a new record version plus an
ADR. A resolved-version mismatch and a nondeterministic summary are therefore
refused as *unsupported* rather than reported as divergence, which is the same
distinction the C5 implementation drew when it turned a misleading divergence into a
refusal.

Expected changes: docs/specifications/SPEC-0009-extension-registry.md,
docs/decisions/ADR-0008-registry-resolution.md, state/backlog.yaml, AGENTS.md,
state/known-failures.md, implementation-plan.md, wiki/status.md, the forward
references in SPEC-0004, SPEC-0005 and SPEC-0008, and this record. No CHANGELOG.md
entry: the changelog records user-visible changes and an accepted contract with zero
behavior is not one, matching the C2 and C5 specification commits.

Follow-up: C8 implementation is dependency-ready under SPEC-0009. It requires the
optimizer-registry crate with the strict registry document, resolution with each
refusal path in its own category, the reusable conformance suite over a fixed grid,
the CLI provider table and subcommands, registry integration in `search`, `verify`
and `schedule solve`, the two JSON Schemas with committed examples, and a gate step
re-executing a committed registry-backed scheduling record so the closed gap is
established across a commit boundary rather than within one process.

## C5 Flow-Shop Scheduling Implementation (2026-09-11)

Objective: implement C5 under the accepted SPEC-0008 and ADR-0007: flow-shop
instances, the makespan recurrence, the positional encoding, deterministic NEH and
insertion producers, a scheduling command surface, and a frozen generated Taillard
development subset.

Status: complete; the specification preceded the implementation, and the full gate
passes with native acceptance covered.

Acceptance gate: the optimum the executive proves on an encoded model equals the
minimum found by exhaustive permutation enumeration over a fixed grid; the recurrence
agrees with an independently written oracle; the generator reproduces Taillard's
published verification instance exactly; a producer whose proposals are refused
leaves the outcome, proven optimum, dual bound, forfeiture state and both prune
counters unchanged; a scheduling run writes a verifiable run record; and
`bash tools/check.sh` passes with native acceptance covered. Resource budget: CPU
only, no GPU workloads.

Evidence (2026-09-11): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0 in 16 seconds
on a warm build directory, with no native-uncovered warning. Rust tests rose from
159 to 191 and Python tests from 39 to 45. Documentation remains 48 pages, because
SPEC-0008 and ADR-0007 were added by the specification commit. The
`AI_OPTIMIZER_SKIP_NATIVE=1` configuration also passed with all 191 tests and its
uncovered-acceptance warning. No checks were waived; the RustSec advisory fetch
recovered through the cached database as already recorded.

`Cargo.lock` changed only by adding local dependency edges and the new
optimizer-schedule-examples crate. No external package version changed and no new
external dependency was introduced: the Lehmer generator is Taillard's own published
algorithm rather than a general-purpose RNG crate, which is a correctness
requirement and not a dependency preference.

Correctness evidence, stated as what was actually checked:

- Over a fixed grid of tiny instances with no randomness, the executive's proven
  optimum on the encoded model equals the minimum from exhaustive enumeration of
  every permutation, and the decoded winner re-evaluates through the recurrence to
  that same value. Three independent views must agree, so neither the encoding nor
  the recurrence can be wrong alone without failing. The grid sizes are asserted so
  they cannot silently shrink.
- The recurrence agrees with a separately written oracle over 5,232
  instance-permutation pairs. The independence is architectural rather than
  asserted: `evaluate` imports neither `encode` nor `heuristic`, and the test oracle
  is a second implementation in the test file.
- The generator reproduces Taillard's published `ta001` matrix exactly from seed
  873654221, checked in Rust against the published matrix and independently in
  Python against a second implementation of the generator. Both a wrong seed and a
  transposed loop order are shown to disagree, so the check can fail.
- Every one of the ten frozen instances regenerates from its manifest-recorded seed
  and parameters to the committed bytes, and its committed checksum is verified.
- A producer whose every proposal is refused leaves the outcome, proven optimum,
  dual bound, forfeiture state and both prune counters identical to the
  producer-free run, with the refusal recorded as rejected rather than absorbed.
- Every scheduling test that depends on a producer asserts the producer's own
  proposal counter first, so none can pass because the producer was never consulted.
- Decoding refuses a fractional assignment, a position selecting two jobs, a
  position selecting none, one job filling two positions, a candidate naming another
  model, and a candidate missing a variable. None is rounded or repaired.
- The end-to-end surface was exercised on the built binary: a 5-job, 3-machine
  instance reported `proven_optimal` with objective 372, matching independent
  brute-force enumeration of all 120 permutations, and its record verified.

Two findings during implementation, both recorded rather than patched silently:

An early test asserted that an *honest* producer left both prune counters unchanged.
It failed, correctly: `nodes_pruned_bound` went from 0 to 1 because an accepted
incumbent legitimately prunes more by bound, which is the entire purpose of a
candidate producer. SPEC-0008 requirement 20 was already scoped to a refused or
absent proposal, so the contract was right and the test was wrong. A
`RefusedProducer` was added to test the invariance claim for what it actually says,
and the honest producer is now asserted against requirement 19's promise instead.
C3's identically worded rule is consistent, because it was established with hostile
extensions whose proposals are all refused. The specification's acceptance section
now records this rather than leaving the scope looking arbitrary.

`optimizer verify` reported a *divergence* for a record produced with the producer
registered, naming a node-count difference. That diagnosis was misleading:
verification re-executes through the extension-free entry point, so it reproduced a
search the record does not describe and the counters differed for that reason alone.
SPEC-0005 requirement 14 already refuses such a configuration on the search path, so
the same rule now applies to verification and the record is refused as unsupported
instead. The consequence is real and is recorded in
[known failures](known-failures.md): a scheduling run performed with the producer is
not verifiable by re-execution today, and the seam is C8's registry.

Scope boundary held: no schema version changed anywhere, no new record type was
introduced, and no existing document gained or lost a field. `RunRecord`,
`SearchRecord`, `Model` and `optimizer verify` are untouched apart from the
verification refusal above, which is why the committed C4 example record still
re-executes and verifies inside the gate.

What is deliberately not claimed: no performance, runtime or solution-quality
result. Proven optimality is asserted only where exhaustive enumeration is the
oracle; a node-limited run over `ta001` is asserted to report its limit rather than
an optimum, and its incumbent is asserted feasible through the recurrence. No
best-known bound is committed, because a committed bound is an acceptance threshold.
The positional encoding's weak relaxation and the suboptimality of permutation
schedules beyond three machines are both recorded in
[known failures](known-failures.md).

Follow-up: C6 (heterogeneous backend and GPU feasibility) now has its dependencies
met, and C8 (registry, SDK and comparative runner) remains unblocked. Both need
their specifications written before any public API.

## C5 Flow-Shop Scheduling Specification (2026-09-11)

Objective: write and accept the C5 contract before any public scheduling API
exists, as required by AGENTS.md, CONTRIBUTING.md and the Stage 3 scope. No C5
behavior is implemented by this change.

Status: complete; SPEC-0008 and ADR-0007 are accepted and the project records that
reference C5 are synchronized.

Acceptance gate: the specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation and link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and unchanged test counts, because no behavior changes.
Resource budget: CPU only, four Cargo workers, no GPU workloads.

Evidence (2026-09-11): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0 and no
native-uncovered warning. Rust tests remain 159 and Python tests remain 39, which
is the expected result for a contract with no behavior: had either count moved,
this change would have been doing something it claims not to. Documentation rose
from 46 to 48 pages, SPEC-0008 and ADR-0007, with internal links and anchors
validated. The RustSec advisory fetch failed and recovered through the cached
database, the condition already recorded in [known failures](known-failures.md).
No checks were waived.

The diff is documentation plus one doc comment. `Cargo.lock`, `Cargo.toml`,
`schemas/`, `tools/` and `examples/` are untouched, and the only change under
`crates/` replaces the stale placeholder comment in optimizer-schedule that claimed
its specification was unassigned. No CHANGELOG.md entry accompanies this change:
the changelog records user-visible changes, and an accepted contract with zero
behavior is not one, matching the C2 specification commit. C5 enters the changelog
when its behavior ships.

Three claims in these documents were verified before being written down rather than
reasoned about, because each is the kind a later implementation could get quietly
wrong. Taillard's generator, reimplemented from the OR-Library transcription of the
1993 EJOR paper, reproduces his published ta001 matrix exactly from seed 873654221.
The positional encoding's optimum equals the makespan recurrence for a fixed
permutation, and its minimum over all permutations equals brute-force enumeration,
over 300 randomly generated instances. And permutation schedules are genuinely
suboptimal for the general flow shop beyond three machines: on a 3-job, 4-machine
instance the best permutation schedule costs 50 while the best general schedule
costs 47, which is why SPEC-0008 states the permutation restriction is part of the
problem rather than an approximation. The exhaustive-oracle bound was also measured:
enumerating 8 jobs is 40,320 permutations in roughly 130 ms, so the fixed grid in
the acceptance tests is affordable at n ≤ 8.

Resolved while writing: the first gate run failed rustdoc with an unresolved
intra-doc link, because the new module comment linked to `optimizer_core` while
optimizer-schedule still declares no dependencies. Adding that dependency edge
belongs to the implementation commit, not to a spec-only change, so the comment now
uses plain backticks. Worth recording because the failure was the workspace's
warnings-as-errors rustdoc correctly catching a documentation claim that referenced
something not yet in scope.

Noted and not changed: `state/backlog.yaml` retains one `status: ready`, which is
now C5's own and is correct. The benchmark protocol gained a paragraph stating when
a generated suite satisfies its freezing rule without download tooling, because the
rule as written required download tooling and ADR-0007 deliberately takes the other
route; leaving the two in apparent conflict would have made the protocol read as
overridden rather than extended.

Follow-up: C5 implementation is now dependency-ready under SPEC-0008. It requires
the instance document and its strict parser, the recurrence evaluator kept
independent of the encoding, the Lehmer generator with the pinned published seeds,
the positional adapter, the NEH and insertion producers in their own crate so the
independence evidence comes from the workspace build, a CLI surface, the frozen
manifest with committed instances and checksums, and the exhaustive permutation
grid that is the slice's load-bearing assertion.

Expected changes: docs/specifications/SPEC-0008-flow-shop.md,
docs/decisions/ADR-0007-flow-shop-encoding.md, state/backlog.yaml,
docs/benchmarks/protocol.md, implementation-plan.md, docs/architecture/overview.md,
docs/architecture/testing.md, README.md, wiki/status.md, AGENTS.md, the stale
placeholder doc comment in optimizer-schedule, and this record.

Two decisions are settled before implementation because both are the kind a later
implementation could get quietly wrong, and both were verified rather than
assumed.

The positional encoding is exactly linear. Makespan is not linear in a raw
permutation, but the positional formulation with binary job-position assignment
and continuous completion times needs no big-M constant. Checked over 300 random
instances: the encoded optimum for a fixed permutation equals the makespan
recurrence, and the minimum over all permutations equals brute-force enumeration.
The consequence is that C5 reuses `Model`, `Model::evaluate`,
`optimizer_solver::search`, `RunRecord` and `optimizer verify` unchanged, with no
new record type and no schema version bump.

The frozen Taillard subset is generated from published seeds rather than
downloaded. Taillard's documented Lehmer generator reproduces his published ta001
matrix exactly from seed 873654221, checked against the OR-Library transcription
of the EJOR paper. The canonical instance host timed out from this environment, so
generating from pinned seeds removes a network dependency from the gate instead of
adding one. `schemas/benchmark-manifest-v1.schema.json` already carries the shape
this needs: `instances[].generator` accepts a name, seed and parameters, so no
schema change is required.

What C5 must not claim: the positional encoding's LP relaxation is weak and a
20x5 Taillard instance is 400 binaries, so the executive will not prove optimality
at that size. Proven-optimal assertions are therefore confined to tiny instances
where exhaustive permutation enumeration is the independent oracle, and the frozen
subset carries feasibility, determinism and validated-incumbent assertions only.
Best-known upper bounds are deliberately not committed, because recording one
would create an acceptance threshold that the benchmark protocol says requires its
own ADR and experiment record.

Also in scope: `state/backlog.yaml` still names C4 as the current and next-ready
milestone and marks it `ready` while every other record in the repository says C4
is complete. It is the only file carrying that staleness. The benchmark protocol's
planned-suites table also still dates the two flow-shop suites in the retired
M-numbering.

## Local C4 Integration (2026-09-11)

Objective: verify the feat/run-surface branch from a clean checkout, integrate it
into local main, and delete the feature branch after confirming its commits are
retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 6725d93; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-11): the branch was cloned to /tmp/c4-final with
`--no-hardlinks` and no `target/` directory present, and `bash tools/check.sh`
passed there in 1 minute 56 seconds with zero skip messages. That run built the
pinned HiGHS 1.11.0 library from the checksum-verified upstream archive inside the
clone, ran 159 Rust and 39 Python tests, re-executed the committed run record
against the freshly built binary, validated 46 documentation pages, and passed
cargo-deny, artifact validation and bootstrap smoke.

Two stale claims were found and fixed before integration rather than carried onto
main. AGENTS.md still stated that C3 was the current scope and had no accepted
specification; it is the first file an agent reads, so a stale scope there
misdirects work rather than merely aging. And the three review markers named
692e19f, the parent the documents were written against, rather than the
implementing revision whose content was reviewed.

main was fast-forwarded from 692e19f to 6725d93 without conflicts or history
rewriting, so the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained, and
`git branch -d` removed the fully merged feat/run-surface branch.

No remote refs were changed. main is now 5 commits ahead of origin/main and
remains unpushed pending separate authorization.

Follow-up: C5, the flow-shop scheduling vertical slice, is dependency-ready.
Write its specification before introducing any public scheduling API. C8, the
local registry, SDK and comparative experiment runner, is also unblocked; the SDK
needs an ADR amending ADR-0003 before any binding code.

## C4 Follow-up: Gated Re-execution and Engine Diagnostics (2026-09-11)

Objective: close three gaps found reviewing the C4 slice — a gate that never
re-executed a committed record, a divergence that could not distinguish a changed
engine from a wrong result, and a non-native build recording a backend version it
never called.

Status: complete; the full gate passes with native acceptance covered, and the
non-native configuration passes separately.

Acceptance gate: the committed example record re-executes against the current
build inside `bash tools/check.sh`, with both refusal directions asserted there
too; a record naming a different revision or compiler still verifies while
reporting the difference; a divergence carries that difference as a note without
changing its exit code; a build linking no native library records `unavailable`
rather than the pinned version, shown by a test that fails when the old code is
reinstated. Resource budget: CPU only, no GPU workloads.

Scope boundary: consulting engine identity as an *explanation* is within
SPEC-0005 as accepted, because requirement 11 fixes the ten compared fields and
requirement 13 forbids strengthening a claim; neither constrains diagnostic text.
Deciding that a version mismatch makes divergence *tolerable* would change the
meaning of agreement, which SPEC-0005's compatibility section says requires a new
record version and an ADR. That remains open and is recorded, not implemented.

Evidence (2026-09-11): the complete gate passed with the pinned library linked and
zero skip messages. Rust tests rose from 156 to 159: two environment-difference
contracts in optimizer-experiment and one CLI contract asserting the diagnostic
does not decide agreement. Python tests remain 39 and documentation 46 pages. The
new `tools/verify_committed_record.py` step reports
`committed run record re-executed and verified: passed`.

`AI_OPTIMIZER_SKIP_NATIVE=1 bash tools/check.sh` also passed with all 159 tests,
still printing its uncovered-acceptance warning, and correctly skipping the
committed-record step because a build with no library cannot solve at all.

The backend-version fix is verified by reinstating the defect rather than by
assertion alone: with `PINNED_VERSION` restored on the pre-cancelled path, the
non-native test fails at backend.rs:172; with the fix, it passes. The same test
runs in both configurations, so the native path is covered by the same assertion.
`interrupted_record` was the reachable path, because a pre-cancelled solve returns
a record without touching the library.

Why the gate step exists: every Rust re-execution test produces its record moments
earlier in the same process against the same binary, so none of them exercised the
property SPEC-0005 actually claims, that a record outlives its author. The gate now
re-runs a record committed at an earlier revision, and asserts the fingerprint
refusal and a counter divergence there as well, so the passing case is not the
only thing checked.

Noted: the example record's own provenance differs from any current checkout by
construction, since it carries the all-zero revision. That made it the natural
fixture for the diagnostic — verifying it now reports `environment_differs: true`
while still agreeing and exiting 0, which is exactly the separation between
explanation and decision that this change is about.

## C4 Agent-Independent Run Surface (2026-09-11)

Objective: implement the first C4 slice under a new SPEC-0005: expose the C2
executive and C3 extension host through the CLI, wrap each search in a
provenance-bearing run record, and add a verification command that re-runs a
search from its record alone and fails on disagreement.

Status: complete; the specification preceded the implementation, and the full
gate passes with native acceptance covered.

Acceptance gate: a search performed through the CLI writes a schema-valid run
record carrying source revision, dirty state, hardware, toolchain, backend
identity and version, the canonical model fingerprint and hashed inputs; that
record is re-executable by `optimizer verify` using only its embedded
configuration and the model it names; verification detects a mutated outcome,
objective, dual bound, forfeiture flag and each node counter individually, and
rejects a model whose fingerprint changed while its `model_id` did not;
elapsed time alone never fails verification; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Scope boundary, decided before implementation: the backlog's C4 line bundles
four deliverables and CONTRIBUTING.md mandates one complete vertical slice. This
slice delivers the CLI run surface and pinned reproducible runs. The local
registry and the Python SDK are deferred to their own specifications and gates
and are recorded in [known failures](known-failures.md) rather than dropped
silently. The SDK deferral has a technical basis: pyo3 expands to unsafe code,
the workspace forbids it, and ADR-0003 permits unsafe only inside
optimizer-highs, so an SDK needs an amending decision record.

Expected changes: new SPEC-0005 and ADR-0006; `crates/optimizer-experiment`
gains its first types and dependencies; new `schemas/run-record-v1.schema.json`
and `schemas/search-record-v2.schema.json`; `crates/optimizer-cli` gains
`search` and `verify` over new optimizer-solver and optimizer-experiment
dependencies; new tests in optimizer-cli, optimizer-experiment and
tests/integration; `examples/run-record-v1.json`;
`tools/validate_artifacts.py`; README.md, CHANGELOG.md,
docs/architecture/{overview,testing}.md, a new run-and-verify tutorial,
docs/operations/build.md, wiki/{status,glossary}.md, schemas/README.md,
cuda/schedule_eval/README.md, implementation-plan.md, state/backlog.yaml,
state/known-failures.md and this record.

Evidence (2026-09-11): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library built and linked, with **zero skip messages**, in 20
seconds on a warm build directory: format, warnings-as-errors Clippy over all
targets, 156 Rust tests, workspace build, warnings-as-errors rustdoc, cargo-deny
(advisories, bans, licenses, sources all ok), artifact validation, 39 Python
tests, 46-page documentation and link validation, and bootstrap smoke. No checks
were waived.

Rust tests rose from 132 to 156: 11 run surface CLI contracts in optimizer-cli,
11 run record contracts in optimizer-experiment, and 2 SHA-256 unit tests.
Python tests rose from 20 to 39: 12 run record and search record schema
contracts plus 2 checksum-agreement tests, counted with subtests as unittest
reports them. Documentation pages rose from 43 to 46: SPEC-0005, ADR-0006 and
the run-and-verify tutorial.

Cargo.lock changed only by adding local dependency edges: optimizer-cli on
optimizer-experiment and optimizer-solver, and optimizer-experiment on
optimizer-core, optimizer-solver, serde and serde_json. No external package
version changed, and no new external dependency was introduced.

Reproducibility evidence, stated as what was actually checked rather than as a
property claimed in prose:

- `optimizer search` over examples/model-v1.json reported
  `outcome: proven_optimal`, `objective: 2.5`, `dual_bound: 2.5`, `forfeited:
  false` and exit 0, matching the C1 solve of the same model exactly. The record
  carried a 40-hex revision, the model fingerprint `fnv1a64:cc63f58b64d1c205`,
  and a SHA-256 for each of the two input documents.
- `optimizer verify` on that record re-ran the search and agreed, exit 0, naming
  all ten compared fields in its verdict.
- Verification was shown to be able to fail, in both directions it must. A model
  whose objective coefficient changed from 2.0 to 2.5 while keeping
  `model_id: tiny-mixed` was refused before any search ran:
  `document: model fingerprint mismatch`, exit 2. A record whose objective was
  edited to 1.5 was refused after re-running:
  `divergence: numerical: objective: recorded 1.5, reproduced 2.5`, exit 2.
- Each of the ten compared fields is asserted to fail when it alone is mutated,
  and the list of mutated field names is asserted equal to
  `RunRecord::compared_fields()`, so a field cannot be dropped from the
  comparison without a test failing.
- A record differing only in `elapsed_ms` by 987 seconds still verified with exit
  0, which fixes elapsed time as diagnostic rather than contractual.
- A node-limited search wrote its record, reported `outcome: node_limit` and exit
  1, and that record verified as still limited. A forfeited search that verifies
  is asserted to remain forfeited and to fail `proves_completion`.

Why the SHA-256 is implemented rather than taken from a crate: `sha2` and its
dependencies would add six external packages under `deny.toml`'s
`multiple-versions = "deny"` policy for one well-specified function. It is
implemented in safe Rust and checked against the FIPS 180-4 published vectors,
including the three padding edge cases at 55, 56 and 64 bytes and the
one-million-character vector, then independently against Python's `hashlib` over
the committed example documents and over a freshly generated record. Agreement
between the two implementations is verified rather than assumed.

Both normative authorities accept the same documents. The new schemas give C2 and
C3 records their first schema coverage, and `RunRecord::from_json` validates the
embedded search record's version on the parse path, so the divergence that
produced commit 6516a6f cannot recur here.

Resolved during implementation: an early assertion that a record with absent
measurements contains no `null` at all was wrong and was narrowed. Search
configuration serializes an absent budget as an explicit `null` meaning
unlimited, which is SPEC-0003's stated convention; the omit-rather-than-null rule
governs measurements. The test now asserts the three measurements are absent and
that `node_limit` is still explicitly null beside them.

Noted and not changed: the example record is generated from a real search and
then rewritten with the all-zero revision and example hardware, matching how
examples/experiment-result.json marks itself as a shape rather than evidence. Its
input hashes are the real ones and are verified against the committed files by
both the validator and a Python test.

Scope split recorded in the backlog: C4's original line covered four
deliverables. C4 is now the run surface and the registry, SDK and comparative
runner are backlog item C8, which depends on C4. C5, C6 and C7 keep their
dependency on C4, which remains meaningful because the run surface is what they
build on. The four deferrals are recorded in
[known failures](known-failures.md) with their blockers.

Clean-checkout verification, which is the stronger C1 and C3 standard and the
case that matters here because this change adds four crate dependency edges where
a stale lockfile or a missing manifest entry would otherwise hide behind a
populated `target/`: the branch was cloned to /tmp/c4-verify with
`--no-hardlinks` and no `target/` directory present, and
`bash tools/check.sh` passed there in 1 minute 36 seconds. That run built the
pinned HiGHS 1.11.0 library from the checksum-verified upstream archive inside
the clone and ran the same 156 Rust and 39 Python tests. The only lines matching
"skip" were CMake's own `Check for working CXX compiler - skipped` probes, not
test skips, so native acceptance was genuinely covered rather than inherited from
a warm build directory.

On the clean committed tree the run surface produces evidence-grade provenance:
`optimizer search` recorded revision c0eac20 with `dirty: false`, and
`optimizer verify` reported `agreement: true` with `evidence: true` and exit 0.
The dirty mid-implementation runs reported `evidence: false`, which is the
requirement 5 rule working rather than a defect.

No remote refs were changed and nothing was pushed; main remains unpushed pending
separate authorization. The branch feat/run-surface holds two commits, 8775da1
specifying the surface and c0eac20 implementing it.

## Local C3 Integration (2026-09-09)

Objective: verify the reviewed feat/extension-runtime branch from a clean
checkout, integrate it into local main, and delete the feature branch after
confirming its commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 6516a6f; the
feature branch is deleted and the worktree is clean. Resource budget: CPU only,
four Cargo workers, no GPU workloads.

Evidence (2026-09-09): the branch was cloned to /tmp/c3-verify with no `target/`
directory present, and `bash tools/check.sh` passed there in 1 minute 44 seconds
with **zero skip messages**, so native acceptance was genuinely covered rather
than inherited from a warm build directory. That run built the pinned HiGHS
1.11.0 library from the checksum-verified upstream archive inside the clone,
producing both `libhighs.a` (10.2 MB) and the standalone reference executable
(5.0 MB). It ran 132 Rust tests and 20 Python tests, validated 43 documentation
pages, and passed cargo-deny, artifact validation and bootstrap smoke.

The clean clone also solved examples/model-v1.json to `termination: optimal`,
`objective: 2.5`, `backend_version: 1.11.0` with an independently validated
feasible incumbent and exit 0, matching the workspace result exactly.

This clean-checkout pass is the acceptance evidence for the integration. It was
run because C3 adds two crates and a new dev-dependency edge, which is exactly
the case where a stale lockfile or a missing manifest entry hides behind a
populated `target/`. The C2 integration relied on its pre-integration gate pass
instead; this record restores the stronger C1 standard.

main was fast-forwarded from b934dbd to 6516a6f without conflicts or history
rewriting, so the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained on main,
`git rev-parse` confirmed main is exactly the verified revision, and
`git branch -d` removed the fully merged feat/extension-runtime branch. The
worktree is clean and the bootstrap smoke was rerun on the integrated revision
for clean revision-bound provenance.

The RustSec advisory-database fetch failed in the clean clone and recovered
through the cached database, as recorded in [known failures](known-failures.md).
Bans, licenses and sources were checked normally. No checks were waived.

No remote refs were changed. main is now 3 commits ahead of origin/main and
remains unpushed pending separate authorization; the origin remote and its
outstanding protection settings are recorded in
[known failures](known-failures.md).

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

## C3 Review Follow-up: Test Provenance and Nested Versions (2026-09-09)

Objective: resolve three problems found reviewing the C3 commit — a history that
made four mandatory test repairs indistinguishable from weakened ones, a
replacement test helper that asserted on serializer whitespace, and Rust record
parsers laxer than the JSON Schemas about nested document versions.

Status: complete; the branch is three commits and the full gate passes with
native acceptance covered.

Acceptance gate: the test repair compiles and passes on its own at search
schema version 1, proving it is not a consequence of the version bump; the
repaired assertions are shown to fail when the helper is sabotaged, so none is
vacuous; a record with a wrong nested version is rejected by both
`from_json` and `tools/validate_artifacts.py`; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Expected changes: the branch history; `crates/optimizer-core/src/{lib,solve}.rs`;
`crates/optimizer-solver/src/search.rs`; contract tests in optimizer-core,
optimizer-solver and optimizer-extension-examples; SPEC-0002 requirement 11,
SPEC-0003 requirement 22, SPEC-0004 requirement 23 and their acceptance
mappings; CHANGELOG.md and this record.

Evidence (2026-09-09): the branch is `b934dbd` → `9a2eda5` (test repair) →
`a85da69` (C3) → this commit. `git diff c3-pre-split a85da69` touches only the
test helper, confirming the split preserved the reviewed C3 content byte for
byte elsewhere; the pre-split tip is retained as tag `c3-pre-split`. The repair
commit's 22 contracts pass at version 1 with no extension field present, which
is what establishes that the repair was independent of the feature rather than
produced by it. Sabotaging `retarget_version` to a no-op makes both version
tests fail, so neither is vacuous.

The complete `bash tools/check.sh` gate passed with the native library built and
linked, with **zero skip messages**. Rust tests rose from 130 to 132: one nested
version contract in optimizer-core and one in optimizer-solver, plus extension
document coverage folded into the existing round-trip test. Cargo.lock changed
only by adding a `serde_json` dev-dependency edge for
optimizer-extension-examples; no external package version changed.

Why the parser change needed no ADR: `schemas/solve-record-v1.schema.json`
already pins the nested candidate's `schema_version` to `const 1` and pins
`options` by `$ref`, and those schemas are normative under SPEC-0007. The Rust
parsers checked only their own top-level version, so the two enforcement paths
disagreed and `tools/validate_artifacts.py` rejected documents the Rust parser
accepted. This change brings code into line with an accepted contract rather
than deciding anything new, and it is strictly narrowing: no document valid
under both paths becomes invalid. Verified by parsing one fixture with a wrong
nested version through both paths and confirming both reject it.

`Candidate::canonical` is deliberately not called on the parse path. It also
sorts and range-checks values, and parsing a record must reject a wrong version
without silently rewriting the document it was handed.

Resolved during implementation: the acceptance suite needed `serde_json` as a
dev-dependency to mutate a parsed document by field path. It is test-only, so
the examples crate's runtime dependencies remain optimizer-core and
optimizer-extension alone, and the independence evidence is unaffected.

Noted and not changed: `crates/optimizer-core/tests/solve.rs` still replaces
every `"schema_version": 1` occurrence in one assertion, which passes only
because the top-level check fires first. It is not wrong today and its
assertion is the top-level rule, so it is left alone; the new nested-version
contract beside it covers what the replacement cannot distinguish.

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

## C3 Extension Runtime and Authority Model (2026-09-09)

Objective: implement C3 under a new SPEC-0004: an extension runtime with a
declared authority model, candidate producers and search advisers, whose actions
the core validates and whose failures are recorded rather than absorbed.

Status: complete; the specification preceded the implementation, and the full
gate passes with native acceptance covered.

Acceptance gate: independently authored extensions build and run against the
published APIs with no engine-internal change; invalid candidates, invalid
advice, incompatible versions, panics and budget abuse each produce a typed
record entry; the proven optimum and the proof claim are identical with and
without extensions, including adversarial ones; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Expected changes: new SPEC-0004 and ADR-0005; new crates optimizer-extension and
optimizer-extension-examples; optimizer-solver contracts, executive and hooks;
`SEARCH_SCHEMA_VERSION` 1 to 2; the C2 search and native executive tests;
SPEC-0003 compatibility and exclusion clauses; implementation-plan.md, README.md,
docs/architecture/{overview,testing}.md, wiki/{status,glossary}.md, CHANGELOG.md,
state/backlog.yaml, state/known-failures.md and this record.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked, with **zero skip messages**: format,
warnings-as-errors Clippy, 130 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny (advisories/bans/licenses/sources), artifact validation, 20
Python tests, 43-page documentation/link validation and bootstrap smoke. Rust
tests rose from 84 to 130: 27 new extension runtime contracts, 18 new
independent-extension acceptance contracts, and 1 new native end-to-end
contract. No checks were waived.

The RustSec advisory-database fetch failed on the final run and recovered
through the cached database, as recorded in
[known failures](known-failures.md). Bans, licenses and sources are offline and
were checked normally; the advisory check ran against the cache rather than a
fresh fetch.

Cargo.lock changed only by adding local dependency edges for
optimizer-extension (optimizer-core, serde, serde_json),
optimizer-extension-examples (optimizer-core, optimizer-extension, and
optimizer-solver as a dev-dependency), the optimizer-solver dependency on
optimizer-extension, and optimizer-highs dev-dependencies on both new crates.
No external package version changed.

Correctness evidence, stated as what was actually checked:

- Three honest extensions and three hostile ones covering 17 distinct
  misbehavior modes (7 bad proposals, 4 bad actions, 6 unadmittable
  declarations) live in optimizer-extension-examples, which depends on the
  published extension and core APIs and takes optimizer-solver only as a
  dev-dependency. That the
  workspace builds is the evidence that a third-party extension needs no
  engine-internal change; it is not an assertion in prose.
- Over a fixed 25-model grid covering both senses, integer and binary domains,
  three capacities, two coefficient settings and a proven-infeasible case, every
  hostile extension leaves the outcome, the
  proven optimum, the dual bound, the forfeiture state and both prune counters
  identical to the extension-free run, which itself agrees with brute-force
  enumeration of the whole assignment space. These comparisons use unlimited
  node and time budgets deliberately: a hostile adviser spending a node budget
  on unpromising nodes legitimately changes which outcome a *budgeted* search
  reaches, so a budgeted assertion would be flaky by design rather than a real
  correctness check.
- An empty extension policy reproduces the extension-free record exactly, apart
  from measured elapsed time. That is the direct check that C3 did not perturb
  C2, and all 22 C2 contracts still pass unchanged in substance.
- Refusals are typed and recorded: infeasible, out-of-bounds, wrong-model,
  incomplete and nonfinite candidates; advice naming a nonexistent node, an
  unknown variable or an integral variable; both directions of host-contract
  mismatch; a refused transformation category; an unclaimed problem class;
  contained panics in `propose`, `advise` and even `declare`; and exhausted
  invocation and proposal budgets. A refused extension is never invoked at all,
  which is asserted against a call counter the extension itself maintains.
- A producer's claimed objective is never read. The out-of-bounds producer
  offers a candidate with an enormous objective and the record still reports the
  true optimum from independent recomputation.
- Recorded diagnostics stay bounded: 10,000 distinct rejections leave the
  counter exact at 10,000 and the retained messages capped at 8.
- The native end-to-end test drives the real executive over pinned HiGHS with a
  lying producer, a ghost-node adviser and a panicking adviser registered
  simultaneously, and still proves the optimum independent enumeration finds.

Resolved during implementation:

- The first acceptance run showed a search adviser being consulted for a
  continuous model, which requirement 20 forbids. Root cause: the node-selection
  hook ran whenever the frontier was non-empty, including when it held exactly
  one node and there was no choice to make. Fixed by not consulting an adviser
  for a decision with one possible answer, and recorded as SPEC-0004
  requirement 9a rather than patched silently. Consulting there could only
  manufacture rejections describing the hook rather than the extension.
- Three acceptance tests initially asserted against models whose LP relaxations
  happen to be integral, so no branching occurred and no adviser was ever
  consulted; they were passing or failing for reasons unrelated to their names.
  They now use a model with a genuinely fractional relaxation and assert
  `nodes_explored > 1` first, so a future change that removes the branching
  cannot make them vacuous.
- Three C2 record tests needed repair rather than renumbering. Two mutated "the
  first `schema_version` in the JSON", which at version 2 is the nested
  candidate's or is absent entirely, so they would have parsed successfully and
  panicked on `unwrap_err`. A third hand-wrote a complete configuration object
  plus an unknown field; with a new required field it would have been rejected
  for the *missing* field while still passing, silently ceasing to test
  unknown-field rejection. All three now target the document's own version or
  build their base from a serialized valid configuration.

Deferred and recorded rather than hidden: the extension host is in-process, so
containment covers panics but not a process abort, stack exhaustion or a memory
fault, and no per-extension memory budget is enforced. Process isolation and the
versioned C boundary for dynamically loaded native components are specified as
deferred and need their own decision record, because a second unsafe boundary
would amend ADR-0003. No CLI subcommand exposes extensions yet, no JSON Schema
covers search or extension records, and no performance claim is made: C3
establishes safety only, and whether advisers improve search is C7's question.

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

Contract decisions worth recording, because they are the ones a later
implementation could get quietly wrong:

- No extension path may reach forfeiture, a search-loop break, or an `Err`
  return from `search`. An adversarial extension must not be able to deny a
  proof the engine would otherwise complete. C2 forfeits when a *backend*
  misbehaves because its bounds become untrustworthy; a bad extension candidate
  implies nothing about bounds, so it is a recorded rejection and a disable.
- A proposed candidate is validated by `Model::evaluate` against the original
  model, and the record's objective is the recomputed one. A producer's claimed
  objective is never read.
- An advised branching variable must lie in the recomputed fractional set. This
  is a termination requirement, not a preference: branching on an integral
  variable yields two children that do not tighten the box, which is the same
  hazard SPEC-0003 requirement 12a exists to prevent.
- Extension budgets are counted in invocations and proposals, never wall clock,
  so the search path cannot depend on machine speed and requirement 21's replay
  guarantee survives.
- The `backend` category is not introduced: `optimizer_core::Backend` is already
  public and replaceable under SPEC-0002, and declaring the category only to
  refuse it would read as a regression of an accepted contract.
- `transformation` is refused at declaration time, so no code path for it
  exists until its validity has its own contract.

## Local C2 Integration (2026-09-09)

Objective: integrate the reviewed feat/solver-executive branch into local main
and delete the feature branch after confirming its commits are retained.

Status: complete; fast-forward integration and feature-branch cleanup finished.

Acceptance gate: fast-forward integration preserves the reviewed tip 5a74184;
the feature branch is deleted and the worktree is clean. Resource budget: CPU
only, no GPU workloads.

Evidence (2026-09-09): main fast-forwarded from c742064 to 5a74184 without
conflicts or history rewriting, so the integrated tree is byte-identical to the
revision whose complete gate pass is recorded below. `git merge-base
--is-ancestor` confirmed the reviewed tip is retained on main, and `git branch
-d` removed the fully merged feat/solver-executive branch. The worktree is clean
and the bootstrap smoke was rerun on the integrated revision for clean
provenance.

No remote refs were changed. main remains unpushed pending separate
authorization; the origin remote and its outstanding protection settings are
recorded in [known failures](known-failures.md).

## C2 Owned Solver Executive Implementation (2026-09-09)

Objective: implement C2 under SPEC-0003: an owned branch-and-bound executive in
optimizer-solver that consumes the C1 backend contract as a relaxation service
and owns proof completion.

Status: complete; executive, contract documents, node representation and
acceptance tests are in place and the full gate passes with native acceptance
covered.

Acceptance gate: exhaustive tiny-model search compared against independent
enumeration, termination semantics, budgets, cancellation, proof completion, and
`bash tools/check.sh`. CPU only, four Cargo workers, no GPU workloads.

Expected changes: optimizer-solver runtime and tests, an end-to-end test in
optimizer-highs, SPEC-0003 implementation/test links, project records, changelog
and this task record.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked, with **zero skip messages**: format,
warnings-as-errors Clippy, 84 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny (advisories/bans/licenses/sources, fetched successfully this
run without the cached-database fallback), artifact validation, 20 Python tests,
41-page documentation/link validation and bootstrap smoke. Rust tests rose from
58 to 84: 22 new search contracts and 4 new native end-to-end contracts. No
checks were waived.

Cargo.lock changed only by adding local dependency edges for optimizer-solver
(optimizer-core, serde, serde_json) and the optimizer-highs dev-dependency on
optimizer-solver. No external package version changed.

Correctness evidence, stated as what was actually checked:

- 192 tiny discrete models over a fixed coefficient, bound and row-limit grid,
  both objective senses, integer and binary domains, agree with brute-force
  enumeration of the entire assignment space on the proven optimum and on proven
  infeasibility. The grid is fixed with no randomness, so a failure reproduces.
- Every non-optimal relaxation termination (time, iteration and node limits,
  interruption, feasible-without-proof, numerical failure, backend failure,
  unsupported) forfeits the proof claim and prunes nothing by bound.
- The executive runs entirely on test backends, which is what demonstrates
  backend neutrality; the end-to-end test over pinned HiGHS lives in
  optimizer-highs so optimizer-solver keeps that guarantee. Both agree with
  independent enumeration.

Resolved during implementation:

- The first test run did not terminate. A backend that returns the same
  fractional solution regardless of node bounds caused the executive to
  regenerate an identical child forever. Root cause: the executive trusted the
  relaxation solution to lie inside the node it asked about. Fixed by checking
  every relaxation solution against its own node before branching, which makes
  termination independent of backend correctness. Recorded as SPEC-0003
  requirement 12a rather than fixed silently.
- A record test asserted no `null` anywhere in the serialized record. That
  conflated two rules: absent *measurements* are omitted, while an absent
  *budget* stays an explicit null meaning unlimited, matching the C1
  configuration convention. The assertion now targets measurements by name.

Deferred and recorded rather than hidden: checkpoint restart is specified in
shape and deliberately unimplemented; no CLI subcommand exposes search yet; no
performance claim is made and no comparison against another solver was run.
Cross-node basis reuse remains Stage 5 reoptimization work.

Follow-up: C3, the extension runtime and authority model, is dependency-ready.
Write its specification before introducing any public extension API.

## C2 Solver Executive Specification (2026-09-09)

Objective: write and accept the C2 contract before any owned search API exists,
as required by AGENTS.md and the Stage 2 entry condition. No C2 behavior is
implemented by this change.

Status: complete; SPEC-0003 and ADR-0004 are accepted and the project records
that reference C2 are synchronized.

Acceptance gate: the specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation/link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and unchanged test counts, because no behavior changed.
Resource budget: CPU only, four Cargo workers, no GPU workloads.

Expected changes: docs/specifications/SPEC-0003-solver-executive.md,
docs/decisions/ADR-0004-owned-search.md, state/backlog.yaml, README.md,
implementation-plan.md, docs/architecture/overview.md, wiki/status.md, the two
stale placeholder doc comments in optimizer-solver and optimizer-schedule, and
this record.

Contract decisions worth recording, because they are the ones a later
implementation could get quietly wrong:

- A relaxation objective is admitted as a dual bound only when that relaxation
  reported `Termination::Optimal`. Any limit, interruption or failure leaves the
  node bound unavailable, forbids pruning that node by bound, and permanently
  forfeits the search's proof claim, recorded as `forfeited` in the record. This
  is what stops a timeout inside a child solve from silently discarding an
  optimal solution.
- `SearchOutcome` is a new type rather than a reuse of `Termination`. The two
  express different claims: one relaxation solve versus an exhausted node tree.
- The executive consumes the C1 `Backend` trait and must not depend on
  optimizer-highs, so the pruning and forfeiture rules are testable against a
  stub backend without the native library.
- `Tolerances.integrality` governs both incumbent acceptance and the decision to
  branch, so the two cannot disagree.
- Checkpoints are specified in shape only; restart is deliberately not part of C2
  and needs its own acceptance evidence.

Numbering: no spec-numbering convention exists in the repository, so SPEC-0003
and ADR-0004 take the next free sequential numbers. Two placeholder doc comments
referenced the retired M0-M6 scheme and dangled at nonexistent specifications;
optimizer-schedule's stale "SPEC-0003" claim would have collided with this
specification and now names C5 with an unassigned number.

No CHANGELOG.md entry accompanies this change: the changelog records user-visible
changes, and an accepted contract with zero behavior is not one. C2 enters the
changelog when its behavior ships.

Follow-up: C2 implementation is now dependency-ready under SPEC-0003. It requires
a stub-backend test crate for the bound-validity and forfeiture rules plus
exhaustive tiny-model comparison against independent enumeration.

## Local C1 Integration (2026-09-09)

Objective: verify the reviewed feat/highs-backend branch from a clean checkout,
integrate it into local main, and delete the feature branch after confirming its
commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip c8bb6f3; the
feature branch is deleted and the worktree is clean. Resource budget: CPU only,
four Cargo workers, no GPU workloads.

Evidence (2026-09-09): the branch was cloned to /tmp/c1-verify with no populated
target/native, and `bash tools/check.sh` passed there in 1 minute 43 seconds.
That run built the pinned HiGHS 1.11.0 library from the checksum-verified
upstream archive, produced both libhighs.a and the standalone executable, and ran
58 Rust and 20 Python tests with **zero skip messages**, so native acceptance was
genuinely covered rather than bypassed. The clean clone also solved
examples/model-v1.json to `termination: optimal`, `objective: 2.5`,
`backend_version: 1.11.0` with an independently validated feasible incumbent and
exit 0, and wrote a smoke record bound to revision c8bb6f3 with `dirty: false`.

This clean-checkout pass is the acceptance evidence for the integration. main was
fast-forwarded from 9b42b62 to c8bb6f3 without conflicts or history rewriting, so
the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained on main, and
`git branch -d` removed the fully merged feat/highs-backend branch. No remote refs
were changed; main remains 9 commits ahead of origin/main and unpushed, pending a
separate authorization to push.

The advisory database fetch failed again during the clean-clone run and recovered
through the cached database, as recorded in
[known failures](known-failures.md). No checks were waived.

Follow-up: C2, the owned solver executive, is dependency-ready. Its specification
is now accepted as SPEC-0003; see the C2 record at the top of this file. No C2
behavior existed at the time of this integration.

## C1 Backend-Neutral Solve Contract and HiGHS Adapter (2026-09-09)

Objective: implement C1 under SPEC-0002: backend-neutral solve/session types,
HiGHS adapter boundary, strict solve configuration and structured records.

Status: complete; contract, native adapter, solve CLI, schemas and acceptance
tests are in place and the full gate passes with native acceptance covered.

Acceptance gate: core and adapter contract tests, strict CLI solve flow,
status/cancellation/limits/warm-start behavior, reproducible records, and
`bash tools/check.sh`. CPU-only; native HiGHS setup uses the pinned 1.11.0
source and at most four build workers.

Expected changes: optimizer-core, optimizer-highs, optimizer-cli, experiment
schemas, specifications, changelog, tests, and task state. No GPU workload.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked: format, warnings-as-errors Clippy, 58 Rust
tests, workspace build, warnings-as-errors rustdoc, cargo-deny
(advisories/bans/licenses/sources), artifact schema/provenance, 20 Python tests,
38-page documentation/link validation and bootstrap smoke. No checks were waived.

Native provisioning and FFI: `tools/setup_highs.sh` builds the pinned static CPU
library under `target/native/highs-1.11.0/install` from the checksum-verified
upstream archive. A hand-written private FFI module links it; no `highs-sys`
dependency is introduced. `Highs_version()` reports 1.11.0 and the compile-time
assertion confirms a 4-byte `HighsInt`, matching the pinned `HIGHSINT64=OFF`.

Differential acceptance: the standalone executable, built from the same source,
is driven as a separate process over generated LP files and agrees with the
adapter on status and objective for LP, objective-offset, equality, ranged, MILP
and infeasible cases. Disagreement fails the test rather than deferring to the
adapter. The reference is run in a sandbox directory with its log redirected, so
native output cannot litter the tree.

Correctness contracts verified: all 18 native model statuses map explicitly with
no catch-all arm; extracted candidates are re-validated through SPEC-0001 before
publication and a validation failure becomes a numerical failure rather than an
optimality claim; a pre-cancelled solve returns interrupted without creating
native state; limits and interruptions never satisfy `proves_completion`; binary
bounds intersect [0,1] regardless of declared bounds; coefficients below the
native small-matrix threshold are rejected instead of being silently dropped; a
basis is bound to a canonical-model fingerprint, so changed data under an
unchanged `model_id` is rejected.

Resolved review findings during implementation:

- The workspace `unsafe_code = "forbid"` made ADR-0003's native boundary
  unimplementable: `forbid` cannot be relaxed by an inner crate
  (`E0453 overruled by previous forbid`). optimizer-highs now declares its own
  `[lints.rust]` block with `unsafe_op_in_unsafe_fn` denied.
- `serde_json` serializes a nonfinite `f64` as `null`, which is indistinguishable
  from an absent field, so SPEC-0002's absent-not-null rule cannot rely on a
  serializer error. Records omit absent measurements and reject nonfinite ones
  explicitly as numerical failures.
- The stub adapter's pre-cancellation path required a provisioned library, which
  contradicted requirement 6. The check now precedes native dispatch and is
  answered identically with or without the library. Found by running the gate
  with the library deliberately absent.
- A no-op `.max()` in bound conversion and an unfulfilled lint expectation were
  caught by Clippy and removed.

Deferred and recorded rather than hidden: sanitizer runs over repeated native
lifecycles are not yet in the gate; presolve, scaling and reoptimization remain
Stage 5 work; owned search remains C2.

## Roadmap redesign (2026-09-09)

Objective: replace the narrow M0-M6 implementation sequence with the
architecture-driven C1-C7 capability roadmap in implementation-plan.md.

Status: complete; plan and backlog metadata synchronized.

Acceptance gate: roadmap is decision-complete, preserves M0/M1 evidence, keeps
HiGHS as the first replaceable backend, defines executive/extension/SDK/GPU
gates, and bash tools/check.sh reaches the required gate.

Evidence: implementation-plan.md, state/backlog.yaml, README.md, and CHANGELOG.md
now describe C1-C7 and the next dependency-ready task is C1. `git diff --check`
passes. `bash tools/check.sh` reaches preflight but cannot start Cargo because
the environment cannot create its sandbox namespace; no Rust checks were waived.

## M2 Backend Contract and Implementation (2026-09-09)

Objective: implement the approved M2-M6 plan sequentially, starting with the
HiGHS backend contract, safe lifecycle, validated solving and reproducible records.

Status: superseded; see the C1 record at the top of this file. The M2-M6 sequence
was replaced by the evidence-staged roadmap, and this objective was delivered as
C1 under the same SPEC-0002 and ADR-0003 contracts.

Acceptance gate: accepted SPEC-0002 and supporting ADR; standalone HiGHS
differential LP/MILP tests, explicit statuses, cancellation/limits, warm starts,
lifecycle sanitizers, structured records, and bash tools/check.sh. Inspect and
fix review findings before committing.

Expected changes: optimizer-highs, core solve contracts, CLI, experiment schemas,
native build/validation tooling, tests, specifications, ADRs and project state.
Resource budget: CPU only, at most four workers, bounded deterministic
tests and benchmark batches of at most 30 minutes. GPU work will use one shared
host GPU lease at a time. Existing M0/M1 defaults remain unchanged.

Follow-up order under the current roadmap: C2 owned executive, C3 extension
runtime, C4 SDK/registry, C5 flow shop, C6 GPU feasibility, C7 adaptive research.
No remote publication is included.

## Local M1 Integration (2026-09-08)

Objective: merge the reviewed feat/model-validation branch into local main and
delete the feature branch after confirming its commits are retained.

Status: complete; local integration and feature-branch cleanup finished.

Acceptance gate: fast-forward integration preserves reviewed commit 27b1b3a;
bash tools/check.sh passes on main; the merged feature branch is deleted and the
worktree is clean after recording evidence. Expected changes: local Git refs and
this task record. Resource budget: CPU only, four Cargo workers, no GPU workloads.

Evidence (2026-09-08): main fast-forwarded from 9e6dc86 to reviewed tip 27b1b3a
without conflicts or history rewriting. git merge-base --is-ancestor confirmed
the reviewed tip is retained on main, and git branch -d removed the fully merged
feat/model-validation branch. No remote refs were changed.

The unchanged runtime passed the complete acceptance gate before integration,
as recorded below. Two post-merge attempts passed format, Clippy, all 29 Rust
tests, workspace build and rustdoc, then stopped because the RustSec advisory
database could not be fetched. These attempts do not constitute a new full-gate
pass; the successful pre-integration gate remains the full acceptance evidence.
The only additional tracked change is this integration record, validated with
the documentation/link builder and git diff --check before committing.

## Repeated Branch Review (2026-09-08)

Objective: review the complete feature branch against main, fix any substantiated
findings, and repeat until the final review has no unresolved actionable findings.

Status: complete.

Acceptance gate: inspect every changed runtime path and the SPEC-0001/ADR-0002
contracts, verify relevant regression coverage, and run bash tools/check.sh.

Expected changes: this review record and any bounded fixes supported by reproduced
failures. Resource budget: CPU only, at most four Cargo workers, deterministic
tests, no GPU workloads. Review base: local main at 9e6dc86; starting HEAD: 58df6bb.

Current finding: model validate panics with exit 101 when a model/candidate path
contains non-UTF-8 bytes because main uses env::args. Preserve native paths with
args_os and report malformed non-path text as an argument error. Expected fix:
CLI parsing, Unix path/error regression tests, specification and release notes.
Follow-up finding: incomplete/unknown model commands returned bare usage without
the required argument category. Add a categorized dispatch error and regression.

Evidence (2026-09-08): both new regressions failed before their fixes and pass
afterward. Native model/candidate filenames retain their OS representation;
non-UTF-8 command, flag and tolerance text returns an argument error with exit 2.
Incomplete and unknown model commands now return the same error category.
Unix regressions cover real non-UTF-8 filenames, successful reports and missing
files. Specifications, tutorial, changelog and regression instructions agree.

The final complete bash tools/check.sh gate passed: format, warnings-as-errors
Clippy, 29 Rust tests, workspace build, rustdoc, cargo-deny, artifact validation,
8 Python tests, 36-page documentation/link validation and bootstrap smoke.
Temporary RustSec advisory-fetch failures recovered; no checks were waived.
Cargo preflight checks also passed for missing Cargo (exit 127 with a diagnostic)
and the rustup-only PATH fallback to the pinned Rust 1.93.1 toolchain.

Final review against local main at 9e6dc86534de2efa414205752ca58d7584976052
found no unresolved actionable findings. Coverage included strict JSON parsing,
canonical model construction, candidate coverage, arithmetic and tolerance
contracts, report output, CLI errors, dependencies, specifications and fixtures.
The existing independent dense oracle covers 18,522 evaluations and the f64
round-trip suite covers 968 values. Resource use remained CPU-only with four
Cargo workers; scope remains M1. Commit after acceptance, then rerun bootstrap
smoke to record the clean committed revision.

## M1 Review Contract Fixes (2026-09-08)

Objective: reject alternate JSON representations for all model/candidate input
types and return categorized CLI I/O errors when report output fails.

Status: complete.

Acceptance gate: regressions for positional records, object-wrapped enums,
and failed stdout writes; full bash tools/check.sh under SPEC-0001 and ADR-0002.

Expected changes: optimizer-core document parsing, optimizer-cli report output,
contract tests, minimized fixtures, specification clarifications, changelog,
and this task record. Resource budget: CPU only, four Cargo build workers,
bounded deterministic tests, no GPU workloads.

Evidence (2026-09-08): new regressions reproduced accepted alternate JSON forms
and exit 101 on failed stdout before their fixes. Public record types and tagged
bounds now reject positional arrays; domain/objective enums require strings.
Direct and nested parsing tests pass, preserving unknown/duplicate-field rejection
and f64 round trips. CLI tests verify categorized io errors and exit 2 for /dev/full
and closed pipes in structural and candidate modes. Output writes and flushes
are fallible; the specification clarifies that delivered bytes cannot be retracted.

The complete bash tools/check.sh gate passed: format, warnings-as-errors Clippy,
26 Rust tests, workspace build, rustdoc, cargo-deny, artifact validation, 8 Python
tests, 36-page documentation/link validation, and bootstrap smoke. No checks were
waived. Rust 1.93.1, four Cargo workers, and CPU-only simulations were used.
Minimized JSON fixtures and reproduction instructions are in tests/regression/.
Both review findings are resolved; no dependency or numerical-policy changes.

## Commit and Branch Review (2026-09-08)

Objective: validate and commit the pending acceptance-script diagnostic change,
then review the complete feature branch against local main in PR style.

Status: complete; committed as 4981aef and reviewed against local main.

Acceptance gate: run bash tools/check.sh before committing; inspect the complete
main-to-branch diff against SPEC-0001 and ADR-0002 and report actionable findings.

Expected changes: the pending tools/check.sh change and this task record.
Resource budget: CPU only, at most four Cargo build workers; no GPU workloads.

Evidence (2026-09-08): the complete bash tools/check.sh gate passed with Rust
1.93.1 and four Cargo workers: format, Clippy, 22 Rust tests, workspace build,
rustdoc, cargo-deny, artifact validation, 8 Python tests, 36-page documentation
build/link validation, and bootstrap smoke. No checks were waived. Review found
alternate JSON representations and panicking stdout writes, resolved by the M1
review contract fixes above. The comparison base was local main
at 9e6dc86534de2efa414205752ca58d7584976052 (also origin/main locally).

## Current diagnostic fix (2026-09-08)

Objective: make the acceptance gate locate the repository-pinned Rust toolchain and report executor failures clearly.

Status: complete.

Acceptance gate: shell syntax and toolchain preflight behavior pass; existing Rust gate remains unchanged after Cargo is resolved.

Evidence (2026-09-08): `bash -n tools/check.sh` passed. With Cargo absent, the gate exits 127 with an actionable diagnostic instead of an opaque `command not found`; with the pinned toolchain bin directory available, the existing Rust checks remain the executed gate.

Expected changes: tools/check.sh and this task record.

Resource budget: CPU only; no GPU workloads.


Objective: implement M1 core models, candidate validation, versioned JSON, and CLI.

Status: complete.

Acceptance gate: accepted SPEC-0001 and ADR-0002; independent property/exhaustive
model tests, serialization and numerical boundary tests, CLI contracts, and
the complete bash tools/check.sh gate. Commit locally after acceptance.

Expected changes: optimizer-core, optimizer-cli, model fixtures/examples,
specification and ADR, current scope/status documentation, changelog, task state.
Resource budget: CPU only, at most four Cargo build workers, bounded deterministic
tests; no GPU workloads. Existing smoke seeds and configuration remain unchanged.

Evidence (2026-09-08): accepted SPEC-0001 and ADR-0002 preceded implementation.
The complete bash tools/check.sh gate passed after the final runtime/test edits:
format, warnings-as-errors Clippy, 22 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny advisories/bans/licenses/sources, artifact schema/provenance,
8 Python artifact tests, 36-page documentation/link build, and bootstrap smoke.
No checks were waived. The 14 new Rust contracts include 18,522 independent dense
oracle evaluations, generated model ordering properties, 968 finite f64 values
round-tripped through both model and candidate JSON, numerical/domain boundaries,
edge-model fixtures, CLI exit/report behavior, and exact 16 MiB file boundaries.

Resolved regression: Serde internally tagged unit variants accepted an unknown
field on infinite bounds. Strict bound deserialization now rejects the minimized
fixture in tests/regression/infinite-bound-extra-field.json; its contract test passes.

Environment: Rust 1.93.1 and cargo-deny 0.19.0 under /tmp/ai-optimizer-cargo,
RUSTUP_HOME=/tmp/ai-optimizer-rustup, Python tooling /tmp/ai-optimizer-venv,
CARGO_BUILD_JOBS=4. Core contracts completed in 0.17 s and CLI model contracts in
0.78 s in the final gate. Work was CPU-only; lease tests used temporary locks and
simulated jobs. Cargo.lock only adds local core/CLI dependency edges; no external
package versions changed. Serde JSON's float_roundtrip feature preserves f64 input.

Provenance: the precommit gate's smoke honestly records a dirty working tree.
The local feature commit is followed by a smoke rerun for clean revision-bound
provenance at artifacts/bootstrap-smoke.json. This remains CLI startup evidence,
not solver or GPU performance. No push or hosting changes are part of M1.

Follow-up: M2 is dependency-ready. Write SPEC-0002-backend-contract.md before
implementing HiGHS lifecycle, status mapping, cancellation, limits and solve records.
No M2 behavior is implemented here.

## Previous Repository Synchronization

Objective: synchronize the project to https://github.com/liuyumou/OptForge.git.

Status: complete.

Acceptance gate: origin points to the requested repository; main is pushed with
upstream tracking; the remote main revision matches local HEAD; the worktree is
clean. Preserve existing history and validate updated documentation.

Expected changes: Git remote/tracking configuration and repository hosting/task
records. Resource budget: bounded CPU checks and Git operations; no GPU work.

Evidence: the original main history was pushed successfully and main now tracks
origin/main. The complete tools/check.sh gate passed, including 8 Rust tests,
8 artifact tests, dependency policy, documentation, and smoke validation. Hosting
records identify the remote. The synchronization includes this documentation
update; remote revision equality and clean worktree are checked after its push.

## M0 Bootstrap Evidence

Objective: implement M0 from implementation-plan.md.

Status: complete.

Acceptance gate: pinned Rust workspace builds; format, Clippy, tests, dependency
policy, rustdoc, documentation links/build, schemas, and benchmark smoke pass.
GPU discovery must report available UUIDs or an explicit unavailable state.
Simulated jobs must serialize and release ownership after cancellation or exit.

Expected changes: repository bootstrap, crates, tools, schemas, CI, documentation,
examples, benchmark fixtures, and task state. Preserve both original plans.

Resource budget: CPU-only builds and bounded tests; GPU discovery only, no kernels.
One developer, one bounded milestone. M1-M6 remain dependency-ordered backlog.

Evidence before initial commit: Rust workspace build, format, warnings-as-errors
Clippy, 8 Rust unit/integration tests, rustdoc, cargo-deny (advisories, bans,
licenses, sources), 8 Python artifact tests, schema/provenance validation, shell
syntax, and a 33-page documentation/link build passed. Discovery returned all
three expected physical GPU UUIDs without launching kernels.

Clean-checkout acceptance: the complete tools/check.sh gate passed on revision
a628c0c8605dd2434cdf7fd775fae85e96423a31 in an independent local clone at
/tmp/ai-optimizer-m0-verification. It rebuilt every crate and generated a validated
measured smoke record with dirty=false. No acceptance checks were waived.

Verified lease cases: competing-process timeout and serialization, normal release,
SIGINT while waiting, SIGTERM while holding, SIGKILL recovery, and interoperability
with the shell runner's flock primitive. All were CPU simulations. Inventory
reported two RTX 5090 devices and one RTX PRO 6000 by their expected UUIDs.

Artifacts: the clean-clone record is at
/tmp/ai-optimizer-m0-verification/artifacts/bootstrap-smoke.json. The workspace
runner can reproduce artifacts/bootstrap-smoke.json. Records measure CLI startup
only; no solver or GPU performance result is claimed.

Environment: Rust 1.93.1 and cargo-deny 0.19.0 were installed under
/tmp/ai-optimizer-cargo with RUSTUP_HOME=/tmp/ai-optimizer-rustup. Documentation
and schema tooling use /tmp/ai-optimizer-venv. Hosting workflows are configured
but were not run on GitHub; remote protection and GPU-runner provisioning remain
external setup, as documented in state/known-failures.md.

Follow-up: M1 is dependency-ready. Write SPEC-0001-model-and-validation.md, then
implement the original-model numerical authority boundary and its independent
property/exhaustive tests. No M1 behavior has been implemented as part of M0.

## Toolchain recovery (2026-09-09)

The pinned Rust toolchain was present under `/tmp/ai-optimizer-cargo` and
`/tmp/ai-optimizer-rustup` but absent from the default PATH. `tools/check.sh`
now discovers those locations and sets `RUSTUP_HOME` automatically, and the
search order is overridable through `AI_OPTIMIZER_CARGO_HOME` rather than being
hardcoded to one machine's layout.

Superseded detail: this record previously stated that the gate stopped at
artifact validation for a missing Python `jsonschema`. That diagnosis is stale.
`jsonschema` is present and artifact validation passes; the missing module was
`Markdown`, which `tools/requirements.txt` already pins. The gate now checks both
imports as a precondition, so this class of failure is reported in seconds rather
than after several minutes of compilation. C1 native HiGHS and solve CLI
implementation are now complete; see the C1 record at the top of this file.

## PR 19 device-extension acceptance evidence (2026-10-13)

Implementation, experiments and final pinned-native acceptance are complete.
Final acceptance log: artifacts/gpup-state-device-v2/final-native.log (289 Python
tests, all Rust/native/dependency, committed-record replay, documentation and smoke
gates passed). Publication checks follow after pushing the reviewed commits.
The user-selected idle RTX PRO 6000 Blackwell completed 42/42 endpoints: all 6170
independent cases, two ordinary fresh checks, four scalar sanitizers and 36 fixed
primitive timing attempts. Each correctness process retains 40 launches, including
partial counts and short benchmark paths; all six numerical hashes match. Every
warmup and measured endpoint independently verifies. Scalar/benchmark images use
40/48 registers and no stack/spills. No full controller or solver speedup follows.

The busy-5090 v1 attempt is retained (3.002084480 s), with 41 cells unexecuted.
The v2 memcheck zero-error stdout was initially misclassified by a stderr-only
reader; the original result and all raw receipts remain immutable. A separately
frozen, exact-source-native-gated verifier correction changes only four permitted
source files and never re-executes an attempted identity. Both cohort summaries,
continuation/source hashes and all reservation/settlement bindings reverify.

Evidence: artifacts/gpup-state-device-v1 and artifacts/gpup-state-device-v2;
reviewed public summaries are docs/benchmarks/data/state/device-v1.json and
device-v2.json. The original full-bin archive also re-verifies unchanged.
Pre-device full native gates passed with 287, then 288, then 289 Python tests;
the last includes nine device-runner regressions (30 focused state tests total).
Artifacts total under 300 MiB and explicit device allocations peak at 4,980,812 B.

Combined charge: 30.114068273 GPU s (acceptance 8.460919662, timing 21.653148611).
Cumulative: 17665.546083611 / 21602.574545061 s. Final 16452-event ledger SHA-256:
24949150272600fe58364f25ebbf7bf892f7454da342edc268d50684568c5f18. Both 16368- and
16366-event prefixes and all historical phase ceilings remain exact. No reservation
or behavior for GPUP-REFINE follows. Publish in existing PR 19 without merging.
## Execution-tool interruption (2026-10-23)

The explicitly authorized corrected ADR-0044 bootstrap passed. The final
in-container supervisor acceptance passes all 22 resource tests, and the final
CPU admission cohort independently verifies all 12 required dense trajectories.
INT8, FP16 and BF16 useful low windows remain admitted on both dense models.
The final component and interval-Gram proof cohorts pass; the compiled SM120
image uses at most 88 registers with zero spills. No GPU execution or GPU
reservation has occurred in this cost continuation.

Resume from `artifacts/gpup-tensor-cost-v1/cpu-journal-resource-v3.json`, preserving
all earlier journals, failures, sources and receipts. Complete and freeze the
GPU harness, run the full native gate, then follow the accepted acceptance,
profile/forecast and conditional timing gates. Do not rerun the bootstrap or
reset any CPU charges. GPUP-8 remains incomplete and GPUP-9 remains gated.

The execution tool interrupted this continuation before a workspace read:
default sandbox startup failed because user namespaces are unavailable, and
both the initial automatic approval review and its permitted retry timed out.
Neither command started. This is a tool execution interruption, not a numerical
or resource-admission failure, and adds no GPU allocation.
