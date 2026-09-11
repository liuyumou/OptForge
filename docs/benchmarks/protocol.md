# Benchmark Protocol

Purpose: preserve comparable, reproducible evidence. Scope: bootstrap smoke and the
C5 scheduling correctness subset now; solver performance suites are unscheduled.

Every measured record names a manifest hash, instance hashes, source revision,
dirty state, hardware, seed, configuration, toolchain, timing method, and failures.
Use a monotonic clock and end-to-end timing including transfers. Kernel-only
measurements may later supplement full timings, never replace them.
The [artifact specification](../specifications/SPEC-0007-artifacts.md) is normative.

The committed [bootstrap manifest](../../benchmarks/manifests/bootstrap-smoke.json)
checks a tiny repository fixture and measures CLI hello startup once with seed 17,
one thread, 512 MiB address-space limit, and a 10-second timeout. Its artifact
reports smoke_passed; it makes no optimization or GPU speed claim. Build time is
excluded. There are no transfers in this CPU-only smoke.

## Planned suites

| Suite | Purpose | Availability |
| --- | --- | --- |
| Taillard flow shop | Primary development/validation scheduling suite | Development subset frozen at C5 |
| Generated flow shop | Exhaustive and distribution-shift testing | Exhaustive tiny grid at C5 |
| OR-Library job shop | Transfer evaluation | After flow shop |
| MIPLIB 2017 | General MILP diagnostics | Planned, no capability assigned |
| Netlib | LP regression | Planned, no capability assigned |
| Generated sparse LP | Later GPU LP research | Research backlog |

No datasets or splits are implicitly frozen by naming a suite. Before use, add
source URL/version, license, checksums, exact splits, seeds, generation parameters,
and download tooling. Keep large datasets outside Git. Report unsupported cases
and failures. Changing seeds, splits, tolerances, defaults, or acceptance thresholds
requires an ADR and a new experiment record. Public datasets are not secret tests.

A suite whose instances are reproduced by a published generator satisfies that rule
without download tooling, provided the manifest records the generator, its seed and
its parameters per instance, the generated documents are committed with checksums,
and the generator is shown to reproduce the source's own published reference
instance. Recording the derivation is stronger than recording only a hash of bytes
a third-party host served, and it keeps the gate independent of that host's
availability. [SPEC-0008](../specifications/SPEC-0008-flow-shop.md) requirements 22
to 24 and [ADR-0007](../decisions/ADR-0007-flow-shop-encoding.md) take this route
for the C5 development subset. A best-known bound is an acceptance threshold and is
therefore not committed by naming a suite either.
