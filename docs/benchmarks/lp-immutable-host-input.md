# GPUP-HOST: immutable model reuse in fresh LP solves

Status: implemented and accepted, 2026-09-29, under
[SPEC-0016](../specifications/SPEC-0016-lp-immutable-host-input.md) and
[ADR-0028](../decisions/ADR-0028-immutable-lp-host-input.md).
Study identity: `gpup-host-v1`, development only.

## Result and boundary

All **28/28 admitted attempts** independently verify with both archived executables;
all **24/24 primary timings** certify. All **14/14 timing/profile pairs** retain
identical numerical and work digests. The two profile pairs show model parsing and
structural validation falling from two calls to one, with two sparse constructions
and every candidate, dual-certificate and gap assessment retained.

`LpInput` owns the validated original Model and borrows its exact input bytes.
The CLI borrows the model for its fresh solve, then consumes that input for evidence.
Private fields prevent pairing a supplied model with unrelated bytes. The existing
raw-byte endpoint constructor remains compatible. Endpoint construction still builds
its own sparse LP and freshly evaluates, certifies and assesses the gap; standalone
verification reconstructs independently. No assessment or certificate is cached.
The source audit confirms only the CLI solve and experiment LP runtime files change.
Backend interfaces, numerical kernels, settings, defaults, old schemas and session
paths are unchanged. The earlier throughput repair is a separate endpoint.

## Frozen protocol and reproducibility

[Protocol](../../benchmarks/configs/lp-host-v1.json),
[analysis](data/host/host-analysis.json), [trial rows](data/host/host-trials.csv),
[provenance catalog](data/host/host-provenance.json) and
[resource receipts](data/host/host-resources.json) retain all outcomes and hashes.
The baseline is commit `1818cdb5405fe466728c9cfb1719c67e22f660a5`; its exact git archive and newly
built executable are retained alongside the repaired source and executable.

Three repetitions compare both executables on small-4, irregular-32768,
irregular-65536 and dense_block-65536. Both write compact-v1 evidence and use tuned
FP64 resident/necessary/warp32_v1/separate. GPUP-EVIDENCE numerical settings are
unchanged: seed 17, one thread, affinity [0], all tolerances 1e-9, 50000 updates,
30-second deadline, two-second cleanup, 8 GiB host/device bounds, 32 MiB output cap,
128 MiB study reads and 120-second independent verifier timeout. Device UUID is
`GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48`. Blocked order uses seed 18001; uncertainty uses seed 18002 and
10000 bootstrap resamples. Four profiles are separate from the primary timings.

```sh
python3 tools/benchmark_lp_host.py --dry-run
python3 tools/report_lp_host.py
```

The report command checks the retained artifacts without starting GPU work or
mutating the ledger. Execution requires the exact-source native/device receipts,
frozen archives and remaining category allowance; attempted identities never rerun.
All raw evidence remains under `artifacts/gpup-host-v1`, baseline construction under
`artifacts/gpup-host-baseline`, and acceptance under `artifacts/gpup-host-acceptance`.

## Certified fresh-process latency

Times include input, fresh device setup, solving, certification, endpoint construction
and output. Independent verifier subprocesses are outside this process envelope.
Ratios are medians of paired baseline/repaired ratios; values above one favor reuse.
They are not ratios of the two displayed medians. No failure is omitted or imputed.

| Instance | Baseline median s | Repaired median s | Paired ratio [95% interval] | Certified baseline + repaired |
| --- | ---: | ---: | ---: | --- |
| small-4 | 0.485534 | 0.353663 | 1.394706 [0.755439, 1.421194] | 3/3 + 3/3 |
| irregular-32768 | 2.678887 | 2.660111 | 1.007059 [0.996458, 1.107853] | 3/3 + 3/3 |
| irregular-65536 | 5.319354 | 4.982512 | 1.067605 [1.064723, 1.069368] | 3/3 + 3/3 |
| dense_block-65536 | 6.729790 | 6.337285 | 1.063417 [1.051992, 1.068385] | 3/3 + 3/3 |

The 65536-row cells show a modest scoped reduction. The smaller cells have intervals
spanning one and do not establish an improvement. Three development repetitions do
not establish a general recipe, winner or supported preset. All settings remain
unchanged. Mixed-65536 was outside this frozen comparison; its existing timeout
limitation remains. These results make no claim about session throughput.

