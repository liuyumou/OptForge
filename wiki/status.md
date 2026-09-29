# Project Status

The repository implements the C8 local extension registry on top of the C5
flow-shop scheduling slice, the C4
agent-independent run surface, C3
extension safety, C2 owned branch-and-bound search, C1 pinned HiGHS solving, M1
model and candidate validation and the M0 bootstrap. Acceptance
evidence is recorded in [active task](../state/active-task.md).

| State | Features |
| --- | --- |
| Implemented | LP-only frozen study infrastructure, independently certified endpoints and a development baseline (GPUP-2), a backend capability declaration a caller cannot widen, a first-order linear programming method with a host-side certified dual bound, host and device backends for it, first-order LP kernels in f64 whose reduction order is fixed so a result cannot depend on scheduling, Original linear models, Rust/JSON/CLI candidate validation with explicit tolerances, backend-neutral solve contract, pinned CPU HiGHS LP/MILP solving with validated incumbents and reproducible records, owned branch-and-bound executive with budgets, cancellation and proof completion, extension runtime with declared authority, validated candidate producers and checked search advisers, typed extension failure records, CLI search over the executive with provenance-bearing run records and re-execution verification, flow-shop instances with an independent makespan recurrence, a big-M-free positional encoding, deterministic NEH and insertion producers, a frozen generated Taillard development subset and CLI scheduling commands, a local extension registry resolving a named identity to an extension this build provides with checked licenses, authority, compatibility, requirements and promotion, a reusable conformance suite and its record, workspace, CLI hello, GPU discovery, simulated leases, artifact schemas, CI and documentation tooling |
| In progress | None |
| Planned | Ordered adaptive/setup/COPT/convergence follow-ups, then GPU LP precision track (GPUP-7 through GPUP-10), adaptive research (C7), Python SDK (C9), comparative runner (C10); full MILP performance is a later track |
| Experimental | Opt-in cuda-lp-matched shared FP64 control and cuda-lp-tuned explicit residency/reduction/fusion execution plus explicit FP32 comparisons with fixed FP64 correction and opt-in adaptive audit/recovery policies and isolated COPT CPU/GPU PDLP controls; feature-gated exact scaling and component sparse research; independently checked versioned endpoints, no supported precision recipe |
| Deprecated | None |

