# SPEC-0001: Core Model and Validation

Status: accepted
Scope: optimizer-core and model validation CLI
Owner: numerical core
Introduced: M1
Last reviewed commit: 5fe8ba30c34662bbf3b79965ab8c12a8b6091231
Supersedes: none
Implementation: [core](../../crates/optimizer-core/src/lib.rs), [CLI](../../crates/optimizer-cli/src/main.rs)
Tests: [core contracts](../../crates/optimizer-core/tests/contracts.rs), [CLI contracts](../../crates/optimizer-cli/tests/model.rs)

## Purpose

Store original linear models and assess supplied candidates. Solving, proof
statuses, transformations, native backends, GPU evaluation and Python SDKs are
excluded. An infeasible or unbounded model can be structurally valid.

## Terminology

Activity is an evaluated sparse expression. Violation is nonnegative distance
outside a finite bound. Allowance is the explicit acceptance tolerance.

## Requirements

1. Models MUST have a nonempty string ID, unique u32 variable/constraint IDs,
   continuous/integer/binary domains, explicit bounds, and a linear min/max objective.
2. Construction MUST reject nonfinite numeric input, reversed bounds, positive
   infinite lower bounds, negative infinite upper bounds, unknown references and
   duplicate terms; empty models/rows, free variables and equality MUST be supported.
2a. Rebounding a model — replacing its variable domains and bounds while keeping
   its rows and objective — MUST produce exactly the model full construction would
   produce from the same variables, and MUST refuse any supplied variable list that
   does not name exactly the original variable IDs. Row and objective term checks
   MAY be skipped on this path, and only because that refusal makes them decide
   identically: those checks establish that coefficients are finite, which is
   carried from an already-valid document, and that every term names a variable the
   model has, which the ID requirement preserves. Supplied bounds are validated as
   requirement 2 validates them. Domains MUST NOT be constrained, because dropping
   integrality is what a relaxation does.
3. Models MUST sort variables, constraints and terms by ID without renumbering,
   merging or removing zero terms; numeric signed zero MUST normalize to positive zero.
4. JSON MUST use version 1, reject unknown/duplicate fields, trailing input and
   unsupported versions/domains, and round-trip f64 values deterministically.
5. Candidates MUST identify the model and assign exactly one finite value per
   variable ID, with no unknown or duplicate assignments.
6. Evaluation MUST require explicit finite nonnegative absolute and relative
   tolerances and integrality tolerance in [0, 0.5).
7. Evaluation MUST recompute original objective, activities, bounds and domains
   without rounding or clamping candidate values.
8. Row allowance MUST equal abs + rel * max(abs(activity), abs(bound), sum(abs(a*x))).
   Variable allowance MUST equal abs + rel * max(abs(value), abs(bound)).
9. Integer/binary checks MUST use distance to the nearest integer/{0,1}, respectively,
   with integrality tolerance. Discrete candidate magnitudes above 2^53 MUST cause
   a numerical error. Bound and domain checks MUST be independent.
10. Arithmetic MUST multiply and add sequentially in sorted ID order without fused
    operations and check every intermediate for finiteness. Numerical failure
    MUST return an error without a successful or partial report.
11. Reports MUST retain tolerances, objective, ordered variable/domain and row
    checks, raw violations, allowances, and candidate feasibility only.
12. CLI MUST implement the commands, resource limits and exit behavior below.

## Interfaces

Public Rust document types use Serde with unknown-field rejection. ModelDocument
contains schema_version, model_id, variables, constraints, objective. Variable
contains id, domain, lower, upper. Constraint contains id, lower, upper, terms.
LinearTerm contains variable_id and coefficient. Objective contains sense
(minimize/maximize), offset, terms. Bounds are tagged objects: {"kind":"finite",
"value":1.0}, {"kind":"negative_infinity"}, or {"kind":"positive_infinity"}.
Domains are continuous, integer, binary. Every input field is required.
Records MUST be JSON objects, including nested records; positional arrays are
invalid. Domains and objective senses MUST be JSON strings, not enum objects.
These shape rules also apply to direct Serde deserialization of public input types.

Model::new validates into private immutable storage; document() exposes a shared
reference. Model::from_json/to_json use the same construction checks.
Model::rebound(Vec<Variable>) -> Result<Model, ValidationError> implements
requirement 2a; it is the relaxation path C2 builds one subproblem per node with,
and it is not a general-purpose constructor. Candidate
contains schema_version, model_id, values; assignments contain variable_id, value.
Candidate::from_json/to_json validate version, shape, finite values and duplicate
IDs; evaluate checks identity/coverage. Tolerances contains absolute, relative,
integrality, with no Default. Model::evaluate returns
Result<ValidationReport, ValidationError>.

