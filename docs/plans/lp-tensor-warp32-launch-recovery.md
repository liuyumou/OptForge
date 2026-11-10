# Bounded recovery of the ADR-0045 compiler launch

Status: Accepted, 2026-10-24. The user explicitly approves this bounded launch
recovery, the 108-CPU-second transfer and continuation under ADR-0045's gates.
Every prior charge is retained; no new budget, host access or bootstrap rerun.

## Retained failure

The user accepted [ADR-0045](../decisions/ADR-0045-warp32-tensor-reference-recovery.md)
and the 6100-CPU-second reallocation. The isolated source/config copies and
historical source/ledger checks passed. The prescribed warp32 reduction is
written, along with host/device test adapters, but remains uncompiled and
unaccepted.

The image-construction command replaced `PATH` with a list that omitted the
working Python installation. `/usr/bin/env python` returned 127 before the
Python entry, Cargo formatting or CUDA compilation began. This is an avoidable
launcher defect. The accepted supervisor returned `command_failed`, charged the
full **108 CPU seconds**, and verified empty cleanup. No bootstrap or GPU work
ran. Do not reclaim this reservation or automatically retry the command.

At the compiler stop, cumulative CPU accounting is **29900.459145450 / 35900
seconds**. The implementation stage has used **145.753331192 / 150** new CPU
seconds. Mandatory CPU-only delivery is charged separately to the existing
150-second reporting stage; see its final accounting receipt. GPU consumption
is unchanged: GPUP-8 **863.208464546 / 3000** and campaign
**22222.794320335 / 25202.574545061**. Preserve the exact 17366-event ledger
prefix, all old sources/images/workers/reports and the failed new resource
receipt/journal.

## Concrete corrected entry

[The prepared entry](../../tools/lp_tensor_warp32_compile.py) preserves the caller's
entire `PATH`, prefixes the pinned Cargo directory, invokes Cargo by absolute
path, and invokes the image builder using `sys.executable`. Only child process
environment values change. The entry has four mocked CPU regressions; those
tests do not invoke Cargo, a compiler or a device. Passing them does not count
as an image construction or native/device acceptance.

After explicit approval, the one corrected supervised command would be:

```sh
python3 tools/lp_cpu_admission.py \
  --stage implementation --reserve-cpu-seconds 108 \
  --output artifacts/gpup-tensor-warp32-v1/image-construction-v2.json \
  --journal artifacts/gpup-tensor-warp32-v1/cpu-journal-recovery-v3.json \
  --slots 4 --declared-memory-bytes 3221225472 \
  --source tools/lp_tensor_warp32_compile.py \
  --source tools/lp_tensor_warp32_build.py --show-log \
  -- python3 -u tools/lp_tensor_warp32_compile.py
```

Neither compiler nor test-suite execution has been retried. The image builder
still refuses if an image already exists and admits only the prescribed
128-register/zero-spill construction. An unexpected partial artifact or another
real failure stops; there is no second construction or automatic repair loop.

## Proposed transfer and remaining sequence

Request transfer of **108 unspent worker CPU seconds to implementation**. Carry
every setup/read/failure/delivery charge forward. Total approved CPU headroom
stays 6100 and the cumulative ceiling stays 35900. Prospective stage allocations,
including amounts already charged, become:

| Stage | CPU seconds |
| --- | ---: |
| Implementation | 258 |
| Proofs and complete eight-model admission | 800 |
| One full pre-device native gate | 1200 |
| Device workers, monitoring and endpoint verification | 3292 |
| Reporting and delivery, including this refusal delivery | 150 |
| Named termination margin | 400 |
| **Total** | **6100** |

The implementation's unspent headroom becomes 112.246668808 seconds before the
corrected invocation. No CPU charge is reset. Reopen a new journal only after
approval, preserving the failed execution and CPU-delivery journals. Restore
scientific stage caps from these allocations, subtracting every retained charge;
do not treat the closed delivery journal's caps as a new allowance.

Keep all ADR-0045 numerical, latency, correctness and source-preservation rules,
the 76-cell roster and six acceptance jobs. GPU limits remain **790 total**:
290 repeatability, 200 profiles/ablations and 300 screening. The new worker CPU
allocation permits at most 823 wall seconds, giving only 33 seconds outside
leases if the entire GPU allowance were consumed. The joint CPU admission and
resource-fit gate must reserve actual verification/monitoring/cleanup exposure
and may refuse earlier; spending all GPU maxima is not guaranteed or promised.
Do not extend a cap to finish the roster or weaken completion requirements.

After the corrected compiler gate passes, finish the reduction oracle and
source-bound harness, complete CPU admission/native acceptance, freeze, then
perform device acceptance, profiles/forecast and conditional timings in the
accepted order. Reporting uses independent source-bound verification receipts;
available failed/interrupted endpoints still require verification. No host
access, bootstrap rerun, supervisor change, device substitution, new GPU study
identity retry, new resources, GPUP-9, publication or merge is authorized.

ADR-0045 explicitly states: “A command/source mismatch or a real failure stops
this continuation.” Acceptance is therefore required for this one corrected
compiler launch and CPU-stage transfer. Until then, GPUP-8 stays incomplete and
only the already reserved CPU-only refusal delivery may finish.


CPU-only refusal delivery passes four mocked launcher regressions, exact historical
source/ledger preservation and a 153-page documentation build. Smoke then cannot
find rustc in the caller's PATH; the full 100 CPU seconds are charged and the
following diff check is unrun. No complete delivery/smoke pass or automatic retry
is claimed. Final accounting, including four last bookkeeping CPU seconds, is
30008.459145450 / 35900. The original reporting stage has 42 CPU seconds left;
any approved continuation must fit final delivery within that remainder. The
prepared child environment must be used for delivery commands as well as the
compiler. See ../benchmarks/data/tensor-warp32/final-cpu-accounting.json (from
this plan) or data/tensor-warp32/final-cpu-accounting.json (from the benchmark).
