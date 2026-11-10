# ADR-0050: Separate bounded logs from bounded model and certificate artifacts

Status: accepted engineering correction within the user's GPUP-BASELINE
implementation request and existing allocation. No additional CPU or GPU budget.
Supersedes: the accidental whole-file 16 MiB implementation limit only.

The specification limits stdout and stderr to 16 MiB each and original JSON
artifacts to 128 MiB. The first worker incorrectly used a 16 MiB `RLIMIT_FSIZE`,
which also applies to native evidence and certificate files. An observed
2048-variable certificate occupies about 1.6 MB; the 32768/65536-variable models
need larger artifacts. This is a transport defect, not a solver accuracy result.

Stop v2 at the completed five-model development block. Preserve all 150 planned
cells (90 attempted, 60 cuOpt-gated), every admission outcome and all charges.
The first large HiGHS reservation crossed the stop boundary; retain its complete
240 CPU-second reservation and its partial evidence, settle only after the
unchanged coordinator reports empty cleanup and all recorded process identities
are gone, and do not count it as a timing. The interrupted guardian's active
journal and `guardian_lost` receipt remain intact; settlement does not relabel
them as passing resource evidence.

The new v3 launcher bounds each output stream independently through pipes,
retains at most 16 MiB per stream, and kills the owned worker group on overflow.
Artifacts retain a separate 128 MiB file limit. New CPU checks must demonstrate
both refusal of excess logs and successful writing of an artifact larger than
16 MiB. The existing process-tree guardian still owns timeout, aggregate RSS,
CPU affinity and cleanup. No host/container or numerical supervisor change.

Reuse all v2 admission outcomes, including cuOpt refusals. Reuse all five completed
development-model blocks after exact configuration, native-adapter body, model
and checker comparison. Only the remaining three large-model blocks run under
the corrected transport. Per-model comparisons never mix v2 and v3 timings.
Native methods, seeds, precision, tolerance, time/work limits and the complete
240-cell denominator stay unchanged. All three identities count against the
same 16000 CPU/3600 GPU seconds, with no phase borrowing or historical refund.

The four cuOpt lanes remain unadmitted. Double precision misses original-model
feasibility on the nontrivial fixture; mixed/single endpoints fail strict quality.
The concurrent presolve-only maximization endpoint has an unresolved dual mapping.
No quality criterion is relaxed and no numerical retry is authorized by this
transport correction. GPUP-8 stays incomplete; GPUP-9 stays gated.
