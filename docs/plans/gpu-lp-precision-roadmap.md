# GPU LP Performance Research and Implementation Roadmap

Status: DELIVERY3 next under revised prospective delivery protocol; DELIVERY2 complete with dense cold gains but failed broad retention; FP4-CHECKER complete, exact dense checker gains without cold retention; FP4-ACCEL complete, dense gains without broad latency retention; FP4-GPU-PILOT complete; FP4-FAST optimization complete; FP4 recovery/integration complete; integrated FP4 latency retention fails; 1e-7/1e-9 final-quality tiers planned; old FP4-PROTO incomplete; GPUP-8 science closed; GPUP-9 gated
Owner: numerical backend and experiment tooling
Introduced: GPU LP precision research track (GPUP)
Last reviewed commit: d453675
Implementation: [backlog](../../state/backlog.yaml), [active task](../../state/active-task.md)
Decision: [ADR-0047](../decisions/ADR-0047-certified-performance-roadmap.md), [cost gates](../decisions/ADR-0054-resident2-cost-priorities.md), [FP4 GPU exploration and quality tiers](../decisions/ADR-0058-fp4-gpu-exploration-quality-tiers.md)
Evidence: [RESIDENT2 result](../benchmarks/lp-resident2-gpup-resident2.md), [system diagnosis](../benchmarks/lp-system-diagnosis-2026-11-10.md), [latest GPUP-8 result](../benchmarks/lp-tensor-expanded-recovery-gpup8.md)

## Next: isolate delivery mechanisms and confirm scoped gains (2026-11-12)

The user permits revising the protocol. [ADR-0066](../decisions/ADR-0066-delivery-retention-scope.md)
and [GPUP-DELIVERY3](lp-delivery3.md) make the next task explicit: independently
switch checker batching and startup overlap, diagnose prepared total regressions,
then confirm a frozen candidate using fresh cold processes and prepared sessions.
Dense128/256/512 are the declared target class; retain a 1.10x benefit target
there and guard every certified family against material regression with
simultaneous uncertainty bounds. The engineering allowance is the larger of 2%
or 0.10 ms, with supported, unfavorable and inconclusive outcomes. Exact original-
model checking and coverage remain hard requirements. Cold and prepared routes
qualify separately. The plan specifies a new 32-block confirmation design;
implementation must first supply its complete independent resource package.

DELIVERY2's historical gate and failed broad decision remain exact. Its timing
results guide this hypothesis, not a retrospective pass. No new numerical/device
execution or TENSOR2/GPUP-9 release follows from this documentation revision.
MIXED2 remains independently ready as the simpler numerical alternative.

## DELIVERY2 complete (2026-11-12)

[GPUP-DELIVERY2](../benchmarks/lp-delivery2.md) implements batched independent-
checker transport and overlapping original-model checker/device setup under
[SPEC-0033](../specifications/SPEC-0033-delivery2.md) /
[ADR-0065](../decisions/ADR-0065-delivery2.md). All 960 cells complete with exact
retained numerical evidence: 880 certificates and 80 intentional refusals.
Strict dense512 cold delivery improves about 1.40x in both native and FP4 lanes.
Broad strict cold ratios 1.0584/1.0665x fail 1.10x/no-regression retention, and
prepared dense512 medians regress despite faster checker transport. Keep the
supported native solver and public defaults unchanged. The separate allocation
is closed; historical budgets remain closed and GPUP-9 remains gated.

## Exact checker acceleration (2026-11-12)

[GPUP-FP4-CHECKER is complete](../benchmarks/lp-fp4-checker.md) under
[SPEC-0032](../specifications/SPEC-0032-exact-checker-acceleration.md) /
[ADR-0064](../decisions/ADR-0064-exact-checker-acceleration.md). Cached feasibility
indices, independent row scheduling and exact product/reduction optimizations
preserve every certificate bit and refusal. All 960 new comparison cells complete
with identical original numerical evidence; eleven bounded families certify at
both tiers. Dense512 CPU assessment improves 2.54x; strict FP4 prepared total
improves 19.203 to 15.924 ms. New native is 16.527 ms; FP4's observed 3.8% lead
has an interval including parity. Broad cold ratios 0.9994/0.9934x still fail
retention, dominated by startup/preparation and unfavorable small tensor work.
Keep defaults unchanged. Further work should measure exact dual/transport and
cold setup/teardown costs; historical experiments and allocations stay closed.

## Corrected FP4 acceleration (2026-11-11)

[GPUP-FP4-ACCEL is complete](../benchmarks/lp-fp4-accel.md) under
[SPEC-0031](../specifications/SPEC-0031-fp4-corrected-acceleration.md) /
[ADR-0063](../decisions/ADR-0063-fp4-corrected-acceleration.md). Cached preparation,
correction state, original-A window references, scaling, parallel tiles and exact
parallel checking resolve the bounded-family refusals. All 1800 cells complete;
eleven bounded families certify at both tiers, and all safety/serial replay gates
pass. Strict dense512 FP4 improves 6.19x in GPU and 2.27x in total prepared time
against fused FP4. Against improved parallel native, GPU improves 1.20x but strict
total time regresses 1.5%. EOF cold geometric means 0.9850/0.9863x fail retention.
Keep native supported and select no public preset. Exact checking and complete
delivery remain the main next costs; larger/batched dense work needs a new
protocol. Historical sources/results/budgets remain closed, TENSOR2 conditional,
and GPUP-9 gated.

## FP4 integration disposition (2026-11-11)

[GPUP-FP4-INTEGRATE](../benchmarks/lp-fp4-integrate.md) is complete under
SPEC-0030 / ADR-0062. Its actual FP4 work certifies coupled endpoints at both final
tiers, and its safety/rollback/checker gates pass. Complete latency fails retention:
cold native/candidate ratios are 0.959–0.986x and prepared ratios 0.623–0.770x.
The eight-model bounded domain is not a large sparse production solver. Keep the
native control and require a new viable complete-cost case before TENSOR2.
MIXED2 remains an independent CPU-only contract/cost preparation alternative;
no follow-on execution or historical retry is released.

## Current plan (2026-11-10)

