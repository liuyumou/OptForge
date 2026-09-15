# ADR-0017: Tuned FP64 Execution and Isolated Ablations

Status: accepted by the maintainer's implementation instruction, 2026-09-15
Owner: numerical backend and experiment tooling
Introduced: GPUP-4
Supersedes: ADR-0016's existing-kernel restriction only for cuda-lp-tuned
Superseded by: none

## Decision

Add explicit experimental cuda-lp-tuned under SPEC-0012, with required version-1
FP64 execution settings. Preserve highs, host-lp, cuda-lp and cuda-lp-matched.
Original coefficients, preconditioning, step-size calculation, host control,
assessment frequency and conservative certification remain unchanged. Runtime
remains Rust through the existing CUDA driver boundary; provisioning produces a
separate tuned code object and does not become an ordinary build dependency.

Compare per-check versus resident working allocation; every-check versus necessary
state uploads; legacy-1024 versus warp32-v1 reduction; separate versus fused
primal/dual execution. Necessary uploads require residency. Initialize all state,
upload new anchors after restart, and explicitly invalidate resident state on
checkpoint restoration. Check cancellation/deadlines at synchronized chunks of at
most 64 steps; physical work/deadlines do not roll back. Count allocations, bytes,
copies, synchronizations and actual launches, including faults.

warp32-v1 assigns one complete warp per sparse line. Lane l sums entries l+32k in
increasing k from +0.0, with separately rounded FP64 products/additions. Full-mask
shuffle offsets 16,8,4,2,1 form a fixed halving reduction; only lower participating
lanes add at each level. Empty lines produce +0.0. No floating atomic, coefficient
reordering/pruning, FMA contraction, lower precision or schedule-dependent mask.
CPU/device identity with the legacy reduction is not asserted for this mode.
Same-device repeatability and independent numerical checks are required.

Fusion uses two ordered kernels: transpose product/primal projection/extrapolation/
primal Halpern update, then row product/dual projection/dual Halpern update. Each
mode preserves its arithmetic order. Extrapolation uses the old primal state;
separate input/output aliases must not violate restrict promises.

Solve record v3 records tuned execution and code-object identity. Endpoint v3
retains requested execution even on pinned fallback; trial/campaign v3 identify
per-configuration binaries and code objects. Existing v2 solve records and v1/v2
endpoints remain readable with unchanged schemas and emission. Exact replay uses
recorded execution settings and verifies the tuned code-object identity.

## Frozen study

Identity gpup4-tuned-fp64-v1. Archive revision 722e0b0 source, matched executable,
and legacy code object before runtime changes. Eight configurations: archived
matched; tuned compatibility; resident/repeated uploads; resident/necessary uploads;
necessary/warp32; necessary/fused legacy; necessary/fused warp32; current host.
All 12 original development instances, three timing repetitions, and one separate
profile for each configuration on small-4, irregular-256, irregular-2048 and
dense_block-1024: 320 attempts, 280 GPU. No warmups, retries or held-out solves.

Keep the ADR-0014 manifests/hashes/settings, seeds 17/17001/17002, 1e-9 targets,
one CPU thread, 50000 steps, checks every 200, 10+2-second limits and 8 GiB bounds.
Use existing activity admission and device GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48.
Primary timing includes fresh-process setup and independent endpoint checks;
profiles are separate. Report per-instance coverage, paired 10000-resample 95%
intervals, work/control differences and component observations. Retain failures.
A development-only provisional control requires preserved per-instance coverage
and supported end-to-end improvement; otherwise retain matched FP64. No preset or
automatic dispatch follows from this study.

Extend the existing canonical ledger without changing its authority/hash or output
binding. Carry forward 445988045904 ns. Add at most 900000000000 ns: cumulative
1345988045904 ns, baseline phase 1800 seconds, campaign 28800 seconds, other phase
allocations unchanged. All leased study time, failures and profiles count. Require
full remaining reservation before launching. Exhaustion produces interim evidence.
Acceptance separately permits 60 CPU wall minutes/four build jobs and 30 GPU minutes,
sequentially with CPU gates. No push or publication is authorized.

## Acceptance

Full pinned-native tools/check.sh; unchanged rational authority and matched
trajectories; bitwise allocation/upload/fusion checks within each reduction mode;
independent warp mirror and exact-rational dot error checks; boundary, restoration,
cancellation, memory, fault, fallback, schema/replay/provenance and ledger tests.
Regular device suites and relevant new cases under memcheck, racecheck, initcheck
and synccheck must pass. Map evidence in SPEC-0012 and the reviewed report before
advancing the backlog and committing the completed slice locally.
