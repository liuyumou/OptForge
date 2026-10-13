# Experiment design for precision components and combinations

Status: proposed protocol; no new workload, seed, threshold or budget is admitted
Owner: numerical backend and experiment tooling
Introduced: GPUP-DESIGN, 2026-10-12
Last reviewed commit: bootstrap
Implementation: GPUP-REP and bounded GPUP-EXEC subsets; remaining design is not implemented
Tests: per-stage admission and acceptance below

## Execution update (2026-10-13)

GPUP-REP CPU validation and the separately admitted [GPUP-EXEC study](lp-exact-executor-gpup-exec.md)
are complete under ADR-0034/0035. GPUP-EXEC preserves 108 attempts, 94 verified
endpoints and 58/96 certified timings, including all failures and range refusals.
Its explicitly amended budget and final ledger supersede the historical resource
snapshot below for current accounting. The remaining component/interaction plan
still grants no workload, behavior or reservation. GPUP-STATE's bounded
[admission refusal](lp-expansion-state-gpup-state.md) under ADR-0036 executes no
GPU jobs: its first full-bin primitive fails register/spill limits in both
formats. PR 19's compact full-range FMA fits at 40 registers and zero spills,
resolving the scalar obstacle in a CPU/compile-only challenge. Full state and
device execution remain gated. GPUP-REFINE is next and
requires its own accepted contract and allocation.

## Questions and primary endpoint

Which component improves certified fresh-solve latency, why does it improve it,
and which compatible combination retains that gain across unseen problems?
Measure the original model at unchanged 1e-9 feasibility/certified-gap acceptance.
A representation study, kernel microbenchmark, easier tolerance tier or amortized
batch measurement answers a different question and keeps a separate label.

Follow [SPEC-0013](../specifications/SPEC-0013-lp-precision-experiments.md), the
[architecture rationale](../plans/lp-precision-architecture-2026-10-12.md), and draft
[SPEC-0020](../specifications/SPEC-0020-lp-expansion-arithmetic.md)/
[SPEC-0021](../specifications/SPEC-0021-lp-refinement.md). This plan specifies the
comparisons to freeze, not results or permission to run. Every affected numerical
contract and concrete protocol/resource record must be accepted first.

Primary latency starts with a fresh process and includes input handling, context,
preparation/packing, transfers, every update/reduction/refresh, recovery, repeated
assessments, final host certification, evidence output and teardown under the
existing process envelope. Independent post-run verification is recorded separately,
as in the existing protocol; moving required certification there to shorten the
primary endpoint is forbidden. Concurrent work is prohibited by the shared GPU lease.

## Hypotheses and discriminating controls

Component IDs refer to the architecture plan. A trial must distinguish a storage
change, an arithmetic change, a controller/method change and a checking policy.
Do not change two factors in a claimed single-component comparison.

