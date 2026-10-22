# ADR-0041: Resident matrix quantization and matched execution

Status: accepted, 2026-10-22, by the user's explicit contract/allocation approval
Owner: numerical backend and experiment tooling
Introduced: GPUP-7R planning
Last reviewed commit: bootstrap
Superseded by: none

## Context

The accepted [ADR-0040](ADR-0040-bounded-matrix-quantization.md) evaluation retains
all historical evidence but establishes no useful quantized solve benefit.
Matched FP64 shares the new path's timeouts, while unchanged tuned FP64 solves
every timing cell. CPU guard scans, host vector updates, per-product transfers,
sparse tile overhead and immediate promotion confound an arithmetic comparison.
All eight GPU profile horizons are censored. The user requests a bounded plan
for resident execution, reduced guard overhead and a fair comparison.

## Proposed decision

On explicit acceptance, implement only the
[GPUP-7R bounded plan](../plans/lp-quant-resident-follow-up.md). It proposes a
new lp-quant-resident-v1 research interface and accepts that implementation subset
of SPEC-0012 requirements 9-21, 24-38 and SPEC-0021 requirements 7-10, 14-20.
At implementation, map the exact requirements and acceptance tests in both
specifications; this draft accepts none of their other extensions.

Supersede ADR-0040 only for the new interface's executor placement, conservative
bound construction, sparse execution tree/layout, diagnostic horizon and task
resource allocation. Its lp-quant-v1 behavior, original numerical evidence,
format/scale definitions, budgets, promotion rules and historical resource
decision remain unchanged and available. No accepted ADR is edited retroactively.

Keep FP64 state/updates resident, reuse tuned execution/update machinery through
an opt-in adapter and use one compact segmented sparse layout. Device guards
combine a cheap outward envelope with coefficient-weighted detailed bounds on
coarse failures. Prove the actual reduction and directed-rounding programs.
Validate caches once per generation and eliminate host scans/vector round trips
per product. Retain host FP64 32-update audits, reference adoption, complete
restoration and charged replay, every 200-update numerical boundary and fresh
original-model host certification. Failure flags predicate dependent device work;
physical work, deadlines and failure status never roll back.

Do not change the 1e-7 product/audit budgets, 1e-9 certification tolerances,
32-by-32 canonical tiles, uniform/selective promotion policy, 25% coefficient cap,
eight selective transitions, no-demotion rule or common safe norm/step envelope.
Device guards never gain mathematical authority. Ordinary builds remain
toolkit-free and existing runtime/unsafe boundaries remain.

Freeze six format/policy candidates, resident matched FP64, a tuned-operator FP64
policy bridge and unchanged tuned FP64. Bound the study at 108 fresh timings,
nine forced-horizon diagnostic profiles and three product/guard microprofile
jobs. CPU accuracy/useful-low admission precedes device work. Refused cells are
retained without replacement; no low-precision eligibility means a documented
negative result, not permission to relax accuracy or add refinement.

## Proposed resource authority

Allocate at most 3600 GPU seconds to the new task: 2300 screening, 450 ablation
and 850 repeatability seconds, with planned reservations 2268/432/816 seconds.
This is a new allocation from existing unconsumed cumulative authority, with
additional_gpu_seconds=0, not a reopening of GPUP-7 or a ceiling increase.
Retain cumulative ceiling 25202.574545061 seconds, the independent 28800-second
cap and every existing phase ceiling. Current consumption is 21113.899268966
seconds; the full allocation fits all caps and leaves 488.675276095 seconds.

Bind the resource record to the exact 17036-event ledger prefix SHA-256
861c90d8d82a20ff9655173742db37a5047d315e8cc4c983e0d6b2e6fa09bb97,
all earlier prefixes and the existing selected 5090 UUID/shared lease/activity
admission. Retain 21600 CPU seconds/four jobs, 8 GiB RSS, 1 GiB device buffers,
2 GiB preparation, 32 GiB artifacts and checked 65536-dimension/2^23-nonzero
limits. The plan specifies reservation arithmetic, stop rules and counter units.

## Alternatives and consequences

Moving only sparse multiplication to CUDA retains the observed host bottleneck.
Raising error budgets, adding anchors/refinement, tuning step sizes or using
Tensor Cores changes a different numerical/hardware question and is excluded.
Running only against unchanged tuned FP64 would retain policy/layout confounds;
the two FP64 controls expose them without a large ablation grid.

Conservative admission may still force immediate full promotion, and 32-update
host audits may still dominate latency. Both are valid results. The proposal
does not require FP8 usefulness, a speedup or a supported preset, and reserves
nothing for later work. A future accuracy expansion needs a separate decision.

## Implementation and tests

Follow the plan's CPU exact-oracle/admission gates, full pinned-native acceptance,
ordinary/new device differentials, fixed-work bitwise replay, four scoped
sanitizers, strict evidence and independently verified endpoints. All acceptance,
packing, transfers, guards, audits and recovery cost is charged. Preserve original
code/evidence and produce a separate report. Local commit follows acceptance;
publication and merge are excluded. The current planning task runs no GPU work.
