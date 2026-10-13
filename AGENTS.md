# Agent Instructions

Implement one dependency-ready bounded task at a time. Follow
[CONTRIBUTING.md](CONTRIBUTING.md), accepted specifications, and ADRs.
Update state/active-task.md before work and record acceptance evidence afterward.
Read state/known-failures.md before implementing related behavior.

Current handoff (2026-10-13): GPUP-STATE is complete as a bounded resource
admission refusal under [ADR-0036](docs/decisions/ADR-0036-full-expansion-state-admission.md).
Its [report](docs/benchmarks/lp-expansion-state-gpup-state.md) independently checks
192 integer, 270 FMA, 64 update and 48 transcendental cases. The first full-range
exact-bin FMA construction in both expansion formats uses 255 registers and
nonzero spills, exceeding the accepted 128-register/zero-spill gate. Bounded
320-bit probes fit but do not qualify the complete family. PR 19 review adds a
full-range compact FMA: 40 registers and zero spills in both formats, with 5900
additional independent cases per construction and host UBSan acceptance. The
first refusal remains exact but no longer establishes a scalar resource obstacle.
The instruction audit and frozen transcendental verification are repaired.
No controller,
state/replay or comparative study is admitted, and no format-impossibility or
performance claim follows. GPU charge is zero; the 16366-event ledger and
17635.432015338 / 21602.574545061 seconds below remain exact. GPUP-REFINE is next
and requires an accepted SPEC-0021 subset and its own allocation; unused state
allowance does not reserve it. Preserve full expansion/alternative construction
gates, original-model host authority, identities and all historical evidence.

Prior handoff (2026-10-13): GPUP-EXEC is complete under accepted ADR-0035 and
the bounded exact-dot subset of [SPEC-0020](docs/specifications/SPEC-0020-lp-expansion-arithmetic.md).
Its [report](docs/benchmarks/lp-exact-executor-gpup-exec.md) retains all 108 attempts,
independently verifies 94 endpoints and certifies 58/96 timings. All 27 cached/
uncached study pairs match bitwise. Full native, 66 regular device tests, oracle,
six replays and four scoped sanitizers pass. Fourteen initial FP64 controls failed
discovery because the archive omitted an unchanged dependency; the repair and
failed attempts are retained without retries. Scheduling/scaling/mixed exact
solves refuse the bounded exponent window. No total-cost win or preset is selected.
The subsequent GPUP-STATE admission result is recorded above. Read the
[architecture and component motivations](docs/plans/lp-precision-architecture-2026-10-12.md),
draft [SPEC-0021](docs/specifications/SPEC-0021-lp-refinement.md), and
[component/interaction experiment design](docs/benchmarks/lp-precision-design-experiments.md).
GPUP-REP remains the CPU reference; full expansion state and correction/anchored
products remain independently gated. No next-task reservation follows from unused
GPUP-EXEC headroom. Preserve final original-model host authority and all identities.
Task charge is 520.157397485 GPU seconds: timing 431.684266725/2300, profiles
36.003675982/450 and acceptance 52.469454778/850. Cumulative consumption is
17635.432015338 / 21602.574545061 seconds under ADR-0035's amended authority.
The 16366-event ledger SHA-256 is
4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b,
preserving the 16134-event prefix
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823.
The dated handoffs below remain historical; follow next_ready_task and the
roadmap's 2026-10-12 order.

For low-precision LP follow-ups, read the preserved
[2026-09-30 research analysis](docs/plans/lp-low-precision-research-2026-09-30.md)
alongside the roadmap and candidate register. It records measured failure
mechanisms, proposed correction-LP/anchored-product methods, SM120 bypasses,
FP16/FP8 progression, limitations and experiment gates. It is research guidance,
not an accepted numerical contract or a change to next_ready_task or GPU budgets.