## Reconstruction and assessment counts

The JSON parse envelope includes structural validation; their times must not be
added. The table gives total invocation counts and inclusive parse wall across the
fresh process. Peak RSS is the existing sampled aggregate process-tree measure,
not an exact allocation trace. Full scope paths and exclusive costs are retained.

| Profile | Parse / validation calls | Sparse constructions | Candidate / certificate / gap calls | Inclusive parse ms | Peak RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| irregular-32768 / baseline | 2 / 2 | 2 | 9 / 9 / 4 | 272.613 | 202.29 |
| irregular-32768 / repaired | 1 / 1 | 2 | 9 / 9 / 4 | 126.979 | 201.85 |
| dense_block-65536 / baseline | 2 / 2 | 2 | 9 / 9 / 5 | 815.783 | 423.83 |
| dense_block-65536 / repaired | 1 / 1 | 2 | 9 / 9 / 5 | 388.359 | 425.80 |

Both profiles retain nine candidate evaluations and nine certifications; their gap
counts remain four (irregular) and five (dense). Each retains one final independent
original-program assessment. CPU before/after checks cover legacy and compact
output and confirm the same counts and numerical bits on a work-limited fixture:
[CPU evidence](data/host/host-cpu-equivalence.json). The sparse reconstruction and
preparation costs remain explicit candidates for later work.

## Acceptance, authority and limitations

Full pinned-native `bash tools/check.sh` passed before admission: **502 Rust tests,
183 Python tests**, independent exact-rational regressions, lint, schema/provenance,
record replay, 103-page documentation validation and smoke. Constructor coverage
includes versions 1-5, fallback, exact original bytes, malformed models, changed
same-ID models, altered witnesses and false assessments. CLI tests cover both
formats, fresh reconstruction, verification, replay and work-limited outcomes.
Budget/provenance tests use synthetic ledgers and need no local campaign artifacts.

All **55 regular device tests** pass. Six baseline/repaired 200-update pairs and
six compact replays cover tuned FP64, FP32 accumulation and gradual adaptive
recovery on small-4 and irregular-2048. Both executables independently accept all
18 endpoints; numerical bits and work counts match:
[device acceptance](data/host/host-device-equivalence.json).
The [source/ledger audit](data/host/host-source-ledger-audit.json) verifies both
source-tree hashes, the baseline git archive and 121 unchanged historical files.

The first final repository gate passed all numerical/integration tests but caught
a broken relative link in this report; its failed receipt is retained with the
corrected final gate. No GPU attempt failed or retried in this slice. Existing sanitizer receipts cover
only their original unchanged code scope; the old tuned_cases racecheck and
65536-row session gaps remain open. Compact mixed-65536 coverage, COPT graph
internals and adaptive overhead are not resolved by this model-only repair.

| Resource | Charged GPU seconds | Task cap |
| --- | ---: | ---: |
| Timing / ablations | 91.461934760 | 900 |
| Profiles / repeatability | 19.113062965 | 200 |
| Acceptance / repeatability | 23.497421121 | 300 |
| Combined | 134.072418846 | 1400 |
| Cumulative campaign | 15205.782575335 | 18002.574545061 |

All original phase caps and the 28800-second campaign bound remain. Added allowance
is zero. The ledger now has **15452 events**, SHA-256
`90dab78c269b74f511416ddd73cf05e123555ae006b9ad75fc896933a35f9cd2`.
Its 15392-event prefix remains
`6a30c1954ff9bc80c733364d8e8a7c0fc4c4439d70b959d2c10996d71993e518`.
No reservation remains unsettled. CPU child usage is separately metered in the
resource receipts, with four build jobs and a four-hour bound; the GPU ledger's
CPU field is not a substitute for those receipts. No new GPU work follows this
report. The next ready task is **GPUP-ADAPTIVE-COST**, which is not implemented here.

The corrected final repository gate passes the same 502 Rust/183 Python tests,
record replay, 104 documentation pages and smoke after report publication. Its
receipt and the initial broken-link failure are retained. Metered child CPU totals
1297.465518 seconds of the 14400-second bound; small source-edit and catalog
checks are outside that metered child total. The final catalog binds 335 artifact
references. No further GPU work or allowance was used.