GPUP-0 has saved the [precision roadmap](../docs/plans/gpu-lp-precision-roadmap.md),
draft specifications, design ADRs, and dependency-ordered tasks. GPUP-1 repairs
host certification and objective/gap arithmetic in both LP backends, with independent
exact-rational regressions. GPUP-2 implements measurement infrastructure and the
[development baseline](../docs/benchmarks/lp-baseline-gpup2.md): 144 trials,
173.148261443 GPU seconds. GPUP-3 adds the shared resumable FP64 controller,
bit-preserving certification optimization and schema/activity repairs. Its
[matched study](../docs/benchmarks/lp-matched-fp64-gpup3.md) retains 160 attempts and
27/36 matched CUDA certified timing trials. GPUP-4 implements explicit cuda-lp-tuned
with resident buffers, transfer avoidance, warp32 reduction and fusion. Its
[reviewed report](../docs/benchmarks/lp-tuned-fp64-gpup4.md) preserves a failed first
round and a complete correction, each 320 attempts. All eight configurations retain
27/36 timing coverage. Cumulative study use is 902.574545061 GPU seconds, including
the original 445.988045904; no ledger history was reset. Matched remains the general
reference; fused-warp is provisional only on three named development instances.
Full native/device/scoped sanitizer gates passed. GPUP-5 now extends cuda-lp-tuned
with explicit FP32 settings, fixed charged FP64 correction and separate code identity.
Its [480-attempt report](../docs/benchmarks/lp-fp32-gpup5.md) retains 27/36 timing
coverage for FP64, 12/36 for storage/products/accumulation/master correction and
6/36 for FP32 working state. COPT CPU/GPU PDLP certify 27/36 and 24/36. Total study
consumption after that study was 1324.210639253 GPU seconds. The subsequent
[213-job FP32 diagnosis](../docs/benchmarks/lp-fp32-slowdown-diagnosis.md) adds
143.056235443 seconds, totaling 1467.266874696, with all history preserved. It
separates extra iterations and representation error from executor/correction costs;
no runtime change was made. The subsequent
[GPUP-5B investigation](../docs/benchmarks/lp-exact-components-gpup5b.md) verifies
all 840 attempts and isolates exact power-of-two/factored scaling and component
products behind a research feature. Every new mode recovers 27/36 timing coverage;
component cross-products remain slower on the larger profiled cases. Full native,
device and all four scoped sanitizer gates pass. Its 697.211414922 study plus
70.875589353 acceptance seconds are charged to screening, totaling 2235.353878971
campaign seconds, with original artifacts and ledger prefixes intact. The
[rounding analysis](../docs/benchmarks/lp-fp32-rounding-analysis.md) and
[candidate register](../docs/plans/lp-precision-candidates.md) retain the diagnosis
and future alternatives. The [FP64-pipe root-cause note](../docs/benchmarks/lp-fp64-pipe-root-cause.md)
attributes the component slowdown to the sm_120 FP64 pipe; GPUP-5C acts on it under
[ADR-0022](../docs/decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md)
with integer-pipe guards, a fused two-launch schedule, double-float FP32 pairs,
explicit tolerance tiers and a frozen development extension; its
[report](../docs/benchmarks/lp-fp64-pipe-gpup5c.md) verifies 806 of 850 attempts,
raising cumulative consumption to 3794.758955639 seconds. Because context creation
and fixed host phases, not arithmetic, now dominate solves, the user pulled
GPUP-THROUGHPUT (repeated-solve throughput with explicit matrix and device reuse)
ahead of GPUP-6 on 2026-09-20. It is complete under accepted
[SPEC-0014](../docs/specifications/SPEC-0014-lp-repeated-solve-throughput.md) and
[ADR-0023](../docs/decisions/ADR-0023-repeated-solve-throughput.md): opt-in tuned
and research sessions pay setup once per batch, and its
[report](../docs/benchmarks/lp-repeated-solve-throughput.md) verifies 687 of 705
admitted attempts with 4785/4785 batch solves bitwise identical to fresh singles,
amortized throughput as a separately labeled endpoint (never single-solve
latency), and cumulative consumption of 6951.059845871 seconds. GPUP-6 is also complete under accepted ADR-0025; its
[adaptive report](../docs/benchmarks/lp-adaptive-gpup6.md) records explicit audits,
rollback, promotion/demotion, independent v5 evidence, complete correctness gates
and retained comparison failures. GPUP-EVIDENCE is complete under SPEC-0015 and
ADR-0027; its [report](../docs/benchmarks/lp-compact-evidence.md) retains 24 fresh
attempts, 15 verified endpoints and 12 certified timings. GPUP-HOST is complete
under SPEC-0016/ADR-0028: its [report](../docs/benchmarks/lp-immutable-host-input.md)
verifies all 28 attempts, certifies 24 timings and preserves all 14 numerical pairs.
One duplicate model reconstruction is removed while every assessment stays fresh.
GPUP-ADAPTIVE-COST is complete under SPEC-0017/ADR-0029; its
[report](../docs/benchmarks/lp-adaptive-host-cost.md) verifies 32 attempts,
certifies 24 timings and preserves all 16 numerical/work pairs. Full native,
regular device, fixed-work/replay and four adaptive sanitizers pass.
The next task is GPUP-SETUP, before the remaining ordered follow-ups. The
[ordered follow-ups](../docs/plans/gpu-lp-precision-roadmap.md#current-follow-up-order-2026-09-27)
separate priority from prerequisites. No supported recipe is available. The
campaign retains its eight GPU-hour cap; acceptance details remain
in the active-task record.

Solve records recompute objectives and violations independently of the backend. A
backend optimality claim holds under the recorded numerical settings; it is not an
exact certificate, and a limit, interruption or failure is never reported as a
completed proof. Owned search adds a second, distinct claim: proven optimality
means the executive exhausted its own node tree with every prune justified by a
relaxation that itself proved optimality. A search whose relaxation hit a limit
forfeits that claim and says so. Extensions may propose candidates and search
actions; the core validates every one of them, and no extension can forfeit a
proof, end a search or change its outcome. Extension containment covers panics,
not a process abort. A search is recorded with the revision, model fingerprint
and input hashes needed to repeat it, and verification re-runs that search from
the record alone rather than trusting its stored result; agreement establishes
determinism on one host, never optimality, and a forfeited search stays forfeited
after it verifies. No Python SDK, dynamically
loaded native extension, persistent checkpoint restart or general comparative experiment runner is
available. Cross-host reproducibility is untested; the development baseline
reports measured costs and coverage without a general solver superiority claim.

The registry decides which extensions a search may consult and records why. It
resolves a named identity to an extension this build already provides and refuses
one it does not; it never loads a separately distributed native component, which
would need a second unsafe boundary ADR-0003 prohibits. An entry is a claim and the
extension's own declaration is authoritative, so a disagreement between them is
refused in both directions rather than reconciled. Resolution is total: a search
either registers every extension its configuration named or does not start.
Promotion means a recorded conformance suite passed, checked against the cited
record's bytes; it never means the extension improves a search, which stays a C7
question and is deliberately unmeasured. A registry-backed run record is now
verifiable by re-execution, which is the gap C5 recorded.

The flow-shop slice adds the first application workload whose objective has a
second, independent computation: a makespan recurrence that shares no code with
anything proposing a schedule. An instance is encoded into an ordinary model with no
big-M constant, so every earlier contract carries it unchanged. It claims
correctness, not tractability: the encoding's linear relaxation is weak, proven
optimality is asserted only for tiny instances checked against exhaustive
permutation enumeration, and the frozen Taillard subset carries feasibility and
determinism evidence only. No best-known bound is committed as a threshold.

C6 is implemented. Two contracts make it up:
[heterogeneous computation](../docs/specifications/SPEC-0010-heterogeneous-computation.md)
fixes device selection, residency, batching, arithmetic width, fallback,
cancellation, recovery and equivalence, and a
[GPU LP backend](../docs/specifications/SPEC-0011-gpu-lp-backend.md) adds a
capability declaration to the solve contract so a caller reaching a backend that
cannot solve its model is refused rather than answered. Neither grants a device any
mathematical authority. A device-produced candidate is validated against the original
model like any other, and an approximate LP iterate becomes a dual bound only through
a host-side certification that treats the device's output as an untrusted guess; a
bad guess is required to yield a weak bound or no bound, never an invalid one.
GPUP-1 repairs the [reduced-cost cancellation defect](../state/known-failures.md#lp-certification-can-lose-the-roundoff-allowance-at-zero-reduced-cost)
with outward arithmetic and a shared, sense-aware objective/gap check. See the
[numerical argument and conservative limits](../docs/architecture/lp-certification.md).

Both are implemented. Two kernels evaluate
flow-shop schedules in 32-bit integer arithmetic and agree with the host recurrence
exactly rather than within a tolerance, which is available only because the
arithmetic is integer. A search selects a device in its configuration, registers a
device-backed candidate producer, and writes a record that names the hardware and
re-executes on it; when the device declines, the host computes the same
neighbourhood and the proposals are identical. A first crossover is measured: the
device loses below roughly fifty jobs and context creation costs about 148
milliseconds, so the CPU remains the default and residency is what makes a device
worth reaching.

The linear-programming half adds a second and a third backend behind the same
contract, selected only by an explicit `--backend`. A restarted primal-dual method
runs on the host or on a device, and in both cases everything it is permitted to claim
is computed on the host: the candidate is validated against the original model, and a
dual bound exists only where a host-side certification builds one from the model's own
coefficients. That certification reads no residual the device computed, which is what
stops it checking the device against itself, and it is valid for an arbitrary
multiplier vector -- a bad guess yields a weak bound rather than an invalid one. The
device's iterates agree with the host engine's bit for bit, which is stronger than the
contract asks and is recorded as this project's property rather than a guarantee.

No performance claim is made. The crossover is a development diagnostic on one host
and no default consults it, so "CPU below the crossover" holds because CPU is the
default everywhere rather than because anything measured. Each remaining gap is
recorded in [known failures](../state/known-failures.md) rather than implied by the
parts that work.

See the [M1 contract](../docs/specifications/SPEC-0001-model-and-validation.md),
[backend contract](../docs/specifications/SPEC-0002-backend-contract.md),
[solver executive contract](../docs/specifications/SPEC-0003-solver-executive.md),
[extension runtime contract](../docs/specifications/SPEC-0004-extension-runtime.md),
[run surface contract](../docs/specifications/SPEC-0005-run-surface.md),
[flow-shop contract](../docs/specifications/SPEC-0008-flow-shop.md),
[extension registry contract](../docs/specifications/SPEC-0009-extension-registry.md),
[heterogeneous computation contract](../docs/specifications/SPEC-0010-heterogeneous-computation.md),
[GPU LP backend contract](../docs/specifications/SPEC-0011-gpu-lp-backend.md),
[backlog](../state/backlog.yaml) and
[implementation plan](../implementation-plan.md) for evidence stages and dependencies.

GPUP-COPT is complete under ADR-0026. Its [component-cost report](../docs/benchmarks/lp-copt-comparison.md)
retains all 1140 attempts, independently verifies 948 endpoints and certifies
402/816 primary timings. Evidence output at 65536 rows and COPT graph internals
remain explicit gaps; no winner or preset is selected. Task charge is
5853.941357570 GPU s; cumulative 14766.435441716/18002.574545061 s.
The 15340-event ledger SHA-256 is
5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b,
preserving the 13056-event prefix and every phase cap. Performance repairs ranked
in the report are ordered in the roadmap and backlog; GPUP-EVIDENCE and GPUP-HOST
are complete, as is GPUP-ADAPTIVE-COST; GPUP-SETUP follows. Current cumulative consumption is
15407.672759957 / 18002.574545061 GPU s. The 15528-event ledger SHA-256
cb0dc57f9f92546f4cc2d93b0de3c8556d6b24517f71b7a6efaa91fa96afedb6
preserves the 15452-event host-input prefix and all prior history.
GPUP-7 still needs its accepted contract.
