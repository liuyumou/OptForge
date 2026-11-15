# GPUP-9 controlled precision study

Protocol: [SPEC-0044](../specifications/SPEC-0044-gpup9-controlled-study.md); decision: [ADR-0078](../decisions/ADR-0078-gpup9-controlled-study.md).

**Complete study; no held-out value pass (0/12).** All 768 planned sessions / 14592 scientific solves complete and certify. The selected configuration regresses with simultaneous intervals below parity for coupled-2048/cold, generic-2048/cold, sparse-128/prepared. Other comparisons do not establish a value pass. These results support retaining the native default; no new FP4 recipe is promoted. Earlier MIXED2-CONFIRM2 and CHECKER2 decisions remain unchanged.

This study compares the same final CHECKER2 source and x86-64-v4 executable in native and FP4 lanes at strict original-model 1e-9. Complete changing-model prepared sessions are primary; cold single solves are measured separately. PREP3 remains optional and its allocation stays unopened. Public defaults and GPUP-10 adoption are separate.

## Coverage and frozen selection

| Stage | Planned sessions | Complete sessions | Retained complete-session solves | Certified |
| --- | ---: | ---: | ---: | ---: |
| screening | 144 | 144 | 576 | 576 |
| validation | 240 | 240 | 7680 | 7680 |
| holdout | 384 | 384 | 6336 | 6336 |

Screening selected: `fp4x2-w16-s0`, `fp4x2-w16-s1`, `native-w32-s0`, `native-w32-s1`. Coverage preceded the frozen geometric-mean timing rule.

Validation selected: `fp4x2-w16-s1`, `native-w32-s0`. Coverage preceded the frozen geometric-mean timing rule.

Descriptive three-block medians of matched native/FP4 complete-session ratios (same window and scaling):

| Family | w16 / unscaled | w16 / scaled | w32 / unscaled | w32 / scaled |
| --- | ---: | ---: | ---: | ---: |
| coupled-1024 | 1.0056 | 1.0279 | 0.9955 | 0.9930 |
| coupled-2048 | 0.9903 | 0.9921 | 0.7705 | 1.0070 |
| generic-1024 | 1.0191 | 0.9842 | 0.9313 | 0.9240 |
| generic-2048 | 0.9282 | 0.9205 | 0.9237 | 0.9235 |
| small-33 | 0.9489 | 0.9415 | 0.9426 | 0.9548 |
| sparse-128 | 1.0095 | 0.9244 | 0.9676 | 0.9500 |

Window 32 / window 16 complete-cost ratios; descriptive medians, with all paired values retained.

| Family | native / unscaled | native / scaled | FP4 / unscaled | FP4 / scaled |
| --- | ---: | ---: | ---: | ---: |
| coupled-1024 | 0.9779 | 0.9722 | 1.0062 | 0.9967 |
| coupled-2048 | 0.9750 | 0.9996 | 1.2604 | 0.9713 |
| generic-1024 | 0.9518 | 0.9999 | 1.0471 | 1.0687 |
| generic-2048 | 1.0143 | 1.0322 | 1.0327 | 1.0288 |
| small-33 | 0.9897 | 0.9859 | 0.9709 | 0.9738 |
| sparse-128 | 0.9760 | 0.9958 | 0.9990 | 0.9980 |

Scaling off / on complete-cost ratios; descriptive medians, with all paired values retained.

| Family | native / w16 | native / w32 | FP4 / w16 | FP4 / w32 |
| --- | ---: | ---: | ---: | ---: |
| coupled-1024 | 1.0082 | 1.0208 | 1.0117 | 0.9929 |
| coupled-2048 | 1.0062 | 0.9659 | 0.9863 | 1.2799 |
| generic-1024 | 1.0365 | 1.0029 | 1.0013 | 1.0046 |
| generic-2048 | 1.0013 | 0.9987 | 1.0173 | 1.0118 |
| small-33 | 1.0005 | 1.0085 | 0.9770 | 1.0037 |
| sparse-128 | 1.0219 | 1.0027 | 0.9809 | 0.9744 |

Descriptive ratios of precision contrasts quantify the tested interactions; values above one favor the numerator setting. These are not multiplicity-controlled confirmation results.

| Family | w16 vs w32, unscaled | w16 vs w32, scaled | scaling on vs off, w16 | scaling on vs off, w32 |
| --- | ---: | ---: | ---: | ---: |
| coupled-1024 | 1.0195 | 1.0256 | 1.0299 | 0.9802 |
| coupled-2048 | 1.2926 | 0.9717 | 0.9960 | 1.3251 |
| generic-1024 | 1.1139 | 1.0721 | 0.9554 | 0.9923 |
| generic-2048 | 1.0428 | 0.9967 | 1.0280 | 1.0183 |
| small-33 | 1.0108 | 0.9300 | 0.9585 | 1.0171 |
| sparse-128 | 1.0236 | 1.0023 | 0.9157 | 0.9818 |

