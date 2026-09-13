# SPEC-0011: GPU Linear Programming Backend

Status: accepted
Scope: backend capability declaration on the solve contract, the first-order LP method, and its certification
Owner: numerical backend
Introduced: C6
Last reviewed commit: pending
Supersedes: none; extends SPEC-0002 with a capability declaration
Implementation: pending
Tests: pending

## Purpose

Add a second backend that is not a replacement for the first. It solves linear
programs with a first-order method whose kernels run on a device, and it produces
approximate primal and dual iterates. This contract fixes what such a backend may
claim, which is much less than what it computes: an approximate solution becomes a
candidate or a warm start by default, and becomes a dual bound only through a
host-side certification procedure that is exact in `f64` and independent of the
device.

It also adds the concept the backend contract has never needed: a capability
declaration. With one backend, "what can this solve" was answered by the single
implementation. With two, a caller selecting the wrong one must be refused rather
than given a silently wrong answer.

Excluded: device selection, residency, lease ownership, transfer timing, fallback,
cancellation and reset recovery, all of which
[SPEC-0010](SPEC-0010-heterogeneous-computation.md) owns and this contract reuses
unchanged; mixed-integer solving on a device (the node loop stays on the CPU under
SPEC-0003 requirement 23); presolve, scaling and reoptimization (Stage 5, each
needing its own contract); interior-point and simplex methods on a device
(unsupported at compute capability 12.0 for the reason recorded under State and
Invariants); crossover to a basic solution; multi-device and distributed solving.

## Terminology

A *first-order method* solves a linear program by repeated matrix-vector products
and vector updates, without factorization. This contract's method is restarted
primal-dual hybrid gradient with a Halpern update, adaptive restart and a
proportional-integral-derivative primal weight. An *iterate* is the pair of primal and
dual vectors at one iteration. An *approximate solution* is an iterate whose
residuals are small but not zero. A *certified bound* is a number the host has proved
to be a valid bound on the original model by an argument that does not assume the
device computed anything correctly. *Weak duality* is the fact that any dual-feasible
vector gives a bound on the primal optimum; it holds regardless of how that vector
was found, which is the property this contract rests on.

## Requirements

### Capability declaration

1. A backend MUST declare its capabilities, and a caller MUST NOT be required to know
   which implementation it holds in order to know what that implementation supports.
2. A capability declaration MUST state the problem classes the backend accepts, the
   arithmetic width it uses, whether it accepts a warm start, and whether it executes
   on a device.
3. A request outside a backend's declared capabilities MUST terminate as
   `Unsupported` rather than be attempted. In particular this backend MUST refuse a
   model with an integer or binary variable, because a first-order method has no
   branch-and-bound and returning a relaxed answer to a discrete request would be a
   wrong answer rather than a refused one.
4. A capability declaration MUST be a property of the backend, not of the request. A
   caller MUST NOT be able to widen it, matching the rule that an extension's
   authority follows from its category rather than from its own claim.

### Method and arithmetic

5. Device arithmetic MUST be `f64` throughout. Reduced-precision or mixed-precision
   iteration MUST NOT be introduced by this contract, because the certification in
   requirements 11 to 14 depends on residuals whose magnitudes are comparable to the
   caller's tolerances.
6. The constraint matrix MUST be held in both row-major and column-major compressed
   forms, so that neither product requires atomic accumulation. This is a determinism
   requirement before it is a performance one: floating-point addition is not
   associative, so an atomic reduction would make a result depend on scheduling.
7. Every reduction MUST use a fixed partition and a fixed tree order, independent of
   launch configuration and of the number of multiprocessors actually resident.
8. A result MUST be bitwise reproducible for a fixed input on a fixed device and a
   fixed code object, matching SPEC-0010 requirement 31. Cross-device bitwise
   reproducibility MUST NOT be claimed.
9. Diagonal preconditioning MUST be recorded as part of the settings that produced a
   record, because it changes the iterates and therefore the result.
10. The iteration limit and the termination check interval MUST be caller-supplied
    and MUST be recorded. A method that checks termination every iteration
    synchronizes the device every iteration; the interval is therefore a real
    parameter and MUST NOT be hidden.

### Authority and certification

11. An iterate MUST NOT become a dual bound by having small residuals. A bound MUST
    be produced only by the certification procedure, and that procedure MUST run on
    the host in `f64`.
12. Certification MUST NOT assume the device computed correctly. It MUST take the
    dual iterate as an untrusted input, repair its dual infeasibility against the
    model's own variable bounds, and evaluate the resulting weak-duality bound from
    the original model. A certification that reused the device's residuals would be
    checking the device against itself.
