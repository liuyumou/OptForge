# Glossary

| Term | Meaning and authority |
| --- | --- |
| Numerical authority | Core validation owns feasibility, objectives, and proof status; [architecture](../docs/architecture/overview.md) |
| GPU lease | Cooperative exclusive ownership across all project devices on one host; [SPEC-0006](../docs/specifications/SPEC-0006-gpu-lease.md) |
| UUID | Driver-reported stable physical GPU identity |
| Manifest | Frozen instances, hashes, split, seeds, settings and timing; [SPEC-0007](../docs/specifications/SPEC-0007-artifacts.md) |
| Measured record | Provenance-bearing run output with a real revision |
| Example record | Schema illustration that is not empirical evidence |
| Differential test | Comparison with an independent implementation |
| Acceptance gate | Evidence required before completing a bounded task |
| M0 | Repository/process bootstrap; no solver claims |
| ADR | Architecture decision record, superseded rather than rewritten |
| Termination | Engine-owned solve outcome; a limit or interruption is never a proof; [SPEC-0002](../docs/specifications/SPEC-0002-backend-contract.md) |
| Backend | Replaceable numerical solver behind the solve contract; native handles stay private |
| Warm start | Validated candidate or model-bound LP basis supplied to a solve |
| Candidate | Proposed solution requiring original-model validation |
| Makespan | Completion time of the final job on the final machine; [SPEC-0008](../docs/specifications/SPEC-0008-flow-shop.md) |
| Recurrence | Definition of makespan from an instance and a permutation; the sole authority on a schedule's cost, independent of every heuristic |
| Permutation schedule | One job order used identically on every machine; not optimal for the general flow shop beyond three machines |
| Positional encoding | Adaptation of a flow-shop instance into a linear model placing jobs in positions, using no big-M constant |
| Decoding | Recovering a permutation from a candidate over an encoded model; a candidate that does not decode is refused, never rounded |
| Extension | Separately authored component that proposes candidates or search actions; [SPEC-0004](../docs/specifications/SPEC-0004-extension-runtime.md) |
| Authority | Consequence the core permits an extension's output to have, derived from its category, never chosen by the extension |
| Declaration | Versioned document by which an extension states identity, category, contract version, determinism and budgets |
| Rejection | Core refusal of one proposal or action; the search continues unchanged |
| Disabling | Permanent exclusion of one extension from the remainder of one search |
| Run record | One search plus the provenance needed to repeat it; [SPEC-0005](../docs/specifications/SPEC-0005-run-surface.md) |
| Provenance | Revision, dirty state, hardware, toolchain, model fingerprint and input hashes identifying what produced a record |
| Verification | Re-executing a run from its record and comparing the two search records; evidence of determinism, never of optimality |
| Divergence | A named difference between a recorded search and its re-execution |
| Model fingerprint | Hash of the canonical model document, identifying model bytes rather than model identity |
