# GPUP-THROUGHPUT branch review and CPU verification repair

Reviewed 2026-09-22: `feat/gpup-throughput` at `14a1a88f1e34efa078549710c005bd63ca20e025`
against `main` at `0e7811a34615ea1fddf072b32f2a2de400904e95`.
Recommendation: request changes for the four findings below. The bounded host
performance repair is implemented separately from those unresolved findings.
The [original throughput report](lp-repeated-solve-throughput.md), protocol,
measurements, code objects and campaign ledger are retained unchanged.

## Review findings

1. **P1 — Stamp the tuned identity on every session outcome.**
   [TunedSession::solve](../../crates/optimizer-lp-cuda/src/session.rs) returns
   `bare(...)` directly after a bound-upload fault, a device fault, or cancellation
   before any completed work. That helper emits `backend: cuda-lp`, schema 2 and
   no execution identity. These exits bypass the tuned stamping at the end of
   `solve`; the ordinary backend applies that stamping around all outcomes.
   The CLI can therefore write an endpoint that its own verifier rejects with
   `inconsistent fallback identity`. Preserve the failure/interruption record,
   but finalize its tuned identity on every exit. The device tests check the
   failure status/poisoning without passing those outcomes through the endpoint
   verifier. A CPU reconstruction of the exact `bare` fields reproduces the
   rejected endpoint; it is not a newly injected device fault.

2. **P2 — Use the ordinary single-solve path for the fresh-variant control.**
   In [the planner](../../tools/benchmark_lp_throughput.py), `fresh-variant`
   belongs to `BATCH_KINDS` and runs `batch`/`solve-batch` with N=1. Thus the 360
   reported variant comparisons test a long session against another session,
   not against the independent ordinary `solve` entry point. A defect shared
   by those two session paths would pass. Materialize the selected variant on
   the host and run the ordinary solve command in a separately versioned
   follow-up protocol. Until then, describe those 360 comparisons as N=1
   session controls; the 4,425 repeat comparisons use the ordinary path.
   The existing small device differential tests remain useful, but do not turn
   these study comparisons into fresh single-solve controls.

3. **P2 — Verify the common tuned execution identity across batch records.**
   [BatchEndpoint::verify](../../crates/optimizer-experiment/src/lp_batch.rs)
   independently validates every file but only compares its requested backend
   and classification to the summary. It never checks that all solves use
   one method settings document and code object. A two-solve directory with
   different internally consistent code-object hashes, correct record hashes
   and a correct batch payload passes verification. That contradicts
   SPEC-0014 requirement 6 and prevents the verifier from establishing that
   these records came from one admissible session. Check common settings and
   execution identity across records and bind intended settings at the batch
   level when evolving the evidence contract. The CPU reproduction uses the
   existing synthetic tuned endpoint fixture and real constructors/verifiers.

4. **P2 — Compare floating-point encodings when reporting bitwise identity.**
   [identity_count](../../tools/analyze_lp_throughput.py) uses Python dictionary
   equality over decoded numbers, so `+0.0` and `-0.0` count as identical.
   The probe `identity_count([({'primal': [0.0]}, {'primal': [-0.0]})])`
   returns `identical: 1`. Compare primal and dual values through their binary64
   encodings, with a signed-zero regression, before calling the counts bitwise.
   This is a verifier weakness; no signed-zero divergence in the archived
   study is asserted here.

Reproduction sources and output are retained in
`artifacts/gpupt-review-cpu-20260922/reproductions.rs` and `reproductions.log`.
The temporary tests were removed after demonstrating the failures; tests that
assert defective behavior are not added to the acceptance suite.

## Challenge to the performance interpretation

Context reuse addresses a measured cost, and keeping cold starts and fresh host
certification makes this a useful controlled experiment. The 26.6x comparison
nevertheless measures amortization of fresh-process setup. It establishes
neither faster numerical iteration nor competitiveness with a persistent CPU
solver, warm-started LP solver, or a MILP workload. Those comparisons were not
measured and need their own contracts and budgets.

The negative large-model result also includes avoidable producer work. Every
research `Evidence::new` reconstructs the preconditioner and Operator while
self-verifying. At batch completion `ResearchBatchEvidence::new` independently
verifies every file again, repeating both preparations. An N-solve batch thus
performs 2N evidence preparations in addition to the solver session's setup.
These preparations are outside the reported session setup phases. The original
32768-row and 65536-row results describe that implementation and evidence
pipeline, not an inherent size limit of reusable sessions.

## Implemented bounded repair

[Research evidence verification](../../crates/optimizer-experiment/src/lp_research.rs)
now reuses independently computed host operator metadata within a batch.
The private cache checks each fresh canonical program's matrix, objective,
row bounds, variable IDs and sense plus the complete method and arithmetic
mode. A bounds-only variant can reuse operator norm bounds, step, matrix tail
and scaling hash. A changed matrix, method or mode forces preparation again.
The producer's per-solve self-checks and final directory verification share
this cache; a separately invoked verifier builds its own cache from the model.
Thus batch evidence preparation falls from 2N to one, and independent batch
verification from N to one. The session's own preparation remains separate.

Model parsing, candidate evaluation, original-model certification, gap checks,
work/identity checks, file hashes and payload hashes still run for every solve.
Public single-evidence verification remains uncached. No device or kernel code,
solver arithmetic, schema, settings, threshold, seed or frozen protocol changed.

CPU verification measurements, three repetitions with alternating baseline and
candidate order, N=8, fused FP64, retained repetition-0 records:

| Evidence | Original median | Repaired median | Ratio | Time reduction |
| --- | ---: | ---: | ---: | ---: |
| irregular-2048 repeat | 0.970 s | 0.638 s | 1.52x | 34.2% |
| irregular-32768 repeat | 18.905 s | 12.732 s | 1.48x | 32.7% |
| irregular-32768 variant | 19.366 s | 12.737 s | 1.52x | 34.2% |

These are CPU-only verification times, **not measured solve-throughput gains**.
All 18 timed invocations accepted the same archived evidence, whose hashes were
checked before and after. Raw samples and input/binary hashes are in
`artifacts/gpupt-review-cpu-20260922/timing.json`. Baseline executable SHA-256:
`ec778ceeba80bc072525c4447863a46e892d72bc11fc94d151c088a4ab776e1e`;
measured candidate:
`a49a0a010363a29828b56b822f3aa2cc6c5ecc8f9a857ebaf38136c9d526838f`.
The candidate executable is retained alongside the results.

Reproduce without GPU work:

```sh
python3 tools/benchmark_lp_batch_verify.py \
  --baseline artifacts/gpup-throughput-v1/lp_precision_research \
  --candidate artifacts/gpupt-review-cpu-20260922/lp_precision_research
```

The three new CPU regressions cover byte-identical cached/uncached evidence,
bounds-specific reassessment, rejection of altered provenance, invalidation
on matrix/method/mode changes, and one preparation across both producer checks
and final directory verification. All 11 research evidence tests pass. The
candidate also re-verifies 17 historical single endpoints covering all twelve
research modes, v1/v2 evidence and all three tolerance tiers. The full pinned
native gate is recorded in the active-task acceptance evidence.

No GPU job ran. The 8178-event campaign ledger remains at
6951.059845871 seconds with SHA-256
`dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6`.
The earlier tuned_cases racecheck coverage gap remains open. End-to-end GPU
throughput for the repaired producer has not been measured. Remaining host
costs include repeated model serialization/parsing and repeated certification;
changing those paths needs separate equivalence evidence.
