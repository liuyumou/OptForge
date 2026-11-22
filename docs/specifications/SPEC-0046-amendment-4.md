# SPEC-0046 amendment 4: prospective solve and audit phase transfers

Measured preparation and serial checking costs require a larger share of the
existing allocation for final solves and independent endpoint audits. Before the
256 M cohort is frozen, transfer unused phase capacity prospectively. The totals
remain **240000 CPU / 30000 GPU seconds**; no earlier allocation or charge changes.

| CPU phase | Previous ceiling | New ceiling, seconds |
| --- | ---: | ---: |
| Implementation | 22000 | 10000 |
| Native acceptance | 20000 | 20000 |
| Admission | 36000 | 12000 |
| Development | 120000 | 130000 |
| Reporting and independent audits | 36000 | 62000 |
| Cleanup | 6000 | 6000 |

GPU admission transfers 5000 unused seconds to development: new ceilings are
1000 and 29000 seconds. Existing charges fit these ceilings. Failed reservations,
including the missing 128 M irregular cell, keep their entire original charges.

A prospective operational readmission plan binds this transfer and the original
cleanup disposition. It names new CPU and GPU admission jobs before launch. The
latest plan requires those successful settlements and current source bindings
before further development. It does not replace the prior cleanup observation,
failure, numerical admission, source snapshots or operational results. Fresh
resource tests and exact GPU continuation comparisons precede new scientific work.

The four CPU slots, 128 GiB sampled RSS, 80 GiB owned device buffers, 400 GiB owned
storage, pinned idle-only device, one-second supervisor and every 100 ms advisory
remain unchanged. Final cohort limits still require a complete prospective
reservation after the remaining capacity observations; the phase transfer alone
does not admit any model or imply a certified solve.