13. A certified bound MUST be valid even when the iterate is far from optimal. A
    procedure that can only produce a bound from a near-optimal iterate is an
    optimality test, not a certification.
14. `Termination::Optimal` MUST be returned only when a certified bound and a
    candidate already validated by `Model::evaluate` close to within the caller's
    tolerances. Every other outcome MUST use an existing termination that does not
    claim a proof.
15. A candidate produced by this backend MUST be validated against the original model
    before publication, matching SPEC-0002. The backend MUST NOT report its own
    objective.
16. An approximate result that does not certify MUST remain usable as a candidate or
    a warm start and MUST NOT forfeit anything the caller had already proved.
17. When this backend is used for a relaxation inside the owned search, a
    non-`Optimal` termination MUST forfeit the search's proof claim and MUST prune
    nothing by bound, exactly as SPEC-0003 already requires of any relaxation.

### Dispatch

18. The CPU backend MUST remain the default. Dispatch to this backend MUST be a
    caller's explicit configuration or a threshold that is a recorded measurement,
    never a constant chosen in advance.
19. A dispatch threshold MUST be expressed in a property of the model that is known
    before solving, such as its nonzero count. A threshold depending on a solve's
    outcome would not be evaluable at dispatch time.
20. Availability failure MUST fall back to the CPU backend and MUST produce the same
    conclusion, under SPEC-0010 requirements 24 and 26.

### Evidence

21. Agreement with the CPU backend MUST be demonstrated on objective value within the
    caller's tolerances, and MUST be demonstrated to be able to fail.
22. The certified bound MUST be shown to be valid and strictly weaker than the CPU
    backend's bound on at least one instance. A certificate that only ever agrees has
    not been shown to be a certificate.
23. This specification MUST NOT record a performance claim. A measured crossover is a
    property of two implementations on named hardware and MUST NOT be described as
    evidence that the engine is faster.

## Interfaces

```rust
pub struct BackendCapabilities {
    pub schema_version: u32,
    pub name: &'static str,
    pub version: &'static str,
    pub problem_classes: Vec<ProblemClass>,
    pub arithmetic: Arithmetic,
    pub warm_start: bool,
    pub device: DeviceClass,
}

pub trait Backend {
    fn capabilities(&self) -> BackendCapabilities;
    fn solve(
        &self,
        model: &Model,
        options: &SolveOptions,
        cancel: &CancellationToken,
        warm_start: Option<WarmStart<'_>>,
    ) -> Result<SolveRecord, ValidationError>;
}
```

`capabilities` is added to the existing trait; `solve` is unchanged. `HighsBackend`
declares continuous and discrete classes, `f64`, warm start, and the CPU device class,
which is a statement of what it already does rather than a change to it.

The new backend is constructed against a device that SPEC-0010 selected and leased:

```rust
CudaLpBackend::open(residency, settings) -> Result<Self, ValidationError>
```

Termination maps onto the existing enum with no new variant, which is the evidence
that the approximate case was already anticipated by SPEC-0002 rather than bolted on:

| Situation | Termination |
| --- | --- |
| Certified bound closes against a validated candidate | `Optimal` |
| Validated candidate, no certified closure | `Feasible` |
| Iteration limit reached first | `IterationLimit` |
| Caller-supplied time limit reached first | `TimeLimit` |
| Cancellation observed | `Interrupted` |
| Model has an integer or binary variable | `Unsupported` |
| Device failure, after falling back fails too | `BackendFailure` |
| Iterate cannot be accepted numerically | `NumericalFailure` |

## State and Invariants

The method is iterative and its iterates are inexact. Nothing downstream may assume
otherwise: the objective in a record is the host's recomputation under SPEC-0002, the
feasibility verdict is `Model::evaluate`'s, and the bound is the certification's.
Three independent computations therefore stand between the device and any claim, and
none of them runs on the device.

Certification rests on weak duality, which holds for *any* dual-feasible vector.
The device's role is to supply a good guess; the host's role is to repair it into a
feasible one and evaluate the bound. This is why requirement 13 can demand validity
far from optimality: a bad guess yields a weak bound, never an invalid one.

Compute capability 12.0 runs FP64 at one sixty-fourth of FP32, and that ratio is the
reason this contract specifies a first-order method rather than an interior-point
one. A sparse matrix-vector product moves roughly twelve bytes per nonzero and
performs two floating-point operations, an arithmetic intensity near 0.17 operations
per byte, against a ratio of peak FP64 to peak memory bandwidth near 0.91 on this
hardware. The product is therefore bounded by memory bandwidth with roughly fivefold
headroom before the FP64 rate could bind, and the segmentation that makes this
hardware unsuitable for factorization does not bind here. Factorization and dense
interior-point steps have the opposite intensity and are excluded for that reason,
not by preference.

