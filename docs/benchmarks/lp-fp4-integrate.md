# Coupled FP4 integration: GPUP-FP4-INTEGRATE

GPUP-FP4-INTEGRATE is complete as a bounded research implementation and measured
negative retention result. Actual persistent FP4 iterations now produce independently
certified coupled LP endpoints at both 1e-7 and 1e-9. **They do not beat the matched
native control in complete solve latency.** Keep the supported native solver; select
no new preset and do not release TENSOR2 from this result.

Contract: [SPEC-0030](../specifications/SPEC-0030-fp4-integration.md),
[ADR-0062](../decisions/ADR-0062-fp4-coupled-integration.md), and the unchanged
[SPEC-0029 recovery policy](../specifications/SPEC-0029-fp4-recovery-policy.md).
Implementation: [research executor](../../research/lp-fp4-integrate/README.md).

## What is implemented

One CTA evolves a genuinely coupled LP of at most 128 coordinates per direction,
with cross-tile forward/transpose products, general finite/one-sided/fixed bounds,
nonzero starts, maximization and objective offsets. Packed E2M1 component state,
both operator orientations, five state vectors, scales and complete checkpoints
remain on the device. Ordinary low-precision updates use local FP32 pairs without
a full FP64 state round trip. The matched native lane traverses exact CSR/CSC
coefficients, skipping structural zeros. The bounded fixed-step PDHG controller
is separate from the production solver's adaptive native controller.

Original-A FP64 observations occur by 200 accepted updates. At most one 32-update
window is submitted. Local guards, ambiguous projections, residual growth and
stagnation trigger complete rollback and monotone 2 -> 4 -> 8 -> native recovery.
Precision conversion is transactional: a failed candidate leaves the previous
checkpoint intact for native recovery. Physical work, deadline and costs never
roll back. The first device refusal reason is sticky. Checkpoints retain packed
codes/scales, all five vectors, controller/residual state, model/operator/settings
identities and local-error history; terminal exports are recorded separately.
Generation and solve identities reject stale commands. Cancellation is terminal.

The local arithmetic terms and residual policy are operational estimates, **not a
proved global trajectory enclosure or convergence theorem**. A separate CPU process
receives only the original model and actual endpoint. It applies unchanged
feasibility, conservative bound and gap mathematics at the explicitly requested
tier. Public solver/checker defaults and infinite-bound refusal stay unchanged.

## Admission and full trajectory coverage

All final admission gates pass:

- 638 repository Rust tests plus three isolated executor tests; 636 Python tests,
  including twelve new CPU contracts; native build/lint, replay, dependency,
  artifact, documentation and smoke gates.
- Ninety actual coupled product/trajectory/rollback checks; thirteen boundary and
  prepared-lifecycle cases covering 32 and 128 coordinates, plus stale finish
  rejection; fourteen safety cases including actual failed conversion recovery.
- Memcheck, racecheck, initcheck and synccheck, each covering fifty service
  processes: **200 zero-error sanitizer reports**, with zero race warnings.
- Fresh one-shot checker replay of **176 unique final endpoints**, reproducing
  all **672 formal cells** and verifying checkpoint and cost consistency.
- All 1,557 pre-task tracked files remain exact except the four intended current
  task/navigation files. Earlier failed scientific results and charges stay exact.

The frozen diagnostic grid contains eight families, six lanes and two tiers:
**96/96 cells complete 600 physical updates**, with no retries. It records 71
certified final endpoints. Native, FP8 and each FP4 starting precision certify six
of eight families at each tier. FP16 certifies six at 1e-7 and five at 1e-9 within
this diagnostic limit. All final endpoints and intermediate observations remain
available; a diagnostic continues after observing a certificate.

The ill-scaled family and intentional infinite-bound-refusal family remain
uncertified in every lane, including native, even in the subsequent 10,000-update
solve cohort. These are explicit limits/refusals, not successful solves. The
ill-scaled result also exposes the limitation of this unpreconditioned fixed-step
research recurrence; it does not describe the production adaptive solver.

## Complete solve comparison

The separately frozen performance grid executes **576/576 cells**: eight models,
six lanes, two tiers, three repetitions, and cold/prepared lifecycles. It has
**432 certified endpoints**. Every lane certifies the same six families: 18/24
trials per tier and lifecycle. No model coverage is silently dropped.

Cold means a fresh Python controller, GPU service/context and independent checker,
timed from outside process startup through exit on the leased, already initialized
GPU. Prepared means reused CUDA context/module and CPU checker processes with
fresh per-solve numerical buffers, iterates and controller. Matrix preparation
still counts per solve. Prepared startup is separate: its median is 210.918 ms.
Sixteen such model/tier sessions each serve eighteen measured solves. Prepared
latency does not include or erase that startup; it is not a cold latency claim.

Ratios below are native time / candidate time, geometrically averaged over the
six certified model medians. Values below one mean FP4 is slower. The retention
criterion remains at least 1.10x cold geometric mean, no certified model-median
regression and no coverage loss against the same final tolerance.

| Final tier | FP4 start | Cold ratio | Descriptive 95% interval | Prepared ratio |
| --- | --- | ---: | --- | ---: |
| 1e-7 | x2 | 0.985781x | 0.957952–1.014230 | 0.703974x |
| 1e-7 | x4 | 0.972182x | 0.971725–1.001510 | 0.718188x |
| 1e-7 | x8 | 0.985770x | 0.921053–1.000264 | 0.769660x |
| 1e-9 | x2 | 0.973316x | 0.959451–1.013101 | 0.622846x |
| 1e-9 | x4 | 0.959382x | 0.959151–0.986990 | 0.684505x |
| 1e-9 | x8 | 0.971935x | 0.958172–0.999902 | 0.747146x |

