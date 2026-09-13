# Architecture

Purpose: define stable ownership boundaries. Scope: M0-M1, C1, C2, C3 and C4, plus planned dependencies.
Owner: architecture. Status: accepted.
Last reviewed commit: a789759.

## Implemented boundaries

The CLI delegates inventory and advisory ownership to optimizer-cuda. That crate
uses nvidia-smi and standard-library file locks without linking CUDA.
optimizer-experiment embeds the versioned JSON Schemas. Python validation tools
apply the schemas and cross-record provenance checks.

optimizer-core stores immutable validated original linear models. Rust and
versioned JSON share construction checks. Candidate evaluation recomputes objective,
row activities, bounds and domains using explicit caller tolerances. The CLI reads
bounded model/candidate files and returns validation reports. See
[SPEC-0001](../specifications/SPEC-0001-model-and-validation.md) and
[ADR-0002](../decisions/ADR-0002-model-validation.md).

optimizer-core also owns the backend-neutral solve contract: explicit solve
options, cooperative cancellation, engine-owned termination, model-bound warm
starts and reproducible records. optimizer-highs implements it against the pinned
CPU HiGHS 1.11.0 build behind a private FFI boundary, and the CLI exposes it as
`optimizer solve`. See
[SPEC-0002](../specifications/SPEC-0002-backend-contract.md) and
[ADR-0003](../decisions/ADR-0003-highs-backend.md).

optimizer-experiment owns the run record: one search record embedded verbatim
plus the provenance needed to repeat it, and the field-by-field comparison that
decides whether a repeat agreed. The CLI exposes it as `optimizer search` and
`optimizer verify`, which is the first surface reaching the executive from
outside Rust test code. Verification re-runs using only the record's embedded
configuration, so it cannot confirm its own input, and a record is bound to model
bytes by fingerprint rather than by `model_id`. Agreement is evidence of
determinism on one host; it adds no mathematical authority and cannot clear a
forfeited proof claim. See
[SPEC-0005](../specifications/SPEC-0005-run-surface.md) and
[ADR-0006](../decisions/ADR-0006-run-provenance.md).

## Planned numerical flow

Original model -> optimizer-core validation -> optimizer-solver executive ->
optimizer-highs LP backend and optimizer-schedule candidate production ->
optimizer-core result validation -> experiment record and CLI.

C4 closes the last leg for search: the CLI drives the executive and
optimizer-experiment wraps its record with provenance, so the flow runs end to
end without an agent. C5 completes the flow's first application under
[SPEC-0008](../specifications/SPEC-0008-flow-shop.md): a scheduling instance is
encoded into an ordinary optimizer-core model, so the existing legs carry it
unchanged rather than gaining a parallel scheduling path, and a makespan recurrence
independent of every heuristic is the authority on what a resulting schedule costs.
optimizer-schedule-examples holds the NEH and insertion producers and depends only
on the published core, extension and scheduling APIs.

C8 connects the extension leg to that flow under
[SPEC-0009](../specifications/SPEC-0009-extension-registry.md). optimizer-registry
turns a recorded extension identity into a registration the executive already
accepts, and refuses anything it cannot check against the extension's own
declaration. It names no extension itself: the concrete provider table lives in
optimizer-cli, which is the same arrangement that keeps `&dyn Backend` free of
HiGHS and `&[Registration]` free of any particular extension. The consequence for
the flow is that a search naming an extension now runs, and its record re-executes,
which is what makes the reproducibility leg cover extension-influenced runs rather
than only extension-free ones.

C1 implements the backend leg of this flow: the CLI drives optimizer-highs
directly through the backend-neutral contract in optimizer-core, and every
extracted candidate returns through optimizer-core validation before publication.

C2 implements the executive leg under
[SPEC-0003](../specifications/SPEC-0003-solver-executive.md) and
[ADR-0004](../decisions/ADR-0004-owned-search.md). optimizer-solver owns node
state, budgets, cancellation, incumbent acceptance and proof completion, and
consumes the C1 `Backend` trait purely as a relaxation service. It does not
depend on optimizer-highs, so its correctness contracts run without a native
library; the end-to-end test over pinned HiGHS lives in optimizer-highs instead.

Two proof claims stay distinct. A backend `Termination` describes one relaxation
solve; a `SearchOutcome` describes whether the executive exhausted its node tree.
A relaxation objective becomes a dual bound only when that relaxation proved
optimality, and any other termination forfeits the search's proof claim.

