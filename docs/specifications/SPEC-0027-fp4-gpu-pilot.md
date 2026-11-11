# SPEC-0027: Independent FP4 GPU pilot

Status: accepted for implementation, 2026-11-11
Decision: [ADR-0059](../decisions/ADR-0059-fp4-gpu-pilot.md)
Parent: [ADR-0058](../decisions/ADR-0058-fp4-gpu-exploration-quality-tiers.md)

## Scope and workload

This is an empirical device experiment, not a certified solver. It does not
reopen SPEC-0026 admission. All historical sources, charges and outcomes remain
exact. Rust owns the executor through the existing research optimizer-cuda-sys
boundary; Python provides independent preparation, checking and orchestration.

Freeze three deterministic block-diagonal workloads: dense 32 (one block),
irregular 29 (one padded block with structural zeros), and dense 2048 (64 distinct
32-by-32 blocks). Each has one RHS; padding seven MMA output columns is wasted
work, not seven additional useful RHS. No cross-block dependency exists in this
pilot; arbitrary sparse coupled models require later integration. Matrix entries,
objectives and right-hand sides use fixed integer formulas and dyadic scales.
The irregular tail remains explicitly zero padded and its costs are counted.

Six lanes: native FP64, E4M3 with four components, binary16 with two components,
and E2M1 with two/four/eight components. Component scales are signed power-of-two
exponents in [-48,48]. Matrix and transpose use the same encoded coefficients.
Packed E2M1 nibbles expand only into local instruction fragments; persistent
state stays packed. All component cross-products are evaluated. E2M1 and E4M3
use m16n8k32; binary16 uses two m16n8k16 instructions. Target sm_120a under CUDA
13.0.88 on GPU-6721b13a-30f9-83ec-dace-ba2d9738556f. Compile without implicit FMA
contraction or FTZ. Explicit error-free-transform FMA in local FP32 pairs is
permitted. Retain PTX, cubin, SASS and compiler resource reports.

## Arithmetic and observations

One ordered update is x' = clip(x - (c - A^T y)/16, -1, 1),
bar = 2*x' - x, y' = y + (b - A*bar)/16. Padding coordinates stay zero.
Native control uses original FP64 A. Component products accumulate each MMA
result with its pair scale into local FP32 pairs. Projection, extrapolation and
renormalization use local pairs; no routine candidate FP64 state round trip.
This defines a new empirical recurrence, not v1's enclosure contract. Pair
rounding and encoding losses remain separate in CPU primitive checks.

Record original-A residuals and iterate differences at 1, 8 and 32 updates;
these are observations, never certificates or proved error bounds. There is no
600-update gate and no favorable full-solve forecast prerequisite. Use a dense
independent host recurrence and exact rational component product oracle for
primitive checking. Original-model certificate defaults remain unchanged.

## Ablations and measurements

Freeze four variants for all lanes: split products/updates (four launches per
update), fused ordered updates (one launch per update), persistent (one launch
for 32 updates), and roundtrip (fused single updates plus full FP64 state export,
host transfer and re-encoding per update). The latter isolates reconstruction
and transport cost. Same initial state, coefficients and 32 physical updates.
Three repetitions of three workloads, six lanes and four variants yield 216
profile cells. Hash-derived fixed order, seed 17112; no cell retry or deletion.

Measure cold wall time and disjoint prepare/context/upload/iteration/export/audit
phases, CUDA event time, launches, host copies/bytes, component products, useful
and padded FLOPs, register/spill/shared memory use, and final state. Cold process
cost and prepared kernel cost remain separate. Report all repetition ranges and
coverage; no supported preset or certified speed claim follows.

## Gates and stop rules

1. CPU primitive, packing, transpose, projection and corrected budget contracts.
2. Explicit toolkit compilation; full repository CPU/native gate plus isolated
   research tests/build/lint. Freeze inputs, sources, binary, device and compiler.
3. Actual instruction smoke and independent primitive differential (both matrix
   orientations, all signs/codes, boundary scales and padded tails).
4. Short ordered update differential and complete transactional state adoption,
   sticky numerical refusal, prelaunch cancellation, bounded window cancellation
   and rollback. Physical work/deadlines must not rewind. Failure of safety or
   primitive arithmetic closes the affected device path, with full charge.
5. memcheck, racecheck, initcheck and synccheck on all lanes and variants, including
   irregular padding and persistent updates. All four must pass before profiles.
6. Frozen 216-cell profiles, complete disposition, source/evidence preservation,
   settled resource receipts and empty supervised cleanup. No scientific retry.

Development corrections may use new identities before scientific freeze and
retain old sources/logs/full charges. A failed frozen gate has no automatic retry.
The implementation can deliver an honest blocked or negative result.

## Resources

Independent task ceiling 72000 CPU / 9600 GPU seconds. CPU phases: implementation
16000 (512 preparation), native 24000, acceptance 16000, study 8000, reporting
6400, cleanup 1600. GPU phases: acceptance 2400, study 7200. Four CPU slots, one
shared GPU lock, sampled host RSS 16 GiB, explicitly admitted device buffers at
most 12 GiB. Per-job reservations include supervisor termination allowance and
must fit both phase caps. Failed/unsettled jobs retain full reservations. The
unchanged in-container supervisor runs every compiler/test/device/profile job.
No historical allocation is reused. Local commit only; no push/publication.

## ISA reference

The fragment mapping and target requirements follow NVIDIA's
[CUDA 13.0 PTX ISA](https://docs.nvidia.com/cuda/archive/13.0.0/parallel-thread-execution/index.html#warp-level-matrix-fragment-mma-16832).
Actual compiler and device evidence is required in addition to documentation.
