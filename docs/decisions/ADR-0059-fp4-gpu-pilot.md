# ADR-0059: Implement independent FP4 GPU pilot

Status: accepted, 2026-11-11
Owner: numerical backend and CUDA runtime
Last reviewed commit: bootstrap
Implementation: [SPEC-0027](../specifications/SPEC-0027-fp4-gpu-pilot.md)
Acceptance: [active task](../../state/active-task.md)

The user requests GPUP-FP4-GPU-PILOT and permits the GPU time it needs. Select a
new bounded 72000 CPU / 9600 GPU resource package, independent of closed history.
Follow ADR-0058's primitive/safety admission path without requiring the refused
600-update CPU trajectory or a favorable solver forecast.

Implement packed multi-component actual E2M1 MMA with ordered updates, local FP32
pairs, matched FP64/FP8/FP16 controls and split/fused/persistent/roundtrip variants.
Use explicitly block-diagonal synthetic workloads to make CTA-local persistence
legal. This restriction is material: arbitrary coupled sparse LPs and certified
convergence remain integration work. Preserve native public control and checks.

Keep empirical iterate/residual errors separate from proved enclosures and
certificates. All four scoped sanitizers precede the 216 frozen profile cells.
Unsupported ISA, arithmetic mismatch, safety or resource failure stops its stage;
retain every failed identity and full charge. No automatic scientific retry.

Reuse the existing research optimizer-cuda-sys driver/event boundary without
modification; runtime code remains safe Rust. CUDA compilation is explicit
provisioning, never an ordinary workspace build dependency. Preserve old
specifications, results and ledgers byte-for-byte. GPUP-FP4-PROTO and GPUP-8 remain
incomplete, GPUP-9 gated; recovery specification remains independently ready.
Commit locally after delivery; publication is not authorized.
