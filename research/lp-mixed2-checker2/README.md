# Exact checker and preparation research executor

SPEC-0042 / ADR-0075 isolate CPU optimizations around the unchanged SPEC-0039
native/FP4 solver and CUDA image. Public solver settings are unchanged.

The candidate parses independent JSON constraint objects concurrently, then runs
original model validation; any error falls back to the original parser. It visits
dense norm inputs in contiguous rows while retaining each column's addition order.
The checker retains original interval products and the exact reduction tree,
separating enclosure fields to permit vectorization. A guarded product path
checks immutable coefficient ranges once and each repaired dual once. Products
of operands with nonzero magnitudes in [2^-40,2^40] (or zero) and their adjacent enclosures stay inside the
existing reduction domain; all other inputs use the original full-range path. Readiness reuses the hash
already computed over the independent checker's original model bytes. It then
releases the transient byte buffer while retaining the complete validated model.

Run `bash tools/check_checker2_cpu.sh` for format, Clippy, unit tests, dependency
checks and study-contract tests. Run it through a separately open CPU allocation.
The default Cargo target remains portable. The measured selected executable uses
`RUSTFLAGS='-C target-cpu=x86-64-v4'` on the admitted compatible host; this is a
research artifact, not a public build preset. Exact compiler flags, hardware
capability, both baseline/candidate target comparisons and source snapshots are
retained in the study evidence. CPU preparation/serial checks and fresh device
sessions separately admit that exact binary before scientific measurement.

Study tooling records every full-lifecycle baseline/candidate attempt and does not
retry scientific cells. See SPEC-0042 for budgets, statistics and limits.
