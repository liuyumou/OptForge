# Corrected FP4 acceleration — GPUP-FP4-ACCEL

Status: implementation and both frozen comparisons complete; broad latency retention fails
Contract: [SPEC-0031](../specifications/SPEC-0031-fp4-corrected-acceleration.md)
Decision: [ADR-0063](../decisions/ADR-0063-fp4-corrected-acceleration.md)
Prior evidence: [integration diagnosis](lp-fp4-integrate-diagnosis.md)

This separate implementation fixes repeated immutable preparation, full-state
encoding loss, avoidable recovery, conditioning, underutilized dense kernels and
serial independent-checker work. It retains actual E2M1 tensor instructions,
original-model certification at both final tiers and the supported native solver.

## Changes and numerical scope

The Rust service reuses the original model, parsed checker, GPU preparation and
buffers, with fresh numerical/controller state per solve. Compact Rust output is
written durably without rebuilding the model or reformatting its full evidence
in Python. Cold execution starts from frozen original input bytes and includes
process/context/checker startup, selected preparation, solving, checking, process
exit and durable output. Prepared measurements separately disclose shared startup.
These delivery boundaries differ from the old model-generation-inclusive harness;
old and new totals are not a matched scientific comparison.

Full FP32-pair iterates retain corrections. A scalar-corrected FP4 development
path removes numerical failures but makes expensive correction products every
update. The retained centered candidate computes original-coefficient FP64
reference products once per at most 32 updates and applies FP4 to increments
about those resident anchors. This is mixed arithmetic with charged FP64 window
references, not FP4-only arithmetic or a proved global trajectory enclosure.

Power-of-two row equilibration restores useful step sizes on the ill-scaled
families. The old 10% progress cliff is replaced by sustained noise-limited lack
of progress. Local estimates are explicitly operational; the final feasibility,
conservative bound, gap and refusal mathematics stay unchanged. Complete state,
controller, solve identity, cancellation and physical-work accounting survive
recovery. An actual conversion failure restores and falls back to native.

Eight warps cooperate on each dense output tile, and separate stream-ordered
x/y/guard launches provide global ordering without a spin barrier. Native FP64
receives the same scheduling improvements. Independent certificate columns use
four CPU workers, then concatenate in original order and use the unchanged
outward reduction tree. Serial replay remains the final authority.

The domain is at most 512 rows/columns. Twelve constructed development families
include irregular tails, ranged/active bounds, two ill-scaled families, generic
dense 128/256/512 targets and an intentional unbounded-direction refusal. This
is not a general large sparse solver or a held-out production benchmark.

## Development evidence and retained failures

Scalar correction passes the initial 135 device comparisons and all bounded
complete trajectories, but its dense 512 strict GPU time is about 86.7 ms.
Centered fused work reduces that to about 27.6 ms; parallel tiles/reductions reduce
it further. The stronger native control improves too, so gains against the first
native kernel are not evidence that FP4 beats the final native control.

Earlier 64-update audits increase complete cost by repeating expensive original
checks. The default maximum stays 200, with responsive near-accuracy checks.
A one-sixty-fourth operational budget prematurely promotes two-component starts;
the separately versioned one-eighth budget is tested before final freezing.
No final certificate tolerance is relaxed.

Every failed attempt retains exact sources, images, logs and full reservations:
missing Cargo PATH in the first build; an invalid packed shared load in the wider
tile variant and its diagnostic reproduction; a trajectory launcher mistakenly
invoked after that failed admission (its partial work is excluded from performance
claims); an unresolved test-only root import in the parallel checker build;
scoped lint findings; the missing block barrier between warp-owned packing
and striped packed-state export; and an optional figure job without installed
Matplotlib (240 CPU seconds retained; the data are presented in tables). The
first final-delivery writer also refuses to overwrite its provisional receipt;
its full 720 CPU-second charge and v1 files stay exact. A versioned v2 writer
reuses identical history evidence and emits new final receipt paths. The CUDA packed-load correction explicitly
forms an aligned word address. The race correction adds the required block
barrier. Versioned recoveries are within the current user's development request;
closed historical experiments and the final scientific no-retry rule stay exact.

## Acceptance and complete-cost results

All 1440 original formal cells complete; 1320 certify. The separate EOF cold
comparison completes all 360 cells, with 330 certificates and **identical endpoints,
certificates and physical work** to its corresponding original cells. All eleven
bounded families certify at both 1e-7 and 1e-9; the intentional unbounded-direction
family refuses consistently. There is no coverage loss. The 102 distinct audit
and terminal endpoints replay through the original serial certificate authority;
the additional cold cohort reuses those receipts only by exact identity.

Validation includes 270 final device/CPU component comparisons, 42 lifecycle and
failure cases, and zero errors in all four sanitizers across 112 service processes.
The full repository gate passes 638 Rust and 646 Python tests, committed-record
replay, dependency/artifact/documentation and smoke checks. The subsequent isolated
checkpoint/generation/metadata correction passes 17 Rust and ten Python tests,
including 600 exact serial/parallel certificate comparisons, then the final device
and sanitizer gates. Checkpoints now also synchronize their raw view without
requiring a prior host export. No numerical source or checker default outside the
isolated research package changes.

