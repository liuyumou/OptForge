# ADR-0051: Remove benchmark validation and serialization overhead

Status: accepted CPU implementation correction within the current baseline task.
The user-authorized GPU cap remains 3600 seconds and the CPU cap remains 16000.

The first large-model transport trials reveal two harness costs: repeated generic
JSON-schema walks over large canonical arrays, and the new checker's unbuffered
pretty-JSON writes. A retained 65536-variable project trial reaches an endpoint
but is killed while writing a certificate tens of megabytes long. These are
benchmark implementation costs; they do not establish GPU solver inferiority.

Stop v3 at a settled job boundary, preserve every timeout and charge, and use a
new v4 identity. Keep all v2 admission outcomes and the five completed small-model
blocks. The large-model observations remain separate historical attempts; v4
does not relabel them. Native adapters, precision, quality, iteration/time limits,
original models and the complete grid stay unchanged. CuOpt numerical refusals
are not retried.

Compile only the two flat, reference-free canonical-model/endpoint schemas with
pinned `fastjsonschema==2.21.2`, installed in a separate hash-bound overlay. Refuse
unsupported dialect keywords. Retain the original strict JSON parser, finite
checks, exact-integer policy, sparse ordering/bounds checks and conversion bodies.
New differential tests cover the compiled validator and malformed records. Bind
the wheel and installed files; do not alter either vendor environment.

Use a 1 MiB `BufWriter` for the research checker's output. Compare the entire
assessment function and strict parser byte for byte with the retained checker;
the only production change is buffering followed by flush and fsync. A new
serialization test checks exact pretty-JSON bytes and immutable output behavior.
The certificate identifies the actual new binary. Reused receipts retain the
old checker hash through an explicit source-equivalence bridge.

Reallocate within the unchanged 16000 CPU seconds: implementation 2700, hardware
240, admission 2400, screening 9860, reporting 600, restricted cleanup 200.
This explicitly moves 300 reporting seconds to implementation and 900 remaining
reporting/cleanup seconds to screening. Every job still reserves its own two
cleanup seconds. All prior charges count before new reservations. GPU phase caps
remain hardware 60, admission 420 and screening 3120; there is no GPU borrowing.

New large-model trials retain the same 40-second native and 60-second outer
limits. Run only while full reservations fit. Original strict certificates and
three matched repetitions remain mandatory for a paired speedup. Missing cells,
past timeouts and engineering corrections remain visible. No general commercial
solver ranking or supported precision preset follows from this development set.
