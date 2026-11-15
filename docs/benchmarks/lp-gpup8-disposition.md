# GPUP-8 disposition and next evidence gate

Date: 2026-11-15. Decision: [ADR-0076](../decisions/ADR-0076-gpup8-disposition.md).
GPUP-8 is **closed_negative** administratively; its original scientific outcome
remains incomplete, with no certified total-latency gain established. GPUP-9
remains blocked on a new complete-cost gate and its own accepted protocol/budget.
This review executes no new scientific cell and changes no solver defaults.

## Requirements and evidence

| Requirement | Retained evidence | Disposition and remaining requirement |
| --- | --- | --- |
| Exact-component proof and useful arithmetic | [Final GPUP-8 recovery](lp-tensor-expanded-recovery-gpup8.md): corrected 7376-case proof, CPU/model/native checks, six device jobs and four sanitizers pass; useful small profiles certify after nonzero work. | Real admission evidence for those exact sources. It does not supply the unexecuted timing roster or prove another executor. |
| Useful INT8 and FP16/BF16, strict fresh-process gain and full coverage under ADR-0042–0046 | Six small profiles finish; the first large BF16 profile times out without an endpoint. Nine profiles and all 60 timing cells are unexecuted. Small certificate prefixes exceed 4 seconds against a 0.415902600-second forecast threshold. | The frozen result records working_families=false and certified_latency_gain=false. Small-profile successes do not complete these roster-level gates. Timeout is not a numerical failure or proof of impossibility. No recovery or deadline extension is selected. |
| Mixed solver correctness and original authority | [MIXED2-CONFIRM2](lp-mixed2-confirm2.md): all 32 blocks, 512 sessions and 16384 original-model certified solves; serial verification, trajectories and fresh operational pilots pass. | Strong scoped prepared-session evidence. FP4/FP64 arithmetic is not the historical INT8/FP16/BF16 contract. No production/general availability claim follows. |
| FP4 complete-cost advantage | MIXED2 passes 5/8 scoped value comparisons; coupled paired medians 1.0367–1.0651x. None passes the provisional 1.10 bound. Generic2048 intervals include parity; generic1024/1e-7 fails the savings floor. | Scoped prepared value, not cold superiority or public-default readiness. Retain all unfavorable/inconclusive comparisons. |
| Exact implementation improvement | [CHECKER2](lp-checker2.md): all 16 blocks, 512 sessions and 16384 certified solves; 16/16 within-lane scoped comparisons and 13/16 provisional 1.10 bounds pass. Paired medians 1.1348–1.2832x. | Shared CPU implementation plus target gain. FP4/native contrasts in that study are descriptive, not another inferential confirmation. No multiplication of speedups from different cohorts. |
| Final compiler-target attribution | CHECKER2's six-block CPU factorial uses the earlier tree candidate; the frozen final source adds the guarded product path. The primary control is portable and the candidate is v4. | Final source/target effects and full-lifecycle interaction remain unresolved. PREP3 measures the final CPU factorial; a later complete-lifecycle study is still required for adoption claims. |
| Resource availability and reproducibility | Later one-second supervision completes MIXED2-CONFIRM2 and CHECKER2; old 100 ms refusals, partial responses, failures and full charges remain. Original serial replay and portable archives pass in their recorded acceptances. | Prospective availability evidence under a changed finite policy; no retrospective repair of old cohorts and no hard peak-memory enclosure. Reuse only source-bound receipts. |
| Fair external controls | [Completed baseline continuation](lp-external-baseline-native-return.md) separates strict certificates from user-authorized cuOpt native-return evidence. | Native vendor success cannot fill strict project-checker gaps. Renew matched-source/tolerance/resource controls for a new study; no historical timing pooling. |
| Production and GPUP-9 progression | Constructed cyclic streams, shared hardware, no unseen grouped holdout, unresolved hosted startup. | A new complete-cost release gate, subsequent frozen GPUP-9 protocol/budget and held-out separation remain required. No public preset is selected. |

The negative closure is a decision about where to spend the next allocation.
It is not a retrospective claim that all historical GPUP-8 comparisons failed:
many were never executed. All 76 frozen recovery cells, resource failures and
unassigned causes remain visible in their original reports.

## Next experiment and value case

Select [PREP3](../plans/lp-prep3.md): a final-source/target CPU factorial, measured
preparation diagnosis and at most one exact preparation candidate with a separate
independent comparison. Proposed ceiling: **24000 CPU seconds, zero GPU**;
phase caps, counts, balanced order, intervals and stop rules are specified there.
This decision does not open that allocation or run the next experiment.

