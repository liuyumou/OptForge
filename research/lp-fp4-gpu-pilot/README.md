# Independent FP4 GPU pilot

This isolated research executor implements [SPEC-0027](../../docs/specifications/SPEC-0027-fp4-gpu-pilot.md).
It has no public solver entry point, certificate authority or production preset.
The workspace build does not compile CUDA or this separate Cargo package.

The active recovery candidate is `cuda/pilot_v3.cu`; `pilot.cu` and `pilot_v2.cu`
are immutable failed experimental sources. V1 has incorrect FP4 instruction
fragment packing. V2 fixes packing but fails racecheck on aliased shared state.
V3 adds a warp barrier before encoding overwrites that state. Exact compiler
images and per-attempt evidence remain in the corresponding local artifact trees.

The six fixed lanes use native FP64, four E4M3 components, two binary16 components,
and two/four/eight E2M1 components. Each warp owns an independent 32-variable
block and one useful RHS. Split, fused, persistent and explicit FP64 roundtrip
variants implement the same bounded ordered recurrence. All component pairs,
packing/scales, projection and normalization are charged. This is not a general
sparse-matrix solver or a proof of long-trajectory accuracy.

`src/main.rs` validates bounded requests, uses the existing safe research CUDA
driver boundary, retains complete state checkpoints and exposes physical work,
sticky refusal, rollback, scheduled cancellation and disjoint worker phases.
Inputs and outputs use JSON; output files must not already exist. Execution
requires the pinned Blackwell GPU and an inherited shared-device lease.

The `tools/lp_fp4_gpu_study_v3.py` coordinator freezes source/input/compiler/device
identities before primitive, trajectory, sanitizer and profile stages. The
`tools/lp_fp4_gpu_budget.py` wrapper accounts for the independent task allocation
through the unchanged in-container supervisor. Closed identities and budgets
are evidence, not reusable authorizations. Fresh experiments require fresh
resource and protocol identities. No ordinary test command launches GPU work.

CPU package checks use `cargo test --manifest-path research/lp-fp4-gpu-pilot/Cargo.toml`
with the repository's pinned Rust environment. CUDA compilation is explicit via
`tools/setup_fp4_gpu_pilot_v3.py`, within a newly admitted supervised job. The
existing provisioning destination is immutable and cannot be overwritten.
