# ADR-0060: Optimize measured FP4 software overhead before solver integration

Status: accepted, 2026-11-11.

The completed [pilot](../benchmarks/lp-fp4-gpu-pilot.md) is slower than its native
control. Retained evidence identifies linear scale selection, expensive component
encoding, repeated matrix-fragment construction, exact-zero component products,
unused MMA columns and an underfilled device. Rational Python preparation also
dominates the cold proxy. Static evidence alone does not quantify dynamic stalls.

The user explicitly asks for aggressive FP4 optimization and permits either FP4
inner arithmetic or independently validated FP64-quality solves. Execute the
separate [SPEC-0028](../specifications/SPEC-0028-fp4-fast.md) allocation with
versioned development corrections and preserved failures. Optimize representation
and execution while comparing state bytes and independent products. Use several
problem sizes and ablations to distinguish overhead from throughput limits.

The consequence is a new research candidate, not an accepted solver preset.
Empirical trajectory errors cannot substitute for final original-model checking.
The completed pilot, its failures, sources and charges remain immutable. Recovery
policy and certified solver integration remain separate gates.