The device is an NVIDIA RTX PRO 6000 Blackwell Server Edition, driver 580.105.08.
The following are five-trial model medians from the original frozen prepared
cohort, all at the **strict 1e-9 tier**. GPU values are CUDA stream-event elapsed
time, including submission gaps; complete values include checking and durable
response delivery.

| Dense dimension | Fused FP4 ×4 GPU / complete ms | Parallel FP4 ×2 GPU / complete ms | Parallel native FP64 GPU / complete ms |
|---|---:|---:|---:|
| 128 | 5.246 / 8.132 | 3.421 / 6.302 | 2.882 / 5.278 |
| 256 | 11.082 / 17.509 | 3.492 / 9.625 | 3.703 / 9.255 |
| 512 | 27.588 / 43.050 | 4.457 / 18.955 | 5.347 / 18.676 |

At dimension 512, the optimized FP4 lane is **6.19x faster in GPU time and 2.27x
faster in complete prepared time than the fused FP4 lane** at the same strict
certificate tier. Against the stronger parallel native control, its GPU advantage
is **1.20x**, while complete strict time is **18.955 versus 18.676 ms**: a 1.5%
regression. At 1e-7, the corresponding complete times are 19.132 versus 19.349 ms,
a small 1.1% win. These are bounded model results, not broad FP4 superiority.
The faster native control itself improves the dense 512 strict complete median
from 68.084 ms for fused FP64 to 18.676 ms.

The original cold adapter's `wait(timeout)` polling produces roughly 50 ms latency
steps. The separately frozen EOF adapter removes that polling and includes exact
response/log fsync costs. It does not alter numerical execution or omit startup.
Its strict dense-512 medians are 738.976 ms for FP4 ×2 and 718.153 ms for parallel
native. Cold startup/preparation dominates; do not interpret the change between
separate cohorts as a controlled cross-cohort speedup.

| EOF cold policy / tier | Native-to-candidate geometric mean | 95% paired-bootstrap interval |
|---|---:|---:|
| gridfp4x2 / 1e-7 | 0.984997x | 0.978278–1.006335x |
| auto / 1e-7 | 0.995587x | 0.990601–1.019469x |
| gridfp4x2 / 1e-9 | 0.986329x | 0.974610–1.010632x |
| auto / 1e-9 | 0.993979x | 0.981833–1.010440x |

All intervals use 2000 within-model paired bootstrap resamples of five trials.
They quantify timing uncertainty on these constructed models, not generalization.
No policy meets the unchanged 1.10x cold geometric-mean/no-regression retention
criterion. Keep native supported and select no public FP4 preset. `auto` remains
an explicitly experimental study policy.

## What remains expensive

The strict dense-512 FP4 median attributes 4.623 ms to iteration submission/wait,
10.342 ms to independent checking and 0.686 ms to original-model audit arithmetic.
Export, coordination and durable evidence delivery account for the rest. Parallel
checking reduces serial work while preserving certificate bits, but the unchanged
outward-bound arithmetic is still the largest complete-solve component. Further
GPU-only acceleration has limited total benefit at this size. Multiple launches
and narrow matrix-vector tensor use also limit smaller cases; the sparse native
path remains much faster there.

There are 40 natural recovery events in the 1440-cell cohort: two-component starts
on dense-rich-65 and ill-scaled-generic-128 promote to four components on the local
budget. All finish certified. There are no natural conversion failures,
noise-stagnation failures or native fallback in those events. All four-component
formal solves finish without recovery. The forced failed-conversion and cancellation
paths remain covered separately. This resolves the former bounded-family refusals
without pretending every guard should be suppressed.

The next worthwhile work is reducing exact checker cost and launch/delivery cost,
and measuring useful batched or larger dense tensor work under a new protocol.
Do not infer a large sparse production speedup from this bounded executor.
TENSOR2 stays conditional on a viable complete-cost case; FP4-PROTO and GPUP-8
remain incomplete, and GPUP-9 stays gated.

## Evidence and accounting

- [All 1440 original rows, medians and uncertainty](data/fp4-accel-result-v1.json).
- [Separate 360-cell EOF cold comparison](data/fp4-accel-cold-eof-v1.json).
- [Original models and 102 serially replayed endpoints](data/fp4-accel-result-v1-endpoints.json.gz).
- [Every cell's final/audit endpoint binding](data/fp4-accel-evidence-v1.json).
- [Acceptance and sanitizer receipts](data/fp4-accel-acceptance-v2.json).
- [Exact historical-file preservation](data/fp4-accel-history-v1.json).
- [Final allocation accounting](data/fp4-accel-accounting-v2.json).

The independent 160000 CPU / 24000 GPU ceiling is separate from closed history.
Final settled charges, including all nine failed reservations, 512 conservative
preparation seconds and 64 closing-administration CPU seconds, are in the accounting
receipt. All coordinator/guardian cleanup is empty; no historical funds transfer.
No scientific cell was retried. Sources, images and logs are retained under
`artifacts/gpup-fp4-accel-v1`; binary images are archived by SHA-256. Commit locally;
no push or publication.

Allocation closed after acceptance: **19460.451448592 CPU seconds** and
**2540.379498809 GPU seconds**, including every failed reservation.
