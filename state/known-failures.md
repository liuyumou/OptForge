# Known Failures and Limitations

## CPU expansion reference is accepted; device and solver behavior are not implemented

GPUP-REP accepts the bounded CPU subset of SPEC-0020 under ADR-0034. The exact
input codec, correctly rounded binary64 reference and separate 64-significand-bit
expansion semantics pass an independent 32852-codec/1058-primitive rational
oracle, long reductions and bounded layout analysis. This is validation tooling,
not a runtime solver implementation or performance result.

The compact codec uses FP32 h/l, an integer tail in [-8,8] with explicit weight
and a symbolic exponent. Raw FP16 tails still underflow. Arithmetic intermediates
use the distinct 24/24/16 positional format; they do not inherit the input codec's
small-tail bound. The accepted exact accumulator needs 67 u64 magnitude limbs at
the maximum admitted dot length and is a costly CPU control, not a proposed GPU
default. GPUP-EXEC must select a smaller implementable subset, prove any bounded
window or omitted-term error, reserve device work and pass instruction/differential/sanitizer gates. Persistent expansion solver state remains untested.

SPEC-0021 refinement remains draft. Its inner-oracle/progress assumptions,
quantitative policies, interfaces and resource caps still need acceptance. Removing
mandatory final original-model certification would not meet the project's authority
contract. No preset or new GPU allowance follows, and historical gaps below remain.

## Convergence costs and incomplete FP32/mixed coverage

The [convergence report](../docs/benchmarks/lp-convergence.md) retains all 176
attempts and independently verifies 174 endpoints; 87/104 primary timings certify.
On irregular-32768, accumulation FP32 saves about 10% of the measured device host
cost per proposal in short profiles but consumes 40464 proposals without certifying
in the full profile; precision FP64 certifies after 1600. This does not establish
a certified latency benefit. Reference arithmetic, audits/probes and original-model
assessments remain material for adaptive policies. No preset or tuning follows.

Two dense-65536 accumulation-FP32 timings (repetitions one/two) time out without
endpoints; empty output and partial worker receipts remain. Every mixed-65536 primary
sample is uncertified and its single repetition has no repeatability interval.
Deliberate bounded-work profiles retain work-limit outcomes. No admitted identity
was retried; no failed sample is promoted or used in certified ratios. Full native,
regular device, fixed-work/replay and COPT min/max/profile acceptance pass. CPU-only
review repairs prevent pre-refusal activity writes, retain non-object partial JSON
and leave missing worker cost envelopes unavailable, with exact source bindings.
Historical tuned_cases racecheck, large-session, mixed-model and opaque COPT graph
gaps remain. GPUP-7 requires an accepted numerical/resource contract first.

## COPT adapter interruption recovery corrected during integration review

Self-review reproduced unbound partial artifacts after coordinator interruption.
Recovery now binds retained files and surviving worker observations, and the report
accepts the ledger's conservative full reservation charge without treating a
recovered trial as successful. CPU regressions cover partial outputs, surviving
receipts, crashes after settlement, substitution and no retry. The declared review
corrections do not alter measured workers, results, defaults or GPU accounting.

## Bulk COPT preparation outweighs native loading savings

The [adapter report](../docs/benchmarks/lp-copt-adapter.md) verifies all 84 attempts
and certifies 42/72 timings. The bulk adapter is slower in every certified cell:
dense GPU PDLP median 11.070 versus 8.983 seconds. Native loading is cheaper, but
CSC preparation (including a repeated guard scan) and cold SciPy import outweigh
the saving. This implementation is experimental; no preset follows.

All 18 CPU-default extension timings and two profiles are interrupted at the
process deadline; native work differs, so their nine timing pairs and two profile
comparisons do not establish numerical/work equivalence. All 12 mixed-65536 PDLP
timings are numerically rejected. The other 27 timing pairs and ten profile pairs
match bitwise. Twelve native readbacks, 24 certified acceptance endpoints and
full native/source-only gates pass. Initial schema-enum and readback API failures
are corrected with receipts retained. Detailed per-trial driver/thermal telemetry
was not sampled and is explicitly unavailable; native GPU identity/execution and
lease admission activity are retained. Original wrappers, records, runtime kernels,
old racecheck/session and mixed-model gaps remain. GPUP-CONVERGENCE is next.

## Fresh primary contexts do not show a consistent latency benefit

The [GPUP-SETUP report](../docs/benchmarks/lp-fresh-setup.md) verifies all 32 attempts,
certifies 24 timings and matches 16 numerical/work comparisons. Primary retain/release
still takes about 170–189 ms in these separate profiles; it does not remove fresh
context work. Three paired intervals span one; direct irregular-32768 shows a small
scoped slowdown (user/primary 0.9947, 95% interval 0.9845–0.9948). User contexts remain
the default. The experimental primary path requires an inactive context and inherited
lease, with checked cleanup and separate setup receipts. No persistent reuse or preset.

All native, regular device and four primary-scope sanitizer gates pass, along with
twelve fixed-work pairs/replays. No actual GPU attempt failed or was retried; one
initial CPU lint failure was corrected and retained. Historical mixed-65536, large
sessions and tuned_cases racecheck gaps remain open. Optional COPT adapter and
convergence diagnosis are the next separately bounded tasks.

## Adaptive host-cost results are scoped; reference arithmetic remains

The [GPUP-ADAPTIVE-COST report](../docs/benchmarks/lp-adaptive-host-cost.md)
verifies all 32 attempts, certifies 24 timings and preserves 16 numerical/work pairs.
Full ladders prepare two operators rather than five; audits stream comparisons and
probes borrow state where narrowing is unnecessary. Reference FP64 updates, sparse
probe arithmetic, checkpoints, recovery and original-model assessments remain.
Only small-4 and irregular-32768, two policies and three development repetitions
were measured. Small-4 direct regresses (paired baseline/repaired ratio 0.7652,
95% interval [0.7336, 0.8291]); its cause remains unestablished. No preset or universal speedup is selected. Mixed-65536, old large
sessions and the historical tuned_cases racecheck gap remain open; fresh setup,
optional COPT construction and convergence diagnosis are separate tasks.
The initial CPU lint and source-only fixture failures are corrected, with receipts
retained. All device attempts passed; no study identity was retried.

## GPUP-HOST scope and latency uncertainty

The [host-input report](../docs/benchmarks/lp-immutable-host-input.md) verifies all
28 attempts and certifies 24 fresh timings, but the small-4 and irregular-32768
paired intervals span one. The large-model result is scoped to three development
repetitions. No general preset follows. The repair removes one duplicate model
parse/validation; sparse construction and all candidate/certificate assessments
remain fresh. Remaining adaptive reference arithmetic, mixed-65536 timeouts, old large-session gaps
and the historical tuned_cases racecheck receipt remain unresolved.

## Compact evidence repairs output coverage; mixed-65536 remains time-limited

The [GPUP-EVIDENCE report](../docs/benchmarks/lp-compact-evidence.md) retains all 24
fresh timing attempts. Compact verifies 12/12 and certifies 9/12, including all
irregular/dense 65536 cases; legacy verifies/certifies 3/12 and retains nine 32 MiB
partial files. All three compact mixed-65536 outcomes verify as interrupted, but
the workers timed out and remain unsuccessful. No large-model paired speed ratio
is available when its legacy member failed. Historical COPT samples are unchanged.

Four CPU full-witness fixtures fit below the unchanged cap; two are explicit
synthetic codec fixtures, never solve results. No solver arithmetic/kernel,
numerical setting, preset or session behavior changed. Existing tuned_cases
racecheck, session and COPT graph limitations below remain open. The first full
CPU gate exposed an overly broad historical-schema test; it now enumerates the
old revision and still checks exact bytes/deletions. Failed and passing receipts
are retained in artifacts/gpup-evidence-acceptance.

## COPT comparison: large evidence output and opaque graph internals

