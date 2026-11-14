# SPEC-0035: measured cold startup and lifecycle delivery

The user requests DELIVERY4 implementation. Follow the
[delivery plan](../plans/lp-delivery4.md) and [ADR-0068](../decisions/ADR-0068-delivery4.md).
New code belongs to `research/lp-delivery4` and new tooling. Preserve historical
sources/evidence and all numerical state-machine, checker, signed-zero, refusal,
checkpoint, recovery, cancellation and original-model 1e-7/1e-9 contracts.

## Measurement and selection

First run CPU-only attribution on retained original models: solver/checker data
construction, JSON/LP scopes, model/image/executable hashing. Preserve sources,
all repetitions and fixed alternating operation order. These warmed measurements
are attribution, not a substitute for complete cold latency.

Add optional process-wide hierarchical scopes and explicit setup/response/owned
teardown spans. Include output construction, checker EOF/reaping, device buffer,
module/stream/context destruction, parent collection and durable writes. Both
profiled and unprofiled cold boundaries end after process exit and durability.
Profiles are diagnostic only. Never sum parent/child overlapping timers.

Choose and document one concrete change from the measured cost case. Control is
DELIVERY3 overlap-only in the new executable, same both lanes and final tiers.
Candidate must preserve early invalid-input refusal and independent checking;
no new CUDA work may precede successful original-model admission. No public
default, precision change or outcome-dependent dispatcher.

Before device work, pass CPU exact representation/checker differentials and the
full native gate. Admit unchanged-image lifecycle/cancellation/failure behavior,
configuration and profiling modes. Reuse only source-bound unchanged device
sanitizer evidence. Device pilot: two profiled and four unprofiled fresh blocks,
four declared families (dense512, coupled equality, fixed bounds, irregular33),
both lanes/tiers, paired control/candidate, cold only: 192 cells. Separately check
prepared reuse in admission. Retain all values and failures. Freeze the candidate
only if the uninstrumented dense512 geometric paired ratio is at least 1.01;
otherwise report the negative pilot without launching confirmation.

## New confirmation protocol

Freeze sources, executables, schedule, candidate and reducer after admission and
pilot. Thirty-two new blocks, twelve original families, both lanes/tiers and
control/candidate cold pairs: 3072 cells. Counterbalance each pair order 16/16,
randomize stratum order with a new recorded seed. All bounded families must
certify; the intentional unbounded-direction refusal stays visible. Every original
endpoint, certificate (apart from binary binding), audit, checkpoint, recovery and
physical/logical work must match. No retry of a started frozen scientific identity.

For each lane/tier: median of block-wise equal-weight geometric ratios over
original dense128/256/512; benefit lower bound >=1.10x. Each of eleven certified
families uses paired `candidate-control-max(2%*control,0.10 ms)` and requires its
median interval upper bound <=0. Four benefits and 44 guards (48 metrics) use
Bonferroni two-sided 95% distribution-free binomial median intervals. Compute the
ranks exactly before freezing. Preserve supported, unfavorable and inconclusive
outcomes and shared-device/independence limitations. Prepared throughput and
TENSOR2's separate retention contract are unchanged.

## Independent resources and delivery

Ceiling 64000 CPU / 4800 GPU seconds. CPU phases: implementation 12000 (512
preparation), native 12000, acceptance 8000, diagnosis 8000, confirmation 16000,
reporting 6000, cleanup 2000 (128 closing administration). GPU: acceptance 600,
diagnosis 600, confirmation 3600. Four CPU slots, 16 GiB sampled RSS, at most
12 GiB owned device buffers, one pinned shared lease and unchanged in-container
supervisor. Confirmation blocks reserve <=90 GPU /360 CPU seconds each.
Every whole job must fit; preserve failed reservations and development versions.
Receipts: `artifacts/gpup-delivery4-v1`. No old allocation transfer.

Record useful diagnosis findings and limits in a durable report and current
handoffs, along with all results, sources, exact historical preservation, software
acceptance and final accounting. Commit locally only; no push/publication or GPUP-9.