The objective is a faster independently certified answer using modern GPU
low-precision computation where it reduces total cost. The comparable cuOpt/COPT
baseline is now complete under an explicit native-return policy. The user now
prioritizes approximate persistent multi-FP4 state and fused iterations, with
original-model FP64 checks and explicit 1e-7 and strict 1e-9 final-quality tiers.
GPUP-FP4-SPEC is complete under
[SPEC-0025](../specifications/SPEC-0025-persistent-fp4-contract.md)
and [ADR-0056](../decisions/ADR-0056-fp4-executable-contract.md). FP4-PROTO's
[bounded CPU attempt](../benchmarks/lp-fp4-proto-gpup-fp4-proto.md) qualifies no
lane; that v1 attempt remains closed under ADR-0057. The separately scoped
**FP4-GPU-PILOT** is complete as a negative performance result under ADR-0058.
**FP4-FAST** is now [complete](../benchmarks/lp-fp4-fast.md): 288 matched cells
show 4.16–7.81x FP4 kernel gains with unchanged endpoint hashes. Its independent
optimization contract is in
[ADR-0060](../decisions/ADR-0060-fp4-fast.md) and
[SPEC-0028](../specifications/SPEC-0028-fp4-fast.md), to fix measured encoding,
component-product, preparation and utilization costs. It does not reopen the
failed 600-update trajectory gate or change final certificate authority. **FP4-RECOVERY-SPEC** is now [complete](../benchmarks/lp-fp4-recovery-spec.md) under
[SPEC-0029](../specifications/SPEC-0029-fp4-recovery-policy.md): explicit operational
residual guards, compatible local errors and bounded precision/native recovery,
without a global enclosure claim. **FP4-INTEGRATE is complete** under
[SPEC-0030](../specifications/SPEC-0030-fp4-integration.md), joining that policy
with the device path and completing the bounded same-tier comparison. Its latency
retention gate fails, so broader TENSOR2 execution remains conditional.
Simpler mixed precision and delivery-cost optimization remain alternatives.
Lean resident execution is
implemented; its bounded study does not pass the latency retention gate, so the
tuned native control remains authoritative for comparisons. Primitive/device
safety gates precede exploratory GPU measurements; solver qualification and
complete-cost admission precede the larger Tensor comparison.
This priority supersedes the dated planning order below;
historical evidence and accepted numerical contracts remain unchanged.

GPUP-8's corrected proof, CPU/native/model gates and six device jobs passed.
Six small profiles completed; the first large BF16 profile timed out. Nine profiles
and sixty timings remain unexecuted. GPUP-8 has neither a complete gain forecast
nor a certified latency win. Its stages remain closed, and GPUP-9 remains gated.
The [final accounting](../benchmarks/data/tensor-expanded/recovery-final-accounting-v1.json)
is authoritative; unused allocations are not new spending authority.

The user authorized the diagnosis, roadmap, cuOpt installation, baseline contract
and then GPUP-BASELINE implementation with 3600 additional GPU seconds.
GPUP-BASELINE-SPEC is delivered as
[SPEC-0022](../specifications/SPEC-0022-external-lp-baseline.md), with
[CPU contracts and a two-phase resource proposal](../benchmarks/lp-external-baseline-v1.md).
The [completed baseline](../benchmarks/lp-external-baseline-native-return.md)
accounts for all 240 planned attempts: 198 comparison passes and 135
strict certificates. The user selected cuOpt error-free native returns as a
separate pass tier; 90/96 pass natively and 24/96 certify strictly. Limits,
native errors, delivery failures and original-model differences remain explicit.
Total baseline GPU charge is 3091.995889713 / 3600 seconds. Gurobi remains
unavailable. This is not a quality-matched commercial-solver ranking or a
supported low-precision preset. New scientific tasks still need their own
concrete protocol/allocation; GPUP-8 stays closed and incomplete, GPUP-9 gated.

The user requested GPUP-RESIDENT2 implementation on 2026-11-11 and permitted
additional time. [SPEC-0024](../specifications/SPEC-0024-native-resident-execution.md)
and [ADR-0053](../decisions/ADR-0053-native-resident-execution.md) define the new
research-only lifecycle, transactional window and separate bounded allocation.
The baseline PR is merged; historical scientific stages and ledgers stay closed.

The [completed RESIDENT2 report](../benchmarks/lp-resident2-gpup-resident2.md)
retains all 64 cells and 96 endpoints. Both modes certify 42/48, with identical
certified candidate bytes and work. All twelve mixed-model limit endpoints export
successfully but retain the infinite-bound refusal. The cold model-median geometric
mean is 1.027370x and four certified medians regress, so the latency retention gate
fails. Keep the native control; prepared throughput is a separate endpoint.
The FP4 planning priority below supersedes the MIXED2-first handoff; no new
numerical execution is released by this review.

### Persistent multi-FP4 direction (2026-11-11)

The user requests several FP4 components per higher-precision value,
reconstruction-free iterations and fused kernels, and explicitly permits
approximate inner arithmetic. The initial strict 1e-9 final target is retained;
the new user-authorized 1e-7 final tier is defined below.
The [design assessment](lp-fp4-persistent-state.md) finds this worth a bounded
feasibility effort: it directly targets the retained reconstruction/update cost.
It does not establish an FP64-equivalent representation or a solver speedup.

The proposed fast path preserves component state across updates and accepted
audit windows, with no routine full-vector FP64 reconstruction/re-encoding.
FP32 accumulation, local component combination, normalization and projection
decisions remain charged work. Original-model FP64 snapshots at 200-update
controller boundaries serve observation and certification, with explicit
correction/escalation. The prototype must establish cross-window error and
whole-checkpoint recovery under SPEC-0025; historical reference adoption is unchanged.

Fuse each product with its legal update/projection/encoding epilogue. Preserve
the dependency between primal and dual phases and all necessary global
reductions. A single persistent kernel is not assumed. Account for component
cross-products, block scales, sparse tails, packing, register pressure and
fallback; a small low-precision GEMM alone cannot admit this solver.

