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
