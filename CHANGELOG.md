# Changelog

User-visible changes are recorded here using Conventional Commit terminology.

## Unreleased

### Added

- C4 agent-independent run surface, under SPEC-0005 and ADR-0006. `optimizer
  search` runs the owned executive over the pinned backend and writes a run
  record; `optimizer verify` re-runs that search from the record alone and fails
  on disagreement. Before this, the C2 executive and the C3 extension host were
  reachable only from Rust test code.
- Reproducibility is established by re-execution rather than asserted.
  Verification reads only the configuration embedded in a record, never its
  recorded outcome, objective, bound or counters, so it cannot confirm its own
  input. Divergence in the outcome, recomputed objective, dual bound, gap,
  forfeiture state or any of the five counters is reported by name.
- Measured elapsed time is recorded and excluded from agreement. It describes the
  host rather than the search, so including it would make every verification
  fail.
- A record is bound to model bytes by `Model::fingerprint`, not by `model_id`, so
  a model edited under an unchanged identifier is refused before any search runs.
  This is the rule C1 already applied to LP bases.
- `RunRecord` in optimizer-experiment at schema version 1, carrying source
  revision, dirty state, hardware, toolchain, the canonical model fingerprint,
  the SHA-256 of each input document, and the complete `SearchRecord` embedded
  verbatim. Provenance field names are taken from SPEC-0007's experiment result
  so the repository's two provenance shapes cannot drift apart.
- A search that reached a limit or was interrupted still writes its record and
  reports exit 1 or 130. Only a run that could not start writes nothing, because
  there was no run to describe.
- A configuration naming an extension policy is refused as unsupported rather
  than run without the extension it names, which would record a search the caller
  did not request. That refusal marks the seam the deferred registry fills.
- JSON Schemas for the run record, the search record and search configuration,
  giving C2 and C3 documents their first schema coverage. The Rust parsers and the
  schemas accept the same documents, and nested versions are validated on the
  parse path so neither authority is laxer than the other.
- SHA-256 in safe Rust, checked against the FIPS 180-4 vectors and independently
  against Python's `hashlib` over the committed documents, rather than adding six
  transitive dependencies under a `multiple-versions = "deny"` policy.
- C4 acceptance evidence: verification is shown to fail as well as pass. A
  perturbed model is refused on its fingerprint, and a mutated outcome,
  objective, forfeiture flag and each counter are detected individually, so no
  field is nominally compared and actually ignored. Agreement establishes
  determinism on one host, not correctness and not optimality; a forfeited search
  stays forfeited after it verifies. Cross-host reproducibility is untested and
  no performance claim is made. The Python SDK, the local registry, checkpoint
  restart and comparative experiment execution are deferred with recorded
  blockers.

- C3 extension runtime and authority model in optimizer-extension, under
  SPEC-0004 and ADR-0005. Extensions declare identity, category, host contract
  version, determinism and counted budgets; the core derives their authority
  from the category and decides what is true. Candidate producers and search
  advisers are the admitted categories.
- Every proposed candidate is validated by `Model::evaluate` against the
  original model before it can become an incumbent, and the recorded objective
  is that recomputation. An objective an extension asserts is never read.
- No extension path can forfeit a proof claim, end a search or return an error.
  An adversarial extension can waste its budget and have everything refused; it
  cannot deny a proof the engine would otherwise complete.
- Advised branching is restricted to variables the executive itself found above
  its integrality tolerance at that node. Branching on an integral value would
  produce two children that do not tighten the node, so the search could
  regenerate an identical child forever.
- Typed extension failures in search records: invalid candidates, invalid
  advice, both directions of contract-version mismatch, a refused
  transformation category, an unclaimed problem class, contained panics and
  exhausted budgets. Counters stay exact while retained messages are capped, so
  an extension refused once per node cannot grow a record with the search.
- Search configuration, search records and checkpoints move to schema version 2.
  Configuration carries the caller's extension policy and records carry one
  summary per permitted extension, so a record cannot conceal that extensions
  influenced it. Version-1 documents are rejected rather than migrated.
- `search_with_extensions` alongside `search`, which remains the extension-free
  entry point. A search with an empty policy produces the same record as the
  extension-free one apart from measured elapsed time.
- optimizer-extension-examples: three honest extensions and three hostile ones
  covering 17 distinct misbehavior modes, depending only on the published
  extension and core APIs with the executive as a test-only dependency. That
  they build and run is the evidence that a third-party extension needs no
  engine-internal change.
- C3 acceptance evidence: over a fixed model grid every hostile extension leaves
  the outcome, proven optimum, dual bound, forfeiture state and both prune
  counters identical to the extension-free run, which itself agrees with
  brute-force enumeration. Extension containment covers panics, not a process
  abort. No performance claim is made.

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

- Record parsing validates the versions of the documents nested inside a
  record, not only the record's own version. The version-1 JSON Schemas already
  pin every nested `schema_version`, so `SolveRecord::from_json`,
  `SearchRecord::from_json` and `Checkpoint::from_json` previously accepted
  documents `tools/validate_artifacts.py` rejects. A wrongly versioned
  incumbent, validation report, relaxation configuration, extension summary or
  extension policy is now a document error at parse time. Strictly narrowing:
  no document that was valid under both paths becomes invalid.

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

No CUDA kernels, Python SDK, extension registry, dynamically loaded native
extensions, or solver performance claims are included. Owned branch-and-bound
search proves optimality but is not tuned and is not compared against any other
solver. Extensions may propose candidates and search actions; the core validates
every one, and extension containment covers panics rather than a process abort.
Relaxations are single-threaded CPU HiGHS under recorded numerical settings; no
benchmark comparison is claimed.