ValidationReport contains schema_version, model_id, tolerances, objective,
feasible, variables, constraints. VariableCheck contains variable_id, value,
optional lower/upper BoundCheck and optional DomainCheck. ConstraintCheck contains
constraint_id, activity, optional lower/upper BoundCheck. BoundCheck contains
bound, violation, allowance, satisfied; DomainCheck contains violation, allowance,
satisfied. Unbounded sides and continuous domain checks serialize as null.

optimizer model validate --model PATH checks structure. Adding --candidate PATH
requires --absolute-tolerance F64 --relative-tolerance F64 --integrality-tolerance F64.
Flags may appear in any order; duplicate/unknown/missing flags are errors.
File paths MUST preserve native OS strings, including non-UTF-8 Unix names.
Commands, flag names and tolerance values MUST be UTF-8 text; invalid text is an
argument error. File contents remain versioned JSON regardless of path encoding.
Tolerances without a candidate are errors. Structural success prints version 1
JSON with model_id and status="structurally_valid". Candidate mode prints a report.
Exit 0 means structural success or feasible candidate; 1 means evaluated infeasible
candidate; 2 means argument/I/O/document/structural/numerical error. Errors identify
their category on stderr. Argument, input and evaluation errors produce no partial
report on stdout. Report write and flush failures MUST return an io diagnostic
and exit 2; bytes already delivered to a failing output stream cannot be retracted.

## State and Invariants

Models are immutable. Sequential sums start at positive zero; objective offset
is added after terms. Row term-magnitude accumulation is checked even for free
rows. Residual subtraction occurs only for violated finite sides. Allowance
threshold comparisons are inclusive. Finite IEEE-754 rounding and underflow,
including subnormals and zero, are permitted; exact arithmetic and cross-toolchain
bitwise guarantees are not claimed. Returned zeros normalize to positive zero.
Absolute tolerances use the checked expression's units; relative is unitless.

## Errors and Recovery

ValidationError categories: document, structural, candidate, tolerance, numerical.
Diagnostics identify relevant fields/IDs. I/O and argument errors are CLI categories.
Return the first error in canonical evaluation order. Invalid candidates leave
models unchanged. Empty discrete domains or contradictory valid rows are not proofs.

## Compatibility and Versioning

Model, candidate and report documents use schema_version 1; unknown versions fail.
No M0 numerical format exists to migrate. Rust API stays at workspace version 0.1.0.
Experiment-result statuses remain unchanged.

## Security and Resource Limits

CLI reads at most 16 MiB plus one sentinel byte per file, rejecting excess. Retain
Serde JSON's default recursion limit. No stdin or network mode exists. Construction
uses O(V+C+T) storage and sorting plus O(T log V) reference checks; evaluation uses
O(V+C+T) storage/time plus candidate sorting and O(T log V) term lookup. Rust
callers own memory/compute budgets. Size/index conversions must be checked.
Evaluation is synchronous, with no cancellation API or GPU access.

## Examples

See [model](../../examples/model-v1.json), [candidate](../../examples/candidate-v1.json),
and [tutorial](../tutorials/model-validation.md).

## Acceptance Tests

Requirements 1-5: structural, malformed JSON and canonical round-trip contracts.
Requirement 2a: rebound results are compared against full construction by canonical
bytes and by fingerprint rather than field by field; every variable list that is not
the original IDs — none, one missing, one renamed, one duplicated, one extra — is
asserted to be refused in its own category, and the refusal is shown to be
load-bearing by disabling it and observing that contract fail.
Requirements 6-11: explicit tolerances, independent dense oracle, exhaustive tiny
assignments, cancellation scaling, overflow and discrete boundaries. Requirement
12: CLI success, infeasibility, input, size, argument, numerical-error and failed
output contracts. JSON tests reject positional records and object-wrapped enums
both directly and nested in model/candidate documents. Linux output tests cover
full-device and closed-pipe errors for structural and candidate reports.
All run through bash tools/check.sh. Fixtures cover infeasible, unbounded,
degenerate, poorly scaled and overflow-prone models without solver classification.
Generated tests enumerate a fixed finite space without random seeds.

## Open Questions

None for M1. Solver statuses, transformations, LP/MPS and backend tolerance
interoperability require later specifications.