The [completed CPU contract](../benchmarks/lp-fp4-spec-gpup-fp4-spec.md) provides
bounded 2/4/8-plane E2M1 oracles, one approximate operator for both orientations,
original-unit error/projection guards and complete observation/rollback state.
Its source-bound review of 24 retained cold control trials rejects six even at
the ideal per-row 10% gain bound, leaves fifteen needing profiles and preserves
three uncertified endpoints. No forecast or device arithmetic is admitted.
The frozen prospective comparison has 192 cells / 288 endpoints; its resource
amounts are proposals only. The CPU implementation used a separate allocation
and zero GPU time.

The [FP4-PROTO CPU attempt](../benchmarks/lp-fp4-proto-gpup-fp4-proto.md) now
delivers independent rational/component recurrences, full checkpoint rollback and
one frozen twelve-cell admission under SPEC-0026 / ADR-0057. Nine cells exceed the
inner error guard and three refuse incompatible metadata; none reaches the first
200-update observation. Short expansions exhibit actual error above the guard,
while eight-component cases also expose substantial enclosure overestimation.
A separate local rounding/encoding correction passes primitive tests but has no
scientific qualification. Device implementation, actual MMA, sanitizers and all
36 pilot/diagnostic cells remain unexecuted; prototype acceptance is incomplete.

The [GPUP-FP4-GPU-PILOT delivery](../benchmarks/lp-fp4-gpu-pilot.md) completes
216 empirical profile cells after corrected instruction/device and four-sanitizer
admission. The [FP4 integration](../benchmarks/lp-fp4-integrate.md) now completes
96 coupled trajectory cells and 576 cold/prepared solve cells with independent
certificates and explicit recovery. Its FP4 cold geometric means of 0.959–0.986x
fail retention. Keep native; a viable new complete-cost case still precedes
**GPUP-TENSOR2**. The pilot/integration does not establish a global trajectory enclosure. No failed v1 cell is retried by this handoff.
MIXED2 remains a simpler alternative, not a prerequisite to this FP4 contract.
The [ADR-0055 decision](../decisions/ADR-0055-persistent-fp4-direction.md) records
the planning priority; ADR-0056 implements its CPU specification. ADR-0057's
independent 32000 CPU / conditional 1560 GPU allocation covers the bounded
prototype attempt; GPU charge is zero and its later stages are closed. Future
pilot/recovery/study resources need new concrete packages; no automatic spending
or GPUP-9 release follows.

### FP4 GPU exploration and quality tiers (2026-11-11)

The user accepts a separate GPU experiment and says a **1e-7 final certificate is
encouraging when FP4 is sufficiently faster**. [ADR-0058](../decisions/ADR-0058-fp4-gpu-exploration-quality-tiers.md)
separates hardware exploration, numerical recovery and certified comparison.
The old monotone 1e-7 iterate-error envelope and a new 1e-7 final LP certificate
are different criteria. Neither a small iterate difference nor a native success
status supplies the final certificate.

| Path | What is planned | Required admission |
| --- | --- | --- |
| **GPUP-FP4-GPU-PILOT**, complete empirical negative result | [SPEC-0027 delivery](../benchmarks/lp-fp4-gpu-pilot.md): actual FP4, native FP64 and FP8/FP16; split/fused/persistent/roundtrip; 216/216 cells | Corrected packing and synchronization, 60 primitives, 90 transaction cases and four sanitizers pass; retained failed attempts and charges. All matched FP4 iteration/cold medians are slower in this bounded grid. No certified solver or preset |
| **GPUP-FP4-FAST**, complete | [SPEC-0028 delivery](../benchmarks/lp-fp4-fast.md): hardware encoding, component columns, zero-plane pruning, exact host preparation and prepared lifecycle | 288/288 cells and 2016 fresh windows; same-lane endpoint hashes match; 4.16–7.81x kernel gains and four sanitizer passes. Rich FP4 x8 still loses to native; no certificate or preset |
| **GPUP-FP4-RECOVERY-SPEC**, complete | [SPEC-0029](../specifications/SPEC-0029-fp4-recovery-policy.md): compatible local errors and explicit operational residual recovery | Distinguish proved bounds from empirical progress/error observations; version the changed policy, retain original-A FP64 audits, complete checkpoints and explicit recovery. No GPU-pilot prerequisite |
| **GPUP-FP4-INTEGRATE**, complete; retention fails | [SPEC-0030 delivery](../benchmarks/lp-fp4-integrate.md): 96 coupled diagnostics and 576 same-tier cold/prepared solves, complete rollback and original-model certificates | Final native/device/four-sanitizer gates and 176 unique endpoint replays pass; matched six-of-eight-family coverage at both tiers. Cold FP4 geometric means 0.959–0.986x fail retention. Native retained; old prototype stays incomplete |
| **GPUP-TENSOR2**, conditional solver study | Complete cold/prepared comparison with separately labeled 1e-7 and 1e-9 cohorts | New frozen quality/grid/resource protocol, integration admission and conservative complete-cost screen informed by the pilot; original-model independent certification and matched controls |

The pilot measures actual arithmetic error, component pairs and padded MMA work,
scales/packing/normalization, sparse tails and single-RHS utilization, register
pressure/spills, launches, copies and audit costs. Ordinary updates retain packed
component state without full-vector FP64 reconstruction; local combination and
normalization remain measured work. Short trajectories may be empirical and
uncertified. Their profiles answer hardware/cost questions and cannot establish
a certified-solver speedup. A missing full error proof does not prohibit this
bounded exploration; primitive correctness and device safety still apply.

Final results use explicit `certified-1e-7` and `certified-1e-9` labels, with both
absolute and relative target tolerances set to the named value. The future
versioned checker retains original coefficients, feasibility/dual-bound authority,
objective offsets, normalization and conservative gap/refusal rules. Existing
defaults remain 1e-9. Assess both tiers where endpoint evidence permits; a 1e-7
pass is never relabeled as strict and need not also pass 1e-9 to be useful.

The initial "sufficiently faster" criterion is **at least 1.10x cold model-median
geometric-mean speedup**, no certified model-median regression and no loss of
certified coverage against a native control **targeting the same tolerance**.
Keep failures/limits in the coverage accounting and report repetition ranges and
uncertainty; gains indistinguishable from variability remain inconclusive. Time
includes setup, extra iterations, audits, correction/fallback, export and checking.
FP4 at 1e-7 versus FP64 at 1e-9 is a labeled quality/time tradeoff, not attribution
of the gain to FP4. Matched FP8/FP16 and fusion/persistence comparisons test that
attribution. Prepared throughput remains separate from cold single-solve latency.

