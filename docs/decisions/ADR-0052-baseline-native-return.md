# ADR-0052: Complete the baseline with an explicit cuOpt return policy

Status: accepted under the user's instruction to continue and complete the
baseline, and to count a cuOpt result without a reported error as a pass while
honestly recording its differences. This supersedes the CPU-only next-step and
cuOpt certificate-based admission restrictions for this continuation only.

Keep the original strict certificate unchanged. Add a separate cuOpt
`native_return_pass` observation from its actual Solution error status, error
message and termination reason. A returned Solution with error status zero,
an empty error message and a recognized non-error termination passes this policy.
Iteration/time limits remain limits, and infeasibility/unboundedness remains an
unverified native claim. None becomes certified optimality. Missing status,
exceptions, numerical errors and malformed provenance never become passes.

Preserve original raw vendor termination, objectives, residuals and duals, along
with the adapter's existing normalization and the independent checker's verdict.
Do not silently fix the concurrent maximization sign or attribute it to cuOpt:
the adapter mapping is unresolved. Native success and mathematical quality are
different report columns. Comparisons using this user policy are explicitly not
quality-matched certified speedups. Unconfirmed GPU activity stays unconfirmed.

Use a new v5 identity and reuse all 123 completed screening trials, including
their 15 uncertified outcomes. Execute exactly the 117 previously unexecuted
cells, with the same models, settings, 40-second native limit, 60-second outer
reservation, deterministic relative order and three repetitions. Existing cuOpt
admission refusals are retained as strict diagnostic outcomes; they no longer
block the newly authorized native-return comparison. No old solver test,
certificate, profile or numerical trial is rerun. New CPU tests cover the policy
and metadata export; existing hardware/source acceptance is reused after hash
admission. No new vendor installation or solver build is necessary.

The user's continuation authorizes this new bounded work allocation; it does not
reopen old scientific stages. Allocate at most 32000 new supervisor CPU seconds:
implementation 1600, screening 28080 (117 full 240-second reservations), reporting
1600 and restricted cleanup 720. The 128-second fixed preparation allowance is
inside implementation. This is a new continuation cap, not a transfer from the
closed GPUP-8 or v1–v4 CPU stages; retain and report every historical charge.
The historical 77640-second GPUP-8 ceiling remains a closed historical allocation,
not a claim that the new continuation fits it.

Keep the user's total baseline GPU cap at 3600 seconds. Prior charge is
1277.244626616, leaving 2322.755373384. Reserve at most 2322 whole GPU seconds in
v5 screening, leaving the fractional remainder unallocated. Full per-job
reservations must fit; no implicit GPU increase, shorter deadline or dropped
failure is allowed. The worst-case GPU grid exceeds this remaining cap, so actual
completion depends on observed usage; a resource refusal must remain explicit.

The retained supervisor, four CPU affinity slots, single shared GPU lease,
16 GiB sampled host RSS, 12 GiB sampled GPU memory, 16 MiB per output stream and
128 MiB per artifact remain unchanged. Resource/transport failures are reported
separately from vendor returns and checker refusals. No worker retry is automatic.

Baseline execution is complete when all 240 planned screening cells have settled
attempts and the new report contains native, transport, resource and certificate
outcomes for all of them. This does not require every solver to succeed and does
not relabel the old incomplete report. GPUP-8 remains incomplete, GPUP-9 gated.
No default solver precision or production backend changes follow.

Contract: [SPEC-0023](../specifications/SPEC-0023-baseline-native-return.md).
