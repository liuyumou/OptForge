# Changelog

User-visible changes are recorded here using Conventional Commit terminology.

## Unreleased

### Fixed

- Model and candidate file paths preserve native OS strings, including non-UTF-8
  Unix names; malformed command/flag/tolerance text returns an argument error.
- Incomplete and unknown model commands include the argument error category.
- Model and candidate JSON now reject positional records and object-wrapped
  domain/objective enums, including direct Serde parsing and nested records.
- Model validation report write and flush failures return a categorized I/O
  diagnostic and exit code 2, including full output devices and closed pipes.

### Added

- M1 original linear models with stable IDs, explicit bounds and continuous,
  integer and binary domains, immutable structural validation and canonical JSON.
- Original candidate objective, bounds, row and domain checks with explicit
  tolerances, inspectable violations/allowances and checked numerical failures.
- CPU model/candidate validation CLI, versioned examples, independent exhaustive
  tests, file-size boundaries and strict JSON regression coverage.

- M0 Rust workspace with a pinned toolchain and seven ownership boundaries.
- Bootstrap CLI, JSON GPU discovery, and cancellable simulated exclusive leases.
- Versioned configuration, manifest, and result schemas with provenance checks.
- CPU CI, documentation builds, dependency policy, and manual serialized GPU CI.
- Contract tests, bounded smoke artifacts, project rules, and milestone backlog.

No model solving, HiGHS calls, CUDA kernels, or solver performance claims are included.