The [component report](../docs/benchmarks/lp-copt-comparison.md) retains all 1140
attempts, 948 verified endpoints and 402/816 certified primary samples. At 65536
rows, the frozen 32 MiB per-file output limit truncates project endpoint writes:
148 partial endpoint files remain, 142 exactly at the cap (82 process failures
and 60 also classified timeout), plus six killed partial writes. The trace-only
512 MiB allowance does not fill primary cells. Compact versioned evidence and its
separate GPUP-EVIDENCE comparison are now complete above; no historical output
limit or result was changed post-result. Other failures include deadlines, work limits and numerical rejection.

The archived verifier initially applied the ordinary 16 MiB cap to endpoint reads
despite explicit 128 MiB study input. The final reader repairs that omission and
independently verifies all 88 retained affected endpoints, recovering 37 certified
outcomes (21 primary), without changing trials, solving again or relaxing checks.
COPT native optimality still does not replace the original-model certificate;
both PDLP modes on mixed-65536 fail that certificate at 1e-9.

All 20 CUDA captures export, but COPT graph granularity leaves internal graph
kernel counts/durations and exact busy time unavailable. Native CPU phases remain
opaque and hardware-counter/CPU-sampling restrictions remain. Offline import
initially appended telemetry to captures and failed checksum validation. Exact
pre-import SHA-256 reconstruction recovered all 20 originals, with mutated copies
and recovery evidence retained; future imports use copies. Tests reject any
reconstruction that cannot match the complete historical hash. Historical
`tuned_cases` racecheck and old large-session limitations below remain open.

## GPUP-6 comparison coverage is incomplete; no preset selected

The [adaptive report](../docs/benchmarks/lp-adaptive-gpup6.md) records the frozen
comparison and every retained failure. An initial archive omitted the unchanged
scheduling code image required by CUDA discovery, causing 288 missing-evidence
attempts before LP execution; coordinator interruption also retained partial
attempts. The image was restored with a hash-bound repair record, and only
unattempted identities resumed. No failed trial was retried or hidden. Archive
preflight now checks all four required images before admission. The earlier v5
configuration-enum preflight failed before any reservation and is also preserved.

These missing cells cannot establish a performance ranking. Work-limit and
numerical-rejection endpoints are independently verifiable but remain uncertified.
The implemented opt-in recovery policies pass host fault injection, regular
device differentials, v5 verification/replay and all four adaptive sanitizers;
no general preset follows from those correctness gates. Adaptive throughput
sessions and disk checkpoints remain out of scope. The previous 65536-row
throughput timeouts and historical tuned_cases racecheck gap below remain open.

## PR #8 clean-checkout budget test failure corrected

Both initial CPU workflows failed because the throughput budget-authority test
read the ignored local GPU campaign ledger. A checkout with retained study data
masked that dependency. The test now uses a temporary root, unchanged checked
source/decision/authority files and a valid synthetic CPU-only ledger. Real
checksum, ceiling, prefix and output-binding rejection checks remain enabled;
all three budget tests pass in a fresh source checkout with no campaign artifacts.
The frozen production pins are still checked separately. No production accounting
code or live campaign data changed. Initial CI failure and clean-checkout receipts
are retained in artifacts/gpupt-integration-20260922; final integration still
requires the complete native gate and GitHub's required checks.

## GPUP-THROUGHPUT review findings corrected

The [correction report](../docs/benchmarks/lp-throughput-corrections.md) closes
all four 2026-09-22 review findings: all tuned outcome identities are stamped;
batch verification rejects mixed method/code identities and fallback; binary64
comparisons distinguish signed zero; and 48 new ordinary fresh-variant controls
verify 360/360 retained variant comparisons. The historical N=1 controls remain
labeled as such. Existing large-model and sanitizer limitations below remain.

## GPUP-THROUGHPUT: 65536-row short batches time out; tuned_cases racecheck incomplete

The [repeated-solve report](../docs/benchmarks/lp-repeated-solve-throughput.md)
verifies 687 of 705 admitted attempts. The 18 unverified attempts are the
65536-row N=8 short batches (batch-repeat-short and batch-variant-short on
irregular-65536, dense_block-65536 and mixed-65536, research-fused-fp64): each
was stopped at its 58-second supervisor reservation with no endpoint written.
At the original study revision, irregular-32768 completes but its amortized per-solve time (6.09 s) exceeds its
fresh single-solve latency (3.95 s): sessions do not pay off at that size with
200-proposal solves, and a batch of one does not pay off anywhere (paired ratio
0.67-1.04). Every 200-proposal short block terminates at the work limit, fresh
and batched alike, so no short block claims a certificate. The pre-existing
tuned_cases filter lacks a clean racecheck receipt: the run exceeded its
90-second reservation after study_observation and matched_control passed with
zero hazards, and the frozen 600-second acceptance cap (then 61.6 seconds left) could
not fit a rerun. The SPEC-0014 session_ scope passed all four sanitizers
including racecheck, and tuned_cases passed the other three; the partial
receipts are retained. Reproduce with benchmarks/configs/lp-throughput-v1.json
and the archived measured executables.

The subsequent [host-input repair](../docs/benchmarks/lp-throughput-host-input.md)
reduces the two scoped 32768-row N=8 batch process times to 10.746 s (repeat)
and 22.484 s (bounds variants), with all 16 results bitwise identical and both
old/new independent verifiers passing. These one-repetition diagnostics do not
rerun 65536-row coverage or establish a current paired single-vs-batch speedup;
the historical timeouts and tuned_cases racecheck gap remain open.

## Consumer Blackwell runs FP64, double compares and 64-bit conversions at 1/64 rate

The [root-cause note](../docs/benchmarks/lp-fp64-pipe-root-cause.md) shows that every
scheme recombining FP32 partials in FP64 is bound by the sm_120 FP64 pipe, that the
guarded research FP64 control is 2.4x slower than tuned for the same reason, and
that the twelve development instances are launch-bound. Hardware counters remain
unavailable (`ERR_NVGPUCTRPERM` even as root), so pipe attribution rests on static
instruction counts plus timing. GPUP-5C addresses the removable costs under
[ADR-0022](../docs/decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md);
context creation (about 208 ms per solve) remains outside every arithmetic change.
Do not extrapolate dense Tensor Core or data-center FP64 throughput to this host.

## GPUP-5C: double-float underflows on scheduling LPs; large instances are host-bound and CLI-refused

The [GPUP-5C report](../docs/benchmarks/lp-fp64-pipe-gpup5c.md) verifies 806 of 850
admitted attempts; 24 planned attempts are missing because the 1500-second study cap
was reached, and 44 admitted attempts have no endpoint (34 CLI refusals of inputs
above the SPEC-0005 16 MiB bound, 10 research 30-second timeouts on mixed-65536).
`doublefloat-fp32` certifies 24/36 at 1e-9 and 27/36 at 1e-6 and 1e-4: its losses are
strict nonzero-to-zero product guards on scheduling-20x5 (1e-9 only), scheduling-50x10,
ta001, ta011 and mixed-65536, where FP32 products of decaying iterates fall below
the binary32 normal range. Do not weaken that guard; a block-exponent or per-vector
scale is the prerequisite. Fused FP64 is slower than integer-guarded separate FP64
on 32768-65536-row instances because its per-block update warp serializes eight
rows' vector arithmetic. On those instances preconditioning and research preparation
cost about one second each, dwarfing kernel time; the CLI cannot read them at all.
Tolerance tiers 1e-6/1e-4 recover FP32 storage coverage to 24/36 and 30/36 but do
not change certified latency materially. Reproduce with
benchmarks/configs/lp-research-v2.json and the archived measured executables.

## GPUP-5B exact representations recover coverage but component arithmetic is slower

The [840-attempt research study](../docs/benchmarks/lp-exact-components-gpup5b.md)
restores 27/36 certified timings with exact power-of-two/factored FP32 storage
and with two/three-component products, versus 12/36 for ordinary scaled FP32
storage. Existing runtime behavior and old failures remain unchanged. All new
modes still exhaust work on scheduling-50x10, ta001 and ta011. Power-of-two scaling
increases proposals on four development instances and its current extra host
preparation costs time. Three-component cross-products take 2.69x/2.67x the native
research update time on irregular-2048/dense_block-1024 and increase certified
solve latency by 10.4%/13.8%. Exact representation is not an acceleration result.
Two-component truncation works at these targets on this corpus; no universal
accuracy guarantee or supported preset follows.