All FP4 cold gates fail. All six certified model medians regress in every prepared
FP4 lane. FP8 and FP16 also fail retention. Intervals use 2,000 paired repetition
resamples within each fixed family; three trials provide limited timing uncertainty,
not evidence about unseen models or a distribution of real LPs. Full model medians,
all controls, uncertified cells and prepared intervals are in the machine results.

Pooled certified-trial median prepared latencies are 17.605 ms native versus
28.101/27.711/23.011 ms FP4 x2/x4/x8 at 1e-7; at 1e-9 they are 17.875 ms versus
32.981/30.581/26.654 ms. Pooled cold medians are approximately 566 ms for these
lanes; this pooled number hides the model regressions captured by the table.

Useful FP4 work is real. At 1e-7, all eighteen certified trials per lifecycle
starting at x2 or x4 perform **every physical numerical update in FP4**, including
rejected updates and precision promotion. At 1e-9, twelve of eighteen do so; the
other six require explicitly charged native recovery. For example, fixed/active
bounds starting at x4 use 201 x4 plus 200 x8 updates at 1e-7, and 201 x4 plus 201
x8 plus 200 native updates at 1e-9. This is neither native-only certification
masquerading as FP4 nor an FP64-equivalence claim.

## Performance work and remaining bottlenecks

The implementation removes the approximately 1.221-second first-use repository
schema construction from each solve by checking the exact CPU-admitted policy
digest. It removes unrelated legacy exports from the CUDA image, retains a
separate checker process across audits, reuses a final same-tier certificate only
for an identical endpoint, removes a redundant stream fence, and adds context
reuse with fresh solve identities. Native sparse traversal prevents a misleading
comparison against unnecessary zero multiplications. Final kernels have no spills.

A separately frozen 756-window paired development ablation tested carrying decoded
pairs across updates and skipping exactly zero encoding tails. Every packed state,
local-error report and endpoint matched, but FP4's geometric gain was only
1.005958x and x8 regressed about 3%. It failed the predeclared 1.02x selection rule;
the original numerical kernel remains, plus the sticky-refusal correctness fix.
The attempted optimization and all costs remain recorded.

The measured limitations have different causes:

- **Cold delivery dominates.** For certified x4/1e-7 trials, median GPU iteration
  time is 2.286 ms versus about 566 ms complete cold latency. Faster MMA alone has
  very little leverage on this endpoint. Process/import, context, preparation,
  transport, export and independent checking remain charged.
- **Small sparse arithmetic favors the native control.** Most rows contain only
  three nonzeros. FP4 still encodes component state, combines component products,
  projects, reduces guards and synchronizes a coupled CTA. One CTA also leaves
  most of the GPU idle. This is a workload/algorithm mapping limitation, not
  evidence of a defective Tensor instruction or GPU.
- **A kernel win is insufficient.** On dense-rich-65 at 1e-7, x4 GPU iteration
  time is about 1.34x faster than native, but prepared complete latency is
  0.920x native/candidate because added representation and delivery costs dominate.
- **Recovery adds actual work.** The ranged and active-bound models require
  promotion and, at the strict tier, native recovery. The current fixed step also
  converges poorly on the ill-scaled family. No tolerance or bound criterion was
  relaxed to conceal either cost.

Further performance work should first quantify immutable preparation reuse and
native host orchestration, and address conditioning and parallelism on genuinely
large coupled workloads. The current one-CTA, 128-coordinate domain cannot support
a claim of extreme large-LP FP4 performance. TENSOR2 still needs a new complete-cost
case and its own protocol/resources; this task does not authorize it automatically.

## Evidence, failures and accounting

- [All grids, timings and uncertainty](data/fp4-integrate-results-v1.json).
- [Endpoint archive index/checksums](data/fp4-integrate-endpoints-v1.json) and
  [self-contained original models, endpoints and certificates](data/fp4-integrate-endpoints-v1.json.gz).
- [Admission, ablation, archives and failures](data/fp4-integrate-evidence-v1.json).
- [Final accounting and cleanup](data/fp4-integrate-accounting-v1.json).

Three development failures retain their full CPU reservations: initial CUDA driver
API naming (1,200 seconds), an over-specific cross-tile fixture assertion (1,200),
and an archive postcondition comparing a rebuilt changed source with its prior
binary (720). The early binary reconstruction itself matched its recorded hash;
all numerical admission binaries now have exact immutable archives. No GPU job or
formal scientific cell failed or was retried. Failed logs/sources and the rejected
optimization remain under `artifacts/gpup-fp4-integrate-v1`.

The independent ceiling is 96,000 CPU / 14,400 GPU seconds. Final GPU charge is
**707.739821097 seconds**, including admission, every optimization attempt and
both complete cohorts. Final CPU charge is **8339.119853692 seconds**. Every reservation/settlement and cleanup
are in the linked accounting receipt. Maximum sampled host RSS across the retained jobs is 2.064 GiB. Host memory is
sampled aggregate RSS, not
hard cgroup containment; bounded device allocations stay below the 12 GiB buffer
ceiling. All retained supervisor cleanup receipts report no remaining processes.
No old allocation is reused, no old numerical source is edited, and no public
solver default changes. FP4-PROTO and GPUP-8 remain incomplete; GPUP-9 stays gated.
Delivery is committed locally without push or publication.
