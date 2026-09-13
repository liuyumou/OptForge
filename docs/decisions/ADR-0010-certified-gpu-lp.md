# ADR-0010: Approximate GPU Linear Programming with Host-Certified Bounds

Status: accepted
Owner: numerical backend
Introduced: C6
Last reviewed commit: 7ec4f53
Superseded by: none; ADR-0001 through ADR-0009 remain in force

## Context

A first-order linear programming method computes approximate primal and dual
iterates. It never produces a basis, it never produces an exact vertex, and its
residuals are small rather than zero. The research plan already anticipated the
hazard this creates: "A GPU algorithm that finds a useful approximate LP solution is
not automatically suitable for branch-and-bound pruning. Accept bounds and
termination claims only through numerically justified procedures."

That sentence names a hazard without resolving it, and the resolution is not obvious.
The tempting move is to declare a bound once the residuals fall below the caller's
tolerance. It is wrong for a reason that has nothing to do with tolerances: the
residuals are computed by the same device, in the same kernels, from the same
iterates, as the bound they would be vouching for. A device that is wrong is wrong in
both. The project has refused this shape of argument before — SPEC-0008 requirement 8
makes the makespan recurrence architecturally independent of everything that proposes
a schedule, precisely so that agreement between them is evidence rather than a
tautology — and the same standard applies here.

There is a second, structurally similar question about what the backend may be asked
to do at all. With one backend, "can this solve my model" was answered by the fact
that there was nothing else to call. With two, and with one of them unable to handle
a discrete variable, a caller that reaches the wrong one must be refused.

## Decision

**The device proposes; the host certifies.** The device computes iterates. Every
claim attached to them — objective, feasibility, bound, termination — is produced on
the host, in `f64`, from the original model. Three computations already exist for the
first two: SPEC-0002 recomputes the objective, `Model::evaluate` decides feasibility,
and SPEC-0003 owns termination. This record adds the third and supplies the missing
one, the bound.

**Certification takes the dual iterate as untrusted input and repairs it, rather than
checking it.** Given the dual iterate `y`, the host projects it onto the multipliers
its rows admit, computes the reduced costs from the original model's own coefficients,
and bounds each variable's contribution by that variable's own bound. The result is a
dual-feasible point, and weak duality makes its objective a valid bound on the primal
optimum. The device's `y` is a guess about where to look; the host's arithmetic is what
makes the answer a bound. This is why the procedure is a certification and not a test.

The repair is available on the row side unconditionally, because projecting `y` breaks
no identity. It is not available on the column side, and an earlier wording here said
the needed bound is always finite. That is true of every model this project currently
produces — each node relaxation is boxed by construction and the flow-shop encoding is
all-binary — and false of a `model-v1` document in general, which may declare a free
variable. The reduced cost is determined by the repaired `y`, so adjusting one reduced
cost on its own falsifies the identity the bound rests on, and where the needed bound
is infinite no finite number bounds that variable's contribution. The honest outcome
there is no bound at all, reported as an absent bound naming the variable that blocked
it. Substituting a large finite number would fabricate a bound and is precisely what
this record exists to forbid.

**A bad guess yields a weak bound, never an invalid one.** This is the property that
makes the decision safe rather than merely careful, and it is what SPEC-0011
requirement 13 asserts. A correctness argument that only works when the device is
nearly right would be an optimality test wearing a certificate's name, and would fail
exactly when it mattered.

**`Optimal` requires two independent things to agree, neither of them from the
device.** A certified bound, and a candidate that `Model::evaluate` has already
accepted, must close to within the caller's tolerances. Every other outcome uses an
existing `Termination` that makes no proof claim. No new variant is introduced, and
that is worth stating as evidence rather than as convenience: SPEC-0002's enumeration
already distinguished "a validated feasible candidate without a proof of optimality"
from optimality, so the approximate case was anticipated four capabilities ago.

**A backend declares its capabilities, and the declaration is the backend's, not the
caller's.** A request outside the declaration terminates as `Unsupported` before any
work. This backend refuses every model with a discrete variable. The rule mirrors the
extension authority model, where an extension's authority follows from its category
and cannot be widened by its own claim, and it exists for the same reason: the
component that would benefit from a wider boundary must not be the one that draws it.

**The CPU backend stays the default, and dispatch is measured rather than assumed.**
A threshold must be a recorded measurement expressed in a property known before
solving. The engine's own node relaxations are small and warm-startable, which is the
regime where first-order methods are weakest, so this backend is expected to be
dispatched at the root and on large models rather than inside the node loop.

