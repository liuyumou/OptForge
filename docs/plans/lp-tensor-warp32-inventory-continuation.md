# Proposed inventory-only continuation of GPUP-8

Status: proposed, not accepted. The user requested this plan on 2026-10-24.
Planning authorizes documentation and source inspection only. No compiler,
native rerun, GPU reservation or reopening of scientific stages follows.

## Reuse the completed software checks

**Yes: finish the missing compile-only inventory in its own bounded phase.**
The prior tools/check.sh run completed Clippy, all Rust/native checks, 424 Python
tests, dependency checks, replay, documentation and CPU smoke. Its retained
native-gate-v3.json receipt binds source
`267c5b7488482ea9005f359e367dcff2b97f363fe2e9ffd7b6008db5cb897138`.
The exact 1137-file source archive is preserved. The failed combined attempt
and its full 1200-CPU-second charge remain unchanged.

A fresh planning comparison verifies that every covered executable, test,
harness and configuration source still matches that archive. The eleven
observed differences are explicitly listed documentation, task state and
post-run delivery receipts. The source-audit receipt is
artifacts/gpup-tensor-warp32-v1/inventory-planning-source-audit-v1.json.
Only about 1.984 seconds separate the software-pass receipt timestamp and the
resource-refusal receipt timestamp. This supports separating the phases; it
does not measure the time a complete inventory needs.

Acceptance of this proposal explicitly amends **gate scheduling and resource
allocation only**. Existing scientific behavior and completion requirements
remain unchanged. The prior resource refusal is not converted into a pass.

Before inventory, verify the original software receipt, archived source and
retained toolchain/dependency, executable and image identities. Recompare the
current tree using an exact path/hash allowlist for the documentation and
receipt changes, including this plan and its eventual authorization. Any change
to covered code, tests, manifests, build inputs, lockfiles, numerical inputs,
compiler flags or dependencies refuses reuse. Missing provenance also refuses.
No broad documentation-directory exemption is permitted: scientific JSON
records and contracts under docs remain protected.

Use a separate admission adapter and focused negative checks for changed code,
changed compiler inputs, a missing/mismatched receipt, altered inventory,
non-passing resource cleanup and unexpected source differences. This adapter is
admission bookkeeping only, retained under artifacts; do not change the tested
solver, kernel, test or execution-harness sources. Its own focused checks are
charged to the 100-CPU-second setup allocation, without rerunning tools/check.sh.

Run the existing inventory command once, with the pinned environment, four CPU
slots, CUDA hidden and the unchanged supervisor/memory policy:

```sh
cargo test -p optimizer-cuda -p optimizer-schedule-examples \
  -p optimizer-lp-cuda --all-features --no-run --message-format=json --locked
```

The unchanged tools/lp_tensor_warp32_inventory.py collects all four required
suites: optimizer-cuda, optimizer-schedule-examples, optimizer-lp-cuda and the
warp32 Tensor suite. Run no test binary or CUDA workload during inventory.
Existing build cache may be reused; no partial binary counts as an inventory
pass. Preserve distinct command, source, binary-hash, resource and cleanup
receipts. A failed or incomplete inventory stops this continuation.

On success, produce a **new composite acceptance receipt** that explicitly
references the old completed software gate, exact source-equivalence evidence,
new inventory and its passing resource receipt. Label it as reused software
checks plus new inventory, with both source identities; do not claim a new
check.sh execution or overwrite/re-sign the original receipt. An external
admission adapter must validate the entire composition before exposing the
current acceptance record to the existing freeze consumer. Merely setting
native=true or replacing a source hash is insufficient. Store the composition
under artifacts/target so recording it cannot change the frozen source digest.
Keep the original receipt and archive immutable.

Freeze the current exact source identity only after that composition passes.
Select the newly approved journal at runtime without changing the verification
helper. Thereafter, run the existing device, profile/forecast and conditional
primary-timing sequence. No source or admission-policy edits follow freeze.

## Recommended prospective CPU allocation

