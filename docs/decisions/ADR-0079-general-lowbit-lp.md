# ADR-0079: General LP improvement through low-bit arithmetic

Status: accepted direction under the user's 2026-11-16 instruction to follow the reviewed plan
Owner: LP numerical backend and evaluation
Implementation: [SPEC-0045](../specifications/SPEC-0045-general-lowbit-lp.md)

The project targets a broadly useful LP solver whose performance improves through
low-bit arithmetic, including FP4. Single-solve certified delivery is the primary
objective. Prepared sessions, selected families, or native fallback alone cannot
establish that objective. This direction supersedes workflow-specific follow-up
routing, including proceeding directly from GPUP-9 to recipe packaging.

Implement a common sparse operator/controller path, state-dependent precision,
general preparation/checking improvements, representative development evaluation,
and an independently frozen, adequately powered confirmation. Preserve original
model certificate authority, strict 1e-9 evaluation alongside 1e-7, exact numerical
rollback, physical-work accounting, complete costs and all failures. Deterministic
replay of a configuration does not require its trajectory to equal FP64.

The GPUP-9 review identified an ineffective numerical scaling factor: every row
maximum of generator-v2 rounds to log2 zero, so all power-of-two scales are one.
All 288 paired screening responses have identical terminal/checkpoint/work and
certificate fields. Its square nonsingular equality systems and single operator
per family do not represent general LP optimization. Preserve the original study,
sources, thresholds and decisions; publish this interpretation as an additive
review, never retrospectively regrade it.

Research progress, numerical correctness, and broad adoption are separate gates.
Maintain the broad roster and power the evaluation appropriately. No public preset
or default changes until broad held-out evidence supports them. PREP3's useful
source/target diagnosis is supporting work, not the main project objective or a
prerequisite. GPUP-10 packaging follows general validation, not a scoped speedup.

The user's execution authorization covers these engineering and evaluation stages.
SPEC-0045 declares an independent finite allocation and milestone checks before
execution. Historical allocations stay closed. All changes and evidence are local;
publication remains outside this authorization.

The user's surrounding-work continuation optimizes projection/encoding layout
without changing FP4 reduction order or strict original certificates. The
[report](../benchmarks/lp-general-overhead.md) records exact old/new transcripts,
matched timings, broad coverage and fusion diagnosis. SPEC-0045 prospectively
moves 2000 unspent GPU seconds from development to admission within the unchanged
30000-second total; all supervision rules and historical charges remain exact.
