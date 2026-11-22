# SPEC-0046 amendment 12: bounded racecheck tracking

The corrected complete memcheck suite passes with the unchanged numerical image.
Racecheck v3 stops during the recursive norm fixture when sampled host RSS reaches
17182568448 bytes, exceeding its 16 GiB job reservation. Its partial sanitizer log
contains no completed deep-norm result; it is not a passing racecheck admission.
Preserve its full 960 CPU / 240 GPU-second charges, retained source and partial
outputs. Supervision cleans up only its owned processes and confirms empty cleanup.

A fresh `array-racecheck-v4` admission retains every fixture and all 20 full solve
continuations. Use three racecheck CPU workers and force a stream synchronization
after at most eight launches to bound queued instrumentation metadata. No kernel,
block, hazard or launch is filtered or skipped; sanitizer errors remain fatal and
exact numerical comparisons remain mandatory. This image uses a single ordered
stream. Synchronizing that stream changes instrumented execution scheduling, not
the shared-memory checks within its kernels. This is an admission run, not a
performance measurement. See the [NVIDIA sanitizer memory guidance](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/).

Declare 64 GiB sampled host RSS for this admission, within the approved 128 GiB
allocation limit, and retain its 240-second time reservation. The never-started
initcheck and synccheck suites each use 120 seconds, more than three times the
completed memcheck suite's approximately 34-second elapsed time. All original
supervisor cadence, GPU ownership and physical headroom checks remain mandatory.
Retain the interrupted racecheck receipt in future image-v3 cohort freezes.
No numerical source, strict certificate, total allocation or phase ceiling changes.