Determinism does not follow from the arithmetic here, unlike the integer evaluator in
SPEC-0010. Floating-point addition is not associative, so determinism is a property of
the reduction order this contract fixes in requirements 6 and 7, and it is lost the
moment an atomic accumulation is introduced.

## Errors and Recovery

`Unsupported` is returned before any work for a request outside the declared
capabilities, including any model with a discrete variable. An availability failure
falls back to the CPU backend under SPEC-0010. An iterate that cannot be accepted
numerically is a `NumericalFailure` and is not retried on the CPU as though it were an
availability failure, because a numerically unacceptable iterate is information about
the model rather than about the device.

Cancellation is observed at the termination check interval, so its latency is bounded
by that interval rather than by the iteration limit.

## Compatibility and Versioning

`Backend` gains one method. `SolveOptions`, `SolveRecord`, `Termination` and every
solve schema are unchanged, so `solve-config-v1` and `solve-record-v1` stay at
version 1. The device is selected once for a whole search by SPEC-0010's
`search-config-v3` field, and a relaxation inherits it; this contract adds no
configuration field of its own.

The capability declaration is versioned with its own `schema_version` so that a later
capability can be added without redefining the existing ones.

## Security and Resource Limits

Device memory is dominated by two copies of the constraint matrix plus a constant
number of vectors, so its requirement is known from the model before any allocation
and is checked against free device memory before the solve begins rather than
discovered by a failed allocation. Iteration count is bounded by the caller's limit.
The device is held under the SPEC-0006 lease for the whole solve, so no other project
job contends with it.

The trust boundary is unchanged: the device is untrusted for mathematics and trusted
only to return bytes. A compromised or faulty kernel can waste time and can cause a
refusal; requirements 11 to 15 are what prevent it from causing a wrong answer.

## Examples

```bash
optimizer solve --model examples/model-v1.json --config examples/solve-config-v1.json \
  --device GPU-6721b13a-30f9-83ec-dace-ba2d9738556f
```

## Acceptance Tests

Requirements 1-4: each backend's declaration is asserted against what it actually
accepts, so a declaration cannot drift from behavior; a model with a binary variable
is refused as `Unsupported` by this backend and solved by the CPU backend, which is
what shows the refusal is a capability boundary rather than a defect; a caller
attempting to widen a declaration does not compile.

Requirements 5-10: a fixed instance solved twice on one device produces bitwise
identical iterates; a build substituting an atomic reduction is shown to break that
assertion, so the test is known to be able to fail; the recorded settings include the
preconditioner and the termination check interval, and a record missing either is
refused.

Requirements 11-17: the certified bound is asserted to be a valid bound on instances
where the iterate is deliberately stopped early, which is requirement 13; it is
asserted to be strictly weaker than the CPU backend's bound on at least one instance,
which is requirement 22; a mutated kernel returning a better-than-optimal objective
has its candidate refused by `Model::evaluate` and its bound rejected by
certification, and the search's proven optimum does not move; a non-`Optimal`
relaxation is shown to forfeit the search's proof claim and to prune nothing by
bound, reusing the C2 evidence form rather than a new one.

Requirements 18-20: the default configuration reaches the CPU backend, asserted
positively; dispatch above a recorded threshold reaches this backend, asserted
against a backend-name field in the record rather than against timing; a forced
availability failure produces the same conclusion through the CPU backend.

Requirements 21-23: differential agreement with the pinned CPU backend on objective
value across the existing LP, objective-offset, equality and ranged fixtures, with a
mutated instance shown to disagree so the comparison is known to be able to fail. No
timing is recorded in any acceptance artifact.

Device-dependent tests report an explicit skip when no device or no code object is
present, so a missing device is never counted as coverage, matching how
native-dependent tests already report a skip when the pinned library is absent. The
complete `bash tools/check.sh` gate with native acceptance covered, plus the device
suite on the labeled runner, is required before this slice is complete.

## Open Questions

Whether this backend is ever faster than the pinned CPU backend on this project's
models is a hypothesis and is deliberately unmeasured by this contract. The encoded
flow-shop models are small and their relaxations are weak, so the crossover may well
sit above every model the project currently produces; that would be a recorded
negative result under Stage 4 rather than a failure of this specification.

Whether a certified bound is ever strong enough to prune usefully is open and
separate from whether it is valid. Requirement 22 deliberately asks only that it be
valid and demonstrably weaker, because a bound that is valid and useless is still a
correct bound and the project has no evidence yet about usefulness.

Presolve and scaling would change both convergence and certification, and belong to
Stage 5 with their own contract. Crossover to a basic solution, which is what would
let this backend supply a warm start the CPU backend can use directly, is not
attempted here.