The isolated prototype splits vectors per nonzero, stores per-coefficient exponents,
and performs many FP64 compensated additions to recombine FP32 product/error pairs.
Packing and metadata add storage/transfers; all are charged. Matched reconstruction
controls and traces separate these costs from convergence. Hardware counters remain
unavailable; no bandwidth/occupancy explanation is asserted. Raw traces initially
need offline import with the existing isolated libdw; all 24 decode and match
1200 launches without rerunning GPU work. No missing endpoint, numerical failure,
timeout or fallback occurred among these 840 attempts. All old artifacts and the
3288-event prefix are unchanged. See the preserved
[rounding note](../docs/benchmarks/lp-fp32-rounding-analysis.md) and
[candidates](../docs/plans/lp-precision-candidates.md). GPUP-6 requires its own
bounded adaptive contract; no recovery or guard relaxation is implicit here.

## GPUP-5 FP32 coverage loss and external-control limits

The [verified GPUP-5 study](../docs/benchmarks/lp-fp32-gpup5.md) retains all 480
attempts. Matched/tuned/precision FP64 certify 27/36 timings; FP32 storage,
products, accumulation and fixed master correction certify 12/36, and FP32 working
state 6/36. Storage-only modes exhaust work; product modes stop on guarded
nonzero-to-zero product loss. Fixed correction every 32 steps does not restore
coverage and can substantially increase transfers and host work. Reproduce with
benchmarks/configs/lp-precision-v4.json and the archived measured source. Next:
GPUP-6 must specify adaptive audits/recovery before changing numerical behavior;
do not weaken guards, tolerances or work limits to hide these outcomes.

The [bounded follow-up diagnosis](../docs/benchmarks/lp-fp32-slowdown-diagnosis.md)
retains 196 equal-work short runs, 14 decoded CUDA traces and three unsuccessful
hardware-counter attempts. FP32 iterations are similar or sometimes faster than
the precision FP64 control, but the failed large cases do 22–31 times as many
proposals. Exact rational row activities identify scaled-matrix bias above original
allowances; this does not explain every nonconverged model. Generic guarded kernels,
six launches/update, frequent state readbacks and host correction add costs. Hardware
counters are unavailable (ERR_NVGPUCTRPERM); cache/bandwidth/occupancy attribution is
unresolved. Saved traces decoded offline with the existing isolated libdw dependency.
No solver behavior or guard changed. Historical reporting now accepts an intact,
settled archived ledger prefix so later diagnostics cannot change GPUP-5's totals.

COPT 8.0.6 CPU/GPU PDLP certify 27/36 and 24/36 timings. Scaling-256 remains
feasible but unclosed; GPU ta001 witnesses are rejected by original-model checks.
Its public API exposes neither a PDLP iteration-limit nor a seed control: record
observed counts above 50000 as work_limit and enforce the common process deadline.
Input coefficients at or below its nonzero 1e-10 threshold are refused rather than
silently dropped; all frozen study coefficients exceed it. Native status and a
requested GPUMode never establish host certification or actual GPU execution.
Isolated setup phase timing is unavailable; native rounded solve time and combined
setup/export/validation/startup overhead are recorded separately. COPT remains
optional study tooling. Presolve-only or CPU fallback is not a GPU success.

HiGHS scaling-256 run errors and irregular-2048 timeouts remain in this study, as
do host time/work limits. Preflight callback/log-parser failures are retained in
the separate acceptance ledger. All six precision cases pass all four sanitizers
on the original measurement GPU; GPUP-4's historical device limitation stays below.

## GPUP-4 launch setup failure, correction and remaining limits

The first 320-attempt round lost 24 matched-reference timing endpoints because an
archived executable was copied without execute permission. Its bytes were intact;
permission repair enabled subsequent attempts. All failed attempts and charges
remain. ADR-0018 preserves that interim round and freezes one separate complete
correction, with identical numerical settings/seeds/order/device and no new GPU
allowance. All 320 correction attempts have verified evidence: 248 certified,
66 work-limited, six host timeouts. Each configuration certifies 27/36 timings.

Both rounds charge 456.586499157 additional GPU seconds; canonical campaign total
902.574545061. The original 622-event prefix, authority and output binding remain.
Executable preflight, mode-preserving copies and prior-prefix verification prevent
silent recurrence or ledger reset. A final schema regression also caught and fixed
object-wrapped execution enum names; string-only parsing now matches the schema.

The [reviewed report](../docs/benchmarks/lp-tuned-fp64-gpup4.md) retains negative
ablation results and unchanged scheduling convergence failures. Transfer savings
do not consistently improve latency; context startup remains substantial. Matched
FP64 stays the general reference, with fused-warp provisional only on the three
named development instances. Three repeats, unadjusted intervals and no held-out
measurement do not support a universal preset. Final parser validation was repaired
after measurement; the report identifies the exact measured source/executable.

## GPUP-4 sanitizer device differs from the frozen measurement device

Acceptance on 2026-09-15: all 41 regular device cases pass on the selected RTX 5090.
Memcheck failed to allocate instrumentation while it reported 31314 MiB used and
797 MiB free, with no process visible from this workspace. The documented
force-synchronization-limit 8 retry also failed. Both failed attempts are retained.

The separate acceptance budget then used an idle sm_120 RTX PRO 6000 Blackwell
GPU-6721b13a-30f9-83ec-dace-ba2d9738556f, under the same shared host lease. All 41
regular cases and eight scoped cases under each of memcheck/racecheck/initcheck/
synccheck passed; zero errors and zero racecheck warnings. CLI evidence, fallback
and replay also passed. This is sanitizer coverage on the named compatible device,
not a claim that the memory-constrained RTX 5090 sanitizer run passed. Measurement
remains on the frozen RTX 5090 UUID. Evidence: artifacts/gpup4-acceptance.

## LP certification can lose the roundoff allowance at zero reduced cost

Resolved by GPUP-1 on 2026-09-14. Discovered during the GPU LP precision design
review and preserved by GPUP-0, this affected the shared host certification used
by both host-lp and cuda-lp, independently of future quantization. The original
counterexample below is retained for reproduction against the previous revision.

The previous variable loop in `crates/optimizer-lp/src/certify.rs` used bound zero
when a computed reduced cost rounded to zero, then multiplied the reduced-cost
error allowance by that chosen bound. The reduced cost can be nonzero in exact arithmetic
over the stored binary64 coefficients, so the required allowance is lost.

Reproducer (continuous variables, equality constraint):

```text
minimize 0.1*x1 + 0.30000000000000004*x2
subject to x1 + 3*x2 = 0
-3e16 <= x1 <= 3e16
-1e16 <= x2 <= 1e16
dual multiplier y = [0.1]
feasible candidate x = [3e16, -1e16]
```

The pre-repair built-library diagnostic returned bound 0 with allowance 0. The
candidate passes the existing feasibility check; ordinary FP64 objective evaluation
reports -0.5. Exact rational evaluation of the *stored binary64* coefficients at
that candidate is `-152587890625/549755813888`, approximately
-0.27755575615628914. Thus zero is an invalid lower bound even for a finite boxed
model; the ordinary objective's -0.5 also illustrates why objective/gap arithmetic
needs review. These values are a correctness counterexample, not timing evidence.

