# ADR-0048: Execute the external baseline under a separate bounded allocation

Status: accepted under the user's 2026-11-10 implementation instruction and
additional 3600 GPU seconds. Scope: GPUP-BASELINE only.

The [comparison contract](../specifications/SPEC-0022-external-lp-baseline.md)
remains the numerical and comparison authority. Its proposal stays nonexecutable.
A new execution manifest freezes adapters, checker, original models, libraries,
device UUID, affinity, settings and ordered jobs. The Rust bridge is an isolated
research binary using the existing original-model evaluator, outward dual bound
and gap predicate. Native infeasibility/unboundedness remains unverified.

Allocate 3600 new GPU seconds: 480 for admission and 3120 for conditional
screening. Preserve the old campaign ledger byte for byte and use a separate
append-only baseline journal. No GPUP-8 allowance is consumed. Allocate at most
16000 CPU seconds for this newly authorized task within the existing remaining
18036.902496786 CPU seconds: implementation 2400, hardware 240, admission 2400,
screening 8960, reporting 1200 and restricted cleanup 800. Historical charges
remain unchanged. The retained supervisor charges four times active wall time,
including finalization; failed jobs retain their complete reservation.

The full ten-lane, eight-model, three-repetition grid remains planned. This
allocation does not promise its worst-case completion. Reserve each entire job
before launch and stop when its phase cannot cover it. Record every remaining
cell as unexecuted, with its reason. No phase borrowing, shorter deadline,
weaker tolerance, automatic retry, replacement solver or held-out access follows.
Independent unavailable lanes stay in the denominator. A failed mapping or
correctness gate blocks that lane's dependent timing; shared provenance or
containment failure blocks the whole release.

Use the retained cooperative supervisor without a host/container change or
bootstrap rerun. The worker adds bounded logs and sampled per-process GPU-memory
observations. Neither sampled RSS nor GPU observations are hard containment.
Four CPU affinity slots and the shared host GPU lease apply to every native job.
Admission jobs reserve 30 wall seconds, including two cleanup seconds; all native
calls in a suite share 20 seconds. Screening reserves 60 seconds including two
cleanup seconds, with a 40-second native solve limit. End-to-end timing spans
fresh worker launch through durable witness, independent certificate and exit.

Separate immutable candidate bytes avoid a certificate/hash reference cycle.
The certificate binds the original model, candidate and actual checker binary;
the enclosing execution manifest binds that binary to its source and libraries.
Effective parameters and readback evidence accompany the candidate. The final
endpoint links the certificate; the controller verifies all bindings before
counting a certified time. A vendor's status and reduced costs confer no authority.

GPU claims require a bound device UUID and affirmative native execution evidence
or a process-attributed GPU activity observation during the solve. A context or
memory allocation alone is insufficient. Unconfirmed execution stays unknown.
Only admitted lanes may enter screening. Missing licenses, runtime incompatibility
and checker refusals are evidence to preserve, not reasons to change dependencies.

GPUP-8 remains incomplete with scientific stages closed; GPUP-9 remains gated.
This decision implements the baseline priority of ADR-0047, not its later solver
redesigns. Gurobi is unavailable and excluded.