The eight development configurations cross native/FP4x2, window 16/32 and scaling off/on. Three repetitions provide descriptive component and precision-by-window/scaling interactions; the portable archive retains every block and all unfavorable contrasts. Fixed fusion, controller, FP64 state, packing and recovery mechanisms have no separately estimated causal effects. Sparse cases use the admitted dense execution path. Cold/prepared differences are not a causal residency ablation.

Development, validation and holdout use distinct seeded operator groups. Every related RHS/objective scenario stays with its operator. Holdout descriptors were frozen before screening; model bytes were generated only after finalist selection. One operator per family per partition limits generalization; timing repetitions do not create independent problem samples. Cold means a fresh process, not flushed filesystem or hardware caches: provenance hashing precedes timed launch and may warm cached model bytes. Prepared requests reset FP64 state rather than warm-starting from prior solutions.

## Held-out results

The selected native-w32-s0 and fp4x2-w16-s1 finalists differ in scaling and audit window as well as arithmetic lane. These held-out results measure whole-configuration value; the matched screening contrasts above provide the narrower component comparisons.

Status: **complete**. 384 / 384 sessions; 6336 / 6336 retained complete-session solves certified. Missing sessions: 0.

| Family | Endpoint | Native ms | FP4 ms | Median speedup | Simultaneous interval | Savings lower bound ms | Scoped value |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| coupled-1024 | cold | 930.2776 | 968.3817 | 0.9555 | [0.8888, 1.0325] | -153.4983 | not established |
| coupled-1024 | prepared | 7194.9616 | 7390.6078 | 0.9638 | [0.5894, 1.0533] | -4557.9657 | not established |
| coupled-2048 | cold | 2214.4648 | 2477.4343 | 0.8847 | [0.8079, 0.9285] | -499.3109 | not established |
| coupled-2048 | prepared | 19233.7056 | 18183.3803 | 1.0535 | [0.9187, 1.1465] | -1826.0562 | not established |
| generic-1024 | cold | 794.7098 | 876.9976 | 0.9257 | [0.8392, 1.2738] | -149.7808 | not established |
| generic-1024 | prepared | 3264.2990 | 3562.1940 | 0.9632 | [0.6268, 1.0712] | -1916.4969 | not established |
| generic-2048 | cold | 1866.1151 | 2220.0144 | 0.8505 | [0.7865, 0.9639] | -507.0040 | not established |
| generic-2048 | prepared | 9914.5199 | 10024.0758 | 0.9811 | [0.8950, 1.0901] | -1146.7390 | not established |
| small-33 | cold | 424.3650 | 434.7846 | 0.9563 | [0.8959, 1.0104] | -48.8604 | not established |
| small-33 | prepared | 1667.8509 | 2320.3561 | 0.6838 | [0.6386, 1.8890] | -941.3621 | not established |
| sparse-128 | cold | 416.4176 | 439.6859 | 0.9579 | [0.8825, 1.0717] | -58.4231 | not established |
| sparse-128 | prepared | 2056.7472 | 2923.0566 | 0.7162 | [0.3925, 0.8676] | -1568.7791 | not established |

Ratios and absolute savings use 24 simultaneous exact-binomial median intervals at familywise alpha .05. With 16 blocks, ranks 2 and 15 give per-interval noncoverage 34/65536. A pass requires complete certified paired coverage, useful nonzero FP4 work, ratio lower bound >1 and savings lower bound >10 ms. No public preset or universal improvement follows.

Sign-test power for the required 15/16 positive blocks: p=0.75: 0.0635, p=0.8: 0.1407, p=0.85: 0.2839, p=0.9: 0.5147, p=0.95: 0.8108. Shared-host temporal dependence limits the independent-block interpretation.

Both execution-order strata, complete per-block values, setup/teardown and checker/audit/iteration partitions, physical work, recovery events and every negative result are retained in the machine analysis. GPU spans are nested diagnostics, not complete delivered cost.

Coupled-2048 prepared session medians are 19.234 s native and 18.183 s FP4, with paired median ratio 1.0535 and interval [0.9187, 1.1465]. Both lanes execute 800 physical updates per solve with no observed recovery. FP4 setup and independent checking account for 34.0% and 30.1% of summed complete cost. This identifies cost locations, not the cause of variation or a proven optimization benefit.


