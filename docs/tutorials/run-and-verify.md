# Run and verify a search

Purpose: run one owned search, read its record, and check that the record is
enough to repeat it. Scope: C4, SPEC-0005.

This assumes the pinned HiGHS build is provisioned:

```bash
bash tools/setup_highs.sh
```

## Run a search

Search configuration is a strict versioned JSON document at version 2. Every
budget is explicit and there are no defaults, so a record always states what
produced it:

```json
{
  "schema_version": 2,
  "seed": 17,
  "node_limit": null,
  "time_limit_ms": 10000,
  "open_node_limit": null,
  "improvement_tolerance": 1e-9,
  "relaxation": {
    "schema_version": 1,
    "seed": 17,
    "time_limit_ms": 10000,
    "iteration_limit": null,
    "node_limit": null,
    "tolerances": {"absolute": 1e-9, "relative": 1e-9, "integrality": 1e-9},
    "threads": 1
  },
  "extensions": []
}
```

A `null` budget means unlimited. The nested `relaxation` block is the SPEC-0002
solve configuration applied to every node.

```bash
cargo run -p optimizer-cli -- search \
  --model examples/model-v1.json \
  --config examples/search-config-v3.json \
  --output artifacts/run.json
```

The example model minimizes `2 x3 + x8 + 0.5` subject to `x3 + x8 >= 2`, with
`x3` binary and `x8` continuous and nonnegative. The record reports
`"outcome": "proven_optimal"` and `"objective": 2.5` for `x3 = 0`, `x8 = 2`,
matching the [C1 solve](solve-a-model.md) of the same model. Without `--output`
the record is written to standard output instead.

## Read the record

A run record has two parts: provenance, and the search record embedded verbatim.

- `revision` and `dirty` identify the source. A dirty record describes a tree no
  revision can reconstruct, so it must not be presented as reproducible evidence.
- `model_fingerprint` is a hash of the canonical model document. It identifies
  model *bytes*, not model identity, which is what lets verification refuse a
  model edited under an unchanged `model_id`.
- `inputs` carries the SHA-256 of each document actually read, so the record
  identifies the bytes it consumed rather than only their paths.
- `hardware` and `toolchain` use the same field names as an
  [experiment result](../specifications/SPEC-0007-artifacts.md), so the two
  provenance shapes cannot drift apart. A CPU run leaves the GPU fields null.
- `search` is the complete SPEC-0003 record: outcome, recomputed objective, dual
  bound, node counters, `forfeited`, per-extension summaries and the exact
  configuration used. Nothing is summarized away.

Inside `search`, `outcome` is the executive's own claim. `proven_optimal`,
`proven_infeasible` and `unbounded_or_infeasible` are completed proofs; a limit or
interruption never is. `forfeited` records whether the search lost its proof
claim, so a completed-looking search that claimed nothing says why.

## Verify it

```bash
cargo run -p optimizer-cli -- verify \
  --record artifacts/run.json --model examples/model-v1.json
```

Verification re-runs the search using only the configuration embedded in the
record and the model file it is given. It never reads the recorded outcome,
objective, bound or counters as inputs — a verifier that did would confirm its own
input. It then compares ten fields and prints a verdict naming them.

Two things it deliberately does not do. It does not compare measured elapsed
time, which describes the host rather than the search. And it does not strengthen
any claim: agreement establishes that the search is repeatable on this host with
this library, not that its answer is correct, and a forfeited search stays
forfeited after it verifies.

The verdict also reports `environment_differs`. When the backend library, source
revision or compiler differs from the one the record names, each difference is
listed. This is explanation, not a decision: a record from another build still
verifies when its search agrees, and a divergence still fails when it does not.
The backend library is called out separately because a rebuilt or upgraded library
can legitimately change a search's counters, whereas a moved revision on its own
cannot.

## Confirm that verification can fail

A check that cannot fail is worth nothing, so both refusals are worth seeing.

Change a coefficient while leaving `model_id` alone, and the record is refused
before any search runs:

```bash
sed 's/"coefficient": 2.0/"coefficient": 2.5/' examples/model-v1.json > /tmp/changed.json
cargo run -p optimizer-cli -- verify \
  --record artifacts/run.json --model /tmp/changed.json
```

```
optimizer: document: model fingerprint mismatch: record fnv1a64:…, supplied fnv1a64:…
```

Edit a recorded measurement, and the re-run disagrees with it by name:

```bash
sed 's/"objective": 2.5,/"objective": 1.5,/' artifacts/run.json > /tmp/mutated.json
cargo run -p optimizer-cli -- verify \
  --record /tmp/mutated.json --model examples/model-v1.json
```

```
optimizer: divergence: numerical: objective: recorded 1.5, reproduced 2.5
```

## Extensions

This surface loads no extensions. A configuration whose `extensions` list names
one is refused with an `unsupported:` diagnostic rather than run without it,
because the resulting record would describe a search you did not request. The
local registry that would populate that list is deferred; see
[known failures](../../state/known-failures.md).

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Completed outcome, or verification agreement |
| 1 | A budget was reached or the outcome is unresolved |
| 130 | The search was interrupted |
| 2 | Argument, I/O, document, unsupported, numerical or backend error, or divergence |

A search that reaches a limit or is interrupted still writes its record: an
unfinished search is a fact about a run, and the record states what happened. Only
a run that could not start writes nothing. Errors write no partial document to
standard output.

See the [run surface contract](../specifications/SPEC-0005-run-surface.md) for the
normative requirements, [ADR-0006](../decisions/ADR-0006-run-provenance.md) for
why reproducibility is defined as re-execution, and
[solve a model](solve-a-model.md) for the single-backend solve this search builds
on.
