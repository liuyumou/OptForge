# Hybrid Tensor Core component execution: GPUP-8

Status: bounded implementation/evaluation finished; GPUP-8 incomplete, 2026-10-23,
under accepted
[ADR-0042](../decisions/ADR-0042-hybrid-tensor-components.md). The working-family and certified total-latency gain gates did not pass.
No supported Tensor solve benefit follows.
The [frozen protocol](../../benchmarks/configs/lp-tensor-v1.json) retains 60
fresh timing cells, twelve 2000-update profiles and three product diagnostics.
Resource allocation is 3000 GPU seconds from existing headroom, without any
campaign/phase ceiling increase or later-task reservation.

## CPU admission and exact arithmetic

All eight models and six configurations are retained (48 cells). The two dense
models place 96.97% of coefficients in selected 32x32 tiles; the other six models
admit no tile with at least 512 nonzeros. All component candidates promote before
a useful 32-update window on both dense models. The first dense-1024 refusal is
on update four: a nonzero dual value 2.0816681711721685e-17 lies below the block
integer unit. Dense-65536 first refuses on update three, with 72 lost nonzeros.
The original values remain in the FP64 checkpoint; the entire window is replayed
in native arithmetic and its work remains charged. This cannot establish useful
Tensor convergence. Refused study cells retain their planned denominators.

The independent integer/Fraction oracle passes 27091 conversion/rounding cases
and all 961 BF16 digit products. An additional 12288 exact-real original-unit
product components pass. Production lane-address helpers are checked on CPU
for 3072 matrix and 1536 vector addresses, each covered exactly once. Signed 56-bit operands need at most 117 magnitude
bits for a 32-term exact tile dot. INT8 and FP16 share eight 7-bit components;
BF16 uses fourteen 4-bit components. Each tile is reconstructed exactly before
nearest-even FP64 rounding. Both orientations share coefficient identity; the
irregular remainder is native FP64. Original-unit bounds include scaling,
representation, final rounding and remainder arithmetic.

CPU regressions cover shared represented operands, both orientations, subnormals,
ties/overflow, checkpoint session ownership, malformed physical work before
aggregation and charged whole-window rollback. The initial BF16 compiler result
used 136 registers and is retained as a compile-only refusal. Disabling loop
unrolling reduces BF16 to 48 registers; INT8/FP16 use at most 88, with zero spills
throughout the final image. Actual IMMA/HMMA instructions are audited. No device
execution is implied by these CPU/compiler results.

The first leased device gate reproduced a vector-fragment packing defect: each
packed register repeated its first input rather than advancing its element
index. Its failed source/executable/image, outputs and 2.105369475-second charge
remain under the first execution cohort. The corrected loader uses the checked
lane helpers; a fresh CPU/image cohort retains the same numerical admission
outcomes. No completed GPU identity is retried.

## Device and study acceptance

All 66 ordinary GPU tests, 260 CPU/device product pairs, five controller pairs,
four admitted fixed-work endpoint/replay pairs and all four scoped sanitizers
pass on the corrected image. The range case refuses before accepting a product.
The three separately charged product diagnostic jobs repeat the frozen synthetic
and recorded fixture trajectories; each passes 260 pairs. They are correctness
and repeatability diagnostics, with no sparse-LP latency claim.

All **75 planned study cells** remain: 27 execute and 48 retain CPU admission
refusals. All **20 admitted timings certify (20/60 planned coverage)**. The forty
component timing cells and eight component profiles are refused without
replacement. None of the three Tensor candidates or the represented SIMT control
admits a useful complete 32-update window on either dense model.

Fresh-process median seconds over five paired repetitions, including input,
preparation, context, uploads, guards, updates, audits, certification and output:

| Model | Policy-matched FP64 | Unchanged tuned FP64 |
| --- | ---: | ---: |
| dense-block-1024 | 0.688316 | 0.523445 |
| dense-block-65536 | 10.290469 | 6.331952 |

These controls do not establish a Tensor benefit. All six predeclared Tensor/
model comparisons retain zero eligible pairs and no speedup interval; the gain
gate cannot pass. A promoted native run or an initial host certificate cannot
supply useful Tensor work. Five-pair bootstrap comparisons, if admitted, use
Bonferroni adjustment across the six comparisons at 95% family confidence.

All four admitted profiles finish exactly 2000 logical updates. Tuned FP64
performs 2000 physical updates and records first certification at update 1400 on
both models. Matched FP64 performs 2070 physical updates, including 70 audits;
its two 2000-update endpoints remain feasible but uncertified. Complete profile
horizons are diagnostic records and do not become successful solve timings.

Fresh CPU verification accepts **128 retained LP records**: 96 across four CPU
cohorts, eight device acceptance/replay records and all 24 study endpoints. Each
CPU cohort verifies with its original frozen executable and the corrected frozen
verifier. No payload is normalized or re-signed. CPU component/MMA counters
represent the reference schedule, including refused prefixes; they imply zero
GPU execution. Actual device work requires the GPU executor and leased worker.
The [machine report](data/tensor/report.json), [numerical oracle](data/tensor/oracle.json),
[instruction admission](data/tensor/instruction-admission.json) and separate
[CPU reader bridge](data/tensor/reader-source-bridge.json) retain the exact evidence.

## Resources and completion decision

GPU charge is **236.856927634 / 3000 seconds**: timing 92.278436607 / 1600,
profiles/diagnostics 22.601859333 / 550 and acceptance 121.976631694 / 850.
Acceptance includes the failed first 2.105369475-second gate. The earlier
allocator-authority preflight reserved no GPU identity and charged zero.
Cumulative consumption is **21596.442783423 / 25202.574545061 seconds**, with
all phase ceilings and the independent 28800-second cap unchanged.

The 17200-event ledger SHA-256 is
5af7782a384ac73226f339d98d0b33e320518053c1accdf67c1339db36d0e0f1,
preserving the exact 17132-event prefix SHA-256
930de6771ab9bfbcb855bd05a07a58f6700aa1ade36bca09346790a94e7ff035.
Final pinned-native acceptance passes 353 Python tests, Rust/native/dependency
checks, historical replay, 140 documentation pages and smoke. The
[delivery receipt](data/tensor/acceptance.json) separates passed software/device
gates from unmet task completion. Its measured CPU jobs, 6000-second preparation/
coordination allowance and 1000-second delivery reserve account for 10337.630178 CPU
seconds within 21600. Sampled process-tree RSS is 3535245312 bytes; retained artifacts are
approximately 1.166 GiB. Source-only portability passes 20 inherited plus nine
Tensor tests with study artifacts/native dependencies absent. RSS and
artifact limits remain 8 GiB and 32 GiB; no native dependency or measured artifact
is removed.

GPUP-8 remains **incomplete**. Correct INT8 and floating Tensor operators do not
satisfy the required useful certified dense-model solves or total-latency gain.
The frozen comparison is exhausted; no retry, replacement cell, relaxed budget,
supported preset or GPUP-9 progression follows from unused headroom.

Historical GPUP-7/7R payloads, reports, workers, images and the exact 17132-event
ledger prefix remain untouched. New source/execution/acceptance receipts and
negative results are separate under artifacts/gpup-tensor-v1 and
docs/benchmarks/data/tensor. No supported preset or GPUP-9 progression follows.
