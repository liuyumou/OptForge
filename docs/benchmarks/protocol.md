# Benchmark Protocol

Purpose: preserve comparable, reproducible evidence. Scope: bootstrap smoke now;
solver performance suites at M6.

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
| Taillard flow shop | Primary development/validation scheduling suite | Planned M3/M6 |
| Generated flow shop | Exhaustive and distribution-shift testing | Planned M3 |
| OR-Library job shop | Transfer evaluation | After flow shop |
| MIPLIB 2017 | General MILP diagnostics | Planned M6 |
| Netlib | LP regression | Planned M2/M6 |
| Generated sparse LP | Later GPU LP research | Research backlog |

No datasets or splits are implicitly frozen by naming a suite. Before use, add
source URL/version, license, checksums, exact splits, seeds, generation parameters,
and download tooling. Keep large datasets outside Git. Report unsupported cases
and failures. Changing seeds, splits, tolerances, defaults, or acceptance thresholds
requires an ADR and a new experiment record. Public datasets are not secret tests.
