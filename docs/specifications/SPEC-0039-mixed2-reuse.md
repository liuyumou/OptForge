# SPEC-0039: FP4 reliability diagnosis and changing-model reuse confirmation

Accepted through the user's instruction to proceed with the recommended fresh
confirmation, 2026-11-13. Decision: [ADR-0072](../decisions/ADR-0072-mixed2-reuse.md).
The incomplete SPEC-0038 study, sources, failures and allocation remain exact.

## Scope and numerical authority

Investigate the retained heartbeat failures and all-process sanitizer exit before
new measurement. Keep the original supervisor and its 100 ms limit. Diagnostic
instrumentation must be separate from primary timings. Compare four-CPU work with
three-CPU work inside the same four-CPU envelope; the latter leaves one CPU free
of our numerical workers, not exclusive of other host users. Both measured lanes
use identical placement. Do not infer a historical cause from nonreproduction.
Prospective placement mitigation pins the guardian/coordinator to the fourth CPU
and numerical descendants to the first three. The original supervisor source,
four-CPU charge and 100 ms limit remain exact. A passed placement probe is evidence
of that run's health, not proof that earlier failures are repaired.

An isolated `research/lp-mixed2-reuse` executor extends SPEC-0038 with a bounded
four-model scenario cache. Each model is independently parsed and checked; every
model has its own original-model checker and cached initial observation. Admit
reuse only when dimensions, scaled matrix, row scaling and step shift are
bit-identical. Switching uploads the new bounds/objective to every prepared
engine. Every solve resets its high-precision state; no warm-start claim. Preserve
the FP4 image, local bounds, recovery, native promotion and both final tiers.
Changing a model never grants authority to an old certificate or checkpoint.
Invalid cache identities, incompatible matrices and active-debug switches refuse.
The numerical solve body remains exact. Public defaults remain unchanged.
Before confirmation, version 2 overlaps CPU model preparation with independent
CPU checker startup, for both initial and cached models and both numerical lanes.
Original-model admission still completes before the first CUDA operation; checker
readiness must bind the same model hash. Owned checker guards reap on validation
failure. This addresses the measured roughly 10-second four-scenario preparation
at dimension 2048 in version 1. Preserve that version and its incomplete admission
reservation, which reached its 238-second work deadline. Split subsequent scenario
admission by family; this is development, never a scientific-cell retry.

## Workloads and value

Four primary families: generic and coupled dense 1024/2048. Each stream cycles
four distinct RHS/objective scenarios eight times (32 solves) per tier, retaining
the matrix and both native/FP4 preparation. Scenarios are constructed from the
previous matrix with deterministic primal/dual shifts; they are not user traces.
Use fresh native and FP4 sessions for each family and tier. Include all model
parsing, independent-checker preparation, representation setup, switches, solves,
durable response writes, EOF and destruction in the primary session endpoint.
Prepared solve times and GPU events are secondary; short prefixes are descriptive.
Retain small/irregular cases as correctness controls without claiming small-case
performance. No historical observations enter the new statistical sample.

Freeze native window 32 / FP4 x2 window 16 and fixed maximum-200 audits, subject
to admission. Both controls receive identical cache and placement improvements.
No timing-selected dispatch. Benchmark all planned cells, including refusals and
failures. A failed scientific cell is never retried or replaced. An incomplete
cohort stays incomplete; untouched cells may proceed if safe under the same freeze.

Plan 32 fresh randomized paired blocks, exactly 16/16 lane-order balance per
family/tier. Eight primary comparisons use exact median order-statistic intervals
with Bonferroni coverage across eight ratios and eight absolute savings. The
independent sampling unit is the paired session block, not its 32 requests.
Before freeze, record rank bounds and detectable sign consistency: the purpose
is to resolve a practically relevant session gain, not prove a fixed 1.10x target.
Declare a useful scoped result only with complete coverage, all original-model
certificates, a simultaneous speedup lower bound above parity, and an absolute
session-savings lower bound above 10 ms (0.3125 ms/request). Report 1.10x separately
as a provisional value comparison, not automatic adoption. Report first-half,
pair-order and block variation without selective removal or adaptive stopping.
Shared-device independence, constructed workloads and bounded scenario reuse
limit generalization. Production readiness remains separately assessed.

## Admission, resources and preservation

CPU/native acceptance precedes device execution. Compare new single-model
execution with the retained executable, all scenario switches with fresh sessions,
and final/audit receipts with the independent original serial checker. Exercise
alternating models, cancellation, recovery and invalid requests. Four scoped
sanitizer suites admit the new host with the unchanged image. Diagnose all-process
instrumentation separately; a zero-hazard log alone does not certify process health.
Freeze source/binary/image/models and successful resource/admission receipts.
The added scenario sanitizer suite performs bounded switch/reset/step/restore
comparisons against fresh engines at dimensions 33 and 2048, including native,
x2 and x4. Full converged scenario comparisons and serial certificates remain
separate admission. Preserve the earlier full-trajectory scenario racecheck attempt,
which hit its 88-second work deadline; it is not a completed sanitizer admission.
The original 97-case arithmetic/lifecycle sanitizer suite remains required in full.

New independent ceiling: 80000 CPU / 8400 GPU seconds, four CPU slots, 16 GiB
sampled aggregate RSS, at most 12 GiB owned device buffers, one pinned shared GPU
lease. CPU phases: implementation 12000 (512 preparation), diagnosis 4000,
native 16000, acceptance 12000, confirmation 27200, reporting 6800, cleanup 2000
(128 closing). GPU: diagnosis 200, acceptance 1600, confirmation 6600. Reserve
each block separately, at most 200 GPU / 800 CPU seconds. Receipts and immutable
development sources: `artifacts/gpup-mixed2-reuse-v1`. Charge failed reservations
in full. Never transfer historical funding or relax the supervisor implicitly.

Prospective CPU phase amendment before native-v2: move 4000 implementation and
4000 diagnosis seconds to native acceptance, keeping the independent total 80000
unchanged. Native-v1 restricted the full repository gate to three worker CPUs;
the supervisor's own tests require four CPUs and refuse that environment. Preserve
its full reservation and results. Run the full repository gate with four CPUs;
three-worker/pinned-control placement remains the scientific execution layout.

Prospective confirmation amendment after the 154.9-second full-size resource
pilot: reserve 200 seconds per block for operational margin. Move 3200 reporting
CPU seconds to confirmation; move 400 diagnostic and 200 acceptance GPU seconds
to confirmation. Total ceilings stay 80000 CPU / 8400 GPU seconds. All 32 maximum
block reservations fit the revised confirmation phase. Historical charges stay
exact. Capture coarse device conditions outside session endpoints, without
timing-selected exclusion or causal attribution from those snapshots.

Deliver durable positive, negative and inconclusive diagnosis, complete cost and
missing-cell accounting, portable evidence/replay, full repository CPU/native
acceptance, historical preservation and local commit. No push, public preset,
GPUP-8 completion, TENSOR2 pass or GPUP-9 release follows.