The old 192-cell/288-endpoint strict proposal remains immutable. Enumerate new
dual-tier cells, stop rules, measured time-to-certificate events, controls and
full reservations before execution; do not infer a new grid or earlier completion
time from old endpoints. The GPU pilot is now complete under its independent
task allocation; recovery and bounded integration are now complete under their
own allocations. A broader TENSOR2 solver study remains prospective. No old
unused GPU allowance funded the pilot or authorizes a later task.

### RESIDENT2 lessons and planning changes (2026-11-11)

The result changes admission and optimization priorities, not the accuracy
objective. The existing control already retains device state and batches 64
updates. The resident admission trace removes 14 of 58 synchronizations but
keeps all 2800 launches, nearly doubles uploads and more than doubles readback.
Safety flags, coefficient transport and transactional adoption are real costs;
their separate latency contributions have not been isolated. All 42 certified
pairs have identical bytes and iteration counts, so extra iterations do not
explain those pairs' timings. This is evidence against selecting this executor,
not against every resident design or mixed precision.

1. **Require a complete-delivery cost case before a certified solver campaign.** Use
   retained per-trial phase partitions under the same lifecycle and transport.
   Identify the portion actually accelerated, expected iteration changes and
   added conversion, guard, correction, fallback and evidence costs. Predeclare
   the total-latency target and regression/coverage rule before a new cohort.
   Do not sum marginal phase medians or treat all native time as kernel time.
   If the attainable saving cannot meet the target, defer the candidate before
   a full device study. Unknown costs require explicit ranges or a separately
   bounded measurement pilot, not assumed zero overhead. ADR-0058 explicitly
   permits the FP4 GPU pilot to collect these missing measurements before the
   complete-solve cost gate; MIXED2 retains its separate contract.
2. **Make delivery cost an actionable alternative: GPUP-DELIVERY2.** On
   dense-65536, control native time is about 2.40 s versus 9.78 s total; checking
   takes 3.16 s and conversion/preparation about 2.33 s (separate medians).
   Inspect parsing, immutable preparation, checker input preparation, provenance
   and process/transport overhead. Remove demonstrated duplicate work while
   retaining exact original inputs, fresh independent certificates and durable
   evidence. Select a bounded delivery slice ahead of precision device work
   when its cost case is stronger; this is not an automatic dependency or a
   claim that the recorded unattributed residual is removable.
3. **Keep prepared throughput explicit.** Reuse immutable models and residency
   across fresh solves, and charge setup in the cold endpoint. The observed
   control cold/prepared ratios are 1.24–2.98 on certified models; each prepared
   configuration has only one batch. They motivate lifecycle reuse, not a
   supported throughput preset or a resident-candidate win.
4. **Reopen resident optimization only for a new cost mechanism.** A future
   proposal must quantify changes in launches, copies, bytes, allocations,
   guards and observation cost. Compact flag transport or graph submission are
   hypotheses requiring their own admission; fewer waits alone is insufficient.
   Preserve the 200-update controller boundary, bounded cancellation and whole
   checkpoint rollback unless a separate numerical contract changes them.
5. **Separate mathematical coverage from transport and performance.** Normal-limit
   export is fixed. The mixed-model finite-dual-bound refusal remains a distinct
   bound-authority problem; diagnose it from retained candidates before proposing
   any new numerical work. Keep these endpoints in the coverage denominator and
   out of certified speedup claims. Do not clip infinite bounds or relabel old
   1e-9 failures. The future FP4 1e-7 tier has separate authority under ADR-0058;
   it does not resolve missing finite-bound authority by changing tolerance.
6. **Match the strength of the claim to the experiment.** Three cold repetitions
   and one prepared batch do not establish a general ranking. Future protocols
   must predeclare repetitions, paired order, uncertainty reporting and stop
   rules. Freeze actual executable hashes and validate produced counter/export
   schemas before device admission; retain every failed attempt and its charge.

These are prospective gates under [ADR-0054](../decisions/ADR-0054-resident2-cost-priorities.md).
The RESIDENT2 retention decision and all prior scientific criteria stay fixed.
ADR-0058 refines their ordering for FP4 exploration and adds a separate future
quality tier; no new experiment, budget transfer, RESIDENT2 retry or GPUP-9
execution follows this documentation update.

### Ordered deliverables and decision gates

