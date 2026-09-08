# Validate an Original Model and Candidate

Purpose: run the M1 Rust numerical authority through the CLI. Prerequisites: the
[build environment](../operations/build.md). Contract:
[SPEC-0001](../specifications/SPEC-0001-model-and-validation.md).

## Check Model Structure

```bash
cargo run -p optimizer-cli -- model validate --model examples/model-v1.json
```

The JSON response has schema_version 1, model_id tiny-mixed and status
structurally_valid. Exit code 0 establishes valid structure, not feasibility or
boundedness. The model has binary variable 3, continuous variable 8, a row requiring
their sum to be at least 2, and objective 0.5 + 2*x3 + x8.

## Evaluate a Candidate

```bash
cargo run -p optimizer-cli -- model validate \
  --model examples/model-v1.json \
  --candidate examples/candidate-v1.json \
  --absolute-tolerance 0 \
  --relative-tolerance 0 \
  --integrality-tolerance 0
```

This candidate supplies x3=1 and x8=1. The report has feasible=true, objective=3.5
and row activity=2.0, and the command exits 0. The zeros here are explicit tutorial
choices, not solver defaults. For a candidate with x3=0.5 and x8=1, the report has
feasible=false, objective=2.5, binary violation=0.5 and lower row violation=0.5;
the command exits 1. Objective recomputation is retained even for rejected candidates.

Reports include each raw violation and applied allowance. Row allowance is
absolute + relative * max(abs(activity), abs(bound), sum(abs(coefficient*value))).
Large cancelling contributions can therefore permit larger residuals. Bounds and
integer/binary domain membership are checked independently, without rounding values.

## Rust Interface

```rust
use optimizer_core::{Candidate, Model, Tolerances};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let model = Model::from_json(&std::fs::read("examples/model-v1.json")?)?;
    let candidate = Candidate::from_json(&std::fs::read("examples/candidate-v1.json")?)?;
    let report = model.evaluate(&candidate, Tolerances {
        absolute: 0.0,
        relative: 0.0,
        integrality: 0.0,
    })?;
    assert!(report.feasible);
    assert_eq!(report.objective, 3.5);
    Ok(())
}
```

Model::new accepts a ModelDocument and validates it into immutable canonical
storage. Model::document exposes read-only original data; to_json produces stable
ID ordering without merging duplicate terms. Duplicates are rejected.

## Errors and Limits

All three tolerances are required with --candidate; none may appear without it.
File paths preserve native OS names, including non-UTF-8 Unix names. Commands,
flags and tolerance values require UTF-8 text.

Malformed arguments, input I/O, invalid documents/models/candidates, invalid
tolerances and nonfinite arithmetic produce a categorized stderr diagnostic,
no report, and exit code 2. Output write or flush failures also return an io
diagnostic and exit 2; any bytes already delivered cannot be retracted. Both files
are limited to 16 MiB. JSON formats are versioned and reject unknown fields,
duplicate fields, nonfinite numbers and unsupported versions.

The command performs CPU validation only. It does not solve, report optimality,
create experiment solve records, or run GPU work.
