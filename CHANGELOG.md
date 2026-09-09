# Changelog

User-visible changes are recorded here using Conventional Commit terminology.

## Unreleased

### Added

- C2 owned branch-and-bound executive in optimizer-solver, under SPEC-0003 and
  ADR-0004. It owns node state, budgets, cancellation, incumbent acceptance and
  proof completion, and consumes the C1 backend contract purely as a relaxation
  service without depending on any particular backend.
- `SearchOutcome`, a proof claim distinct from the backend's `Termination`:
  proven optimality means the executive exhausted its own node tree, not that
  one relaxation solve reported optimality.
- A relaxation objective is admitted as a dual bound only when that relaxation
  proved optimality. Any limit, interruption or failure leaves the node bound
  unavailable, forbids pruning that node, and permanently forfeits the search's
  proof claim, recorded as `forfeited` so a reader can see why a completed-looking
  search claimed nothing.
- Versioned search configuration, search record and checkpoint documents at
  schema version 1, with absent measurements omitted rather than serialized as
  null. The checkpoint shape is defined and serializable; restart is deliberately
  not implemented and needs its own acceptance evidence.
- C2 acceptance evidence: 192 tiny discrete models agree with brute-force
  enumeration of the entire assignment space on both proven optimum and proven
  infeasibility, plus end-to-end agreement with independent subset enumeration
  over the pinned HiGHS relaxation service. No performance claim is made.

- C1 backend-neutral solve contract: explicit solve options with no default
  seed, limits or tolerances; cooperative cancellation; engine-owned termination
  that never reports a limit, interruption or failure as proven optimality;
  model-bound candidate and LP-basis warm starts; and reproducible solve records
  in which an absent measurement is omitted rather than serialized as null.
- Pinned CPU HiGHS 1.11.0 LP/MILP backend behind a private FFI boundary, with
  every native model status mapped explicitly, native handles destroyed exactly
  once, and every extracted candidate re-validated against the original model
  before publication.
- `optimizer solve --model PATH --config PATH [--candidate PATH | --basis PATH]`,
  with exit 0 for a completed outcome, 1 for a limit, 130 for interruption and 2
  for argument, I/O, unsupported, backend or numerical errors.
- Versioned solve configuration and solve record JSON Schemas, plus their
  negative acceptance tests.
- `tools/setup_highs.sh` is now part of the acceptance gate. Running without the
  native library requires `AI_OPTIMIZER_SKIP_NATIVE=1` and is reported as
  uncovered native acceptance rather than a full pass.

### Changed

- Replaced the narrow M0-M6 implementation sequence with an evidence-staged
  roadmap covering the completed contract stage and the planned execution,
  application, research, hardening and reproduction stages.
- Solve errors use the existing `ErrorKind` taxonomy, extended with
  `unsupported` and `backend` categories, instead of unstructured strings.
- `optimizer-highs` declares its own lints rather than inheriting the workspace
  set, because a workspace-level `unsafe_code = "forbid"` cannot be relaxed by an
  inner crate; every other runtime crate keeps the prohibition.
- The acceptance gate runs cheap preconditions before compilation and falls back
  to the cached RustSec database when the advisory fetch is unavailable.

### Fixed

- Model and candidate file paths preserve native OS strings, including non-UTF-8
  Unix names; malformed command/flag/tolerance text returns an argument error.
- Incomplete and unknown model commands include the argument error category.
- Model and candidate JSON now reject positional records and object-wrapped
  domain/objective enums, including direct Serde parsing and nested records.
- Model validation report write and flush failures return a categorized I/O
  diagnostic and exit code 2, including full output devices and closed pipes.
- Candidate domain evaluation no longer relies on an unreachable branch, so
  adding a variable domain cannot introduce a latent panic.

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

No CUDA kernels, Python SDK, extension registry, or solver performance claims are
included. Owned branch-and-bound search proves optimality but is not tuned and is
not compared against any other solver. Relaxations are single-threaded CPU HiGHS
under recorded numerical settings; no benchmark comparison is claimed.
