# FP4 pilot: synchronization recovery

Status: explicitly approved by the user, 2026-11-11
Date: 2026-11-11
Parent: [SPEC-0027](../specifications/SPEC-0027-fp4-gpu-pilot.md)
Prior release: [packing recovery](lp-fp4-gpu-pilot-packing-recovery.md)
Diagnosis: [retained racecheck failure](../benchmarks/data/fp4-gpu-pilot-race-diagnosis-v2.json)

V2 passes all 30 corrected FP4 primitives, reuses 30 control primitives, passes
90 trajectory/transaction checks and all 24 memcheck paths. Racecheck passes four
native paths, then refuses FP8-four-component split updates with 128 warnings
(100 hazards displayed, zero error-severity reports, exit 86). Warning-severity
races fail the unchanged zero-hazard criterion. Nineteen racecheck, all initcheck
and synccheck paths, and all 216 profiles remain unexecuted. The failed sanitizer
retains its full 960 CPU / 240 GPU-second reservation. Every v1/v2 file stays exact.

Shared-state unpacking reads codes/scales that encode subsequently overwrites.
The [v3 candidate](../../research/lp-fp4-gpu-pilot/cuda/pilot_v3.cu) adds one
full-warp barrier at encode entry, after those reads and before stores. All lanes
participate, and subsequent early exits are warp-uniform. No arithmetic, packing,
tolerance, variant, workload or control changes. NVIDIA's [racecheck guidance](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html)
requires explicit synchronization for these intra-warp shared-memory hazards;
the [CUDA guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/) documents
memory ordering from syncwarp. This diagnosis does not treat the warning as benign.

CPU-only compilation succeeds with zero spills. A source audit verifies exactly
one barrier addition and identical native-FP64 SASS. All original sources,
images, outputs and failure charges are preserved. Device safety of v3 is untested.

## Bounded attempt

Freeze a fresh v3 manifest, corrected image and resource identities. Reuse the ten
native primitives, fifteen native device cases, and four native paths each from
memcheck/racecheck, with hashes and unchanged native SASS. Re-execute the changed
five component lanes under v3 identities: 50 primitives, 75 trajectory/transaction
cases, 20 memcheck and 20 racecheck paths. Run all 24 initcheck and 24 synccheck
paths, which have no prior passes. After admission, execute the unchanged 216
profile cells once. Reused v2 arithmetic successes remain observations from an
image that failed sanitizer admission; they do not excuse checking v3.

Reserve at most 300 GPU seconds each for primitives and device checks, and 240
each for the four sanitizer suites: 1560 GPU / 6240 CPU seconds. The existing
599.495183240 GPU-second charge plus this maximum is 2159.495183240, within the
unchanged 2400 acceptance cap. Nine profile batches reserve at most 180 GPU /
720 CPU seconds each, within the unchanged study caps. Total task ceilings remain
72000 CPU / 9600 GPU seconds, with all failures charged and no historical transfers.

This proposed release authorizes one synchronized candidate and conditional
continuation. A numerical, safety or resource failure stops the affected stage;
no automatic further correction/retry is included. No criterion is relaxed,
certificate issued, preset selected or closed historical experiment reopened.

The user explicitly released this concrete synchronization recovery after review.
