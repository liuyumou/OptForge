# SPEC-0046 amendment 52: approved phase transfer and GPU packing readmission

The user explicitly answers amendment 51's exact phase-transfer question:
"Approve the phase transfer". Apply its CPU caps 6000/18000/52000/151000/92000/1000
for implementation/native/admission/development/reporting/cleanup, and GPU caps
7000/28000 for admission/development. Totals remain 320000 CPU / 35000 GPU seconds.
Keep the original recovery approval and settlement unchanged. A separate immutable
transfer record binds that approval, the old and new phase caps, this protocol and
the explicit user answer. The original single-overrun exception is unchanged.

Operational CPU v22 must pass the original supervisor and complete billion
resource harness tests. A new CPU-only observation job must then establish the
unchanged five-minute idle window, at least six samples with gaps at most ninety
seconds and a fresh final sample. Operational GPU v19 uses the previously admitted
image-v2 sixty-continuation exercise. All prior non-overrun cleanup dispositions
receive additive plans binding these same gates. No GPU preparation candidate or
performance job starts before those source-bound gates pass. Every other overrun
still closes execution; attempted jobs/cells cannot be retried.

The new packer remains opt-in and separately compiled; public defaults, solve
CUDA, FP64 preparation CUDA, strict original-model certificates and all physical,
idle, ownership and cleanup limits remain unchanged. Candidate bitwise packing,
solve-continuation and four-sanitizer admission precede any timing cohort.
