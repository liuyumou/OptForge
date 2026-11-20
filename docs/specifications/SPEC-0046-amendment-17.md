# SPEC-0046 amendment 17: complete racecheck time reservation

Racecheck v5 completes the seven small preparation comparisons, including the
explicit CPU fallback, then reaches the 240-second reservation's guardian deadline
during the full recursive-norm case. The deep-norm sanitizer log is incomplete;
there is no completed result or passing suite. Owned cleanup is empty, there is no
overrun, and the full 960 CPU / 240 GPU-second charge and all source/partial output
remain. No scientific cell has started or repeated.

Fresh racecheck v6 keeps the complete original fixture, all power iterations,
three analysis workers, eight-launch synchronization limit, 56 GiB host reservation
and every fatal sanitizer check. Reserve 600 seconds before launch from the current
admission phase; the normal full-charge and physical-headroom rules remain. This
changes the time reservation only, not coverage, numerical code or strict
certificates. Fresh preparation-harness CPU v6 verifies cohort bookkeeping and
retention of the failed v5 receipt. Initcheck and synccheck retain their never-started
identities and 120-second reservations. Total and phase ceilings remain unchanged.
