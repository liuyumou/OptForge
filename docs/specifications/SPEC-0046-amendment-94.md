# SPEC-0046 amendment 94: FP4x2 PDLP overhead

Status: user-authorized implementation, 2026-11-27. The user requests applying the
reviewed overhead techniques to FP4x2 PDLP, preserving PR #30, correctness before
benchmarking, strict original-model 1e-9 checks, and the existing resource limits.
A default change is authorized only when evaluation demonstrates improvement.

This changes the isolated original-array low-bit executor. Pricing algorithms,
pricing kernels, shared runtime crates, resource supervisors and historical
images remain exact. The baseline and protected-source hashes are retained in
`/storage/ai-optimizer-billion-v1/fp4x2-overhead-v1/plan.json`.

Implement in order:

1. Transfer solve-owned device matrices and packing buffers from preparation to
   execution. Keep host reference mirrors and exact original kernels. Transfer
   ownership rather than retaining duplicate device allocations. Keep all shape,
   finite-value, transpose, allocation and hash-overflow fallback checks.
2. Skip uploads only at a downloaded, accepted control boundary. Initial state,
   restoration and probes use full resets. Preserve FP4 anchors, reference
   products, encodings, control100/certificate500 and strict rejection tests.
3. Reuse bounded solve-local certificate arrays, preserving every enclosure bit,
   reduction order, first refusal, repaired multiplier and objective convention.
4. Overlap one immutable snapshot's CPU proof with durable witness output within
   the same assessment boundary. Join before any next PDLP update or acceptance.
   Use at most three certificate workers plus the writer. Publish repaired-dual
   arrays after the writer joins. Propagate both proof and output failures.
   Deadline rollback and all intermediate and independent final proofs remain.

All four options default off. The first overlap deliberately contains no
speculative GPU advancement; it does not change the iterate or stopping policy.
Nested proof/output timings must not be added to exclusive complete time.

Keep the 570000 CPU / 68000 GPU totals and all exact phase caps, four slots,
128 GiB global host / 80 GiB GPU / 400 GiB storage limits and existing ownership,
idle, sampling, cleanup and async-v1 storage rules. The smaller planned candidate
envelope is four slots, 16 GiB host, 4 GiB device, 8 GiB new storage; scope CPU
maxima by phase are implementation 4000, native 1720, admission 4800, development
16000, reporting 4000, cleanup 480 seconds. GPU maxima are admission 1200 and
development 4000 seconds. These reserve only existing headroom; no new funds or
phase transfers. Every failure retains its original/full charge. All launches
require fresh identities and source-bound reservations; no old LP or driver repeats.

Correctness gates precede benchmarking: complete CPU differential tests, explicit
option/default and legacy-interface rejection tests, source preservation, then
fresh sustained idle admission, exact GPU continuations and all four sanitizers.
Cover genuinely FP4-active inputs, zero-eligible fallback, long-line host
preparation fallback, recovery, cancellation, deadline rollback, multiple
requests and every candidate combination. Run no GPU work while the device is busy.

Default promotion requires at least three fresh seeds in rotated cold pairs,
separate witness stores, complete input/preparation/solve/output/final-proof cost,
unchanged certification coverage and criteria, >=5% median complete improvement,
no family >5% median regression, and no memory-limit regression. Preserve all
failed/uncertified attempts. If evidence is unavailable or inconclusive, retain
opt-in settings. Frozen pricing sources and its selected paths must remain exact;
no pricing algorithm is introduced into PDLP.


The original local planning envelope named 1600 native CPU seconds. The additive
`native-envelope-v2.json` raises only that self-imposed subset to 1720 to cover the
retained cache-selection failure and the worst-case quality reservation; the
26000 native phase cap is unchanged. Its prospective label was recorded while
the quality reservation was already active. It is a contemporaneous accounting
correction, not prior evidence or a retroactive change to the shared budget.
Actual native charges for this work are 863.011299344 CPU seconds, including the
full failed reservation. See the [evaluation report](../benchmarks/lp-fp4x2-overhead.md).
