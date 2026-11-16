# General sparse low-bit LP research executor

See [SPEC-0045](../../docs/specifications/SPEC-0045-general-lowbit-lp.md).
This isolated candidate targets fresh single solves of general LPs. It does not
change public solver defaults and has no broad performance claim yet.

The original sparse CUDA kernel uses packed FP4 coefficients with FP32 SIMT
increments and FP64 references/state. It is not a Tensor Core kernel. Native
FP64 and FP32 controls share geometry, controller and original-model checking.
Both matrix orientations refer to a canonical represented operator. Every
rejected attempt remains in physical work and complete cost.

Ordinary Cargo builds need no CUDA toolkit. The GPU image is explicitly compiled
and admitted under the independent budget and unchanged shared-device lease.
All numerical jobs use `tools/lp_general_budget.py`; CPU and device admission
tools retain source-bound responses and original serial certificates. Diagnostic
`gpu-fixed` bypasses the local value limit only for bounded arithmetic admission;
it cannot return a solver certificate or be used for performance claims.

JSONL commands are `cpu`, `operator`, `assess`, `gpu`, `gpu-probe`, and `gpu-fixed`.
GPU commands also require an explicitly supplied cubin. Every request includes
validated settings. `gpu` creates and destroys its owned context for each solve.
The product admission command alone caches a context across diagnostic requests.

`tighten` emits an equivalent model and original-row implication proof;
`assess-proven` checks an external endpoint using the same proved bounds and
limited dual-repair proposals as the solver. Original `assess` remains available
for diagnosing the unextended checker. Every actual certificate dual is retained
separately from the numerical continuation state. Independent exact-rational
proof verification precedes unchanged serial checking of equivalent bounds and
original primal feasibility. These shared improvements do not establish FP4 value.

Generated models, raw responses, binary images and portable evidence bundles stay
under the ignored local `artifacts/gpup-general-v1` directory. Commit source,
protocol, compact results and reproduction instructions; do not commit build
targets or large generated matrices. Retain all scientific inputs and failures.

The initial 128-cell pilot is complete. The extended 176-cell pilot stopped with
137 retained responses after a missing supervisor receipt; 136 have complete
resource receipts and 39 planned cells are missing. Numerical admission does not
establish performance: FP4 supplies only about 0.48% of accepted updates in the
retained extended results. See the [development report](../../docs/benchmarks/lp-general-lowbit.md)
and its compact result record for all outcomes and continuing engineering work.
The interruption disposition permits CPU work; new GPU/scientific execution
requires operational readmission. Neither existing cell identities nor failed
resource reservations may be reused.

`tools/lp_general_portable.py archive --id NAME` creates a local evidence bundle;
`replay --id NAME` checks its exact bytes and independently reassesses every
retained endpoint from an extracted root. Use a fresh budget job identity and
the reporting phase for each command. Replay retains the missing-cell ledger
and does not turn missing supervision into a successful experiment. The archive
receipt gives its hash, compressed size and retained file count.


## Actual FP4 Tensor Core backend

`gpu-tensor MODEL CUBIN` is a separate opt-in backend. `tensor-operator MODEL`
emits its canonical sparse-block packing and `gpu-tensor-probe MODEL CUBIN`
admits products only. The SM120 image uses actual E2M1 MMA with FP32 accumulation
and FP64 state. `fp4x1` through `fp4x4` select one through four components;
`fp4x4` means sixteen logical coefficient bits per orientation, plus metadata
and original FP64 data, not four-bit total storage.

A request has `settings` and optional `tensor` objects. Tensor controls are
`min_tile_nnz` (default 128 of 1024), `control_interval` (100), `incremental`
(true), `compact_fragments` (true), and `tensor_warps` (1, alternatively 4).
The component count follows `settings.format`. The same settings support native
and real FP32-storage controls. Local original-row replacements preserve global
FP4 eligibility; actual tensor nonzeros and corrected nonzeros are counted
separately. Zero-tile models explicitly select native and contribute no FP4 work.
Global progress/nonfinite failures still restore a complete checkpoint.

Control feedback is separate from strict original-model certificate assessment.
Periodic original-A references allow the Tensor Core path to quantize increments.
Direct products, expanded fragments and four-warp launches remain diagnostic
ablations. Every fresh solve pays its own preparation, context and teardown.
Public defaults are unchanged; development observations do not imply adoption.

`tools/lp_general_tensor_cpu.sh` builds and checks a candidate; the tensor
admission tool covers independent rational products, original serial certificates,
restoration and all four sanitizers. A hash-bound composite admission precedes
`tools/lp_general_tensor_bench.py freeze` / `campaign`. These commands must run
within the existing budget/supervisor protocol; old identities cannot be reused.
`tools/lp_general_tensor_portable.py` archives and independently replays a local
**delta** bundle, keeping the original large evidence bundle separate. Only
compact results and validation receipts belong in Git.
