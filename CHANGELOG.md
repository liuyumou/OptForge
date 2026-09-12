# Changelog

User-visible changes are recorded here using Conventional Commit terminology.

## Unreleased

### Added

- `Model::rebound`, which replaces a model's variable domains and bounds while
  reusing its already-validated rows and objective, under new SPEC-0001
  requirement 2a. It is the relaxation path branch-and-bound builds one subproblem
  per node with, not a general-purpose constructor: it refuses any variable list
  that does not name exactly the original variable IDs, and that refusal is what
  makes skipping the row checks sound rather than merely cheaper.
- C8 local extension registry and conformance, under SPEC-0009 and ADR-0008. A
  registry document maps a declared extension identity to an extension this build
  provides, together with the facts needed to decide whether to permit it: version,
  license, category, authority basis, host contract compatibility, declared
  determinism, counted limits, data and hardware needs, inter-extension
  requirements and conflicts, and promotion state. Before this, the extension
  runtime was reachable only from Rust test code.
- `optimizer search`, `optimizer verify` and `optimizer schedule solve` accept
  `--registry` and resolve a configuration's extension policy through it. This
  closes the gap C5 recorded: a scheduling run performed with the NEH producer is
  now verifiable by re-execution, where before it was refused as unsupported.
- `optimizer registry list` reports every entry a registry records, and separately
  whether this build provides the identity at all, so an entry that would be
  refused is visible without attempting a search. `optimizer registry check` runs
  the conformance suite over one entry and writes its record.
- The registry resolves; it does not load. An entry names an extension the binary
  already provides through a caller-owned provider seam, and an entry naming an
  identity this build does not provide is refused rather than skipped. Dynamic
  loading of separately distributed native components would need a second unsafe
  boundary ADR-0003 prohibits, and stays deferred with its recorded blocker.
- Resolution is total: it either produces a resolved set for every named entry or
  refuses, so a search never begins with a subset of what it was configured with.
  The extension's own declaration is authoritative and an entry is a claim about
  it; a disagreement on version, category, host contract version, problem class,
  determinism or limits is refused in both directions rather than reconciled.
- Promotion is checkable rather than assertable. A promoted entry cites a
  conformance record by path and SHA-256, and is refused when the record is absent,
  its bytes do not match, its outcome is not a pass, or it names another extension
  or version. An experimental entry needs `--allow-experimental`, and a record
  written with one registered carries a warning naming it.
- A conformance record and a registry document are new versioned strict-JSON
  documents at `schema_version` 1, each with a JSON Schema that accepts exactly
  what the Rust parser accepts. No existing schema version changed and no existing
  document gained or lost a field, so the committed C4 example record still
  verifies unchanged.
- Nothing here grants an extension mathematical authority. Resolution decides which
  extensions a search may consult; SPEC-0004 continues to decide what their output
  is worth. Promotion means the contract conformance suite passed, never that the
  extension improves a search, and no performance or solution-quality claim is made
  or measured.
- C5 flow-shop scheduling slice, under SPEC-0008 and ADR-0007. This is the first
  application workload with an independent notion of a correct answer: a makespan
  recurrence computes a schedule's cost from a job order, so a candidate is checked
  against a definition rather than against another solver.
- `optimizer schedule generate` writes a flow-shop instance from a published
  Taillard seed, and `optimizer schedule solve` encodes an instance, registers the
  NEH producer, runs the executive and writes a SPEC-0005 run record. `solve` also
  writes the encoded model, which is what a caller hands `optimizer verify`: a run
  record's fingerprint is computed from the model that was searched, and for a
  scheduling run that is the encoded model rather than the instance.
- Flow-shop instances are versioned strict-JSON documents. A ragged matrix, a
  processing time that is zero or negative, a matrix disagreeing with its declared
  shape, an unknown or duplicate field, and a positional array are each refused at
  parse time rather than clamped or repaired.
- The positional encoding turns an instance into an ordinary model with no big-M
  constant, so the existing solve, search, extension and run-record contracts apply
  unchanged: no new record type, and no schema version changed anywhere.
- Deterministic NEH and insertion candidate producers, registered by a caller and
  never loaded by default. They hold no authority: every proposal is validated
  against the original model and the recorded objective is that recomputation.
