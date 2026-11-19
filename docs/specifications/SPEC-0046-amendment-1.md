# SPEC-0046 amendment 1: native acceptance reservation

The first new native gate reserved 12 GiB and stopped at 12.00019 GiB sampled
aggregate RSS. Its preceding native gates measured 12.77 GiB under 16 GiB
reservations. Preserve the interrupted gate, completed Rust checks, missing Python
tail, source snapshot, empty cleanup and full 12000 CPU-second charge.

Before another native gate, transfer 8000 unspent CPU seconds prospectively from
implementation to native acceptance: their ceilings become 22000 and 20000 CPU
seconds. Every other phase ceiling stays as opened. The user-approved aggregate
240000 CPU / 30000 GPU seconds, four CPU slots, 128 GiB sampled host RSS, 80 GiB
owned device buffers, 400 GiB storage, idle-only Pro6000 use and supervision stay
unchanged. The corrected native gate reserves 16 GiB, matching prior acceptance.

This administrative correction launches no scientific cell and changes no earlier
charge, certificate criterion, default, benchmark outcome or allocation.
