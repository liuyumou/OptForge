# GPUP-8 inventory admission stop

The approved 2500 additional CPU seconds and unused-fund reallocation are
recorded. The cumulative CPU ceiling is 39640, with continuation allocation
9840 including historical charges. The 790-second GPU cap and every completion
criterion remain unchanged. GPUP-8 is incomplete; GPUP-9 stays gated.

## What passed and what stopped

The existing completed software gate remains exact: Clippy, Rust/native,
424 Python tests, dependencies, replay, documentation and CPU smoke. Its
1137-file source archive and original receipt are retained without modification.
No passed software check was rerun in this continuation. Exact comparison finds
only 15 explicitly enumerated documentation, state and authorization differences;
all covered implementation, tests, build inputs and configurations match.

Eleven new admission-adapter checks pass. The subsequent provenance check fails
because the adapter assumes Cargo's extracted registry source contains
`.cargo-checksum.json`. The first missing file is for `bitflags` 2.13.1. This is
an adapter assumption error. Full source admission and composite acceptance are
not claimed. The unchanged supervisor charges the full 64-CPU-second setup
reservation and verifies empty workload and guardian cleanup.

No compile-only inventory command, study freeze, GPU reservation, device check,
sanitizer, profile or timing runs. No numerical failure is inferred. The exact
17366-event ledger remains
`9142829b3be8afdb1865425c83ca9122371284ca0e16f7bc8b18d303a5894426`.
GPUP-8 consumption remains 863.208464546 / 3000 GPU seconds; campaign consumption
remains 22222.794320335 / 25202.574545061 seconds.

## Independent CPU-only diagnosis

Post-stop read-only inspection finds all 26 retained crate archives match their
checksums in the unchanged Cargo.lock. Every extracted archive member matches
byte for byte. All 26 extracted caches lack the assumed checksum metadata file.
This establishes a concrete replacement provenance procedure; it does not turn
the failed admission into a pass or authorize a retry.

A separate, unexecuted artifact draft replaces that assumption with locked crate
archive hashing, exact extracted-member comparison and rejection of unexpected
extra source files. The original adapter and failure remain exact. The draft
still requires a newly authorized journal and exact updated metadata allowlist
before execution. See the [bounded correction proposal](../plans/lp-tensor-warp32-inventory-admission-recovery.md).

## Evidence and accounting

The [authorization](data/tensor-warp32/inventory-authorization-v1.json) preserves
the accepted allocation. The [failure receipt](data/tensor-warp32/inventory-admission-refusal-v1.json)
binds the failed adapter, resource/log, passed software receipt/archive, retained
1200-second combined-gate failure, diagnostic resource receipt and correction
draft. Artifact sources and logs live under artifacts/gpup-tensor-warp32-v1.

Cumulative CPU at the setup stop is 34581.056321890 / 39640 seconds, including
8 conservative setup seconds and the full failed 64-second reservation. CPU-only
diagnosis and delivery are charged separately to reporting. Exact final totals
and remaining allocations are recorded in native-final-cpu-accounting-v4.json
in the adjacent data directory after delivery completes.

All scientific stages are closed under the accepted no-automatic-retry rule.
There is no host/container change, supervisor change, bootstrap rerun, numerical
or latency relaxation, local commit, publication, merge or later-task allowance.

Final CPU-only delivery passes exact failure/source/receipt/budget checks,
161 documentation pages/internal links and diff hygiene. No passed software
check is rerun. Final cumulative CPU is 34613.208366762 / 39640;
this continuation charges 104.152044872 CPU seconds, retaining all
prior charges. Reporting retains 117.847955128 CPU seconds;
unused funds do not authorize an automatic retry. Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-admission-final-v16.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v4.json.
Workload/guardian cleanup and diagnostic/delivery cleanup are empty. Fresh hashing
confirms the unchanged exact 17366-event GPU ledger. No commit occurred.

