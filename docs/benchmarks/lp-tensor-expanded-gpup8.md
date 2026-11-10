# GPUP-8 expanded-window CPU proof refusal

The approved bounded attempt stops at its new independent CPU proof gate.
GPUP-8 remains incomplete and GPUP-9 stays gated. No new GPU work, passed-check
rerun, historical profile rerun, native acceptance, local commit or publication
occurs. Expanded state across audit windows remains unallocated future work.

## Implemented and validated

[ADR-0046](../decisions/ADR-0046-expanded-audit-window-state.md) and
[the accepted plan](../plans/lp-tensor-expanded-windows.md) record the arithmetic,
audit and resource amendment. Twelve new authority/evidence adapter checks pass.
Sixteen new CPU prototype checks pass, covering expanded state between updates,
shared canonical audit input, clipping, signed zero, conversion failure, rollback,
sticky native replay, cancellation, checkpoint identity and component counts.
These CPU prototypes do not constitute a CUDA solver or model admission.

A separate FP32 error-free-transform scalar construction and host harness are
written; host-only UBSan compilation succeeds. The full independent numerical
proof does not pass. No compiled CUDA image, eight-model admission, device
acceptance, new-cohort profiles, resource forecast or timing gate follows.
Serial host-cost reductions and the complete solve/trace/verify/replay executor
remain unimplemented because the prerequisite proof gate stopped.

## Exact failure and preservation

The fixture generator emits 7376 triples. The host harness emits 18 results and
then rejects the nineteenth input. Its third operand is magnitude
8585062395809358020, exponent -63, sign 1. The significand is below 2^63 although
the exponent is above the subnormal boundary. The generator first creates a
valid subnormal operand and later changes its exponent for a fast-path case
without normalizing the significand. Its equivalent canonical encoding would
be magnitude 17170124791618716040, exponent -64, sign 1.

The harness's canonical-input check rejects this input. The driver checks the
subprocess return status before comparing outputs, so none of the 18 scalar
outputs is claimed independently verified. The exact scalar subprocess exit
code was not persisted; the retained driver failure establishes a nonzero exit,
not a complete numerical mismatch. No arithmetic defect is inferred. The later
product, conversion and projection proof loops were not reached.

Preserve the original corpus, output, source, binary, compiler logs, failure and
closed journal. The generator correction is diagnosed but not applied, and no
proof retry is made. See [the diagnosis](data/tensor-expanded/proof-fixture-diagnosis-v1.json)
and [the original refusal](data/tensor-expanded/independent-proof-refusal-v1.json).
Any corrected proof needs a separately authorized identity and allocation.

## Resource disposition

The [accepted authorization](data/tensor-expanded/authorization-v1.json) raises
the cumulative CPU ceiling to 77640 seconds. The failed proof stage retains its
full 5600-CPU-second reservation. The implementation, native, device acceptance,
profile and timing allocations remain unused. The restricted 400-second margin
is untouched. Reporting uses only its separately allocated funds. Final exact
accounting will be recorded after the reporting resource receipts settle.

GPU consumption is unchanged: GPUP-8 1232.909411024 / 3000 and campaign
22592.495266813 / 25202.574545061 seconds. The exact 17412-event ledger SHA-256
is `9913d391634bdb0f74012be909be377e5a693d00b76e6882abcf336796ac863e`.
Every retained historical charge remains. Both proof-stop cleanup receipts are
empty. No supervisor/bootstrap, host, container or scientific criteria change
occurs beyond the explicitly accepted representation amendment.