**`f64` throughout, and no reduced-precision iteration.** Compute capability 12.0
runs FP64 at one sixty-fourth of FP32, which is why a first-order method is specified
here and a factorizing one is not: a sparse matrix-vector product has an arithmetic
intensity near 0.17 operations per byte against a ratio of peak FP64 to peak bandwidth
near 0.91 on this hardware, so it is bandwidth-bound with roughly fivefold headroom
and the segmentation never binds. That argument holds only for `f64` SpMV. Dropping to
FP32 would trade a bottleneck we do not have for residuals comparable to the caller's
tolerances, which would undermine certification to buy throughput that is not
available to spend.

## Alternatives

**Declare a bound when residuals fall below tolerance.** Simple, fast, and what a
naive reading of "the solver converged" suggests. Rejected because the residuals and
the bound share an author. This is the tautology SPEC-0008 requirement 8 exists to
prevent, arriving from a different direction.

**Return only candidates and warm starts, never a bound.** Safe, and genuinely
tempting: it needs no new argument, and it is what the implementation plan's own
wording ("approximate results remain candidates or warm starts until justified bounds
and statuses exist") describes as the starting position. Rejected because "until
justified bounds exist" is an invitation to justify them, the justification is short,
and deferring it would leave the backend unable to contribute to a proof at all —
which would make its value hard to evaluate and easy to overstate on throughput
alone.

**Verify the device's bound on the host instead of recomputing it.** Cheaper, and
sufficient when the device is merely imprecise. Rejected because verifying a claimed
bound requires the same host-side dual-feasibility work as constructing one, so it
costs what certification costs and buys a weaker statement.

**Use a vendor library for the kernels.** Faster to working code, and the tuned
implementations are better than ours will be at first. Rejected for this slice
because reduction order inside a vendor library is not ours to fix, and SPEC-0011
requirements 6 to 8 make bitwise reproducibility on one device a contract. Revisit
with a record that states which determinism claim is being given up.

**Solve mixed-integer models on the device.** Rejected as out of scope and as
premature. SPEC-0003 requirement 23 fixes the node loop as sequential, and the
published work that does accelerate mixed-integer solving on a device accelerates
primal heuristics while the dual side stays on the CPU — which is the arrangement
this project already has, with C3's producers on one side and the owned executive on
the other.

## Consequences

The engine can now obtain a dual bound from a method that proves nothing, which is a
capability it has not had, and the entire safety of that rests on one host-side
procedure. That procedure is therefore load-bearing in a way little else in the
project is, and it is tested for validity far from optimality rather than only near
it.

Costs and limits, each recorded rather than absorbed:

- A certified bound is expected to be weaker than the CPU backend's. Whether it is
  ever strong enough to prune usefully is unknown, and SPEC-0011 requirement 22
  deliberately asks only that it be valid and demonstrably weaker. A valid useless
  bound is still a correct bound.
- Certification costs a pass over the nonzeros on the host, so it is not free and it
  partly offsets the device's advantage. It is charged to the solve in the recorded
  end-to-end timing rather than excluded from it.
- This backend produces no basis, so it cannot warm-start the CPU backend. Crossover
  to a basic solution is not attempted.
- Determinism here is a property of a fixed reduction order, not of the arithmetic,
  and it is lost the moment an atomic accumulation is introduced. The integer
  evaluator in SPEC-0010 has the stronger property for free; this one does not.
- Presolve and scaling would change both convergence and certification. They belong
  to Stage 5 and this record does not anticipate their interaction.

Follow-up work, each needing its own contract: crossover to a basic solution,
presolve and scaling for a first-order method, and whether a certified bound can be
strengthened enough to be worth pruning with.

## Implementation and Tests

This record is accepted before its implementation, as ADR-0004 through ADR-0009 each
were.

Implementation: [SPEC-0011](../specifications/SPEC-0011-gpu-lp-backend.md), the
capability declaration in `optimizer-core`, the kernels under `cuda/`, and the
certification on the host beside the backend.

Acceptance evidence is SPEC-0011's mapped tests, and in particular the two that can
fail: the certified bound asserted valid on deliberately early-stopped iterates, and
asserted strictly weaker than the pinned CPU backend's bound on at least one
instance. A certificate that only ever agrees has not been shown to be one.
