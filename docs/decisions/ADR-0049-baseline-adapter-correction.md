# ADR-0049: Correct baseline integration and expose supported thread controls

Status: accepted implementation correction under the user's instruction to
implement GPUP-BASELINE within 3600 additional GPU seconds. No resource increase.
Supersedes: ADR-0048 only for the explicitly described engineering correction;
all numerical, timing, memory and full-grid requirements remain unchanged.

The first frozen execution establishes six COPT admission passes: CPU PDLP,
GPU PDLP and CPU default each pass both five-case suites. Preserve and reuse
these exact results. Two device probes pass. Preserve every original source,
archive, manifest, failed attempt, partial artifact and full failure charge.

The cuOpt adapter calls nonexistent `set_row_lower_bounds` and upper-bound
methods; its public API names them `set_constraint_lower_bounds` and
`set_constraint_upper_bounds`. This is an adapter defect before any cuOpt solve.
Correct both setter and getter mapping in separate v2 source files and cover it
with a CPU mock that exposes only actual public API names.

Project and HiGHS requests for four threads are rejected by the retained
`SolveOptions` validator, which supports one thread. Do not weaken that retained
contract or silently label a one-thread solve as four-thread execution. The v2
proposal explicitly requests one supported native thread for these three lanes;
cuOpt and COPT retain four. All jobs retain the same four-CPU affinity/budget
envelope. This comparison measures implementations within equal available CPU
resources, and reports their different native thread usage. It is not a claim of
equal parallel CPU work. This setting change has its own proposal hash.

The project execution-settings file also collides with the worker's execution
observation filename. Correct the settings filename in the new adapter. This
fix preserves the method settings and observation format.

These are construction/admission defects, not failed solver convergence. The
new identity `gpup-external-baseline-v2` admits only the corrected/new lanes.
It reuses COPT suites after exact function/configuration/checker/model comparison,
and reuses both hardware probes. No passed suite or old failed identity reruns.
New journals account for **both** identities before reservation. No phase
borrowing or historical refund occurs. New mathematical or resource failures
retain their charges and block their dependents; they do not authorize another
correction or numerical retry. Screening remains all eight models, ten lanes and
three repetitions, with explicit unexecuted cells when gates or funds prevent it.

The original proposal and v1 implementation remain intact. The v2 entrypoint is
`tools/lp_baseline_study_v2.py`; v1 is a retained failed admission identity.
GPUP-8 remains incomplete and GPUP-9 remains gated.
