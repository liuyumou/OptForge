# SPEC-0042: Exact checker and preparation optimization

Status: accepted for isolated research
Scope: GPUP-CHECKER2
Owner: LP research
Introduced: GPUP
Last reviewed commit: bootstrap
Supersedes: none
Implementation: research/lp-mixed2-checker2
Tests: original serial differential checks, native gate and new independent study

## Purpose

The user requests continuing exact-checker and preparation optimization after
SPEC-0041. Diagnose and reduce CPU cost for both native and FP4 without changing
original-model authority, solver trajectories, public defaults or historical evidence.

## Requirements

1. Attribute preparation and certificate cost before selecting optimizations.
   Distinguish instrumented observations from uninstrumented complete cost.
2. Every optimized assessment MUST match the independent original serial checker,
   including certificate fields, tolerance tiers, signed zero and refusal behavior.
   Preserve original operation/reduction order or prove exact equivalence with a
   guarded fallback across the full supported binary64 domain. No result memoization
   by recurring endpoint or relaxed certification is permitted.
3. Original input validation and identity binding remain prerequisites. No unchecked
   model cache, skipped original data or GPU certificate is allowed.
4. Keep the numerical solve body, CUDA image, reset, work and recovery exact.
   Apply shared CPU improvements equally to native and FP4.
5. Admit CPU differential/process tests, full native gate, fresh same-image device
   comparisons and complete-size resource pilots before a frozen cohort.
6. Prospectively freeze 16 independent balanced blocks: four historical 1024/2048
   generic/coupled families, two tiers, native/FP4, baseline/candidate; 512 sessions,
   16384 solves. Each session cycles four original scenarios eight times. Compare
   candidate with baseline within each family/tier/lane. Retain every failed or
   missing cell; no scientific retry or historical pooling. Primary endpoint is
   complete fresh-session wall time including durable outputs and teardown.
7. Report paired ratio and saved-time medians with simultaneous exact median
   intervals (32 endpoints, familywise alpha .05). Scoped benefit requires ratio
   lower bound >1 and saved-time lower bound >10 ms/session; report 1.10 separately
   as provisional, not a diagnostic veto. No public/default adoption follows.
   Freeze order, source/binary/image identity and admission receipts before launch.
8. Preserve all source versions, failed reservations, original scientific bytes,
   unfavorable findings and portable evidence. A negative measured result is valid.

## Interfaces and invariants

Existing research JSON protocol, original model SHA-256 and independent child
checker ownership stay unchanged. Preparation may change internally only with
identical validated model data and error behavior. Four-scenario sessions reset
FP64 state on each request; these are constructed streams, not warm starts.

## Errors and recovery

Keep malformed/nonfinite input, overflow, unsupported bounds, cancellation and
limits explicit. Preserve first numerical refusal. No stale certificate may survive
model switching. Use the existing admitted one-second supervisor unchanged.

## Security and resource limits

Independent ceiling 96000 CPU / 12000 GPU seconds; four CPU slots, 16 GiB sampled
RSS, 12 GiB owned device buffers, one pinned shared GPU lease. CPU phases:
implementation 16000 (512 preparation), diagnosis 12000, native 16000,
acceptance 12000, confirmation 32000, reporting 6000, cleanup 2000 (128 closing).
GPU acceptance 2000, confirmation 10000. Receipts artifacts/gpup-checker2-v1.
All old allocations remain closed. Reserve four times wall cap as CPU seconds;
failed jobs retain full reservations and immutable sources. Finite one-second
sampling/freshness/scan bound, 5–10 ms target and all >100 ms advisories retained.
Sampled RSS is not a hard memory enclosure. No frozen retry or funding transfer.
If projected cohort cost cannot fit, stop before freezing and record the limitation.

## Acceptance and limitations

Meaningful full-domain arithmetic tests; exact model/preparation differential tests;
all original serial certificates and numerical trajectories; native check.sh;
source-bound unchanged-image admission; paired complete-session analysis and
portable reproduction. Preserve GPUP-8 incomplete and GPUP-9 gated. Commit locally.
Shared hardware, constructed streams and temporal independence limit inference.

## Host vectorization admission

Before final selection, a source-identical `x86-64-v4` build may be evaluated on
this verified compatible host, retaining strict floating-point compilation and
all exactness gates. Compare both baseline and candidate under that target to
separate compiler-target and source effects. Record flags and hardware capability;
no public build default changes. The selected binary, including its compiler
target, must receive current CPU/device/process/session admission before freezing.