| ID | Falsifiable hypothesis | Required controls / diagnostics |
| --- | --- | --- |
| R1 | Smaller exact tails or integer decoding lower traffic/preparation enough to lower total time without changing the represented operator. | Original-bit storage; existing Parts3; mixed-tail layouts under the same arithmetic. Exact round trips, full resident/peak bytes, both matrix views, split/decode time and metadata. |
| R2 | Explicit exponent handling removes pair underflow; accurate expansions can avoid expensive native FP64 in the sparse path. | Unscaled pair, scaled pair, accurate expansion and tuned FP64; independent oracle and range/error failures. Scaled pair is not an exact-precision control. |
| X | Cached vector splits and a lean executor remove overhead independently of numerical changes. | Same represented inputs, reduction/rounding order, state and stopping; count launches, conversions, registers, spills and decoded copies. If fusion changes order, label a second arithmetic experiment. |
| S | Persistent accurate/compensated state prevents lost updates and reduces work. | Native FP64 masters, plain FP32 masters, compensated FP32 and full expansion masters with the same product policy. Measure lost-update frequency and original residual, not just iterate difference. |
| N | Stable equivalent formulas reduce cancellation and avoidable exceptions. | Same method/settings, one formula changed per first comparison; include boundary/range fixtures and full trajectories. |
| F | Residual-driven correction repays accurate outer work by preventing FP32 stagnation. | Ordinary tuned/precision FP64, existing fixed correction and adaptive policy, then new refinement with native FP64 outer masters. Record original KKT merit before/after every correction and all failed corrections. |
| A | Anchoring reduces bias from E*v to E*delta and increases feasible inner work between accurate refreshes. | Refinement with and without anchoring, then an admitted non-refinement anchored control; exact E*delta bounds, refresh frequency and vector traffic. |
| Q | Only a small fraction of rows/blocks need expensive arithmetic. | Uniform admitted precision and selective precision at the same error budget; histogram of tail activity, promoted fraction and summary/exception memory/time. |
| H | Fewer optional assessments save more than delayed stopping adds. | Inherited fixed schedule and proposed trigger schedule on the same method; offline common-trajectory assessment replay first, then separately timed online solves. Mandatory final checks stay on. |
| P | Better scaling/preconditioning or an active-face correction reduces total work enough to pay setup. | Same represented-operator fidelity; factor setup, accuracy/refinement, rank failures, rejected faces and full-model assessment charged. |
| T | Admitted dense tiles/integer limbs beat the best scalar operator on actual single-RHS work. | Same represented operands and accuracy; include padding, permutation, pack/unpack, scales, sparse remainder, conversions and reductions. No sequential-iterate batching. |
| Z | Stochastic rounding helps beyond deterministic compensation. | Same model/operator contract with independent predeclared rounding seeds; report variance, bias, state and setup costs. This is a later separately budgeted comparison. |

A cheaper per-proposal path can lose through more work. An exact representation
can lose through bandwidth. A faster assessment schedule can delay a successful
stop. Each experiment records these possibilities instead of explaining them away.

## Stage 0: CPU mathematics and cost admission

GPUP-REP first closes a bounded SPEC-0020 subset. Run an independent rational or
integer oracle and proof review for every admitted format/primitive. The current
[design artifact](../plans/data/lp-precision-design-examples.json) and
[validator](../../tools/check_lp_precision_design.py) are a starting example suite,
not acceptance for arithmetic that does not exist yet.

Required strata are every exponent, both signs, signed zero, subnormal/normal and
rounding boundaries, cancellation, nonrepresentable tails, overflowing intermediates
with finite final values, long reductions, exact transpose and malformed tuples.
GPUP-REFINE also needs exact tiny LP maps in both objective senses, offsets,
ranged/one-sided/equality rows, free/fixed variables, degenerate active faces and
a deliberately inaccurate inner oracle. Exhaustive tiny vertices are useful;
random tests do not replace the derivation.

Compute actual layout sizes and peak allocation formulas. Derive instruction/work
counts and a simple roofline/cost bound from the actual sparse shapes; do not use
advertised Tensor Core peak as a prediction. For H, replay assessment decisions on
an unchanged recorded trajectory before claiming any numerical improvement.
For P/T, establish a real admissible subproblem/tile population before kernel work.
Reject candidates whose required mathematical assumptions or memory caps fail.
A theoretical cost estimate may guide priority but cannot establish performance.

The original GPUP-REP proposal was CPU-only, with one CPU-hour and four
build jobs and zero GPU time. That task is now complete. New
proof failures and minimized counterexamples are first-class outputs.

## Stage 1: Primitive and executor validation

Only after a contract and reservation exist, validate one operator/kernel family
against the independent CPU oracle on the actual target. Require deterministic
same-device replay and all four scoped sanitizers for new kernel behavior.
Fault-inject conversion, range, cache-generation and error-budget failures.
Inspect generated instructions and reachable paths; record actual FP64 conversions,
comparisons and fallback. Denied hardware counters remain unavailable, never zero.

Use two distinct diagnostic endpoints: fixed-work operator/update timing, and a
fresh solve including all setup and checks. Provisioning/compilation is described
separately and never hidden as per-iteration speed. Compare strong tuned FP64 as
well as the precision-executor FP64 control. Keep one-GPU-at-a-time admission.

## Stage 2: Bounded development screening

