# SPEC-0046 amendment 11: preparation sanitizer harness correction

Operational GPU v8 passes after the required idle observations. Image-v3 then
passes all 66 bitwise preparation comparisons and 60 exact solve continuations.
The first memcheck reservation, `array-memcheck-v3`, stops at its 1025-term host
fallback: compute-sanitizer rejects a target that makes no instrumented CUDA call.
Its raw response is exact and explicitly reports zero allocated device bytes and
host fallback. Six preceding GPU cases report zero errors. Preserve the failed
reservation, partial outputs, source snapshot, empty cleanup and full 960 CPU /
240 GPU-second charges. This is not a completed sanitizer suite.

The corrected harness runs the unchanged host fallback fixture without CUDA
instrumentation and still requires its bitwise comparison and explicit backend.
Every actual GPU case, including the recursive norm fixture and all 20 solve
continuations, retains mandatory instrumentation and fatal sanitizer errors.
Run the complete corrected memcheck suite under fresh identity
`array-memcheck-v4`; the other three never-started sanitizer suites retain their
original identities. Prospective image-v3 cohort freezes bind both the failed
receipt and corrected admission. This does not repeat a scientific cell or alter
the numerical implementation, certificate checks, memory/idle guards, supervision,
resource ceilings or any historical result.
