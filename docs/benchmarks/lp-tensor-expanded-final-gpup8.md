# GPUP-8 expanded-window final handoff

The approved attempt remains incomplete after the independent CPU proof gate
rejects a noncanonical generated operand. Twelve new authority checks and sixteen
new CPU prototype checks pass; the full scalar proof, native/model admission and
all GPU stages remain unpassed. The first eighteen host scalar outputs were not
independently compared. No arithmetic defect or latency result is inferred.

The [original report](lp-tensor-expanded-gpup8.md) and
[exact fixture diagnosis](data/tensor-expanded/proof-fixture-diagnosis-v1.json)
preserve the failed corpus and source. The correction and retry are not applied.
The accepted [plan](../plans/lp-tensor-expanded-windows.md) includes the separately
unallocated future path for state persistence across audits.

Cumulative CPU: **51568.693453526 / 77640 seconds**. This attempt charges
**5666.151624356 CPU seconds**, including the full failed 5600-second
proof reservation. Reporting retains **761.762326424 seconds**.
Exact reconciliation: [final accounting](data/tensor-expanded/final-cpu-accounting-v1.json).

GPU work added: zero. GPUP-8 remains 1232.909411024 / 3000 seconds and campaign
22592.495266813 / 25202.574545061. The exact 17412-event ledger is unchanged.
No passed historical check/profile or endpoint verification is rerun. The
implementation, native, acceptance, profile and timing allocations are untouched,
as is the restricted termination margin. No automatic transfer or retry follows.

The failure and delivery cleanup receipts must all be empty. Final delivery
checks cover documentation/internal links, source/evidence preservation, new
Python syntax and diff hygiene; they do not replace the failed numerical proof.
No commit, publication, merge, host/container change or GPUP-9 occurs.
