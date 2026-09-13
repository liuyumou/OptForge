# ADR-0011: A Scale Split for Crossover Measurement

Status: accepted
Owner: heterogeneous computation
Introduced: C6
Last reviewed commit: c547f0c
Superseded by: none; ADR-0001 through ADR-0010 remain in force

## Context

SPEC-0008 requirement 24 and the benchmark protocol both require a decision record
before a split changes, and the development subset's own documentation says that
enlarging it or changing a seed in it is a split change. C6 needs instances the
existing split cannot provide, so this record makes that change explicitly rather
than by addition.

The frozen C5 subset is ten instances of one shape: twenty jobs and five machines.
That is the right sample for the question C5 asks, which is whether an encoding and a
recurrence are correct — ten instances of one shape exercise the same code paths ten
times, and correctness does not vary with shape. It is the wrong sample for the
question C6 asks. A full construction on that shape is roughly 1.3e4 integer
operations, tens of microseconds of tuned CPU work. A device measured only there
would lose, the report would say so, and nothing would have been learned about where
the crossover actually lies — which is the number SPEC-0010 requirement 22 makes the
CPU default depend on.

## Decision

**Add a scale split rather than enlarging the development split.** The development
subset keeps its ten instances, its shape and its seeds, so every C5 correctness
claim and every committed record that cites it is untouched. The new split has a
different purpose, a different shape distribution and a different manifest.

**Sweep shapes; do not sample one.** The scale split takes the *first* instance of
each of the paper's twelve published classes rather than ten instances of one. A
crossover is a statement about how cost grows with shape, so the split needs range on
the axis that varies. Ten per class would commit twelve times the bytes and would
answer a question about variance within a shape that nothing in C6 asks. The split
spans twenty to five hundred jobs and five to twenty machines, which is the full
published range and, not coincidentally, the full range the existing document limits
allow.

**Keep the smallest shape in the split.** Twenty jobs by five machines is where a
device is expected to lose, and including it is what makes a crossover report
falsifiable: a report that shows the device winning everywhere is evidence the
measurement excluded transfers, not evidence the device is fast. SPEC-0010's
acceptance tests state that as an expected outcome, and this is the row that can
produce it.

**Overlap the development split at `ta001`, and derive it from the same seed.** The
same instance appears in both splits. That is sound only because both generate it
from the paper's published seed rather than copying bytes between manifests, so the
two cannot drift; a contract test asserts the two derivations produce the same
instance.

**Record shapes, not names, as the identity of a measurement.** Seeds are reused
across classes in the published table — `ta051` and `ta071` share one — so a seed is
unique only together with its shape. Anything asserting uniqueness says so, and a
measurement row is labelled by shape.

**Commit no bound.** The split records no best-known makespan and no target. A
committed bound is an acceptance threshold, which SPEC-0008 requirement 26 forbids
and which this record does not reopen.

**`purpose` is `performance` and `split` is `validation`.** The split exists to be
measured, and naming it `correctness` would let a correctness gate silently acquire a
timing dependency. It is not held-out: it is visible to development, it is not sealed
evaluation data, and no result from it may be reported as a held-out effect.

## Alternatives

**Enlarge the development subset to cover more shapes.** Fewer moving parts, one
manifest. Rejected because it would change the split a completed capability's
evidence cites, for a reason that has nothing to do with that capability, and
requirement 24 exists to stop exactly that.

**Generate instances on demand instead of committing them.** Tempting, since they are
reproducible from seeds and the generator is verified against the paper's own printed
matrix. Rejected because the manifest's checksum is what detects a document edited
after generation, and a manifest with no file to check would verify the generator
against itself.

**Take all 120 published instances.** Complete, and the obvious thing to do if the
question were about solution quality. Rejected as roughly 3 MB of tracked documents
to answer a question twelve instances answer, and as an invitation to report averages
over a split that was never designed to support them.

**Use random shapes beyond the published range.** Rejected: the existing document
limits stop at five hundred jobs and twenty machines, the published generator is what
makes provenance checkable, and raising a limit is its own change with its own
record.

## Consequences

The repository gains roughly 280 KB of tracked instance documents, which is the cost
of checkable provenance and is small enough not to need a hosting decision.

Costs and limits, each recorded rather than absorbed:

- One instance per shape means a crossover located on this split is located on one
  instance per shape. Variance within a shape is unmeasured and no claim about it may
  be made from this split.
- The split is visible during development, so no result from it is held-out evidence.
  Stage 4's held-out comparison needs a split this record does not create.
- The 500-job instance is near the document limits, so a later limit increase changes
  what the largest row means and needs its own record.
- Adding shapes later is another split change and another record. That is the point.

## Implementation and tests

Implementation: the `SCALE_SUBSET` table in
[the generator](../../crates/optimizer-schedule/src/generate.rs), the committed
documents under `benchmarks/instances/flow-shop/`, and
`benchmarks/manifests/taillard-flow-shop-scale-v1.json`.

Tests: `the_scale_subset_sweeps_published_shapes` asserts coverage, shape uniqueness,
seed-and-shape uniqueness, the document limits and the cross-split agreement at
`ta001`. In Python, `test_the_scale_manifest_regenerates_from_its_recorded_seeds`
reproduces every committed document from its recorded seed with an independently
written generator and checks its checksum, and
`test_a_wrong_seed_and_a_transposed_loop_order_both_disagree` establishes that the
reproduction check can fail.