Order sensitivity and FP4 cost shares (summed partition time / summed full cost); order-stratum medians are descriptive because eight pairs give no finite interval at the simultaneous threshold.

| Family | Endpoint | Native-first ratio | FP4-first ratio | Setup % | Independent checking % | Iteration % | Native updates | FP4 updates | Native / FP4 recoveries |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| coupled-1024 | cold | 0.9584 | 0.9341 | 67.5 | 4.1 | 10.1 | 800 | 800 | 0 / 0 |
| coupled-1024 | prepared | 0.9656 | 0.9411 | 22.9 | 18.1 | 45.7 | 800 | 800 | 0 / 0 |
| coupled-2048 | cold | 0.8967 | 0.8643 | 78.1 | 7.0 | 5.1 | 800 | 800 | 0 / 0 |
| coupled-2048 | prepared | 1.0489 | 1.0538 | 34.0 | 30.1 | 22.9 | 800 | 800 | 0 / 0 |
| generic-1024 | cold | 0.9627 | 0.9097 | 78.3 | 1.8 | 2.4 | 200 | 200 | 0 / 0 |
| generic-1024 | prepared | 0.9818 | 0.9572 | 47.2 | 15.6 | 22.4 | 200 | 200 | 0 / 0 |
| generic-2048 | cold | 0.8288 | 0.8767 | 87.7 | 2.6 | 1.3 | 200 | 200 | 0 / 0 |
| generic-2048 | prepared | 0.9811 | 0.9839 | 60.9 | 18.0 | 11.3 | 200 | 200 | 0 / 0 |
| small-33 | cold | 0.9646 | 0.9435 | 58.5 | 0.3 | 14.0 | 600 | 600 | 0 / 0 |
| small-33 | prepared | 0.6792 | 0.6838 | 12.1 | 1.7 | 75.0 | 600, 800 | 600, 800 | 0 / 0 |
| sparse-128 | cold | 0.9694 | 0.9455 | 54.5 | 0.4 | 17.9 | 800 | 800 | 0 / 0 |
| sparse-128 | prepared | 0.7275 | 0.6975 | 9.2 | 1.6 | 78.9 | 800 | 800 | 0 / 0 |

All 58 available before/after block samples use driver 580.105.08; unavailable samples: 0. Boundary GPU utilization ranges 0–91%, device memory 15–40039 MiB, and temperature 23–51 C. These shared-device snapshots do not identify competing owners or establish the cause of any timing difference. Numerical workers use three of the four admitted CPU slots, with the fourth reserved for supervision.


## Correctness, failures and reproducibility

The full pre-device native gate passed 638 repository Rust / 794 Python tests, committed-record replay, 281 documentation pages and smoke. Isolated CHECKER2 acceptance passed 31 Rust tests; focused GPUP-9 contracts cover split separation, balance, failed/unsettled accounting, missing/duplicate cells, coverage-first selection, held-out retuning refusal, useful execution, multiplicity and strict schema/path/time validation. Final acceptance is recorded separately in the resource receipts.

Fresh CPU original-checker comparisons and device arithmetic/process/model-switch/recovery admission bind the selected executable. The CUDA image and numerical source remain unchanged; the prior exact image/source-bound four-sanitizer evidence is retained. No runtime, kernel or public build default changed.

The first admission pilot produced 32 retained responses, then the harness rejected an existing `checkpoint` cost field missing from its schema. The corrected schema admits the executor’s existing checkpoint/rollback/conversion partitions. The first attempt retains its sources, partial files, empty cleanup and full 2400 CPU / 600 GPU-second reservation. The new admission attempt has a distinct identity; no scientific cell was retried. All prospective design and implementation source versions remain separate; implementation-v5 is the frozen scientific harness. Two unused post-freeze review edits were preserved and restored before execution; the applicable selection checks were incorporated before scientific freezing. The initial sparse generator was refused for cross-partition operator leakage; generator-v2 adds seeded diagonal perturbations. A redundant inner budget check also refused the administrative freeze job itself; the outer unsettled-reservation gate remains unchanged. These two CPU-only refusals retain 2400 and 1200 CPU seconds respectively. No scientific cell was retried. The first source snapshot omitted the initial schema; its exact bytes were recovered by removing only the three added cost names and matching the immutable original design SHA-256. The supplemental recovery record preserves that provenance. Initial archive packaging then hit the unchanged 512 MiB per-file supervisor limit; its partial payload and exact publisher source are retained locally and hash-bound, with the full 4800 CPU-second charge. The replacement writer emits 48 MiB parts directly, and the reader seeks across those parts without constructing an oversized temporary file. A boundary-crossing ZIP contract verifies this correction. The first compact archive attempt then failed on an existing catalog (1200 CPU seconds); its initial replay also refused a decoder-window mismatch (240 CPU seconds). Production-stream tests exposed and corrected compressed versus uncompressed ZIP offsets and expanded-size accounting, and the replacement uses a bounded 64 MiB decoder window for its 32 MiB stream. Both failed attempts, sources, partial archives and full charges remain retained. No numerical observation was retried or resource limit enlarged.