- A frozen Taillard development subset, the published 20x5 class, generated from
  the seeds in the cited paper rather than downloaded. The manifest records each
  instance's generator, seed and parameters beside its checksum, so the derivation
  is verifiable and the gate needs no network access.
- C5 acceptance evidence: the proven optimum on encoded models equals exhaustive
  enumeration of every permutation over a fixed grid; the generator reproduces
  Taillard's published `ta001` matrix exactly; a producer whose proposals are all
  refused leaves the outcome, proven optimum, dual bound, forfeiture state and both
  prune counters identical to the producer-free run; and a scheduling run record
  verifies by re-execution.
- No performance or solution-quality claim is made. The positional encoding's
  linear relaxation is weak, so proven optimality is asserted only for tiny
  instances, and no best-known bound is committed as a threshold.

### Fixed

- The branch-and-bound node path no longer performs work it discards. The backend
  extracted an LP basis on every node — computing the model's canonical
  fingerprint, which serializes the whole model — for a value `Backend::solve`
  dropped immediately and that SPEC-0003 requirement 23 forbids reusing across
  nodes. Evaluation and structural diagnostics were formatted eagerly, costing
  several string allocations per matrix nonzero on the success path for text a
  valid model never produces. Both are now built only when a check fails.
  `Candidate::canonical` cloned and re-sorted a candidate the backend had just
  built by iterating the model's own sorted variables, and now borrows when the
  input is already canonical. `node::relaxation` rebuilt each subproblem through
  `Model::new`, revalidating every row and the objective once per node for data
  the node did not touch, and now uses `Model::rebound`, which validates the
  supplied bounds and refuses any variable list that is not the original's IDs.
  Conclusions are unchanged: every field verification compares, every node
  counter and every diagnostic message is identical, and the messages are pinned
  byte-exactly by tests written against the previous code. No performance
  property is claimed of the engine; `tools/benchmark_search.py` is a development
  diagnostic that records no threshold.

- `tools/verify_committed_record.py` now re-executes a record whose search
  branched. Both committed records reported `nodes_explored: 1`, so the only check
  that re-runs a record against a later build had never descended past the root
  node — the exact blind spot that matters for work on the per-node path. The new
  fixture explores 37 nodes, prunes 23 by bound and proves optimality, and its
  counters are asserted against the committed record so the check cannot decay
  into a third single-node case.

- A run record's identifier no longer depends on measured elapsed time. `optimizer
  search` built `record_id` as `run-{model_id}-{elapsed_ms}` and `optimizer
  schedule solve` built `schedule-{model_id}-{elapsed_ms}`, so a record's identity
  was a property of how busy the host happened to be: two runs of the same search
  got different identifiers, and two unrelated searches that took equally long got
  the same one. Both now derive it from the SHA-256 digests of the input documents
  the record already carries. SPEC-0005 requirement 1a states the rule, so the
  derivation is specified rather than incidental. `record_id` is not among the
  fields verification compares, so no record version changed and existing records
  remain valid.

- `optimizer verify` now refuses a record whose configuration names an extension
  policy, reporting it as unsupported instead of as a divergence. Re-execution
  loads no extension, so such a record was reproduced by a search it does not
  describe and its node counters differed for that reason alone; calling that a
  divergence blamed the record for a limitation of the verifier. SPEC-0005
  requirement 14 already refused such a configuration on the search path, and this
  applies the same rule to verification.

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
- A divergence reports whether the backend library, source revision or compiler
  differs from the one the record names, so a changed engine is distinguishable
  from a wrong result. This is diagnostic only: the ten compared fields are
  unchanged, a record from another build still verifies when its search agrees,
  and a divergence still fails. Whether such a mismatch should ever be tolerated
  is unresolved and needs its own record version and decision record.
- The acceptance gate re-executes the committed example run record against the
  current build. Every other verification test produces its record moments
  earlier in the same process, so none of them covered the property actually
  claimed, that a record outlives its author.
- Fixed: a build that linked no native library recorded `backend_version:
  "1.11.0"` for a pre-cancelled solve, making its record indistinguishable from
  one produced against the real library. It now records the adapter's own report,
  `unavailable`, so provenance cannot claim a library that was never called.
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