| Task / priority | Deliverable and prerequisite | Acceptance / go-no-go decision |
| --- | --- | --- |
| **GPUP-DIAG**, delivered | Saved source-bound diagnosis, ADR-0047, corrected status/backlog and isolated cuOpt setup record | Evidence and numerical sources preserved; documentation/dependency/package checks; no solver timing claim |
| **GPUP-BASELINE-SPEC**, delivered, CPU-only | SPEC-0022, three schemas, canonical conversion/endpoint/proposal validation, fixtures and resource arithmetic | Twenty focused tests pass; ten lanes and eight source-bound development models; proposal remains non-executable |
| **GPUP-BASELINE**, complete under the user amendment | Separate adapters/checker, frozen 240-cell report; 123 results reused and 117 new attempts | 198 comparison passes, 135 strict certificates; cuOpt 90/96 native passes and 24/96 strict certificates. Separate native/quality/transport outcomes and retained failures; no equal-quality speedup claim |
| **GPUP-BASELINE-FOLLOWUP**, delivered | ADR-0052 / SPEC-0023, exact continuation roster, explicit native-return policy and resource allocation | Original certificate unchanged; native errors and normal limits distinguished; raw vectors and mapping uncertainty preserved; previous numerical trials not rerun |
| **GPUP-RESIDENT2**, complete as bounded negative result | SPEC-0024 / ADR-0053; cold/prepared phases, immutable preparation, coefficient/flag transport, transactional native windows and normal-limit export | 64 cells/96 endpoints; 42/48 strict certificates per mode and 42 bitwise pairs. Four sanitizers pass. Cold geomean 1.027370x and four regressions fail latency retention; keep the native control |
| **GPUP-FP4-SPEC**, complete, CPU-only | [SPEC-0025](../specifications/SPEC-0025-persistent-fp4-contract.md) / ADR-0056; E2M1/error/projection oracles, observation-only checkpoint contracts, three schemas and frozen resource/grid proposal | 32 focused CPU contracts and full native integration pass; source-bound cost review admits no forecast; strict 1e-9 final certificate unchanged; no GPU execution |
| **GPUP-FP4-PROTO**, incomplete; bounded CPU attempt closed | SPEC-0026 / ADR-0057 independent CPU reference, component trajectories, rollback and frozen twelve-cell admission; depends on GPUP-FP4-SPEC | Zero qualified lanes: nine guard and three metadata refusals, zero observations; separate local-budget correction has primitive tests only. Device/MMA/four-sanitizer/profile work unexecuted; no performance or certification claim |
| **GPUP-FP4-GPU-PILOT**, complete as bounded negative result | SPEC-0027 / ADR-0059; actual E2M1 MMA and persistent state, six lanes/four variants/three workloads; depends only on GPUP-FP4-SPEC | [216 cells complete](../benchmarks/lp-fp4-gpu-pilot.md), all four sanitizers pass after two explicitly released corrections. Dense-2048 persistent FP4 ×2/×4/×8 iteration ratios 0.349/0.178/0.079 versus native; observed errors are not certificates. Native retained; no preset |
| **GPUP-FP4-FAST**, complete | [SPEC-0028 delivery](../benchmarks/lp-fp4-fast.md): hardware encoding, component columns, zero-plane pruning, exact host preparation and prepared lifecycle | 288/288 cells and 2016 fresh windows; same-lane endpoint hashes match; 4.16–7.81x kernel gains and four sanitizer passes. Rich FP4 x8 still loses to native; no certificate or preset |
| **GPUP-FP4-RECOVERY-SPEC**, complete, CPU-only | [SPEC-0029](../specifications/SPEC-0029-fp4-recovery-policy.md) delivers local accounting, operational guards, complete checkpoints, dual-tier receipt validation and a non-executable integration proposal | New versioned contract; empirical inner error never masquerades as a proof; original-model FP64 audits and independent final certification at the declared 1e-7/1e-9 tier; no automatic old scientific retry |
| **GPUP-FP4-INTEGRATE**, complete; retention fails | [SPEC-0030](../specifications/SPEC-0030-fp4-integration.md): coupled recovery and certificates admitted; 672 cells complete, same coverage, no retained speedup | Nontrivial trajectory, full checkpoint/cancellation/recovery and original-model endpoint admission; a useful certified-1e-7 lane may proceed without a strict pass; retain all costs and failures |
| **GPUP-MIXED2**, simpler alternative, dependency-ready | CPU-only complete-delivery cost admission against the native control, then separately admitted FP32 matrix / FP64 state-and-compute; lower-precision state is a later candidate; depends on GPUP-BASELINE and GPUP-RESIDENT2 | Predeclared latency/coverage rule and accelerated cost fraction, iteration/guard/transfer/fallback costs; defer device study if the cost case fails. Explicit matrix-error/residual contract, useful nonzero work and original 1e-9 certificate |
| **GPUP-DELIVERY2**, complete; broad retention fails | [SPEC-0033 delivery](../benchmarks/lp-delivery2.md): batched checker IPC and overlapping independent checker/device setup; depends on GPUP-RESIDENT2 | 960 cells / 880 certificates / 80 intentional refusals; exact numerical evidence. Strict dense512 cold improves about 1.40x for native and FP4; broad 1.0584/1.0665x fails retention. Prepared dense512 regresses; no preset or GPUP-9 release |
| **GPUP-DELIVERY3**, next ready | [ADR-0066 / execution plan](lp-delivery3.md): independent batching/overlap controls, prepared-regression diagnosis and fresh confirmation; depends on GPUP-DELIVERY2 | Freeze candidate per lifecycle, complete resource package and 32 independent blocks; dense target benefit >=1.10x with simultaneous intervals, material-regression guards and exact coverage. Cold/prepared qualify separately; no historical regrading or public preset |
| **GPUP-TENSOR2**, conditional FP4 study | New versioned native FP64, FP8/FP16 and FP4 cohorts at explicit 1e-7/1e-9 final tiers; depends on GPUP-FP4-INTEGRATE | Integration and complete-cost admission before campaign; at least 1.10x cold model-median geometric mean, no certified model-median regression or coverage loss against same-tolerance control; uncertainty and complete cold/prepared costs; old proposal/GPUP-8 criteria unchanged |
| **GPUP-PRESOLVE**, planned | Minimal reversible fixed-variable, singleton and bound-tightening transformations plus postsolve maps; depends on GPUP-BASELINE evidence | Independent original-model validation of postsolved primal/dual information and statuses; benchmark saved total work; reject transformations that cannot preserve required proof information |
| **GPUP-8-DISPOSITION**, planned review | Review new engineering evidence and the retained incomplete GPUP-8 record; depends on GPUP-BASELINE and GPUP-MIXED2 | Either propose a separately funded bounded recovery with unchanged GPUP-8 criteria, or seek an explicit negative-result closure and superseding progression decision; neither marks GPUP-8 passed by default |
| **GPUP-9 / GPUP-10**, gated | Controlled held-out ablations, then evidence-supported dispatcher/recipes | GPUP-8 completion or a separately accepted replacement gate is required; retain coverage, uncertainty, total costs and native fallback; no preset from partial profiles |
| **GPUP-MILP**, deferred | Relaxation adapter, bound authority, warm starts and full search study after supported LP recipes | Correct pruning/bounds, cancellation and reproducibility, followed by full MILP time/node/coverage comparisons |

One task owner handles each accepted slice. Expected ownership is experiment
tooling for BASELINE-SPEC/BASELINE/DELIVERY2, CUDA runtime for RESIDENT2,
numerical backend/CUDA runtime for the FP4 pilot/recovery/integration path, numerical backend for
MIXED2/TENSOR2/PRESOLVE, and solver executive for MILP. Tasks are sequential
unless their accepted resource plans explicitly permit independent work.

