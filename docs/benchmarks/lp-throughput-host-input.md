# GPUP-THROUGHPUT host input reuse

Status: implemented and accepted, 2026-09-22. This is a second internal performance repair after the
[review corrections](lp-throughput-corrections.md), under the existing
[SPEC-0014](../specifications/SPEC-0014-lp-repeated-solve-throughput.md) contract.
The CPU binary is retained as lp_precision_research; the final checked binary
is lp_precision_research.checked and differs only by removing a needless Rust
reference found by Clippy. Both exact executables are retained.
No method, kernel, numerical tolerance, default, record schema or supported
preset changes.

## Design and authority

The original research evidence path repeatedly parsed the same JSON model and
rebuilt both sparse matrix orientations during evidence construction, assessment
and re-verification. A 32768-row input is about 32 MB. Even after caching
operator verification, N=8 verification spent about 12.8 seconds in host work.

A private HostInput now owns a validated host Model, its canonical LinearProgram
and the exact model-byte hash. Single-record entrypoints construct it from raw
input once. Batch boundaries independently construct a canonical base input
once; repeat solves borrow it. A bounds variant is materialized against the
validated host model and the host LP is rebound through with_variable_bounds.
The variant constructor is private and only accepts the existing materializer's
output, which preserves the matrix, objective, domains and row bounds.

The producer and standalone verifier each construct their own host inputs.
Neither accepts a device/session-supplied model or program. Every evidence check
still recomputes candidate feasibility/objective, certification and gap from the
current bounds. Assessments and certificates are never cached. Request, payload,
model and operator identities remain checked. Memory retains one base and at
most one active bounds variant, rather than all materialized batch models.

## Paired CPU measurements

Three paired repetitions, alternating executable order, using unchanged archived
N=8 fused-FP64 evidence. Baseline is the correction executable, which already
includes the earlier operator-verification cache. All 18 timed invocations
accepted the same evidence and the tool checked that input files were unchanged.
These are CPU-only verification times, not solve latency or GPU throughput.

| Archived case | Baseline median | Candidate median | Speedup |
| --- | ---: | ---: | ---: |
| irregular-2048 repeat | 0.656 s | 0.186 s | 3.53x |
| irregular-32768 repeat | 12.821 s | 3.484 s | 3.68x |
| irregular-32768 bounds variant | 12.832 s | 7.344 s | 1.75x |

Raw samples, executable hashes and input hashes are in
artifacts/gpupt-host-input-20260922/timing.json. Reproduce on retained archives:

```sh
python3 tools/benchmark_lp_batch_verify.py \
  --baseline artifacts/gpup-throughput-controls-v1/lp_precision_research \
  --candidate artifacts/gpupt-host-input-20260922/lp_precision_research
```

## Bounded producer diagnostic

The active task admits exactly two existing original cells: irregular-32768,
N=8, fused FP64, tier 1e-9, 200 updates, repetition 0, short repeat and short
bounds-variant batches. All numerical requests are regenerated from the frozen
original protocol and compared before substituting the new source/executable
hashes. No thresholds, seeds, limits or precision policies change.

`tools/check_lp_host_input.py run` requires the exact-source full native gate,
archives source and inputs before admission, and uses one 48-second supervised
worker with a 54-second reservation in the original gpupt study pool. There is
no retry or new allowance. Its `verify` action checks both directories with the
original and new executables and compares every per-solve numerical/work
identity using binary64 encodings. Per-command process times are recorded;
comparisons against historical supervised batch times are unpaired diagnostics,
not confidence intervals or a general performance claim.

At entry, remaining study budget is 54.022860302 seconds, acceptance
58.328048581 seconds; cumulative consumption is 6982.408046756 seconds. Every
previous ledger prefix and the 8102.574545061-second cumulative ceiling remain.


Both diagnostic batches completed. Each contains eight iteration-limit records,
exactly as the original 200-update controls; no record is promoted to certified
success. The original and optimized executables independently verify both new
directories. All **16/16** primal/dual, status, iteration, restart and launch
identities match the archived corresponding solves bit for bit.

| Whole N=8 batch process | Historical original | Optimized diagnostic | Ratio |
| --- | ---: | ---: | ---: |
| irregular-32768 repeat | 48.679 s | 10.746 s | 4.53x |
| irregular-32768 bounds variant | 49.444 s | 22.484 s | 2.20x |

These ratios include both host repairs relative to the original study. The
historical times are the original supervisor's batch process durations; new
per-command times are measured around process launch/completion within the
leased diagnostic worker. Supervisor polling/launch overhead is not identical.
Each new case ran once, so this is a scoped historical comparison with no
statistical claim. The updated ordinary single-solve path was not timed here;
these results do not establish a current paired amortized-vs-fresh speedup.
The 65536-row cases were not rerun. No general preset is selected.

## Acceptance and budget

Full pinned-native tools/check.sh passes: 481 Rust test results, 150 Python tests,
93 documentation pages, strict lint/format, schema, provenance, replay and smoke
gates. The new host-input regression checks byte-identical evidence against raw
input, bound-specific assessments, incorrect model hashes and independently
rebuilt LP equality. Seventeen archived single endpoints covering all twelve
research modes, evidence v1/v2 and the three tolerance tiers reverify. All 18
paired CPU measurements accepted unchanged evidence. The original and optimized
verifiers independently accept the two new batch directories and all 16 solve
identities match. Numerical kernels did not change; this host-only repair does
not close the earlier tuned_cases racecheck gap.

The device diagnostic charged 33.512914747 seconds. GPU accounting is now:

| Quantity | GPU seconds |
| --- | ---: |
| gpupt study / unchanged cap | 2679.490054445 / 2700 |
| gpupt acceptance / unchanged cap | 541.671951419 / 600 |
| gpupt combined / unchanged cap | 3221.162005864 / 3300 |
| cumulative campaign / unchanged ceiling | 7015.920961503 / 8102.574545061 |

The 8278-event ledger SHA-256 is
`c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a`.
Its 8276-event prefix remains
`b3451186b7a5fc0029fbbd612b07e795072476ab76137a78a375b1d97866c236`;
all earlier prefixes are unchanged. No reservation remains unsettled.
Measured producer source identity:
`97a77c12e52a87d185442a168a5211dbba0019ebe46284f58c1b91aaf9cbb362`.
The exact source archive, native receipt, both executables, code object, frozen
requests, plan, timings, endpoint directories, old/new verifier receipts and
ledger are retained in artifacts/gpupt-host-input-20260922. The worker's observed
aggregate peak RSS was 521310208 bytes, inside its unchanged 8 GiB limit.
