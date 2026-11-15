# ADR-0078: Controlled GPUP-9 experiments on the current FP4 executor

Status: accepted under the user's 2026-11-15 instruction to implement GPUP-9
Owner: LP research
Introduced: GPUP-9
Last reviewed commit: bootstrap
Supersedes: SPEC-0013 requirements 10, 13 and 20 only for this scoped study
Implementation: [SPEC-0044](../specifications/SPEC-0044-gpup9-controlled-study.md)
Acceptance: [GPUP-9 report](../benchmarks/lp-gpup9.md)

GPUP-8 satisfies the research dependency under ADR-0077. Implement a bounded
component/interaction campaign using the final CHECKER2 executable at the same
x86-64-v4 target for native and FP4. The primary endpoint is a complete fresh
32-request changing-model session. Measure cold single solves separately, with
one model and one request, including process startup and destruction. This
explicitly amends the cold-primary/secondary-throughput rule for GPUP-9 only.
Historical cold experiments keep their original interpretation.

The eight configurations cross native/FP4x2, window 16/32 and original/equilibrated
operators. FP64 state, independent original-model certificates and transactional
recovery remain mandatory. Component effects and precision-by-window and
precision-by-scaling interactions are measured on development data. Small/sparse
and dense generic/coupled families expose density/path sensitivity. No new sparse
kernel is introduced. Fusion, vector/state precision, compression representation,
controller, packing and recovery remain the admitted executor's fixed mechanisms;
disabling them would require a new numerical implementation and admission. Their
individual causal effects remain unmeasured, rather than being inferred from a
native/FP4 contrast. Cold/prepared observations are distinct workloads, not a
causal residency ablation. No all-component optimum is claimed.

Direct controls are algorithmically matched native runs. Prior HiGHS, host-FP64
and external comparisons remain background; they are not pooled into this study.
SPEC-0013 requirement 20 is scoped accordingly: this campaign answers whether
FP4 value survives shared host improvements, not external competitiveness.
Only strict original-model 1e-9 is studied; no inference about 1e-7 is made.

New seeded operator groups define development, validation and holdout partitions;
all four RHS/objective variants stay with their operator. Historical inspected
operators remain development evidence. Holdout bytes are materialized only after
validation selects and freezes finalists. Selection cannot read holdout results,
and any later tuning requires a new study. All instances are constructed research
data; repeated timings do not establish production generalization.

PREP3 is deferred: equal source and target controls answer this study's question
without the optional source/target factorial or another optimization. Its 24000
CPU allocation remains unopened. Public defaults and GPUP-10 adoption remain
separate. Commit locally; no publication or historical allocation transfer.

The independent allocation is 112000 CPU / 15500 GPU seconds, with phase caps
and stopping rules in SPEC-0044. This is new authority for GPUP-9 execution,
not reopening earlier campaigns. Full native and current source-bound device,
process, recovery and serial admission precede scientific measurements. The
one-second supervisor, 100 ms advisories, four slots, sampled 16 GiB RSS, 12 GiB
owned device buffers and one pinned host lease remain unchanged.