### External comparison contract

SPEC-0022 supplies the strict mathematical contract; the accepted
[SPEC-0023 amendment](../specifications/SPEC-0023-baseline-native-return.md) adds
cuOpt native-return acceptance separately. The completed run binds executable,
source, device and resource identities before release. The current comparison
policy is explicit below:

| Dimension | Selected design |
| --- | --- |
| Required solvers | Current tuned project FP64, explicit project FP32/mixed candidates when admitted, cuOpt 26.10.0, local COPT 8.0.6; Gurobi excluded until available |
| Algorithm cohorts | Forced PDLP/PDHG where supported, forced native FP64 control, and vendor portfolio/default mode as separate rows; no attribution of a concurrent winner to PDLP without evidence |
| Precision | Explicit cuOpt single/double/mixed settings; record actual supported mode and arithmetic/storage distinction; do not label all GPU execution as Tensor or low precision |
| Primary endpoint | Complete cold worker delivery, including setup, conversion, solve, export and independent checking; strict certificate required for project/HiGHS/COPT, explicit error-free native-return policy for cuOpt. Publish the two acceptance bases separately |
| Secondary endpoints | Warm in-process solve and native solve time with exact boundaries; repeated RHS/batches reported as throughput; none substitutes for cold latency |
| Quality | Original 1e-9 certificate is unchanged. CuOpt native-return passes can fail it; log exact termination, raw vectors and original-model discrepancies. Native-return comparisons are not quality-matched speedups. Any future relaxed tolerance tier needs its own identity |
| Resources | Pin one GPU/driver and explicit CPU affinity/thread limits per matched cohort; separate any vendor-recommended parallel cohort; disclose memory, presolve, scaling, crossover and seed/settings |
| Models | Retain development families and add real sparse, dense-block, ill-scaled, degenerate and trivial controls; freeze exact IDs, hashes and grouped holdout before tuning; do not inspect holdout for selection |
| Endpoints | Export actual primal/dual/reduced-cost information, objective offset, row/column mapping and bounds needed by the common checker; unsupported exports cannot count as certified |
| Statistics | Predeclare repetitions and paired order, include all timeout/refusal/error rows, uncertainty and coverage; compare only like endpoints and disclose excluded/missing pairs |
| Admission and budget | CPU fixtures first; a separately reserved small solver smoke before a timed cohort; predeclare total/phase/job CPU, GPU, memory and deadline limits plus stop policy; no implicit historical transfer |

The initial adapter should consume canonical arrays and export the solver's actual
endpoint without invoking another optimizer to repair it silently. Test objective
sense/offsets, free variables, ranged rows, fixed variables, infinities, duplicate
entries, missing duals, limits and infeasible/unbounded statuses. Postsolve and any
explicit repair must be visible and charged. Compare native sparse-array import
with existing row-by-row construction before attributing adapter time to a solver.

### Baseline follow-up decisions

The user's native-return amendment resolves baseline comparison eligibility; it
preserves strict certification as a separate quality result. All 240 attempts
are now accounted for. Native success is not evidence that an uncertified answer
meets the project's tolerance, and native limits are not optimality claims. The
postsolve mapping uncertainty remains an optional adapter follow-up rather than
an implicit prerequisite or an attributed vendor defect.

