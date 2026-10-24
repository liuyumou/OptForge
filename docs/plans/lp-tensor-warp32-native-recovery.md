# Bounded recovery of the warp32 native acceptance gate

Status: Accepted by explicit user approval, 2026-10-24. One new native gate and the conditional continuation below are authorized.

## Retained result and exact correction

The approved compiler-launch recovery succeeds. The prescribed warp32 image
uses at most **88 registers with zero spills**, retains the required Tensor
instructions/rounding and preserves every historical numerical body/image.
Independent comparison of the actual kernel body with the actual unchanged
host reference passes **592 bit/refusal cases**. Eight-model CPU admission
retains all **48 cells**, independently verifies **24 endpoints**, and admits
all **12** required dense-model configurations through useful 400-update
trajectories. Ten launcher/harness regressions pass. The proof/admission phase
charges **696.176327576 / 800 CPU seconds**.

The first full native gate stops in Clippy because the new device-test fixture
casts an already-i32 value to i32. No Rust test suite, Python integration suite,
native replay, final documentation/smoke command or device inventory completes
in that gate. Its full **1200 CPU seconds** remain charged. Cleanup is verified
empty; there has been no new GPU execution, bootstrap rerun or host access.
At this failure, cumulative CPU accounting is **31950.822722026 / 35900**.

The prepared one-line correction removes only `as i32` from that fixture's
exponent expression. Clippy itself establishes that the source value is i32,
so the change preserves the generated values. The old file is archived and
both hashes are recorded in
[native-refusal-v1.json](../benchmarks/data/tensor-warp32/native-refusal-v1.json).
All numerical-source hashes in the admitted CPU cohort still match. The
corrected image, host numerical bodies, norm/layout proofs, request semantics,
CPU endpoints and verification receipts are unchanged and must not be rerun,
normalized or re-signed. A source bridge covers this test-only correction.

## Approved CPU transfer

The user approves transferring **1240 unspent worker CPU seconds**: **1200 to native
acceptance** and **40 to reporting**. Carry every implementation, proof,
failed-gate and delivery charge forward. Additional reporting funds final
targeted delivery after this separately charged refusal delivery; it does not
fund another numerical attempt. The original continuation allocations,
including already charged amounts, become:

| Stage | CPU seconds |
| --- | ---: |
| Implementation | 258 |
| Proofs/admission | 800 |
| Native acceptance | 2400 |
| Workers, monitoring, endpoint verification and report calculation | 2052 |
| Reporting/delivery | 190 |
| Named termination margin | 400 |
| **Total** | **6100** |

No new CPU seconds are requested. The cumulative ceiling remains 35900, and
the maximum allocated accounting remains 35854.705814258. Preserve the failed
execution journal and each CPU-delivery journal. A new authorized journal must
restore only these prospective caps, subtracting all retained charges; closing
delivery stages does not create new headroom.

## One new full gate, then the existing conditional study

Run exactly one new final-source full native gate,
reserving 1200 CPU seconds, followed by compile-only device-test inventory.
[The prepared entry](../../tools/lp_tensor_warp32_native.py) preserves Python's
PATH, adds the pinned Rust toolchain, hides CUDA during acceptance, runs every
command in `tools/check.sh`, and verifies exact source identity before writing
its separate receipt. It does not waive or replace any native check.

```sh
python3 tools/lp_cpu_admission.py \
  --stage native --reserve-cpu-seconds 1200 \
  --output artifacts/gpup-tensor-warp32-v1/native-acceptance-v2.json \
  --journal artifacts/gpup-tensor-warp32-v1/cpu-journal-native-recovery-v6.json \
  --slots 4 --declared-memory-bytes 4294967296 \
  --source tools/lp_tensor_warp32_native.py \
  --source tools/check.sh --show-log \
  -- python3 -u tools/lp_tensor_warp32_native.py
```

On success only, freeze the corrected source/image, unchanged host binaries,
source-bound CPU admission, all 76 study cells, six device acceptance jobs,
forecast and resource-fit rules. Then run the already specified correctness,
profiles/ablations and conditional timing sequence, once per new identity.
There are no executed device identities in this continuation to retry.

The GPU cap stays **790 seconds**: 290 repeatability, 200 profiles/ablations,
300 screening. The worker CPU envelope shrinks to **2052 seconds**, at most
513 wall seconds under the unchanged four-times-wall accounting. It cannot
fund all GPU maxima simultaneously. Full per-job lease/verification admission
and the frozen whole-roster resource-fit estimator must enforce the tighter
joint limit; they may stop before timings even if GPU allowance remains.
Do not shorten the roster, omit a family, reduce repetitions or claim success
from a subset. This is a conditional bounded attempt, not a completion promise.

All numerical and latency completion criteria remain unchanged, including
useful integer/floating Tensor solves, original-model 1e-9 certification, 1e-7
local budgets, resident FP64 state, explicit residuals, sticky promotion,
charged replay, all five repetitions and the six-comparison adjusted
total-latency interval. A missing gate, real failure, budget refusal or no gain
leaves GPUP-8 incomplete. No automatic retry, new image, host access, bootstrap
rerun, supervisor change, device substitution, GPUP-9, publication or merge.

The user explicitly approves this new native gate and these transfers.
ADR-0045's real-failure stop remains in force for this bounded recovery; no
further native or GPU retry is authorized.


Final CPU-only delivery acceptance passes formatting, 155 documentation pages,
repository CPU smoke and diff hygiene; no full native or numerical/device gate
is inferred. Final CPU accounting is 31980.332668818 / 35900, with
12.490053208 reporting CPU seconds unspent before any proposed transfer.
The separate native-final-cpu-accounting-v1.json receipt retains every charge.
No new GPU work or resource bootstrap ran; all project cleanup is verified empty.

Accepted execution disposition (2026-10-24): the single new invocation passes
Clippy, then stops at the existing driver-availability assertion. Its full
1200 CPU seconds remain charged. No device work or retry follows. The separate
[native-stop report](../benchmarks/lp-tensor-warp32-availability-gpup8.md) retains
the exact failure, CPU-only delivery and final accounting.