Before admission, freeze at most eight development cells spanning: a launch-bound
tiny case, scheduling/range failure, small and large irregular sparsity, a large
dense-block case, mixed non-FP32-exact coefficients at two scales, and a new
ill-conditioned/cancellation fixture if accepted. Use existing IDs where available;
a new generated family needs a reviewed manifest addition and fixed seeds.
The exact roster is unresolved until its CPU/memory/deadline admission is known.
Do not remove a hard cell because a candidate fails on it.

One slice admits at most four configurations, including its local control, across
those cells with the existing three screening repetitions: at most 96 primary
attempts. This is an upper bound, not an admitted Cartesian product. Reserve fixed-
work profiles and acceptance separately; no unbounded retries or tuning loops.
If the available phase budget cannot reserve the whole frozen slice, shrink its
scope or obtain a separately authorized allowance **before** any attempt; never
truncate after seeing favorable results. All failed/rejected/interrupted attempts
retain identity and budget charges. Diagnostic profiles do not add primary samples.

Keep the known mixed-65536 and scheduling failures visible. Small/synthetic success
cannot support a general recipe. The primary 1e-9 tier remains fixed; opt-in
1e-6/1e-4 comparisons, if separately admitted, do not repair 1e-9 coverage loss.

## Stage 3: Interaction experiments

Do not test the full Cartesian product of every format and algorithm. Use these
small blocks after component admission; eliminate invalid combinations before the
freeze and retain the reason in a compatibility matrix. A dependency is not an
interaction estimate.

| Block | Frozen comparison | What it isolates |
| --- | --- | --- |
| B1 storage | Up to four R1 layouts, identical arithmetic and controller | Packing/traffic versus decoding, without numerical confounding. |
| B2 executor | Cache splits off/on, then admitted guard/fusion off/on | Independent executor effects; preserve operation order or label changed arithmetic. |
| B3 accurate state | 2 x 2: native-FP64 versus admitted expansion masters, original versus stable formula set N | State cost and formula interaction; compensation is a separate preliminary candidate. |
| B4 correction | 2 x 2: outer refinement F off/on, anchors A off/on, fixed native-FP64 accurate path | Whether anchors help independently and whether they change refinement's effect. A cell without a valid algorithmic contract is inadmissible. |
| B5 hybrid | 2 x 2 x 2: native-FP64/expansion masters S, F off/on, uniform/selective Q | The user's combined strategy and whether selective products need accurate outer correction. All other policies and tolerances stay fixed. |
| B6 assessments | H off/on on tuned control and the best frozen numerical candidate | Saved checks versus delayed stopping and any controller interaction. |
| B7 optional structure | P or T off/on on an admitted candidate, one at a time | Whether factor/tile costs repay on actual structure; separate single-RHS and throughput experiments. |

B5 is at most eight configurations and needs its own reservation; it is not added
to every screening slice. Begin with paired effects at each problem, then report
interaction of log latency for complete certified cells, for example
I = log(T11)-log(T10)-log(T01)+log(T00). Negative I indicates an additional joint
latency reduction on that scale. Treat coverage/failure interaction separately;
missing success cannot be imputed as a favorable time or discarded from the table.
With only three screening repetitions, such estimates guide subsequent freezing,
not promotion to a preset. Finalists need independent repeated evidence.

A compatible combination of S+F+A+Q is an explicit candidate, not the presumed
winner. Alternative finalists are tuned FP64 alone, accurate expansions without
refinement, and refinement with native FP64 outer state. H may improve each under
its own accepted contract. T/P/Z remain optional; no final tournament requires
implementing a component rejected at a prior admission gate.

## Stage 4: Frozen finalists and held-out evaluation

Freeze at most three candidate recipes plus tuned FP64 as the primary tournament;
add legacy host/matched controls, pinned HiGHS and optional COPT as separately
reserved accuracy-qualified comparisons where applicable. Their native iteration
counts are different units. Do not present project certification and an external
solver's own success flag as equivalent evidence.

Use at least ten independent fresh-process repetitions per admitted final cell,
as required by the existing final-study protocol, or label evidence incomplete.
Specify trial interleaving/order, deterministic scheduling seed, deadlines and
all configurations before launch. Paired repetitions share problem and repetition
identity, never a reused process/context. Record available device/driver/thermal
state and any telemetry limitation. Do not quietly warm a cold-start endpoint.

