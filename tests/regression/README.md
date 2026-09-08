# Regression Tests

Each discovered behavioral defect requires a minimized fixture, reproduction,
contract reference, and corrected-behavior assertion.

## Infinite Bound Unknown Field

[Minimized input](infinite-bound-extra-field.json) reproduced Serde's acceptance of
an extra value field on an internally tagged unit variant despite unknown-field
rejection. SPEC-0001 requirement 4 requires an error. Bound deserialization now
uses strict empty struct variants internally. Reproduce the corrected assertion:

```bash
cargo test -p optimizer-core strict_json_rejects_unknown_duplicate_and_unsupported_input --locked
```

## Alternate JSON Representations

[Positional model](positional-model.json) and [object-wrapped enums](object-enum-model.json)
previously passed validation despite violating SPEC-0001's input shapes. Records
now require objects and domain/objective enums require strings, including nested
and directly deserialized public input types. Core and CLI assertions reproduce
the corrected behavior:

```bash
cargo test -p optimizer-core json_ --locked
cargo test -p optimizer-cli --test model alternate_json_representations --locked
```

## Report Output Failure

Redirecting a structural report to /dev/full previously panicked with exit 101:

```bash
target/debug/optimizer model validate --model examples/model-v1.json > /dev/full
```

SPEC-0001 requires a categorized io diagnostic and exit 2 for output failures.
The Linux CLI regression uses /dev/full and a pipe with its read end closed as
minimal failing output fixtures, in both structural and candidate modes:

```bash
cargo test -p optimizer-cli --test model failed_report_output --locked
```
