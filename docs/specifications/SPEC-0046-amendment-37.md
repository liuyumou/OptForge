# SPEC-0046 amendment 37: preserve CPU fallback peak and correct the unstarted billion reservation

The fresh-process diagnostics expose an earlier CPU engine-construction peak.
`Engine::new` clones the prepared scaled CSR/CSC before releasing their originals;
those original vectors can have geometric capacities. GPU preparation normally
consumes exact-length arrays, but the unchanged explicit CPU fallback must also
fit. The amendment-36 lifetime formula omitted this transient. Preserve its frozen
formula and preliminary 60 GiB coupled estimate as superseded, not as final
capacity admission. Keep the unchanged 8 GiB internal allowance and 4 GiB physical
headroom above every newly included stage.

The six-family 64 M and coupled 256 M diagnostic reservations already cover this
CPU transient with their existing allowances. They may finish unchanged. Before
the one-billion preparation is attempted, source-bound operational plans remove
that identity from the CPU-only whitelist. This is a prospective preflight stop;
no active job is interrupted and no process is signalled. Preserve the original
15-cell freeze and its 56 GiB host declaration. After deriving and testing the
corrected CPU construction and spectral bounds, issue an additive disposition
and new plans for that still-unattempted cell, with the larger derived reserve.
Do not repeat any of the fourteen attempted paired observations.

The corrected formula must include CPU engine construction, CPU spectral scratch,
GPU preparation, bounded packing, upload, control/certificates and independent
checking. Retain all stage times, actual peaks, regressions and exact hashes.
No numerical source or executable changes are required by this correction. Fresh
harness admission must bind the corrected formula before the unstarted billion
CPU diagnostic or any future full solve. No GPU admission, certified solve,
allocation-cap increase, guard relaxation or publication is implied.
