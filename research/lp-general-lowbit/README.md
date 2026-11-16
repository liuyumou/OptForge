# General sparse low-bit LP research executor

See [SPEC-0045](../../docs/specifications/SPEC-0045-general-lowbit-lp.md).
This isolated candidate targets fresh single solves of general LPs. It does not
change public solver defaults and has no broad performance claim yet.

The current sparse CUDA kernel uses packed FP4 coefficients with FP32 SIMT
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
