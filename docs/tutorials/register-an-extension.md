# Register an Extension and Verify the Run

This walks through the C8 registry under
[SPEC-0009](../specifications/SPEC-0009-extension-registry.md): registering a
candidate producer from a registry document, running a search with it, and
re-executing that run from its record alone.

The last step is the reason the registry exists. Before it, a search that named an
extension was refused outright, and a scheduling run performed with the NEH producer
could not be verified at all.

Every command needs the pinned native library. Run `bash tools/setup_highs.sh`
first if you have not.

## 1. Read the registry

```bash
optimizer registry list --registry examples/extension-registry-v1.json
```

Each entry reports what it claims — version, license, category, determinism, data
and hardware needs, promotion state — plus `provided_by_this_build`, which says
whether this binary can actually construct it. The two facts are separate: an
identity this build does not provide is refused at resolution rather than skipped.

A listed entry is only a claim. Resolution checks every field against what the
extension itself declares and refuses a mismatch in either direction, so a registry
cannot grant an extension a category, an authority or a version it does not have.

## 2. Check conformance

```bash
optimizer registry check --registry examples/extension-registry-v1.json \
  --extension flow-shop-neh --instance examples/flow-shop-v1.json \
  --output artifacts/conformance.json
```

This runs the reusable suite over a fixed grid of six tiny models with unlimited
budgets, and records whether the extension left the outcome, the proven optimum,
the dual bound, the forfeiture state and both prune counters exactly as an
extension-free run left them. It asserts the extension was actually invoked before
asserting anything about its effect, so a record cannot pass because nothing ran.

The record carries no timing and no solution quality. A passing record means the
contract held; it never means the extension helped. Whether an extension improves a
search is a C7 question.

To promote an entry, cite the record and its checksum:

```bash
sha256sum artifacts/conformance.json
```

Then set the entry's `promotion` to `{"state": "promoted", "conformance_path": ...,
"conformance_sha256": ...}`. Resolution reads the record, re-hashes it, and requires
a passing outcome for that exact extension and version. An entry left
`experimental` needs `--allow-experimental` at every command, and the record it
produces carries a warning naming it.

## 3. Run a search with the extension

```bash
optimizer schedule solve --instance examples/flow-shop-v1.json \
  --config examples/search-config-neh-v3.json \
  --registry examples/extension-registry-v1.json \
  --output artifacts/schedule-run.json \
  --output-model artifacts/schedule-model.json
```

The configuration's `extensions` list names `flow-shop-neh` with counted invocation
and proposal budgets. The registry is what turns that name into a running
extension; without `--registry` the run is refused, because there is deliberately
no default registry location and no discovery. A run's extensions depend on the
command, not on the filesystem.

The example instance is three jobs on two machines with minimum makespan 7. The
record reports `proven_optimal` with objective 7, and its embedded
`search.extensions` summary shows the producer registered, invoked, and its
proposal accepted. The objective is always the core's own recomputation; a
producer's claimed objective is never read.

The encoded model is written separately because a run record's fingerprint is
computed from the model that was searched, which for a scheduling run is the
encoding rather than the instance.

## 4. Verify by re-execution

```bash
optimizer verify --record artifacts/schedule-run.json \
  --model artifacts/schedule-model.json \
  --instance examples/flow-shop-v1.json \
  --registry examples/extension-registry-v1.json
```

Verification reads only the configuration embedded in the record, resolves the
extensions it names, re-runs the search, and compares the two records on ten
fields. It never reads the recorded outcome as an input. The instance is supplied
because the producer is built from one and a run record does not embed it.

`agreement: true` with exit 0 means the two runs matched. It is evidence of
determinism on this host with this library, and nothing more: it is not a proof of
optimality, and a forfeited record stays forfeited however often it agrees.

Three things are refused rather than reported as divergence, because each would
otherwise blame the record for a property of the verifier's inputs:

- omitting `--registry`, since nothing could reconstruct the named extension;
- a registry resolving a different version of that extension;
- a record whose extension declared itself nondeterministic, for which SPEC-0004
  withholds replay equality in the first place.

If the two runs disagree on a compared field, verification names the field and
exits 2. It may add notes about a changed backend library, revision or compiler,
and about an extension whose counters moved. Those notes explain a divergence and
never decide one; the ten compared fields decide it.

## What this does not do

The registry resolves extensions this build provides. It cannot load a separately
distributed native extension, which would need a second unsafe boundary ADR-0003
prohibits, and it refuses an entry requiring a GPU because no device selection
exists yet. Both refusals are explicit, and both remain recorded in
[known failures](../../state/known-failures.md).

A run record names each extension's identity and version but not the registry
document itself, so licenses and promotion state are auditable through the registry
rather than through the record.