These are **remaining headrooms at approval**, not replacements for any charge:

| Stage | CPU seconds | Purpose |
| --- | ---: | --- |
| Source-equivalence admission, composition adapter and focused checks | 100 | Validate reuse and prepare immutable receipts |
| One compile-only inventory | 400 | 100 wall seconds, including finalization |
| Freeze, device jobs, monitors, profiles, forecasts, timings and endpoint verification | 4000 | 1000 aggregate wall seconds |
| Final evidence/report/docs/smoke delivery | 150 | Keep delivery funded independently |
| Existing named termination margin | 400 | Preserve its restricted purpose |
| **Total prospective headroom** | **5050** | |

Request **2500 additional CPU seconds**, plus explicit reallocation of the
existing unused stage funds into the table above. The cumulative ceiling becomes
**39640** (37140 + 2500), and the continuation allocation including historical
charges becomes **9840** (7340 + 2500). Preserve every previous charge; do not
refund any unused portion of a failed reservation. Leave leftover/unallocated
headroom unused rather than authorizing implicit transfers.

Before this planning task, cumulative accounting is 34492.792106322 / 37140;
unused assigned stage funds total 2601.913707936 CPU seconds. This plan spends
at most 24 of the existing reporting seconds. Even at that full planning charge,
unused assigned funds plus the proposed 2500 new seconds exceed the 5050
headroom by 27.913707936 seconds. Maximum cumulative accounting after consuming
all proposed headrooms is then **39566.792106322 / 39640**, leaving at least
73.207893678 seconds overall. The final planning receipt supplies the exact
smaller measured charge when available. All amounts are checked in integer
nanoseconds; the proposal itself grants no resources.

The **400 inventory CPU seconds are an engineering allowance**, not a measured
minimum or a promise. They provide 98 work wall seconds under the existing
supervisor's two-second reserve, without spending another 1200 seconds on the
passed gate. If inventory still times out, retain the full charge and stop.

The existing 2052 worker CPU seconds allow only 513 wall seconds. Merely funding
inventory would retain that bottleneck. The proposed 4000 worker CPU seconds
allow 1000 wall seconds: after the supervisor's two-second reserve and the
entire 790-second GPU cap, 208 wall seconds remain outside leases. The unchanged
per-job admission helper requires a 120-second tail for lease/verification
admission, leaving 88 wall seconds for freeze, coordination and other work if
all GPU maxima are used. This is a bounded allowance; observed overhead and
per-job worst-case reservations can still refuse early. The 400-second
termination allocation is separate and cannot fund scientific work.

## All completion and stop criteria remain unchanged

GPU limits remain **790 total: 290 acceptance, 200 profiles/ablations, 300
primary timings**. The exact 17366-event prefix and inherited device UUID remain
fixed. Keep all six acceptance jobs, 280 product comparisons, five controller
comparisons, twelve fixed-work/replay pairs, four sanitizers and all 76 study
cells. Keep complete 2000-update profiles, original ordering/deadlines, the gain
forecast and 1.25 resource-fit estimator, all configurations and controls.

Completion still requires useful INT8 and at least one FP16/BF16 nontrivial
certified solve; 1e-7 local budgets, 1e-9 original-model host certification,
resident FP64 state, residual corrections, sticky promotion and charged replay;
five certified repetitions without coverage loss on either timing model; and
at least one paired total-latency bootstrap interval excluding one, adjusted
across six comparisons at 95% family confidence, 10000 resamples, seed 17002.
Independently verify every retained endpoint. A forecast or software pass alone
cannot complete GPUP-8, and no budget can guarantee a measured speedup.

Any source mismatch, resource refusal, missing gate, device/numerical failure,
timeout, sanitizer finding, missing forecast, exhausted cap or absence of the
required gain leaves GPUP-8 incomplete. No automatic retry, alternate image,
new cell, device substitution, GPUP-9, preset, host/container change, bootstrap
rerun, supervisor change, publication or merge is authorized by this proposal.
