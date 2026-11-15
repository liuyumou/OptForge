# SPEC-0044: GPUP-9 controlled study and frozen finalists

Status: accepted under the user's GPUP-9 implementation request
Scope: bounded LP research; no runtime defaults or public presets
Owner: LP research
Introduced: GPUP-9 / ADR-0078
Last reviewed commit: bootstrap
Supersedes: scoped endpoint/control rules identified in ADR-0078
Implementation: tools/lp_gpup9_*.py; unchanged CHECKER2 Rust executor and CUDA image
Tests: tests/integration/test_lp_gpup9.py and source-bound acceptance receipts

## Frozen design

The protocol MUST be written before any comparative measurement. It binds source,
binary/image, original serial checker, generator, seed, split, grid, schedule,
analysis and resource policy. Hash mismatches, duplicate trials, changed finalist
identities and cross-partition operator reuse MUST refuse execution. Each trial
is immutable, including failure. An interrupted trial is never scientifically
retried. Admission is labeled separately and never pooled with study results.

Six families are small-33, sparse-128, generic-1024/2048 and coupled-1024/2048.
Operators are seeded diagonally dominant matrices; coupled cases add a cyclic
0.5 neighbor. Sparse cases have only diagonal and cyclic neighbor terms; the
executor still uses its admitted dense path. Dense signed off-diagonals provide
cancellation. Four bounded primal/dual vectors generate equality RHS and objective
streams. These are independently seeded operators, not transformations of one
operator across partitions. All four scenarios share one partition. Exact binary
values in the generated original model are certificate authority; construction
witnesses are not substitutes for independent checking. Source/license: repository
generator under the repository MIT license. Seeds and operator digests are stored.

Development seed base 440078, validation 540078, holdout 640078; family index is
added to each. Admission uses 340078 and is always development-only. Generator
parameters and future holdout descriptors are committed before screening, but
holdout bytes, solves and assessments MUST remain inaccessible to selection.
One operator group per family/partition limits generalization; inferential claims
are per named group, never across a population of LP instances.

Eight configurations cross lane native/FP4x2, window_max 16/32, and scaling off/on.
All use fixed audits, audit_max=200, max_updates=10000, wall_ms=30000, original
absolute/relative 1e-9 checking, identical resource limits and FP64 reset per solve.
The binary is CHECKER2 build-v5, target x86-64-v4, and its existing CUDA image.
No endpoint-answer cache or mathematical/runtime change is permitted.

| Stage | Blocks | Configurations per group | Requests/session | Endpoints |
| --- | ---: | ---: | ---: | --- |
| Screening/component interactions | 3 | 8 | 4 | complete prepared |
| Validation | 10 | 4 (best scaled/unscaled per lane from screening) | 32 | complete prepared |
| Frozen holdout | 16 | 2 (one native and one FP4 finalist) | 32 and 1 | complete prepared and cold separately |

Within every group/block the configuration order is a seeded cyclic balanced
schedule; for the two holdout finalists each order occurs eight times per endpoint.
Family/endpoint pair order is independently shuffled within each block.
Screening chooses the best window separately for each lane/scaling using
coverage first, then the geometric mean of paired per-group session medians
relative to native-w32-s1, then lexical identity. Validation chooses one finalist
per lane by the same coverage-first aggregate rule. Aggregates are selection
rules only; reports retain every per-group result and never hide regressions.
Selection requires all expected rows; missing evidence stops progression.
Uncertified completed sessions rank below fully certified configurations. If no
configuration in a lane has full coverage, freeze its best available configuration
for explicitly labeled failure evaluation; no winning recipe can result.

Before each freeze, all planned blocks' full worst-case reservations MUST fit the
remaining stage cap. Admission timing MUST show 1.5 times projected session cost
fits the block reservation. Failure of feasibility stops before freeze; do not
shrink the roster after seeing measurements. Stage block wall reservations are
screening 400 s, validation 360 s, holdout 480 s. They include teardown and
supervision. The roster is respectively 144, 240 and 384 complete sessions;
holdout includes 192 prepared sessions / 6144 solves and 192 cold single solves.

## Measurement and analysis

Prepared time starts before process/input creation and includes four-model cache,
preparation, switching, all requests, audits, recovery, independent certificates,
durable response files, EOF and owned destruction. Cold runs cache no additional
models. Nested solve/checker/GPU spans are diagnostics and MUST NOT be added to
overlapping outer spans. Capture environment/competing-device telemetry before
and after blocks, or an explicit reason it is unavailable.

Screening reports all main contrasts and the two two-factor interactions at each
third-factor setting, with paired block values. These three-repetition estimates
are descriptive and MUST NOT be called confirmation. Density comparisons remain
between named instances, not isolated execution-path effects.