Admission, including the first partial pilot: original serial authority checks 800 responses / 3136 assessment requests / 170 distinct endpoint/tier assessments. Timed certificates were never memoized; only identical requests in offline verification were deduplicated.

Scientific study: original serial authority checks 14592 responses / 56572 assessment requests / 490 distinct endpoint/tier assessments. Timed certificates were never memoized; only identical requests in offline verification were deduplicated.

Independent logical-work replay truncates updates at recovery and terminal rollback; rejected FP4 attempts do not count as useful execution. It verifies 7296 FP4 responses and records 0 responses with no retained FP4 updates. Every reported held-out pass retains nonzero accepted FP4 work in every candidate session.

Final native acceptance: **638 repository Rust / 810 Python tests**, plus the separately passed 31 isolated Rust tests. Portable replay and exact historical preservation pass. No scientific retry.

Portable exact-byte observation archive: [GPUP-9 evidence index](data/gpup9-evidence-v1.json). Run `python tools/replay_gpup9_archive.py replay` to reproduce selection, component contrasts, coverage and simultaneous decisions without the original artifacts tree. The compact archive embeds every response byte, all retained source versions and settled resource receipts. Original generated model bytes remain locally retained; the bundle preserves their generator versions, seeds, byte hashes and model manifests. Replay checks those bindings without regenerating model bytes. Solid Zstandard compression shares repetition across traces; decoding uses temporary parts bounded at 48 MiB, requiring about 5 GB of temporary disk. Install the pinned optional replay dependency with `python -m pip install -r tools/gpup9-evidence-requirements.txt`. The earlier full-model bundle remains locally retained and hash-bound. Statistical replay is separate from fresh serial-certificate execution; original serial acceptance is recorded above. Raw responses, partial files, sources and resource receipts are retained. The [closure companion](data/gpup9-closure-v1.json) preserves later administrative receipts and source bytes; `python tools/replay_gpup9_archive.py closure` independently recomputes all charges and validates full failed reservations.

Committed evidence payload: 102.58 MB in 3 parts, reduced from 2.13 GB (95.19% smaller). All response bytes are retained; 124 generated model files are represented by source/seed/hash bindings. The earlier full bundle and original inputs remain local.


## Independent resources and disposition

| Phase | CPU charged s | CPU ceiling s | GPU charged s | GPU ceiling s |
| --- | ---: | ---: | ---: | ---: |
| implementation | 7628.338318732 | 12000 | 0.000000000 | 0 |
| native | 3175.609392300 | 16000 | 0.000000000 | 0 |
| acceptance | 4205.968250484 | 16000 | 780.307440048 | 2000 |
| screening | 2313.542749264 | 6000 | 575.771492199 | 1500 |
| validation | 8056.475015676 | 16000 | 2005.388773384 | 4000 |
| holdout | 7664.866645692 | 32000 | 1902.250103782 | 8000 |
| reporting | 11530.888080588 | 12000 | 0.000000000 | 0 |
| cleanup | 135.144034116 | 2000 | 0.000000000 | 0 |

Total charged: **44710.832486852 CPU / 5263.717809413 GPU seconds**, against 112000 / 15500. Includes 512 preparation and 128 closing CPU administration. Historical allocations stay closed; held-out resources did not fund tuning.

Four CPU slots, sampled aggregate RSS 16 GiB, owned device buffers at most 12 GiB, one pinned shared host lease and the unchanged one-second supervisor apply. Every >100 ms advisory remains in the receipts. Sampled RSS is not a peak-memory enclosure. Full failed reservations are charged.

Allocation status: **closed**; failed reservations: 6; all resource cleanup empty: True. Retained 100 ms advisories: 340; maximum observed sample gap 276.168 ms and scan work 253.867 ms; maximum sampled aggregate RSS 12.732 GiB. No push, publication or GPUP-10 execution release.

Historical preservation: 2256 files byte-exact; earlier navigation text and unrelated backlog entries preserved against `3377bf96eeb5`.
