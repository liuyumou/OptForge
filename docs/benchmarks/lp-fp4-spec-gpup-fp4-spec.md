# GPUP-FP4-SPEC: executable CPU contract and cost admission

Status: GPUP-FP4-SPEC complete; CPU/native acceptance passed; no device execution
Owner: numerical backend and experiment tooling
Date: 2026-11-11
Authority: [SPEC-0025](../specifications/SPEC-0025-persistent-fp4-contract.md), [ADR-0056](../decisions/ADR-0056-fp4-executable-contract.md)
Proposal: [frozen configuration](../../benchmarks/configs/lp-fp4-proposal-v1.json)

## Delivered behavior

The CPU specification encodes 2/4/8 E2M1 residual planes with bounded power-of-two
scales, exact rounding/error oracles and consistent matrix/transpose tiles. It
implements interval projection decisions, the PDHG/Halpern error recurrence,
original-unit audit guards and complete checkpoint validation/rollback. Accepted
observations preserve component bytes. Snapshot rounding, signed binary64
controller scalars, stale generations, cancellation and physical-work accounting
have explicit contracts.

Three strict schemas cover proposals, checkpoints and cost inputs. The CLI
validates source hashes, frozen models/lanes, complete cell coverage and whole-job
resource arithmetic. Its verdict always says `execution_authorized: false` and
`hardware_admitted: false`; it is not a solver or certificate issuer.

```sh
python3 tools/lp_fp4_protocol.py --proposal benchmarks/configs/lp-fp4-proposal-v1.json
python3 -m unittest discover -s tests/integration -p test_lp_fp4_contract.py -v
```

These commands need only repository Python dependencies. They do not read ignored
model installations or launch a device. The proposal binds original model hashes
through the committed RESIDENT2 results; actual input/device/source readback is
still required before a future numerical run.

## What the retained cost evidence establishes

The [machine review](data/fp4-spec-cost-review-v1.json) evaluates all 24 cold
native-control deliveries from [RESIDENT2](lp-resident2-gpup-resident2.md).

| Disposition | Trials | Meaning |
| --- | ---: | --- |
| Reject ideal 10% bound | 6 | Even removing the entire native phase cannot yield 1.10× total speedup with other phases unchanged |
| Need component profiles | 15 | The optimistic bound permits the target; actual accelerated work, throughput and overhead remain unknown |
| Ineligible quality | 3 | The mixed-model native endpoints remain uncertified |
| Forecast admitted | 0 | No actual component profile is available |

This is a per-trial upper bound for changing native execution alone, not a
measured FP4 result. Native time includes more than arithmetic, so assuming all
of it disappears is intentionally generous. Missing profiles do not pass. The
forecast evaluator uses worst-case accelerated-fraction/work/throughput intervals
and charges all incremental preparation, scaling/reduction, state traffic, audit,
fallback, launch and scratch costs. The 1.10× row screen is distinct from the
prospective campaign's geometric-mean/no-model-regression retention rule.

## Frozen comparison and proposed resources

Eight development models and six lanes remain visible: native FP64, four-plane
FP8 E4M3, two-plane FP16, and 2/4/8-plane FP4. Three cold repetitions plus one
prepared batch of three independent fresh solves yield **192 cells / 288
endpoints**. All approximate lanes owe the same error/audit/1e-9 certification
policy. Component count is a research parameter, not an accuracy guarantee.

The prototype proposal includes CPU reference/integration, device admission,
four sanitizers, 24 pilot jobs and twelve fusion/persistence diagnostic jobs.
It proposes **19040 CPU / 1560 GPU seconds**. The subsequent full study separately
proposes **55760 CPU / 13440 GPU seconds**. Both include reporting/cleanup and
four-slot whole-job reservations. These are prospective proposals, not spending
authority for this specification task. No GPU work ran here.

## Acceptance and limits

The 32 focused tests cover independent codebook/tie expectations, residual tails,
transpose identity, exact mathematical group products, projection and dual-prox
nonexpansiveness, independent scalar PDHG transitions, original-unit guards,
cross-window persistence, complete rollback, strict schemas, evidence binding
and pessimistic cost admission. Mathematical FP32 representability does not prove
actual FP4 MMA behavior; the actual instruction/architecture/error bound remains
a prototype admission requirement.

The exponent range [-48, 48], monotone 1e-7 relative error enclosure and ambiguous
projection refusal are intentionally conservative. They can cause escalation
well before the original-model 1e-9 final certificate is attainable. The helpers
check declared enclosures; a future executor still must derive every local error
term and prove its accumulation/normalization behavior. No long-trajectory,
convergence, fused-kernel, hardware-accuracy or performance claim follows.

The full repository gate passes native build/Clippy/dependency checks, all Rust
tests, 549 Python tests, committed-record replay, 197 documentation pages and
smoke. Final documentation/source preservation and settled resource receipts are
in the [acceptance record](data/fp4-spec-acceptance-v1.json) and
[accounting record](data/fp4-spec-accounting-v1.json). The independent task ceiling is
16000 CPU seconds, including 256 conservative preparation seconds, with zero GPU.
Historical numerical sources, accepted evidence and resource ledgers are unchanged.
Next ready after acceptance: GPUP-FP4-PROTO, beginning with the CPU reference and
numerical admission. Keep the native control; GPUP-8 remains incomplete and GPUP-9
remains gated.