Holdout inference uses simultaneous exact binomial median intervals for six
groups x two endpoints x ratio/savings = 24 intervals at familywise alpha .05.
With 16 blocks, ordered observations 2 and 15 have noncoverage 34/65536 per
interval, satisfying Bonferroni. A scoped group/endpoint pass requires all 16
pairs, every original-model certificate, useful nonzero FP4 execution, ratio
lower bound >1 and savings lower bound >10 ms. The 10 ms floor is a research
criterion, not a production SLO. Report sign-test power at p=.75/.8/.85/.9/.95
and both order strata. Small/sparse controls retain the same decision and full
regression table; no universal win is required. Incomplete evidence suppresses
confirmation; failures and partial files remain visible. A complete negative
result completes the study, while missing coverage is explicitly incomplete.

Every response's final and intermediate assessments MUST be checked against the
original serial authority. Repeated identical assessment requests may be deduplicated
for offline validation, but never for timed solver certification. Validate all
record/model/configuration/image hashes, work counts and disjoint lifecycle costs.
Portable replay MUST reproduce selection, intervals, coverage and decisions without
the original artifacts tree. Retain all observations and admission/source receipts.

## Resources and stopping

| Phase | CPU seconds | GPU seconds |
| --- | ---: | ---: |
| Implementation, including 512 preparation administration | 12000 | 0 |
| Full native acceptance | 16000 | 0 |
| CPU/device/process/recovery admission and pilots | 16000 | 2000 |
| Screening | 6000 | 1500 |
| Validation | 16000 | 4000 |
| Holdout | 32000 | 8000 |
| Independent serial checking, replay and reporting | 12000 | 0 |
| Cleanup and closure, including 128 closing administration | 2000 | 0 |
| **Total** | **112000** | **15500** |

Receipts: artifacts/gpup9-v1. Reserve four times the wall deadline in CPU seconds;
GPU jobs reserve the entire lease-held lifecycle. Failed jobs retain full charges
and immutable sources. Unsettled reservations or overruns close further execution.
Use the unchanged one-second supervisor, 5–10 ms target, all >100 ms advisories,
four CPU slots, 16 GiB sampled RSS, 12 GiB device buffers and one pinned shared
lease. Sampled RSS is not a peak enclosure. Holdout resources cannot fund tuning.
Loss of supervision or nonempty cleanup stops execution for disposition; no
automatic scientific retry. Preserve old files, allocations and decisions exactly.

Acceptance requires the full native gate, isolated CHECKER2 CPU checks, current
source/image/device/process/recovery admission, meaningful protocol corruption and
leakage tests, original serial certificates, portable replay, complete positive,
negative or explicitly incomplete report and empty cleanup. GPUP-10 remains
separate; no public preset follows automatically.

## Prospective implementation corrections before scientific execution

The initial admission exposed a wire-schema omission for existing checkpoint,
rollback and conversion cost fields. Keep its 32 partial responses and full
2400 CPU / 600 GPU-second charge; the corrected admission is separately identified.
The original sparse generator then failed the cross-partition operator-hash guard:
its diagonal and cyclic neighbor were constant despite distinct seeds. Keep that
CPU-only refusal and its full 2400-second charge. Neither event launched or froze
a scientific cohort, and neither opens additional resources.

Study identity **gpup9-v2**, generator **gpup9-diagonal-v2**, adds seeded bounded
diagonal perturbations to the sparse family, preserving its sparsity and conditioning.
All future partitions use newly recorded manifests under models-v2. The original
design, partial models, pilots and sources remain immutable. Seeds, splits,
configuration grid, endpoints, sampling, statistical criteria, solver, CUDA image
and the independent allocation are unchanged. Implementation-v3 binds the final
source before scientific measurement. Offline evidence validation may hash each
distinct original model once per invocation; timed certificates are never cached.

Implementation-v4 finalizes the preflight projection before any scientific
freeze: retain all observed non-request cost, add the maximum observed request
cost times the declared count, and apply the predeclared 1.5 margin. Cold
projections conservatively retain the four-model pilot setup. This corrects the
overly conservative use of all 32 pilot requests for four-request screening;
the hard block reservations and every statistical choice remain unchanged.

Implementation-v5 removes a redundant inner admission check that rejected the
metadata freeze job's own active reservation. The outer budget wrapper still
checks all earlier reservations before admitting any job; whole-stage caps and
the supervisor remain unchanged. Retain the failed administrative reservation's
full 1200 CPU seconds and sources. No scientific cell had been frozen or run.