The core owns feasibility, objective recomputation, and mathematical status.
Extensions may propose candidates or actions; the core must validate them.
C3 implements that rule under
[SPEC-0004](../specifications/SPEC-0004-extension-runtime.md) and
[ADR-0005](../decisions/ADR-0005-extension-authority.md). optimizer-extension
owns the declaration document, the authority model derived from an extension's
category, and the guarded host that counts budgets and contains panics.
optimizer-solver validates every proposal with `Model::evaluate` against the
original model and every action against its real frontier and its own
recomputed branchable set. No extension path can forfeit a proof claim, end a
search, or return an error, so an adversarial extension cannot deny a proof the
engine would otherwise complete. Containment covers panics, not a process abort;
process isolation and dynamically loaded native extensions are deferred.

Raw native handles remain inside the corresponding FFI crate.
M1 defines candidate numerical tolerances. C1 records backend termination under
explicit native settings; owned proof contracts belong to C2.

## Ownership and resources

| Crate | Responsibility | First behavior |
| --- | --- | --- |
| optimizer-core | Original models, numerical validation, solve contract | M1 / C1 |
| optimizer-highs | Safe backend lifecycle and status mapping | C1 |
| optimizer-schedule | Flow-shop instances, recurrence, encoding and heuristics | C5 |
| optimizer-schedule-examples | Independently authored scheduling candidate producers | C5 |
| optimizer-solver | Search executive, branch and bound | C2 |
| optimizer-extension | Extension declarations, authority model, guarded host | C3 |
| optimizer-extension-examples | Independently authored and adversarial extensions | C3 |
| optimizer-registry | Registry documents, resolution, conformance suite | C8 |
| optimizer-cuda | Discovery, ownership, device selection and residency | M0 / C6 |
| optimizer-cuda-sys | The CUDA driver boundary and its owned handles | C6 |
| optimizer-experiment | Artifact schemas, run records, verification comparison | M0 / C4 |
| optimizer-cli | Agent-independent command interface | M0 / C4 |

optimizer-highs and optimizer-cuda-sys are the only crates permitted to contain
unsafe code. Because a workspace-level `forbid` cannot be relaxed by an inner crate,
each declares its own lints rather than inheriting the workspace lints; every other
runtime crate keeps the prohibition. See
[ADR-0003](../decisions/ADR-0003-highs-backend.md) and
[ADR-0009](../decisions/ADR-0009-cuda-driver-boundary.md). The extension runtime
keeps the prohibition too, which is why C3 specifies the versioned C boundary without
implementing it: ADR-0009 authorizes one boundary for CUDA and no other, so a
dynamically loaded native extension still needs its own decision record. See
[ADR-0005](../decisions/ADR-0005-extension-authority.md).

The split between the two GPU crates is deliberate. optimizer-cuda-sys holds the
foreign declarations and the owned handles and knows nothing about optimization;
optimizer-cuda keeps discovery, the lease, device selection and residency, and keeps
`unsafe_code = "forbid"`. Every existing GPU consumer depends on the second, so
adding a kernel path does not make the crate they already use unsafe.

All GPU devices share one host lease, so a search uses at most one device and the
selected device is one field on its configuration rather than one per component.
Selection uses UUIDs and the driver-reported UUID is read back and compared, so a
record cannot claim hardware the run did not use. Transfers and batching are explicit
and timings include them. Multi-GPU work is deferred. See
[ADR-0001](../decisions/ADR-0001-bootstrap-boundaries.md),
[SPEC-0010](../specifications/SPEC-0010-heterogeneous-computation.md),
[lease implementation](../../crates/optimizer-cuda/src/lib.rs), and
[acceptance tests](../../crates/optimizer-cli/tests/cli.rs).

C6's device leg is now partly built. `optimizer-cuda-sys` resolves the driver at
runtime and owns every handle; `optimizer-cuda` holds the lease, decides
admissibility before any allocation, and keeps an instance resident across calls. Two
integer kernels evaluate flow-shop schedules and agree with the recurrence exactly.
Nothing above them dispatches to a device yet, so the leg reaches the flow only from
test code, which is the same gap C8 closed for extensions.

C6 adds the device leg of the numerical flow, under
[SPEC-0010](../specifications/SPEC-0010-heterogeneous-computation.md) and
[SPEC-0011](../specifications/SPEC-0011-gpu-lp-backend.md). It reaches the flow at
two points and at neither does it gain authority. A batched integer evaluator reaches
it through the C3 candidate-producer seam, which already returns a batch and whose
output `Model::evaluate` already validates, so a wrong kernel produces a recorded
refusal rather than a wrong answer. A first-order LP backend reaches it through the
C1 `Backend` trait, which gains a capability declaration so that a caller reaching a
backend that cannot solve its model is refused rather than answered; its approximate
iterates become a bound only through a host-side certification that does not assume
the device computed correctly. See
[ADR-0010](../decisions/ADR-0010-certified-gpu-lp.md).