Strict coupled2048 FP4 CHECKER2 sessions fall from 17.853 to 14.049 seconds at
the same 800 updates per solve. Aggregate final cost is 40.5% setup and 34.8%
independent checking; GPU events are nested and cannot be added again. A
hypothetical halving of setup alone would yield 1/(1 - .405/2) = **1.254x** on
that aggregate, assuming unchanged work, all other costs and no new overhead.
This is an opportunity estimate, not a measured gain or a median prediction.
It favors inspecting preparation before enlarging arithmetic benchmarks. It
does not establish how much setup is reducible or transferable to cold solves.

The new [replacement gate](../decisions/ADR-0076-gpup8-disposition.md#replacement-progression-gate)
retains strict certification and fresh-process primary cost, requires direct
same-target native controls, full coverage, simultaneous value/regression guards,
source/target attribution, portable evidence, resource closure and hosted CI.
An exact native improvement can qualify on its own scope; a claimed FP4 benefit
needs its own direct comparison. The original GPUP-8 pass criteria stay unchanged.

## Hosted CI observation

The main revision reviewed is `e0d9e8ad3ebea268299150b47df758002ce695a8`.
Its [push run](https://github.com/liuyumou/OptForge/actions/runs/43677094346)
and the [PR #26 run](https://github.com/liuyumou/OptForge/actions/runs/43677094912)
report `startup_failure`. The main run has zero jobs and the GitHub Actions
check suite has zero check runs. Repository Actions is enabled with all actions
allowed. The run references a workflow object with path `BuildFailed`, empty
name and state `deleted`; the commit status API supplies no diagnostic. These
fields do not establish a root cause. This observation was read during this
review; it is not a hosted test pass.

No runner log identifies a repository build/test defect or a specific billing,
quota or service cause. Track **CI-STARTUP** separately: inspect the repository
owner's Actions/account diagnostics, resolve the actual startup refusal, then
obtain a normal hosted CPU acceptance run for the release source. No workflow,
account setting, branch protection or bypass is changed here. A successful local
gate cannot resolve this infrastructure condition or substitute for hosted CI.

## Validation and preservation

The full native gate passes **638 Rust / 785 Python tests**, format, Clippy,
dependency policy, artifact validation, committed-record replay, documentation
links and smoke. The Rust total includes 637 workspace cases and the buffered
transport case run by Python. No new device or scientific timing is executed.
The verification reads retained summaries and hashes; it does not claim a fresh
numerical replay of historical certificates.

All **2243 historical files outside the seven explicit planning edits**
are byte-exact against `e0d9e8ad3ebea268299150b47df758002ce695a8`. Prior handoff
text and all 64 unrelated backlog task blocks are exact. Original GPUP-8
acceptance is unchanged; old GPUP-9/disposition acceptance strings remain in
historical fields. The dependency graph is acyclic, GPUP-9 is still planned and
PREP3 is next-ready. The prospective 512-process factorial and 128-process
candidate design pass count, pair-order balance and exact interval arithmetic
checks. These are protocol checks, not executed experimental results.

The independent **16000 CPU / zero GPU** review allocation closes with empty
owned cleanup; measured charges and any full failed reservations are retained in
[acceptance and accounting](data/gpup8-disposition-acceptance-v1.json). The unchanged
one-second supervisor, four slots and 16 GiB sampled RSS apply; all 100 ms
advisories remain visible and no hard peak-memory enclosure is claimed. The
next experiment's proposed budget is not charged here.

[Historical preservation and evidence mapping](data/gpup8-disposition-verification-v1.json)
and the [source/log/resource archive](data/gpup8-disposition-evidence-v1.tar.gz)
retain the read-only hosted snapshot, original delivery verifier, native/final
receipts, source versions and allocation closure. Review-base Git objects plus
retained summaries provide the historical comparison; the original numerical
artifacts tree is not used by this disposition verifier.

Historical GPUP-8 charges remain 59603.097503214 / 77640 CPU seconds,
1410.959187474 / 3000 GPU seconds and campaign 22770.545043263 /
25202.574545061 GPU seconds, with the 17438-event ledger unchanged. MIXED2 and
CHECKER2 closed allocations also remain exact. Backlog status/dependency changes
are explicit forward-planning edits; earlier handoff text and scientific bytes
are preserved. Local commit only.
