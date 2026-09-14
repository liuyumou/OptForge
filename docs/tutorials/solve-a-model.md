# Solve a model with the pinned backend

Purpose: run one CPU LP/MILP solve and read its record. Scope: C1, SPEC-0002.

This assumes the pinned HiGHS build is provisioned:

```bash
bash tools/setup_highs.sh
```

## Run a solve

Solve configuration is a strict versioned JSON document. There are no default
seeds, limits or tolerances, so every record states what produced it:

```json
{
  "schema_version": 1,
  "seed": 17,
  "time_limit_ms": 10000,
  "iteration_limit": null,
  "node_limit": null,
  "tolerances": {"absolute": 1e-9, "relative": 1e-9, "integrality": 1e-9},
  "threads": 1
}
```

```bash
cargo run -p optimizer-cli -- solve \
  --model examples/model-v1.json \
  --config examples/solve-config-v1.json
```

The example model minimizes `2 x3 + x8 + 0.5` subject to `x3 + x8 >= 2`, with
`x3` binary and `x8` continuous and nonnegative. The record reports
`"termination": "optimal"` and `"objective": 2.5` for `x3 = 0`, `x8 = 2`.

## Read the record

- `termination` is engine-owned. `optimal`, `infeasible`, `unbounded` and
  `unbounded_or_infeasible` are completed outcomes; `time_limit`,
  `iteration_limit`, `node_limit` and `interrupted` are not, and never imply a
  finished proof.
- `native_status` retains the backend's own status name for diagnosis.
- `objective` is recomputed by the core from the returned assignment. It is not
  the backend's reported value echoed back.
- `validation` is the full SPEC-0001 report for the incumbent, including per-row
  activities, violations and allowances. A candidate that fails this check is
  reported as a numerical failure rather than as a solution.
- `best_bound` and `gap` appear only when the backend supplied finite values. An
  unavailable measurement is omitted, never sent as `null`.
- `options` repeats the exact configuration used, so the solve can be repeated.

An `optimal` termination means HiGHS reported optimality under the recorded
numerical settings and the extracted candidate passed original-model validation.
It is not an exact-arithmetic certificate.

## Warm starts

Pass a validated candidate or a previously returned LP basis, but not both:

```bash
cargo run -p optimizer-cli -- solve \
  --model examples/model-v1.json \
  --config examples/solve-config-v1.json \
  --candidate examples/candidate-v1.json
```

A candidate warm start must be feasible for this exact model. A basis is bound to
a fingerprint of the canonical model, so it is rejected if the model's data
changed even when its `model_id` did not.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Completed outcome: optimal, infeasible, unbounded, or unbounded-or-infeasible |
| 1 | A limit was reached or the outcome is unresolved |
| 130 | The solve was interrupted |
| 2 | Argument, I/O, document, unsupported, backend or numerical error |

Errors write no partial record to standard output. Without the pinned library the
command fails with an `unsupported:` diagnostic rather than reporting a solve.

See the [backend contract](../specifications/SPEC-0002-backend-contract.md) for
the normative requirements and [model validation](model-validation.md) for the
candidate report format.
## Reading a first-order LP bound and gap

For `host-lp` and `cuda-lp`, a bound is computed on the host from the original
model with outward rounding. Uncertain reduced costs on an infinite variable side
can leave the bound absent even for a bounded LP. That is a certification refusal,
not a proof that the model is unbounded.

The objective field remains the core's ordinary binary64 recomputation. Gap
closure additionally encloses objective rounding and respects minimization versus
maximization. The LP `gap` field is a nonnegative conservative upper bound in
absolute objective units, so it need not equal subtraction of the rounded objective
and bound fields. HiGHS instead reports its relative MIP gap. A missing gap or a
small diagnostic alone never establishes optimality; consult the termination and
validation fields under the recorded tolerances. See
[the arithmetic argument and limitations](../architecture/lp-certification.md).
