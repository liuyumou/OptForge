# ADR-0057: Admit persistent FP4 trajectories before device execution

Status: accepted, 2026-11-11

## Context

The user requests GPUP-FP4-PROTO after the accepted SPEC-0025 CPU contract. The
prototype must retain approximate component state across observations while
meeting the existing original-unit enclosure guard and final 1e-9 certificate.
Mathematical FP32 representability of component groups does not admit a GPU
instruction or an entire iteration.

## Decision

Implement [SPEC-0026](../specifications/SPEC-0026-fp4-prototype-admission.md).
First implement a separately coded rational PDHG reference and a persistent
component trajectory oracle that explicitly accounts for local two-FP32 rounding,
matrix/state quantization, projection decisions, and enclosure propagation. Freeze
the CPU admission fixtures and sources before one formal attempt. A candidate
must retain a nontrivial 600-update trajectory under all mandatory fixtures,
including three observation boundaries, without native replacement. Native
escalation may safely recover a refusal but does not qualify the FP4 fast path.

Expected adversarial refusals test safety separately. If no component count
qualifies, close device/sanitizer/profile execution and report the CPU numerical
refusal, actual errors and remaining work. Do not relax SPEC-0025, change the
fixtures after seeing results, or retry the scientific admission automatically.
The full repository CPU integration gate remains required for delivered code.

The new independent ceiling is 32000 CPU seconds: implementation 6000 including
256 preparation, proofs 8000, native 8000, workers 6240, reporting 2960 and cleanup
800. Conditional GPU ceiling is 1560 seconds: device/sanitizer admission 480,
pilot 720 and diagnostics 360. Four CPU slots, one GPU lease, 16 GiB sampled host
RSS and 12 GiB device buffers use the unchanged in-container supervisor. This
explicit implementation allocation supersedes the prototype's proposed CPU
amount only; historical budgets remain closed. Whole reservations must fit;
failed/unsettled runs retain full charges.

## Consequences

A successful software test run can accompany a numerical admission refusal.
The report must distinguish them. Local arithmetic is a CPU oracle until actual
instructions, compiler behavior, device error and synchronization are admitted.
Device implementation remains conditional, and a CPU refusal leaves the overall
prototype incomplete. TENSOR2 and GPUP-9 remain gated; no supported preset or
public solver change follows. Commit locally after acceptance; no publication.