All already inspected instances and their trivial rescalings/permutations are
**development data**. Hold out whole base-instance groups, including related
transforms; keep novel family/size/range shifts distinct from in-distribution
holdout. The exact manifest, generator revision, seeds and group split must be
accepted and hashed before finalist results are inspected. Do not rename the
existing development corpus held-out or tune a policy on final failures. Any
follow-up tuned using those failures requires a new independent holdout.

Freeze the statistical analysis, including confidence level, resampling seed,
resample count, instance/repetition hierarchy and treatment of missing cells.
The proposed analysis uses 95% paired intervals, with resampling at independent
instance level for cross-instance claims and within-instance repeats for timing
noise. Use simultaneous intervals or a declared multiplicity correction for
multiple finalist claims. A three-repetition screening interval is not strong
selection evidence. No optional stopping on a favorable interval.

## Metrics, accounting and choosing a recipe

Every trial records original model/source/configuration/code identities; raw
input, represented-operator and transform hashes; arithmetic/reduction policies;
full timing envelope and exclusive component times; memory/metadata/spill counts;
logical updates, physical proposals, audits, rejected/replayed work, outer solves,
anchor refreshes and final certification; original feasibility/gap and rejection
cause; and replay/verification status. Counter unavailability is explicit.
Exclusive time scopes must sum to their parent without double-counting child
certification costs. Kernel time is a secondary endpoint.

Decision order:

1. **Validity:** reject an arithmetic or authority failure regardless of speed.
2. **Coverage:** report certified/planned counts by family and tolerance. A
   supported general recipe cannot introduce observed coverage loss relative to
   the primary control on the frozen required cells. Small samples still limit
   claims about unseen reliability. A scoped recipe needs a predeclared,
   observable admission rule, not a list of test instances it happened to win.
3. **Total latency:** compare paired certified results, complete coverage tables,
   medians and tail behavior. Claim superiority only when the predeclared final
   confidence criterion supports it; otherwise retain a Pareto set or the control.
4. **Cost/robustness:** publish peak memory, preparation, recovery, worst observed
   regressions and admitted range/shape limits. A fast median cannot hide failures.
5. **Simplicity:** among indistinguishable supported candidates, prefer fewer
   formats, fallbacks and parameters. Tuned FP64 can remain the best recipe.

Report time to a certified solution with failed solves explicitly right-censored
at the common deadline; do not invent a certified latency for a timeout. Paired
speedups restricted to common successes are labeled and accompanied by full
coverage, avoiding survivorship claims. An optional penalized score must state its
penalty and cannot replace coverage or certification. Do not choose a single
weighted score after seeing results. Development-learned selection rules count as
part of the recipe and are frozen before holdout, not retroactive instance dispatch.

## Resource and implementation gates

Historical planning snapshot (before ADR-0035): consumption was
17115.274617853 / 18002.574545061 GPU seconds; all
16134 events and ledger SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823 remain untouched.
The initial 28800-second campaign cap and all phase caps persist. Neither the
887.299927208-second difference nor unused historical reservations authorize this
plan. No GPU allocation is created by documentation.

Each execution slice must first record its accepted numerical subset and protocol
identity; exact roster/configurations/seeds; repeats and per-attempt deadlines;
CPU time/jobs, peak memory and scratch limits; separate study/profile/acceptance
GPU caps and reservation formula; source/image binding; cancellation/refusal/no-
retry rules; verifier and failure classifications; and the remaining campaign and
phase headroom. Worst-case admitted reservations must fit before launch. Do not
reset the ledger, shift a failed attempt out of its phase or borrow another phase's
unused cap. Scope reduction or new authorization is a future concrete decision.

## Required output artifacts

Produce a component report with the motivation and falsification result for every
admitted candidate; exact CPU fixtures/proof obligations; format/layout and kernel
instruction inventories; full frozen protocol/manifest and compatibility matrix;
all raw outcomes and immutable budget receipts; disjoint cost and work tables;
per-family coverage and paired uncertainty; ablation/interaction tables; and a
final recipe card stating admission, accuracy, limits, reproducible command and
full costs. Record rejected/deferred candidates and why. A report may conclude
that no new recipe is supported. It must not relabel a proposed design as measured.