M1, C1, C2, C3, C4, C5, C6 and C8 are complete and specified. C6 was heterogeneous
computation and GPU feasibility, specified as
[SPEC-0010](docs/specifications/SPEC-0010-heterogeneous-computation.md) for device
selection, residency, batching, arithmetic width, fallback, cancellation, recovery and
the batched integer schedule evaluator, and
[SPEC-0011](docs/specifications/SPEC-0011-gpu-lp-backend.md) for the GPU linear
programming backend. Both are implemented with evidence: a search can register a
device-backed candidate producer and re-execute from the record it writes, and
`optimizer solve --backend host-lp|cuda-lp` runs a first-order linear programming
method whose dual bound comes only from a host-side certification. The next capability
is C7, adaptive portfolios, which has no specification yet and needs one before any
behavior. The user has prioritized the separate
[GPU LP precision research track](docs/plans/gpu-lp-precision-roadmap.md) before C7;
follow `next_ready_task` in state/backlog.yaml and implement one GPUP slice at a time.
SPEC-0013 is accepted and GPUP-2 implements the bounded LP study and baseline report.
SPEC-0012 is accepted for implemented GPUP-3 shared resumable FP64 control. The
opt-in cuda-lp-matched backend and measured overhead repairs preserve legacy cuda-lp.
GPUP-4 adds explicit experimental cuda-lp-tuned under ADR-0017, with the preserved
first round and complete ADR-0018 correction documented in
[the report](docs/benchmarks/lp-tuned-fp64-gpup4.md). Matched remains the general
reference; scoped provisional fusion results are not supported presets. GPUP-5 is
implemented under ADR-0019: lp-precision-v1 on cuda-lp-tuned, separate precision
code identity, FP32 storage/products/accumulation/state and fixed FP64 correction,
v4 evidence and optional isolated COPT 8.0.6 CPU/GPU PDLP baselines. Its
[report](docs/benchmarks/lp-fp32-gpup5.md) verifies all 480 attempts and records
coverage losses; no supported preset is selected. Existing identities/replay and
original-model authority remain. GPUP-6 is a separate explicit adaptive contract (below); no audit/rollback/promotion/demotion is implicit
in GPUP-5. Later quantization and precision requirements remain pending.
The [FP32 latency diagnosis](docs/benchmarks/lp-fp32-slowdown-diagnosis.md) adds
213 equal-work/profiler diagnostics under ADR-0020: convergence amplification,
scaled-matrix bias and executor/correction overhead, with hardware counters denied.
The diagnosis reached 1467.266874696 campaign GPU seconds: the prior 1324.210639253
plus 143.056235443 diagnostic screening seconds. Never reset the ledger or evidence.
GPUP-5B is complete under ADR-0021: feature-gated exact scaling and two/three-component
sparse products, separate research code object/executable and strict research-v1
host evidence. Its [report](docs/benchmarks/lp-exact-components-gpup5b.md) verifies
all 840 attempts and full native/device/four scoped sanitizer gates. New modes
restore 27/36 timing coverage; component cross-products remain slower. Preserve
the [rounding note](docs/benchmarks/lp-fp32-rounding-analysis.md) and
[candidate register](docs/plans/lp-precision-candidates.md). No preset or adaptive
recovery is selected. Carry forward 2235.353878971 campaign seconds, including
697.211414922 GPUP-5B study and 70.875589353 acceptance screening seconds. All 4996
ledger events retain the 3288-event prefix; the final ledger SHA-256 is
737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f.
GPUP-5C is complete under ADR-0022 after the
[FP64-pipe root-cause note](docs/benchmarks/lp-fp64-pipe-root-cause.md): three
feature-gated research modes (integer-pipe guards, fused two-launch schedule,
double-float FP32 pairs), research-v2 evidence, explicit tolerance tiers
1e-9/1e-6/1e-4 recorded per request, a frozen lp-manifest-v2 development extension
up to 65536 rows, and a protocol-driven harness (`--protocol`) whose v1 behavior is
byte-identical. Its [report](docs/benchmarks/lp-fp64-pipe-gpup5c.md) verifies 806
of 850 admitted attempts under identity gpup5c-v1: integer guards and fusion are
bitwise identical to the FP64 control and halve update cost at study size;
double-float is fastest at scale but underflows on scheduling LPs; tiers recover
FP32 storage coverage without changing latency. Cumulative campaign consumption is
3794.758955639 seconds; the 6722-event ledger SHA-256 is
ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b with the
4996-event prefix intact. On 2026-09-20 the user pulled GPUP-THROUGHPUT ahead of
GPUP-6: after GPUP-5C, context creation (208-330 ms) and the fixed host phases, not
arithmetic, dominate solves, and at 65536 rows preconditioning and research
preparation each exceed total kernel time. GPUP-THROUGHPUT is complete under
[SPEC-0014](docs/specifications/SPEC-0014-lp-repeated-solve-throughput.md) and
[ADR-0023](docs/decisions/ADR-0023-repeated-solve-throughput.md), both accepted
2026-09-20: opt-in TunedSession/ResearchSession reuse one context, prepared matrix
and residency per batch, with per-solve cold iterates, fresh certification and
bound rebinds counted separately. Its
[report](docs/benchmarks/lp-repeated-solve-throughput.md) verifies 687 of 705
admitted attempts under identity gpup-throughput-v1: 4785/4785 batch solves are
bitwise identical to fresh singles, amortized throughput reaches 26.6x fresh
single-solve latency at N=32 on small-4 as a separately labeled endpoint, a batch
of one does not pay off, sessions lose at 32768 rows, and all 18 65536-row short
batches timed out. It leaves the single-solve endpoint, protocol, defaults and
archived evidence unchanged and never reports amortized throughput as
single-solve latency. Cumulative campaign consumption is 6951.059845871 seconds
inside the 8102.574545061-second ceiling (2617.929459541 study / 2700,
538.371430691 acceptance / 600); the 8178-event ledger SHA-256 is
dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6 with the
6722-event prefix ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b
intact. The pre-existing tuned_cases filter lacks a clean racecheck receipt (the
session_ scope passed all four sanitizers); the partial receipts are retained.
The [review corrections](docs/benchmarks/lp-throughput-corrections.md) under
ADR-0024 repair outcome identity, common session identity and binary64 comparison;
48 new ordinary fresh-variant controls validate 360/360 retained comparisons.
Historical fresh-variant controls were N=1 sessions and remain labeled as such.
After the correction: cumulative 6982.408046756 s, study 2645.977139698/2700,
acceptance 541.671951419/600; 8276-event ledger SHA-256
b3451186b7a5fc0029fbbd612b07e795072476ab76137a78a375b1d97866c236 preserves the
8178-event prefix above. No new GPU allowance.
The subsequent [host-input repair](docs/benchmarks/lp-throughput-host-input.md)
removes repeated host parsing/reconstruction without caching assessments:
16/16 new 32768-row N=8 diagnostic results match, with original and new verifier
acceptance. Whole-batch historical comparisons are 4.53x repeat and 2.20x variant
(one repetition, no general preset). Campaign consumption is now 7015.920961503 s;
study 2679.490054445/2700, acceptance 541.671951419/600. The 8278-event ledger
SHA-256 is c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a, preserving
the 8276-event prefix above and all prior prefixes. No new allowance or kernel
change; 65536-row coverage and the old tuned_cases racecheck gap remain open.
GPUP-6 is complete under accepted ADR-0025 and SPEC-0012: explicit lp-adaptive-v1
ladders/audits, whole-window rollback and charged replay, direct/gradual promotion,
sticky or probed demotion, fresh-single v5 evidence and replay. Original-model
host certification remains authoritative; old kernels, records and defaults remain.
Its [report](docs/benchmarks/lp-adaptive-gpup6.md) independently verifies
2086 endpoints from 2376 admitted of 2376 planned attempts.
Failed archive-discovery attempts and comparison gaps remain visible; no preset
is selected. Native, regular device and four adaptive sanitizer gates pass.
Campaign consumption is 8912.494084146 s inside the 14402.574545061 s ceiling;
GPUP-6 study 1826.094392481/5400 s, acceptance 70.478730162/900 s.
The 13056-event ledger SHA-256 is
6db55153153e66ed5c2398417d008e4edd278e11153cf87b975345f1a574d34d, preserving the 8278-event prefix
c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a and every earlier prefix.
GPUP-7 remains the next precision feature after the COPT follow-ups ordered below;
it needs its bounded quantization/FP8 interface and resource contract before behavior.
Adaptive sessions, persistent checkpoints and supported presets remain outside GPUP-6; old 65536-row and tuned_cases racecheck gaps remain.