Resolution: [GPUP-1](../docs/plans/gpu-lp-precision-roadmap.md#implementation-slices)
replaces the scalar allowance estimate with finite outward enclosures for every
product, reduction, reduced cost, bound contribution, and final sum. Uncertain
signs use both variable-bound sides; an unusable infinite side yields no finite
certificate. Exact zero remains usable even for a free variable. Both backends
share an outward objective/gap check with the correct maximization direction and
finite conservative tolerance arithmetic. The reported objective and the existing
feasibility tolerance policy are unchanged.

Evidence is in [active task](active-task.md). The original cancellation and free
variable cases failed before the repair. Independent rational fixtures and the full
native CPU gate cover the numerical contract. Integration acceptance added all
regular device suites; full memcheck, initcheck, and synccheck for all three suites;
full racecheck for CUDA/scheduling; and 11 LP racecheck cases, all with zero errors.
The long publication case completed in an earlier partial racecheck run. The broad
run was subsequently stopped during the existing atomic-reduction negative-control
stress case. That stress case remains an explicit sanitizer coverage limit accepted
in the integration review for unchanged kernels; the full broad gate is not claimed
as passed. The original RTX 5090 scoped sanitizer evidence remains valid. No GPU
kernel or experimental precision mode changed.

Remaining limit: outward enclosures can be wider than necessary because they lose
correlations. A finite boxed model may refuse certification after intermediate
overflow, and uncertainty can prevent certification on an infinite side even when
the exact reduced cost is zero. This is a conservative refusal, not a proof that
the LP is unbounded. Feasibility and the objective field remain tolerance-based
binary64 computations, not exact-rational primal certificates. See
[the numerical argument](../docs/architecture/lp-certification.md).

## GPU LP precision experiments and recipes are not implemented

GPUP-2 now implements the bounded LP-only harness under accepted SPEC-0013 and
frozen ADR-0014. The [development baseline](../docs/benchmarks/lp-baseline-gpup2.md)
records 144 trials and 173.148261443 GPU seconds. Existing CUDA FP64 certified only
the two small witness instances at the selected targets; host LP certified nine
instances and HiGHS ten. Larger GPU cases reached work/time limits, HiGHS failed
scaling-256 and timed out on irregular-2048, and host LP timed out on three
scheduling cases. These unsuccessful outcomes are preserved evidence, not
infrastructure gate failures or permission to weaken numerical targets.

GPUP-5 implements precision settings and bounded FP32 comparisons under accepted
SPEC-0012/0013 and ADR-0019. cuda-lp-quantized, adaptive recovery, lower-width
quantization and supported recipes remain unavailable. Opt-in cuda-lp-matched shares
host control. Legacy cuda-lp retains fixed control. The
[matched study](../docs/benchmarks/lp-matched-fp64-gpup3.md) certified 27/36 timing
trials for both matched CUDA and host, versus 6/36 for legacy CUDA. Scheduling-50x10,
ta001 and ta011 remain uncertified at 50,000 matched iterations; no finite gap is
claimed for them. Small cases remain slower on GPU because setup dominates.
Certified per-instance paired timings establish bounded development evidence only.
The independent exact-rational certification regressions remain authoritative.
The section heading retains its earlier link identity; the missing experiments
here are later precision/recovery comparisons and recipe selection; GPUP-5
FP32 comparisons are now implemented and measured.

Follow [the backlog](backlog.yaml) one slice at a time, preserving the study ledger
and all failures. Validation and held-out models were generated/hash-checked only;
existing Taillard observations remain development diagnostics. Later campaign
migrations must carry forward consumption within the unchanged eight GPU-hour cap.
The general C10 runner remains unspecified. Repeated-solve throughput and full MILP
performance need separate specifications and budgets. No implementation failure
has been accepted as a waived gate.

## GPU LP latency and harness overhead are measured limitations

The [follow-up diagnosis](../docs/benchmarks/lp-gpu-slowdown-diagnosis.md) reproduced
the GPU's slow convergence bit-for-bit on the host for irregular-256 and scaling-64.
The fixed GPU controller differs from the adaptive host controller. Repeated host
certification consumed 7.369 of 9.276 seconds on irregular-2048; its padded
1,024-entry reductions perform extensive work on short sparse columns. Small
fresh-process solves are dominated by device startup. Transfers were a minor cost
on the measured instances; the kernel source's idealized bandwidth argument does
not account for padded work and is not a measured bottleneck classification.

The ADR-0016 tooling follow-up now compiles one strict immutable schema snapshot
per process and waits for quiet telemetry with bounded post-lease admission.
CPU simulations, full pinned-native gate and the supplementary study pass. One
invocation completed all 160 attempts, with 55.606 seconds of pre-reservation
activity waiting. The same-catalog ledger validation falls from 166.575 ms including
a fresh snapshot to 0.067 ms with reuse; large document validation remains a cost.
The bit-preserving certifier cuts irregular-2048 certificate cost from 26.455 to
2.198 ms, with independent rational and padded-oracle regressions preserved.
Historical diagnosis: Python validator construction
rechecked all schemas for every event/result; ledger
replay and report generation repeat that overhead. The activity guard can pause
on a recent utilization sample from the project's own completed job. Four
supplementary invocations paused and resumed without repeated trials. Proposed
fixes preserved schema strictness, shared-lease exclusion and host numerical
authority. GPUP-3 is complete; GPUP-4 is next. The original diagnosis changed no
solver behavior. Supplementary study spending is 251.845179881 GPU seconds, bringing
the canonical cumulative ledger to 445.988045904 seconds. Original records remain
unchanged. Endpoint-v2 controller-phase schema omission was caught in acceptance,
fixed with a CPU regression and verified by the affected leased CLI rerun; no
required check is waived.

Seven supplementary jobs added 20.994604580 GPU seconds, including profiler export
failures. Cumulative campaign use is 194.142866023 seconds. Raw traces were recovered
offline using a privately extracted importer dependency; all seven endpoints and
both 1,200-launch trace counts verified. CPU call-stack sampling and GPU
bandwidth/occupancy counters were unavailable or not collected, respectively.

## Legacy HiGHS LP best_bound is not independent certificate evidence

GPUP-2 endpoint checks observed the existing adapter reporting best_bound 0 for
examples/lp-model-v1.json while its validated minimum objective is -3.5. The
adapter reads mip_dual_bound even for an LP; the pinned library can return a
finite MIP-only default, preventing the adapter's objective fallback. This field
must not be treated as a conservative LP certificate. The owned executive already
uses the objective of an optimal relaxation rather than this field.

Reproduce with optimizer solve --backend highs on examples/lp-model-v1.json and
examples/solve-config-v1.json. With --lp-evidence, the new independent endpoint
certifies -3.5 from native row multipliers; it never uses the legacy best_bound or
native optimal status as certificate evidence. Both objective senses are tested.
Existing solve-record meanings and runtime defaults are preserved in GPUP-2.
A separate bounded adapter-contract repair should address the legacy LP field;
this does not block the independently certified LP study endpoint.

## Source planning references

The preserved ai-native-optimizer-plan.md references optimizer-survey.md and
llm-or-survey.md from another session; neither is present. Reproduction:
inspect its Background links. Next diagnostic step: recover those source surveys
if research work needs them. The maintained documentation book excludes the two
original planning inputs from recursive link validation.

## LP integration CI fixtures

On 2026-09-16, post-merge CPU CI run 35041476887 correctly timed out the
coordinator-loss fixture but recorded 1.340948131 leased seconds against its
one-second assertion. That assertion imposed a second wall-clock ceiling on
teardown and durable output, independent of the requested 0.1-second solve and
cleanup limits. The fixture now retains its existing three-second completion wait
and checks timeout signal timing, terminated child status, lease coverage of full
elapsed work and nonblocking lease reacquisition. Production supervision, study
limits, charged overruns and all GPU behavior are unchanged. The failed hosted log
is retained in artifacts/gpup4-pr-integration/main-ci-failure.log.

Resolved during GPUP-2/3 PR review on 2026-09-15. The new archived-schema regression
needs the e415918 Git tree, so CPU CI now fetches full history. A fresh native gate
also exposed a startup-dependent lease test: its 150 ms parent sleep included
worker imports, leaving only 40.380 ms of actual queue wait against a 50 ms check.
The test now waits until the worker opens the lock, then measures held-lease delay
and asserts no solve output opens before release. Ten consecutive targeted runs and
a full pinned-native gate pass. Production lock and supervisor code did not change.

## External configuration

The origin remote is https://github.com/liuyumou/OptForge.git. Main protection is
configured and verified as of 2026-09-16 under the active
[Protect main ruleset](https://github.com/liuyumou/OptForge/rules/23515452): required
PRs, up-to-date GitHub Actions cpu/docs/smoke checks, resolved conversations, no
force pushes or deletion, and no bypass actors. Human approval is not mandatory.
See [release operations](../docs/operations/release.md#protected-main). Labeled GPU
runner provisioning and artifact retention remain separate hosting administration.

Publication state (verified 2026-09-15): GPUP-2/3, the baseline diagnosis and the
CI/test review fixes are published and merged in
[PR #2](https://github.com/liuyumou/OptForge/pull/2), merge commit 3c8d1ff.
All six hosted CPU/docs/smoke runs passed for reviewed head faf4a90. The author's
self-review is recorded on the PR. Original implementation/reference commits are
preserved; local main was synchronized and both completed branch copies deleted
after ancestry verification. The maintainer authorized these operations; no
hosting/protection change or additional GPU study work occurred.

Publication state (verified 2026-09-14): GPUP-0/1 and the CI cache correction are
published and merged in [PR #1](https://github.com/liuyumou/OptForge/pull/1), merge
commit `2c84a95`. The original slice commits are retained on main, local main was
synchronized, and both completed local branches and the published feature branch
were removed after ancestry verification. Earlier local-only publication statements
remain historical records. The maintainer explicitly authorized publication,
self-review, merge, and cleanup; AGENTS.md's authorization rule is unchanged.
See [active task](active-task.md) for acceptance, CI, review, and cleanup evidence.

## No dispatch threshold is committed, for either specification

SPEC-0010 requirement 22 and SPEC-0011 requirements 18 and 19 ask the same thing of
two different decisions, and neither is answered by a committed number.

The crossover is recorded below and no default reads it. Dispatch is the caller's
explicit `device` field, or for a backend the explicit `--backend` flag: there is no
threshold anywhere that compares a model against a measurement and chooses. "CPU
remains the default below the measured crossover" therefore holds because CPU is the
default everywhere, not because anything measured.

For SPEC-0011 the position is the same and the mechanism is even simpler: there is no
threshold document, no `Default` for one, and no code path that could promote a solve
to another backend. The pinned CPU backend is what runs when nothing is named.

That is deliberate rather than outstanding work. A dispatch threshold is an
acceptance-shaped number -- it decides what runs where, on evidence from one host --
and the benchmark protocol requires an ADR and an experiment record before a
threshold like that is committed. Recording the measurement and leaving the choice
to the caller is the honest intermediate state.

Reproduction: `grep -rn "crossover" crates/` finds only comments, and
`optimizer solve` with no `--backend` reaches `highs`, asserted positively by
`the_default_configuration_reaches_the_pinned_backend`. Next step: an ADR proposing
a threshold, with the held-out evidence Stage 4 asks for rather than the single-host
diagnostic recorded here. One ADR can cover both decisions or they can be split;
what neither may do is commit a number without that evidence.

## A fallback cannot be verified field for field

SPEC-0011 requirement 20 requires an availability failure to fall back to the CPU
backend and produce "the same conclusion". That is satisfiable for the conclusion and
is not satisfiable for the record. A fallback writes a record naming `highs` where the
caller asked for `cuda-lp`, so `backend`, `backend_version` and `lp_settings` all
differ, and `optimizer verify` compares those fields.

So a run that fell back is reproducible only in the sense that re-running it reaches
the same answer, not in the sense that its record matches one from a run that did not
fall back. `an_availability_failure_falls_back_to_the_pinned_backend` asserts the
conclusion and asserts explicitly that the two records name different backends, rather
than asserting an agreement that does not hold.

The related entry above -- verification assuming an unchanged native library -- is the
same shape of limit arriving from a different direction.

Reproduction: point `CudaLpBackend::open_with_code_object` at an absent code object and
compare the record it writes with the pinned backend's. Next step: none proposed. A
record that recorded "asked for A, ran on B" would make the divergence describable, but
that is a SPEC-0005 change and needs its own contract.

## A device that cannot be opened is refused, not fallen back from

The two rules meet here and the boundary between them is a choice this implementation
made rather than one either specification states outright. A device that cannot be
*opened* -- absent, hidden by `CUDA_VISIBLE_DEVICES`, or not leased -- is a refusal,
because SPEC-0010 requirement 3 forbids a record claiming a device the run did not use
and the C6 device work already established that a GPU-naming configuration is refused
rather than silently run on the CPU. A device that opens and then cannot do the work --
no code object, not enough memory -- is an availability failure and falls back under
requirement 20.

Both are defensible and they are not the same rule. A caller who mistypes a UUID gets
an error; a caller on a correctly named device with an unprovisioned code object gets a
CPU answer and a diagnostic. That difference is worth knowing before relying on either.

Reproduction: `optimizer solve --backend cuda-lp --device GPU-does-not-exist` versus
the same command with `AI_OPTIMIZER_CUDA_DIR` pointed at an empty directory. Next step:
none proposed; if the distinction proves confusing in use it belongs in SPEC-0011's
Errors and Recovery section rather than in code.

## Tolerances are reused as an optimality-gap policy

SPEC-0011 requirement 14 closes `Optimal` when a certified bound and a validated
candidate agree "within the caller's tolerances", and the only tolerances a caller
supplies are `absolute`, `relative` and `integrality` on the solve configuration. Those
are documented as a *feasibility* policy: they decide whether a candidate satisfies the
model. Using them as a duality-gap policy overloads them.

The practical consequence is that a caller who wants a strict feasibility check and a
loose optimality gap, or the reverse, cannot express it. Nothing is wrong today because
both uses want small numbers, and a gap field cannot be added without changing
`solve-config-v1`, which SPEC-0011 deliberately leaves at version 1.

Reproduction: read `assess` in `crates/optimizer-lp/src/backend.rs` against
`Tolerances`'s documentation in `crates/optimizer-core/src/evaluate.rs`. Next step: a
gap tolerance on the solve configuration, which is a schema change with the cascade
into `search-config-v3` that SPEC-0011's Compatibility section avoided.

## CPU/GPU bitwise identity is this project's property, not the contract's

SPEC-0011 requirement 8 asks only that a result be bitwise reproducible on a fixed
device and code object. The device suite asserts something stronger: that the device's
iterates equal the host engine's bit for bit. That is deliberate -- a tolerance on an
iterative method is nearly untestable, since one loose enough to pass at iteration ten
thousand hides a real defect at iteration ten -- but it is not contractual.

It holds because `-fmad=false` removes the device's only contraction, because Rust
never contracts, and because `log`, `exp` and `sqrt` are computed host-side and passed
in as scalars. A toolchain that broke any of those would break the assertion without
breaking the specification.

Reproduction: rebuild `lp_pdhg.cubin` without `-fmad=false` and run
`the_device_iterates_match_the_host_engine_bitwise`. Next step, if it ever breaks:
record which operation diverged and narrow the assertion to that operation, rather than
widening everything to a tolerance and losing the instrument.

## The LP device suite does not run in CI either

The entry above about device acceptance applies unchanged to the three device suites,
not two. `tools/gpu_check.sh` now runs `optimizer-cuda`, `optimizer-schedule-examples`
and `optimizer-lp-cuda`, and sanitizes all three under each of the four tools, but the
labeled GPU runner is still unprovisioned. Every result recorded for SPEC-0011's device
half is a local run on one host.

Reproduction: `.github/` contains no device job. Next step: unchanged -- provision a
labeled runner, or keep recording device evidence as local.

## A weak certified bound will have two causes

SPEC-0011's open question is whether a certified bound is ever strong enough to prune
usefully. On this project's own models that question cannot be answered cleanly yet,
because the flow-shop encoding's linear relaxation is already weak before any method
touches it -- which the entry on that encoding records.

So a weak bound on an encoded scheduling instance has two candidate explanations, the
relaxation and the certification, and attributing it to either without an instance
family whose relaxation is known to be tight would be wrong.

Reproduction: none needed; it follows from the two contracts. Next step: if the
question is pursued, measure on instances whose relaxation quality is known
independently, not on the frozen scheduling subset.

## Rebuilding a poisoned context is not implemented

Requirement 29 permits two responses to a sticky fault: destroy and rebuild the
context, or fall back for the remainder of the run. This implementation takes the
second. A residency that observes a sticky driver status marks itself poisoned and
refuses every later call without touching the device, and the device producer's
sweeps go to the host from then on.

The consequence is that one sticky fault costs a run its device even if the fault
was transient. Rebuilding would need the residency to replace a context its buffers
hold through an `Rc`, which is a lifetime problem rather than a driver one, and the
specification does not require it. Reproduction: there is no test that faults a real
device, because provoking a genuine sticky fault means corrupting one, so the
poisoning path is covered by unit tests over `DriverStatus::is_sticky` and
`DeviceError::poisons_context` rather than end to end. That gap is the honest one to
record: the decision logic is tested, the recovery from a real fault is not.

## Resolved: device sanitizer coverage runs and is clean

`bash tools/gpu_check.sh`, run under `tools/gpu_job.sh`, executes the device suite
and then all four `compute-sanitizer` tools over it. On 2026-09-13 on an RTX 5090:
memcheck 0 errors, racecheck 0 hazards, initcheck 0 errors, synccheck 0 errors.

This mattered more than a formality. The kernels are hand-written and index shared
memory from computed offsets, and the neighborhood kernel has two threads writing
disjoint halves of one dynamically sized array while 254 others wait on a barrier --
which is precisely the shape racecheck exists to find and precisely the shape a
reviewer cannot check by reading.

The script refuses to run without an inherited lease rather than taking one itself,
so it cannot be invoked outside the wrapper that names a single device. It is
deliberately not part of `tools/check.sh`: that gate is CPU-only and must stay so,
because almost every task record in this project states a "CPU only, no GPU
workloads" budget that a kernel-running gate would make false.

What is still uncovered: the C1 native-library sanitizer gap below is unrelated and
unchanged, and none of this has run in CI, because the labeled runner is not
provisioned. A local run is recorded as a local run.

## Device acceptance does not run in CI

The device suite is opt-in behind `AI_OPTIMIZER_GPU=1` so the ordinary gate stays
CPU-only and no task record's "CPU only, no GPU workloads" budget is made false by
it. The consequence is that device evidence exists only where someone ran it by
hand: the labeled GPU runner is still not provisioned, so no device test has ever
run in CI. Evidence recorded from a local run is recorded as such and must not be
read as a CI pass.

## Deferred hardware evidence

HiGHS differential tests are implemented and passing under C1; see
[active task](active-task.md). No solver performance or hardware claim is made, and
the crossover recorded below is a development diagnostic on one host rather than a
benchmark result.

## The device loses below roughly fifty jobs, and context creation dominates

The first crossover measurement, recorded here because both of its findings are
inconvenient and would be easy to leave out.

Measured on one RTX 5090, compute capability 12.0, 170 multiprocessors, release
build, best of three after a warmup, over the ADR-0011 scale split. The workload is
one full insertion neighborhood: for every job, the cost and position of its best
reinsertion. The CPU column is the tuned `insertion_neighborhood`; "resident" is the
device with the instance already uploaded and the context already created; "with
setup" is end to end from nothing, which is what the benchmark protocol requires be
reported and which no kernel-only number may replace.

| instance | shape | cpu tuned | device resident | device with setup | ratio |
| --- | --- | --- | --- | --- | --- |
| ta001 | 20x5 | 0.010 ms | 0.041 ms | 151.6 ms | 0.25x |
| ta011 | 20x10 | 0.019 ms | 0.043 ms | 151.7 ms | 0.45x |
| ta021 | 20x20 | 0.037 ms | 0.054 ms | 148.4 ms | 0.69x |
| ta031 | 50x5 | 0.063 ms | 0.054 ms | 143.9 ms | 1.17x |
| ta041 | 50x10 | 0.122 ms | 0.074 ms | 163.4 ms | 1.64x |
| ta051 | 50x20 | 0.230 ms | 0.087 ms | 162.3 ms | 2.63x |
| ta061 | 100x5 | 0.250 ms | 0.079 ms | 148.2 ms | 3.19x |
| ta071 | 100x10 | 0.478 ms | 0.095 ms | 147.1 ms | 5.03x |
| ta081 | 100x20 | 0.916 ms | 0.134 ms | 149.9 ms | 6.85x |
| ta091 | 200x10 | 1.898 ms | 0.159 ms | 146.8 ms | 11.97x |
| ta101 | 200x20 | 3.749 ms | 0.232 ms | 147.0 ms | 16.15x |
| ta111 | 500x20 | 23.868 ms | 2.507 ms | 148.7 ms | 9.52x |

The device loses at twenty jobs, by a factor of four. That row is the reason the
measurement is believable: SPEC-0010's acceptance list states it as the expected
outcome, and a report winning everywhere would have been evidence that transfers
were excluded. The crossover sits at roughly fifty jobs on this hardware, and
requirement 22 makes the CPU the default below it.

Context creation costs about 148 milliseconds and dwarfs every other number in the
table, including the largest CPU time. A device is therefore worth reaching only
when the context is amortized across many calls, which is requirement 16's residency
rule arriving as a measurement rather than as a design preference. Nothing in the
project currently amortizes it, because nothing dispatches to a device outside a
test.

The ratio peaks at 200 jobs and then falls, from 16.15x to 9.52x. That is not noise
and the cause is known: the head and tail tables are 80,000 bytes at 500 jobs by 20
machines, so only one block is resident per multiprocessor, and the per-block
recurrence is built by two threads while the other 254 wait. The kernel comment says
so and names the fix -- a max-plus scan across machines per step -- which is
deliberately not done, because correctness came first and an unmeasured optimization
would have had nothing to be measured against. The falling tail is what makes the
table worth keeping: a sweep that stopped at 200 jobs would have reported a
monotonic trend that does not hold.

These numbers are a development diagnostic on one host. They are not a benchmark
result, not evidence, and not a claim about the engine, and SPEC-0010 requirement 36
forbids reading the crossover as evidence that device execution improves a search.

## A device fault is outside every containment claim this project makes

The C3 extension host contains panics. A device fault is not a panic: an illegal
memory access in a kernel poisons the context, and a driver-level fault can end the
process. ADR-0009 records this as a cost of the boundary rather than solving it, and
SPEC-0010's security section states it rather than implying containment. A
device-backed extension therefore cannot be contained the way a CPU extension is, and
no per-device memory budget is enforced. Next step: the same process-isolated workers
the panic-only entry below already names, which would cover both cases and needs its
own decision record.

## Resolved: the flow-shop heuristics are a tuned baseline

`neh` and `insertion` evaluated each candidate insertion position by cloning the
sequence and re-running the whole recurrence, which is `Theta(n^3 m)` where
Taillard's exact head and tail acceleration is `Theta(n^2 m)`. That was the right
choice for C5, which claims correctness and forbids a performance claim, and it
became a problem only because Stage 4's entry condition requires baselines be tuned
before any intervention is measured: a device speedup over the naive pass would have
measured the pass.

The acceleration is implemented in
[the recurrence module](../crates/optimizer-schedule/src/evaluate.rs) rather than in
the heuristics, so requirement 8's rule that nothing proposing a schedule owns a
second definition of its cost still holds. The returned permutations are unchanged
and that is asserted by `accelerated_scoring_returns_the_naive_permutations`, which
compares against the pre-change algorithm scored by the independent oracle and
requires the same sequence rather than the same makespan. The weaker assertion would
have passed a real break: requirement 17 fixes which of several tied permutations a
caller receives, and two different permutations can tie.

The test was confirmed able to fail. Relaxing the insertion tie-break from strictly
less to less-or-equal — the exact mistake the acceleration invites, because the
rewrite moves that comparison — fails it, while
`construction_is_deterministic_including_under_ties` still passes, since a
deterministic wrong answer is still deterministic.

Measured on the development host, release build, best of three after a warmup, over
the whole ADR-0011 scale split, with a 0.19% noise floor from an identical binary:

| instance | shape | construction | improvement pass |
| --- | --- | --- | --- |
| ta001 | 20x5 | 0.18 ms to 0.03 ms | 0.16 ms to 0.04 ms |
| ta011 | 20x10 | 0.07 ms to 0.01 ms | 0.16 ms to 0.02 ms |
| ta021 | 20x20 | 0.12 ms to 0.02 ms | 0.31 ms to 0.04 ms |
| ta031 | 50x5 | 0.33 ms to 0.04 ms | 0.84 ms to 0.06 ms |
| ta041 | 50x10 | 0.64 ms to 0.07 ms | 1.70 ms to 0.12 ms |
| ta051 | 50x20 | 1.52 ms to 0.13 ms | 4.23 ms to 0.23 ms |
| ta061 | 100x5 | 2.29 ms to 0.13 ms | 6.26 ms to 0.25 ms |
| ta071 | 100x10 | 4.67 ms to 0.25 ms | 13.24 ms to 0.47 ms |
| ta081 | 100x20 | 11.26 ms to 0.48 ms | 32.49 ms to 0.92 ms |
| ta091 | 200x10 | 34.33 ms to 0.97 ms | 99.13 ms to 1.89 ms |
| ta101 | 200x20 | 87.05 ms to 1.89 ms | 257.39 ms to 3.75 ms |
| ta111 | 500x20 | naive not run; 11.98 ms | naive not run; 23.86 ms |

The improvement pass speeds up by roughly 4x at twenty jobs and roughly 69x at two
hundred, and the ratio tracks the job count rather than the machine count: ta061 and
ta091 differ only in jobs and their ratios differ by a factor of two, while ta061 and
ta081 differ mostly in machines and their ratios are much closer. That is what an
`O(n)` factor should look like, and it is the reason the whole sweep is in the table
rather than one row: any single instance would have supported almost any claim about
the shape of the improvement. The naive pass was not run at five hundred jobs, where
it takes minutes; that row reports the tuned time only and says so.

These are a development diagnostic on one host, not a benchmark result and not
evidence.

What this changes for C6 is worth recording, because it is the opposite of
convenient. The number a device now has to beat at 500 jobs is 23.86 ms of tuned
single-threaded CPU work, not the several seconds the naive pass would have taken.
The crossover, when it is measured, will sit further out than it would have against
the old baseline, and that is the honest position to measure from.

## Intermittent advisory database fetch

`cargo deny check advisories` fetches the RustSec database from github.com, which
has repeatedly been unreachable in this environment. The acceptance gate now
falls back to the cached database rather than failing spuriously or skipping the
check; an absent cache is still a hard failure. Reproduction: run
`cargo deny --locked check` without network egress to github.com. Next step: seed
the advisory database in CI so the check does not depend on egress at gate time.

## Native acceptance can be skipped explicitly

`AI_OPTIMIZER_SKIP_NATIVE=1 bash tools/check.sh` runs without the pinned HiGHS
build and prints a prominent warning that native acceptance was not covered. Such
a run is not a complete acceptance gate pass and must not be recorded as one.

## Sanitizers not yet in the gate

SPEC-0002's acceptance list mentions running repeated native lifecycle tests under
available sanitizers. The repeated-lifecycle test exists and passes, but no
sanitizer run is part of `tools/check.sh` yet. This is an uncovered part of the C1
acceptance list, recorded rather than waived silently.

## Extension containment covers panics only

The C3 extension host runs extensions in-process and contains panics with
`catch_unwind`. It cannot contain a process abort, stack exhaustion or a memory
fault, and it enforces no per-extension memory budget. A hostile extension can
therefore still take down the process, even though it cannot affect a search's
mathematical conclusion. Reproduction: an extension calling
`std::process::abort` ends the test process. Next step: process-isolated
workers, which SPEC-0004 defers and which need their own decision record. The
host also requires the unwind panic strategy; no repository profile sets
`panic = "abort"`, and nothing currently pins that.

## Python SDK is deferred with a stated blocker

SPEC-0005 delivers the C4 run surface through the CLI and defers the Python SDK
to its own specification. The blocker is concrete rather than a matter of
sequencing: pyo3 expands to unsafe code, the workspace sets
`unsafe_code = "forbid"`, and ADR-0003 permits unsafe only inside
optimizer-highs. An in-process binding therefore requires a decision record
amending ADR-0003, plus maturin packaging and a Python test layer in the gate.
AGENTS.md also states that Python under tools/ is validation tooling and not the
SDK. Reproduction: add a pyo3 dependency to any runtime crate and build. Next
step: decide the SDK's shape in its own specification, now backlog item C9; a
subprocess wrapper over the versioned run records needs no unsafe boundary and is
the cheaper option if an SDK is wanted before that decision.

## Resolved: the local extension registry is implemented

This was recorded from C4 through C5 and is now closed by C8 under
[SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md) and
[ADR-0008](../docs/decisions/ADR-0008-registry-resolution.md). `optimizer search`,
`optimizer verify` and `optimizer schedule solve` resolve a configuration's
extension policy through a registry document the caller names with `--registry`,
and registration, promotion, licenses, compatibility, authority basis and
inter-extension requirements are all checked rather than parked. The declaration
fields SPEC-0004 deliberately left unread — data needs, hardware and dependencies —
now have checked meanings.

Retained as the limits the implementation actually has, each recorded rather than
absorbed:

- A run record names each extension's identity and version but not the registry
  document that resolved it, so licenses and promotion state are auditable through
  the registry rather than through the record. Closing this needs a run-record v2
  and an ADR, because SPEC-0005 makes a change to the compared fields breaking.
- An extension is identified by identity and version, so two different builds of one
  version are indistinguishable. This is the same limitation already recorded for
  the pinned native library, and it is why the summary-difference diagnostic exists.
- The registry resolves only extensions this build provides. It cannot name a
  dynamically loaded native extension, and it refuses an entry requiring a GPU;
  both refusals are explicit and both remain recorded below.
- Provider construction happens before SPEC-0004's guarded host exists, so a
  provider that panics while constructing an extension is outside the
  panic-containment claim. The host's containment of `declare`, `propose` and
  `advise` is unchanged.
- Conformance establishes contract invariance only. A passing record means the
  contract held, never that the extension improved a search, which stays a C7
  question.

## Resolved: a scheduling run record with a producer registered now verifies

Recorded from C5 and closed by C8. `optimizer verify` previously re-executed every
record through the extension-free search entry point, so a record whose
configuration named an extension policy was refused as unsupported: re-running
without the named producer would have reproduced a search the record does not
describe, and its node counters would have differed for that reason alone.

Under [SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md)
requirement 19 the verifier reconstructs the producer a record names, through a
registry the caller passes with `--registry`. Reproduction of the closed case:
`optimizer schedule solve` with a configuration naming `flow-shop-neh` and a
registry, then `optimizer verify` on the resulting record with the same registry;
it agrees and exits 0. The gate re-executes such a record across a commit boundary
in `tools/verify_committed_record.py`. A record naming an extension policy with no
`--registry` is still refused, which is requirement 18 rather than a limitation.

## Resolved: a run record's identifier no longer depends on the clock

`optimizer search` built `record_id` as `run-{model_id}-{elapsed_ms}` and
`optimizer schedule solve` built `schedule-{model_id}-{elapsed_ms}`. The
identifier was a pure function of a measurement the project excludes from meaning
everywhere else: SPEC-0005 requirement 12 fixes elapsed time as diagnostic rather
than contractual, and verification ignores it. Two runs of the same search on the
same machine got different identifiers whenever the host spent a different number
of milliseconds, and two unrelated searches that took equally long collided.

Found by the C8 clean-checkout verification, which is the case it takes to see it:
the requirement 17 contract compares a record produced with a registry against one
produced without, and both runs completed in 0 ms on a warm working tree but in 0
and 1 ms on the clean clone.

Closed by SPEC-0005 requirement 1a, which now states that an identifier is derived
only from what the record describes. Both commands derive it from the SHA-256
digests of the input documents the record already carries, so a different model or
a different configuration yields a different identifier and a repeated run yields
the same one. Two runs of the same inputs sharing an identifier is the intended
reading rather than a residual collision: the identifier names the inputs, and
whether two such runs agree is what `optimizer verify` answers. Reproduction of the
closed case: run `optimizer search` twice over the same model and configuration and
compare the two `record_id` values; the contract test asserts this and was shown to
fail with the old derivation reinstated.

## Resolved: two SPEC-0009 acceptance gaps closed by diagnosis

Both were recorded when C8 was integrated and both are now closed, one by a
specification correction and one by a test that reaches a branch previously
believed possibly dead.

Requirement 14 said resolution "MUST NOT ... construct" a refused extension, which
was not true of the declaration- and role-mismatch paths: `Extension::declare` is
the authority being compared and the provider is what supplies the role, so both
are necessarily decided after construction. The rule is now split. Requirement 14
governs invocation, which holds everywhere. Requirement 14a governs construction
and names the three refusals that can be decided before it — an unprovided
identity, an unsatisfied data requirement and a gpu hardware requirement — and
states that a mismatch is constructed, read and then refused without ever being
invoked. This was a specification correction, not a code change; the
implementation was already right.

Requirement 20's record-versus-resolved version comparison is **reachable**, and
is now tested. The earlier doubt came from testing it the wrong way round:
restamping the *registry* is refused by the declaration check first, because the
extension still reports the version it always did. The rule the requirement
actually describes runs the other direction — a record naming a version the
current build no longer declares, which is what happens when a record outlives the
build that produced it. Restating the version in the record's extension summary
reaches it, and disabling the branch makes that test fail. The branch is not dead
and was not removed.

That diagnosis also found a defect in the acceptance gate itself.
`tools/verify_committed_record.py` restamped the registry and asserted only that
the restamped version appeared in stderr — but resolution's declaration-mismatch
message contains that version too, so the check passed on the wrong error and
never reached requirement 20. Its comment claimed an isolation it did not achieve.
The gate now covers both rules separately and each asserts the message its own
rule produces; with the requirement 20 branch disabled the gate step fails, where
before it passed. This is the same class of defect the C8 clean-checkout run
found: a check that passes for a reason other than the one it names.

## C8 requirements whose acceptance tests are thinner than the specification

SPEC-0009's acceptance section describes cases that the implementation does not
yet assert. These are recorded rather than quietly downgraded, because the
specification is accepted and its own test mapping is the thing out of date.

- Requirement 20's nondeterministic-record refusal has no test. Neither example
  extension declares nondeterminism, so producing such a record needs a fixture
  that does not exist in the CLI's provider table.
- Requirement 21's positive case — a run that agrees while reporting an extension
  summary difference as a diagnostic note — is asserted only in its negative form,
  that no difference is reported when none exists. `ExtensionDifference` has no
  unit test.
- Requirement 22's forfeited registry-backed record is not produced by any test.
  The forfeiture rule itself is covered without a registry under SPEC-0005.
- Requirement 18 is asserted for `optimizer schedule solve` but not for
  `optimizer search --registry` with a non-empty policy, because both extensions
  this build provides are flow-shop producers that cannot be constructed from a
  bare model. A search-command case needs a provider that takes no auxiliary
  instance.
- Requirement 1's document-level missing-field refusal and requirement 3's
  duplicate-field rejection are covered for entries but not for the document
  itself.

## Verification assumes an unchanged native library

`optimizer verify` re-runs a search and compares the two records field by field. A
divergence now reports whether the backend library, source revision or compiler
differs from the record's, so a changed engine is distinguishable from a wrong
result *in the diagnostic*. What remains unresolved is whether such a mismatch
should ever be **tolerated**: verification still fails, because deciding otherwise
would change the meaning of agreement and needs a new record version plus an ADR
under SPEC-0005's compatibility rule. Cross-host reproducibility is separately
untested, because floating-point behavior and library builds may differ between
machines, and closing it needs a second machine in CI rather than local code.
Agreement therefore remains evidence of determinism on one host over time, which
is what ADR-0006 claims and no more.

## Per-node work Track B measured and deliberately did not remove

Track B removed five items from the branch-and-bound node path without changing
any conclusion; see [active task](active-task.md) for the measurements. Two
candidates were identified, reasoned about and left in place, and both are
recorded here so they read as decisions rather than as oversights.

`node::relaxation` still clones the original model's constraints and objective
once per node — 5,175 nonzeros for the encoded ta001. `Model::rebound` removed the
revalidation that sat beside that copy but not the copy itself, and the copy is
now likely the dominant per-node cost. Reproduction: profile a node-budgeted
`schedule solve` over ta001 and attribute time inside `node::relaxation`. Next
step: sharing the rows between a model and its relaxations needs an `Rc` or `Arc`
inside `ModelDocument`, which is a public type in a crate other crates deserialize
through; that is a wide change and needs its own measurement before it is worth
making, not a follow-on commit.

Reusing the `Highs` object across nodes is permitted — SPEC-0003 requirement 23
forbids reusing a *basis*, not the instance — and is the obvious next per-node
item. It was deferred because the measurement harness that would justify it did
not exist when the ranking was made. Cross-node warm start and parallel search
remain forbidden by SPEC-0003 requirement 23 and SPEC-0002 requirement 5
respectively, and each needs its own decision record; neither is blocked on
measurement.

Also worth recording, because it is a gate property rather than an engine one:
until Track B's last commit both committed run records reported `nodes_explored:
1`, so `tools/verify_committed_record.py` had never re-executed a branching search
across a commit boundary. A multi-node fixture now closes that. Its
`nodes_pruned_infeasible` is 0 and is deliberately not asserted, because the
positional encoding's relaxation was feasible at every size tried and choosing a
fixture to hit that counter would be choosing it for the wrong reason.

## Checkpoint restart is still unimplemented

C2 defines and serializes `Checkpoint` and SPEC-0003 states that restart is not
implemented. The C4 run surface does not add a restart entry point either, so a
long search cannot be resumed and a run record cannot be continued. Verification
re-runs from the beginning under the record's own budgets. Reproduction: no CLI
command consumes a checkpoint. Next step: restart needs its own acceptance
evidence before any public entry point exists.

## The flow-shop encoding is correct but weak

Two limits recorded before implementation, both confirmed by it.

The positional encoding is exactly linear and its optimum equals the instance's
minimum makespan by construction, but its linear relaxation is weak and the model
is quadratic in the job count: a 20-job, 5-machine Taillard instance is 400 binary
variables. The executive is not expected to prove optimality at that size, so the
specification confines proven-optimal claims to tiny instances checked against
exhaustive permutation enumeration and confines the frozen subset to feasibility,
determinism and validated-incumbent evidence. This is a stated scope boundary, not
a defect, and it is why requirement 26 forbids recording a performance claim.
Reproduction: encode any 20-job instance and run the executive without a budget; a
node-limited run over `ta001` is asserted in the CLI contracts to report its limit
rather than an optimum. Next step: a stronger formulation or a scheduling-specific
bound would each need its own contract, and the evidence justifying one does not
exist yet.

Permutation schedules are also not optimal for the general flow shop beyond three
machines, confirmed by direct enumeration on a 3-job, 4-machine instance where the
best permutation schedule costs 50 and the best general schedule costs 47. The
permutation restriction is part of the problem C5 solves rather than an
approximation it makes, and nothing in the slice should be read as solving the
general flow shop.

## Dynamically loaded native extensions are not implemented

SPEC-0004 specifies host-contract-version negotiation and implements it in safe
Rust, but the versioned C-compatible boundary for separately distributed native
components is deliberately absent. It needs a second unsafe boundary, which
ADR-0003 prohibits outside optimizer-highs, so it requires an amending decision
record plus its own lifecycle, ABI-stability and crash-isolation evidence. This
is a recorded deferral, not a gap discovered late.

[SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md) does not change
this. Its registry *resolves* a named identity to an extension the build already
provides and refuses one it does not, so the registry is now the obvious place a
dynamically loaded extension would be named and deliberately cannot name one. That
makes the deferral more visible rather than closing it.
