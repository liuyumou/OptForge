# FP4 pilot: proposed packing recovery

Status: explicitly approved by the user, 2026-11-11
Date: 2026-11-11
Parent: [SPEC-0027](../specifications/SPEC-0027-fp4-gpu-pilot.md)
Diagnosis: [retained primitive comparisons](../benchmarks/data/fp4-gpu-pilot-diagnosis-v1.json)

The frozen v1 attempt completed 31 of 60 primitive cases. Thirty FP64/FP8/FP16
comparisons pass; the first FP4 comparison fails. All remaining device/safety,
four-sanitizer and 216 profile cells stay unexecuted. The failed reservation
retains 1200 CPU and 300 GPU seconds. No result is relabeled as a pass.

The CUDA 13.0 PTX contract requires E2M1 in bits 5:2 of each byte for
kind::f8f6f4. V1 incorrectly puts it in bits 3:0. The separate
[corrected kernel](../../research/lp-fp4-gpu-pilot/cuda/pilot_v2.cu) shifts the
nibble by two in exactly the two A/B fragment-expansion sites. Persistent packed
storage, component scales, recurrence, mathematical comparison tolerances and
all controls remain unchanged. Four new CPU tests cover every canonical code,
all 225 signed code pairs and the exact two-site source delta. A separate
compile-only image retains PTX, cubin, SASS and resource reports. A CPU model of
noncanonical bytes matches all 32 failed outputs, but that behavior is empirical:
nonzero padding is outside the instruction contract.

The first CPU diagnosis assumed padding was ignored and failed. Its source/log
and full 480 CPU-second reservation remain. The corrected diagnosis makes no
claim that the old malformed fragments obey a specified hardware behavior.

## Concrete proposed attempt

Use a fresh gpup-fp4-gpu-pilot-v2 manifest and output tree. Bind the corrected
kernel, compiler/image, unchanged Rust executor, passed CPU correction tests,
source bridge and all v1 failures/receipts. Reuse the 30 unaffected primitive
comparisons with explicit provenance. Execute the 30 FP4 primitive cases once,
then conditionally all 90 ordered-update/transaction cases, four independent
24-path sanitizer suites, and the same 216 planned profile cells under new
versioned identities. No passed v1 numerical identity is retried.

Reserve at most 300 GPU seconds for corrected primitives, 300 for device safety,
and 240 for each sanitizer: 1560 GPU seconds total. Together with v1's 300 charge,
this fits the task's 2400-second acceptance cap. CPU reservation is four times
wall (6240 seconds), within the acceptance cap after the failed 1200 charge.
Nine profile batches may reserve 180 GPU / 720 CPU seconds each, subject to
whole-job admission under the unchanged study caps (7200 GPU / 8000 CPU seconds).
Actual successful charges settle; failures retain full reservations. No new
allocation or transfer from any closed historical task is requested.

The same primitive tolerances, safety requirements, four sanitizer gates,
workloads, update counts, repetition order and empirical-only conclusions apply.
Any corrected numerical/safety/resource gate failure closes that stage again.
No solver certification, public default, GPUP-8 retry or GPUP-9 release follows.

SPEC-0027's frozen stop rule requires a new explicit recovery release before
this device attempt. Preparation and CPU-only validation do not supply that
release. The user explicitly released this recovery after reviewing the concrete proposal.
The original v1 attempt remains refused; the new v2 attempt has its own identity.