The large mixed model has no strict certificate from any configuration. The
baseline adapter's normal-limit export failure is historical: RESIDENT2 now
exports complete primal/dual vectors from all twelve mixed-model limit endpoints.
The strict checker still lacks finite bound authority for variable 3's
reduced-cost enclosure. Diagnose sound bound construction from retained evidence
without inventing finite bounds or relaxing the certificate. Use certifying
models for matched latency claims, keep mixed-model failures in the coverage denominator,
and require an explicit bound-authority contract before claiming a certified win
there. The [completed report](../benchmarks/lp-external-baseline-native-return.md#what-the-completed-comparison-changes)
binds those observations.

The completed RESIDENT2 result is linked above. Its first required deliverable was
phase attribution for conversion, import/readback, native solve, export, checking
and durable output without additional device synchronizations. COPT's first
retained dense-65536 GPU PDLP solve took 0.574 native seconds but 25.574 complete
seconds, including 4.326 seconds in independent checking. Faster arithmetic can
only improve the portion it actually accelerates; preparation/evidence costs
must remain visible.

RESIDENT2 defines cold and prepared-model lifecycles and immutable preparation.
Further binary/buffered transport or compact evidence must use those explicit
boundaries. Cold time must still charge preparation; amortized prepared
throughput is a separate endpoint. Preserve
exact original coefficients, independent assessment, source bindings and bounded
cancellation/cleanup. Compare native controls under the same transport before
claiming an algorithmic improvement. The old v2/new v5 small-model transport
mismatch is explicitly excluded from paired speedup claims.

Keep the measured native control. FP4-SPEC is complete; the old FP4-PROTO CPU
attempt remains refused. FP4-GPU-PILOT and FP4-FAST are complete; CPU recovery is complete under SPEC-0029; FP4-INTEGRATE is complete under SPEC-0030 with failed latency retention;
MIXED2 is the simpler numerical alternative and DELIVERY2 targets host/evidence
savings when those offer the stronger cost case. An admitted MIXED2 prototype
uses FP32 matrix storage and FP64 state/arithmetic before a separately guarded
low-precision state. MIXED2 requires useful work, explicit error/progress guards,
charged correction/fallback and its existing 1e-9 certificate; the new FP4 tier
does not change that scope. The certified Tensor solver campaign requires a
complete-path cost case, while the exploratory GPU pilot follows its separate
gates above. No future experiment is funded or executed by this handoff, and
GPUP-8/GPUP-9 gates remain unchanged.

### Resident execution and precision choices

RESIDENT2 implemented bounded coefficient tables, sticky flags and transactional
observation under the existing 200-update controller boundaries. Its latency gate
failed, so it remains a research candidate and is not the base for FP4 or MIXED2.
A future resident proposal must identify a materially different cost mechanism
and include the full safety/transport cost before device admission. Predicated
execution must not publish invalid work; refusal must preserve the entire host
checkpoint and charge attempted work. Graph capture, compact flags or additional
fusion remain unmeasured proposals, with bounded cancellation required.

For MIXED2, begin with fewer representation changes than GPUP-8: original FP64
matrix for residual/check authority, FP32 stored matrix for an approximate inner
operator, and native FP64 state/arithmetic as the first comparison. Add FP32 state
only under a separately defined accumulated-error and progress policy. Escalate
when residual progress stalls or an error budget fails; preserve a native recovery
path. Scaling, primal/dual progress and final certification all remain explicit.
The prior refinement and resident-quantization failures are required design inputs,
so zero inner updates or zero useful low-precision windows cannot pass admission.

For TENSOR2, retain the bounded FP4-INTEGRATE safety/certificate evidence and
first establish a new complete-cost case at the declared 1e-7 or 1e-9 final tier.
Its present cold latency gate fails. Require a coupled workload that
amortizes packing, component products, normalization and correction. A dense tile
test alone is insufficient. Compare actual sparse tails and single-RHS utilization;
multiple right-hand sides require a separate throughput cohort and memory
accounting. Cross-window persistence is the proposed numerical change requiring
a new error/recovery contract, not an inherited GPUP-8 pass. Exact reconstruction
remains available for reference or exceptional paths, with its cost reported.

No supported dispatcher is chosen yet. Its eventual candidates are native CPU,
native GPU, admitted mixed precision and selective dense/batch Tensor execution,
chosen by dimensions, sparsity/block coverage, numerical range and required quality.
Selection thresholds must be fixed on development data and tested on held-out
groups; a runtime refusal falls back explicitly and charges the transition.

### Historical record below

The dated sections and slice descriptions below explain earlier decisions.
Statements such as “next”, “current handoff” and “proposed” in those sections are
historical to their dates. The current priority, status and authorization boundary
are the sections above and the structured backlog.

## Objective and working agreement

Historical GPUP-8 disposition (2026-10-23): the accepted in-container supervisor and
full pre-device native gate pass. The bounded cost continuation stops at its first
INT8 controller mismatch: device reference products sum serially, while the host
oracle uses warp32 order. All 66 ordinary tests and 280 product pairs pass; no
profile or primary timing runs. The [separate report](../benchmarks/lp-tensor-cost-device-gpup8.md)
retains both acceptance attempts, every CPU failure/charge and the 17366-event
ledger. Numerical/latency criteria stay unchanged; no retry, new cohort or GPUP-9
work is authorized by unused allowance. Earlier dated dispositions below remain
historical in their original context.

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

## GPUP-8 accepted in-container supervisor: bootstrap refusal (2026-10-23)

The user accepts revised ADR-0044 and the CPU allocation. The first supervisor
bootstrap stops before workload release because Python lacks os.pidfd_open.
The separate refusal retains the failed source and unsettled journal; no
numerical preparation or device reservation runs. A portable binding repair has
four mocked regressions, while real resource acceptance remains unrun. A corrected
bootstrap requires authorization under the accepted single-attempt rule. GPUP-8
remains incomplete; the numerical/latency gates and exact GPU ledger are preserved.

## GPUP-8 proposed in-container admission amendment (2026-10-23)

At the user's request, [ADR-0044](../decisions/ADR-0044-tensor-cost-continuation.md)
now proposes a cooperative in-container supervisor/guardian, serialized slots,
four-CPU affinity, sampled-memory admission and conservative four-times-wall CPU
charging. It explicitly cannot promise cgroup-equivalent memory/swap enforcement.
The 16000-second prospective CPU allocation requires 14300 additional CPU seconds,
transfer of the remaining 1700 and a cumulative CPU ceiling of 35900. Acceptance
of those changed resource terms is pending; implementation has not started.
All numerical, GPU study and latency completion sections remain byte-identical
to the archived accepted ADR. GPUP-8 remains incomplete and GPUP-9 stays gated.

## GPUP-8 Kubernetes constraint revision (2026-10-23)

The user confirms Kubernetes and prohibits escaping the container. The
[revised continuation plan](lp-tensor-kubernetes-constraint.md) withdraws host
provisioning, preserves ADR-0044's failed admission and records the exhausted CPU
admission/reporting stages. No equivalent permitted enclosure is demonstrated.
The additional 3600-GPU-second offer stays unreserved; the existing 1806-second
GPU package already fits its allowance. GPUP-8 remains incomplete, with no
preparation, device attempt, implicit CPU transfer or GPUP-9 progression.

## GPUP-8 approved cost continuation: CPU admission refusal (2026-10-23)

The user accepted [ADR-0044](../decisions/ADR-0044-tensor-cost-continuation.md).
The [resource-admission report](../benchmarks/lp-tensor-cost-gpup8.md) retains a
CPU refusal: the executor has no writable delegated task cgroup or reachable
host manager. The accepted decision stops before preparation/device reservations.
Seven bootstrap refusal tests pass; real containment/coordinator, native and
numerical/device gates remain unrun. Conservative CPU charge is 350 seconds;
GPU charge and all 17362 ledger events remain exact. GPUP-8 stays incomplete.
Further admission requires host-provided delegated containment, not renewed
approval of the already accepted ADR or a relaxation of the resource contract.

## GPUP-8 latency diagnosis and initial cost proposal (2026-10-23)

The [CPU-only diagnosis](../benchmarks/lp-tensor-latency-diagnosis.md) identifies
shared preparation, conservative norm restriction and host audits as the main
costs; the forced original-tuned profile is a research wrapper, distinct from
the unchanged timing control. [Proposed ADR-0044](../decisions/ADR-0044-tensor-cost-continuation.md)
requires repaired aggregate CPU admission, compact preparation, a proved tighter
norm and an equivalent device reference audit. It proposes at most 1806 GPU and
2050 CPU seconds within the remaining allocations after a 400-CPU-second diagnosis
charge, with CPU/cost refusal gates before timings. Current cgroup controls are
read-only; delegated task containment is a prerequisite. At diagnosis time this
proposal was unaccepted; the subsequent acceptance/refusal is recorded above.
No retries, resource increases or GPUP-9 work follow from this history.
The historical CPU overlap remains uncertified; new admission is prospective.

## GPUP-8 residual continuation: latency gain incomplete (2026-10-23)

Explicitly approved [ADR-0043](../decisions/ADR-0043-tensor-residual-continuation.md)
and its [separate report](../benchmarks/lp-tensor-residual-gpup8.md) preserve the
ADR-0042 result below. Explicit FP64 vector residuals recover useful integer and
floating Tensor solves: all 30 Tensor timings certify, with 66 useful windows
and no native promotion; total coverage is 60/60 timings. All twelve profiles
finish and 120 continuation LP records verify. All six adjusted latency-gain
comparisons fail. The initial CPU admission/build overlap also leaves aggregate
four-job resource acceptance uncertified. INT8 medians are 0.614776/10.390881 s versus tuned FP64
0.462114/6.331022 s. GPUP-8 remains incomplete on gain; GPUP-9 is not authorized.
Continuation charge is 588.257104641 GPU s, combined GPUP-8 825.114032275 / 3000;
cumulative 22184.699888064 s. All 17362 ledger events retain the exact
17200-event and 17132-event prefixes. No retries or later-task reservation follow.

## GPUP-8 bounded result: incomplete (2026-10-23)

The user explicitly accepts [ADR-0042](../decisions/ADR-0042-hybrid-tensor-components.md)
and allocates 3000 GPU seconds within unchanged ceilings for INT8 and FP16/BF16
component Tensor execution. Its [separate report](../benchmarks/lp-tensor-gpup8.md)
records 27 executed jobs, 48 CPU refusals, 20/60 certified timings and four complete
profiles. Correct integer/floating operators do not admit useful dense-model
solve windows; the working-family and certified latency-gain requirements remain
unmet. All 128 retained LP records independently verify. GPU charge is
236.856927634 s, cumulative 21596.442783423 s; 17200 ledger events preserve the
exact 17132-event prefix. GPUP-8 remains incomplete; GPUP-9 is not authorized.

## Current handoff: GPUP-7R complete (2026-10-23)

Accepted [ADR-0041](../decisions/ADR-0041-resident-matrix-quantization.md) and the
[resident plan](lp-quant-resident-follow-up.md) produce the
[GPUP-7R report](../benchmarks/lp-quant-resident-gpup7r.md). All 36 admitted
fresh timings certify, three FP64 profiles finish 2000 logical updates, and
21 operator endpoints verify. CPU useful-low admission refuses all quantized
model cells, retaining 78 dependent study cells without replacement. The planned
timing denominator remains 108. Resident matched FP64 recovers coverage but
unchanged tuned FP64 stays faster on nontrivial models; no preset follows.
Full native/device/replay/four sanitizer acceptance passes, and final CPU
verification accepts all 313 LP plus 21 operator endpoints. Preserve every
historical source/image/worker and both resident execution cohorts.
Task charge is 245.686586823 GPU s, cumulative 21359.585855789 / 25202.574545061;
17132 ledger events preserve the exact 17036-event prefix. No ceiling increases.
GPUP-8 is next for a conditional numerical/hardware/resource disposition before
behavior. No unused allowance is reserved for it.

## Completed GPUP-7 handoff (2026-10-22)

Accepted [ADR-0040](../decisions/ADR-0040-bounded-matrix-quantization.md) implements
matrix-only uniform/selective FP16/E4M3/E5M2 with canonical transpose tiles,
original-unit bounds, FP64 state and charged sticky recovery. The
[report](../benchmarks/lp-quantization-gpup7.md) retains all 104 attempts, verifies
34 study endpoints and certifies 33/96 timings. New paths only certify initial
host-only small-4; tuned FP64 certifies 12/12. Seventy timeouts and all eight
censored profile horizons remain; no useful low-product solve benefit or preset.
CPU admission, full native/device/replay/four sanitizer gates and fresh CPU
verification of all 182 retained endpoints pass. Both admission cohorts, reports,
source bridges, raw failures and the resource-sampling correction are retained.

Task charge is 1382.959456122 GPU seconds (1109.904216936 timing,
215.675211186 profiles, 57.380028000 acceptance), within 3600 and phase caps.
Current cumulative charge is **21113.899268966 / 25202.574545061 seconds**;
17036 events, SHA-256
861c90d8d82a20ff9655173742db37a5047d315e8cc4c983e0d6b2e6fa09bb97.
The exact 16816-event prefix dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c
and all earlier history remain. The independent 28800-second campaign ceiling
holds. GPUP-8 needs its conditional hardware/layout/error/cost and resource
contract before behavior; no Tensor Core implementation is mandatory. Unused
headroom reserves nothing. Vector quantization, stochastic rounding, combined
refinement/assessment policies, sessions and supported presets remain gated.

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
| 6 — GPUP-7 (complete bounded subset) | ADR-0040 matrix-only uniform/selective FP16/E4M3/E5M2. | 56 CPU cases, 104 retained attempts/34 verified study endpoints/33 certified timings; host-only new-mode success and censored profiles establish no solve benefit or preset. |
| Follow-up — GPUP-7R (complete) | Resident FP64 state/updates, compact sparse execution and two-level conservative device guards. | 36/108 planned timing coverage, three complete FP64 profiles, 78 CPU refusals, 21 product endpoints; resident matched recovery but no useful quantized window or preset; 245.686586823 GPU s within existing ceilings. |
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

At the GPUP-ASSESS handoff, charge was **19730.939812844 / 21602.574545061 GPU seconds**, with
16816 events and SHA-256
dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c.
[GPUP-ASSESS](../benchmarks/lp-assessment-scheduling-gpup-assess.md) charges
523.674592721 seconds within its 2300-second allocation, preserving the exact
16684-event prefix e83d07792fb0775fc26d8d2cca8a2411f59fcbc94f742cafd8f6b844ffb60535
and every earlier prefix/phase ceiling. Its CPU-only final review strengthens
bitwise replay and profile eligibility while retaining all measured workers and
results. [GPUP-REFINE](../benchmarks/lp-refinement-gpup-refine.md)'s earlier
1541.719136512-second charge, telemetry refusal and report-reader correction remain.
That handoff required GPUP-7's contract/allocation, now completed above under ADR-0040; unused headroom reserves nothing. Historical handoffs and budgets
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