GPUP-COPT is complete under ADR-0026. Its [component-cost report](docs/benchmarks/lp-copt-comparison.md)
retains all 1140 attempts, independently verifies 948 endpoints and certifies
402/816 primary timings. Evidence output at 65536 rows and COPT graph internals
remain explicit gaps; no winner or preset is selected. Task charge is
5853.941357570 GPU s; cumulative 14766.435441716/18002.574545061 s.
The 15340-event ledger SHA-256 is
5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b,
preserving the 13056-event prefix and every phase cap. The user requested follow-up
ordering on 2026-09-27. GPUP-EVIDENCE and GPUP-HOST are now complete (below).
GPUP-SETUP, GPUP-COPT-ADAPTER and GPUP-CONVERGENCE are now complete (below);
continue with GPUP-7's required contract work. Fresh setup diagnosis and optional COPT adapter
construction were separately prioritized investigations, not quantization prerequisites;
see the [ordered roadmap](docs/plans/gpu-lp-precision-roadmap.md#current-follow-up-order-2026-09-27)
and next_ready_task. Planning adds no GPU allowance or accepted numerical behavior;
GPUP-7 still needs its accepted contract.
GPUP-EVIDENCE is complete under accepted SPEC-0015 and ADR-0027. Its
[report](docs/benchmarks/lp-compact-evidence.md) records strict study-only compact
v1-v5 evidence, verified transcode and replay, four full-witness CPU round trips,
full native acceptance, 55 device tests and six format pairs plus six replays.
All 24 fresh attempts are retained: 15 verify and 12 certify; compact verifies
12/12 and certifies 9/12, while mixed-65536 remains time-limited. Historical outputs,
legacy defaults, numerical settings and kernels are unchanged; the old racecheck
and session gaps remain. Task charge is 305.274714773 GPU s; cumulative
15071.710156489/18002.574545061 s, with no new allowance. The 15392-event ledger
SHA-256 is 6a30c1954ff9bc80c733364d8e8a7c0fc4c4439d70b959d2c10996d71993e518,
preserving the 15340-event prefix above and all phase caps.
GPUP-HOST is complete under accepted SPEC-0016 and ADR-0028. Its
[report](docs/benchmarks/lp-immutable-host-input.md) verifies all 28 attempts,
certifies all 24 fresh timings and matches all 14 numerical/work pairs. LpInput
removes one duplicate parse/structural validation, retaining fresh sparse construction
and every candidate/certificate assessment. Native, 55 regular device tests, six
old/new fixed-work pairs and six compact replays pass. No numerical/default/kernel
change or cross-solve reuse; historical racecheck/session/mixed-65536 gaps remain.
Task charge is 134.072418846 GPU seconds; cumulative 15205.782575335 /
18002.574545061 seconds, no added allowance. The 15452-event ledger SHA-256 is
90dab78c269b74f511416ddd73cf05e123555ae006b9ad75fc896933a35f9cd2,
preserving the 15392-event prefix above and all phase caps.
GPUP-ADAPTIVE-COST is complete under accepted SPEC-0017 and ADR-0029. Its
[report](docs/benchmarks/lp-adaptive-host-cost.md) verifies all 32 attempts,
certifies all 24 timings and matches all 16 timing/profile pairs. Shared operators
reduce full-ladder preparation from five operators to two; streamed audits and
borrowed probes preserve arithmetic and charged recovery. Twelve fixed-work pairs
and twelve replays match; full native, 55 regular device tests and four adaptive
sanitizers pass. No preset or cross-solve reuse. Historical gaps remain open.
Task charge 201.890184622 GPU seconds; cumulative 15407.672759957 /
18002.574545061 seconds, with no added allowance. The 15528-event ledger SHA-256
cb0dc57f9f92546f4cc2d93b0de3c8556d6b24517f71b7a6efaa91fa96afedb6
preserves the 15452-event prefix above and all phase caps.
GPUP-SETUP is complete under accepted SPEC-0018/ADR-0030. Its
[report](docs/benchmarks/lp-fresh-setup.md) verifies all 32 attempts, certifies 24
fresh timings and matches all 16 numerical/work comparisons. Four control profiles
precede the sole experimental primary-context repair; retain/release provides no
consistent fresh-process latency benefit. User contexts remain the default, primary
contexts are study-only, with checked lifecycle receipts and setup-bound replay.
Full native, 58 candidate device tests, four primary sanitizers, twelve fixed-work
pairs and twelve replays pass. Historical racecheck/session/mixed-65536 gaps remain.
Task charge 224.608447458 GPU seconds; cumulative 15632.281207415 /
18002.574545061 seconds, no new allowance. The 15606-event ledger SHA-256
ad3d84354f0b74ae62fcc019ee4dcbf29b0a3251d066f1e0f2df11ccb107230b preserves the 15528-event prefix above
and every phase cap. The following adapter slice retains this prefix.
GPUP-COPT-ADAPTER is complete under accepted SPEC-0019/ADR-0031. Its
[report](docs/benchmarks/lp-copt-adapter.md) independently verifies all 84 attempts,
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
[report](docs/benchmarks/lp-convergence.md) retains all 176 frozen attempts,
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
2026-10-12 planning update above now makes GPUP-REP CPU-only proof/contract
validation next, before any new numerical behavior.

GPUP-5's exact cumulative ceiling was 4502.574545061 seconds. Its separate acceptance
used 80.458622460 of 900 GPU seconds. Future work must retain the campaign/phase caps.
GPUP-1 repairs certification and objective/gap arithmetic; preserve its independent
exact-rational regressions before introducing lower precision. The initial
experiment campaign is capped at eight GPU-hours. Repeated-solve throughput is
GPUP-THROUGHPUT above; full MILP search performance remains a separate future direction.
Unsafe CUDA code is permitted only inside optimizer-cuda-sys under
[ADR-0009](docs/decisions/ADR-0009-cuda-driver-boundary.md), which amends ADR-0003's
single-boundary rule; optimizer-cuda keeps the prohibition and keeps discovery and the
lease. A device never holds mathematical authority:
[ADR-0010](docs/decisions/ADR-0010-certified-gpu-lp.md) requires every bound to come
from a host-side certification that does not assume the device computed correctly.
`optimizer-lp` holds that certification and the method, takes no device dependency, and
is the oracle the kernels are differentially checked against; `optimizer-lp-cuda`
depends on it and never the reverse. Neither is a fallback: a fallback is the pinned
HiGHS adapter, because SPEC-0010 requirement 23 requires one to be the implementation
the project already treats as authoritative.
The C8 local extension registry is implemented under SPEC-0009 and ADR-0008;
it resolves a named extension identity to an extension this build provides and
deliberately does not load dynamically distributed native components, which would
need a boundary ADR-0009 does not authorize either. The Python SDK (C9) and the
comparative experiment runner (C10) are unspecified, and
[known failures](state/known-failures.md) records each blocker along with the C8
requirements whose acceptance tests are thinner than SPEC-0009 describes. Later
SDK and comparative-runner APIs require their own specifications and
acceptance gates; do not introduce them without one.
Use Rust for runtime work; Python under tools/ is build and validation tooling,
not the SDK. Native HiGHS code is permitted only inside optimizer-highs behind its
private ownership boundary, with the pinned 1.11.0 CPU contract, and CUDA driver
calls only inside optimizer-cuda-sys. Those two crates declare their own lints
because a workspace-level unsafe prohibition cannot be relaxed per crate; every
other runtime crate keeps the prohibition, and no third boundary is authorized.

Run bash tools/check.sh for acceptance; it requires the pinned native HiGHS build.
AI_OPTIMIZER_SKIP_NATIVE=1 skips it and reports uncovered native acceptance, which
must never be recorded as a full gate pass. Discovering GPUs does not authorize a
kernel workload; all actual project GPU jobs require the shared host lock, and the
lock permits one holder across device selections, so two devices are never used at
once. nvcc is a provisioning dependency, never a build dependency: an ordinary
cargo build must keep working on a host with no toolkit and no device.
Do not change experiment seeds, thresholds, splits, or defaults silently.
Do not publish, push, or configure external hosting without authorization.
