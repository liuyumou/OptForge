# SPEC-0046 amendment 45: retain stale-allocation assertion; bound owned children

Operational CPU v19 passes all 75 supervisor tests and 55 of 56 resource tests.
Its sole failure is the obsolete assertion of the original 240000/30000 totals
following the user's explicit 320000/35000 approval. Retain full 720 CPU / zero GPU
seconds and empty cleanup. Correct only those two expected totals; all physical
and idle/ownership assertions remain. Fresh CPU v20 replaces failed CPU v19 in
plans v29/v30 and the exact-overrun bootstrap. GPU v17 remains unattempted.

Admit a directly owned child deadline for prospective COPT capacity/science and
checker workers, leaving thirty seconds inside each outer reservation for owned
termination, evidence persistence and supervisor finalization. Never signal a
PID discovered from GPU telemetry or another job. A timed-out child remains a
failed cell, retains raw output and the full reservation charge, and is never
retried. This does not lengthen vendor solver limits, weaken the outer supervisor,
relax any future overrun, or turn missing output into a successful timing.

For the never-started COPT capacity tail, separate independent final checking
into CPU reporting reservations so a vendor call cannot consume the checker's
allowance. Reserve the whole stage's solve and possible check costs prospectively.
Final checking stays strict and includes all available endpoints; absent endpoints
remain explicit. No previously attempted capacity cell repeats. Keep 300-second
64 M tail process reservations and 240/360 seconds at 256/512 M, respectively,
with unchanged 30/60/120-second vendor solver walls.
