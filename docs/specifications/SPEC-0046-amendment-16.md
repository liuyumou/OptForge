# SPEC-0046 amendment 16: prospective racecheck host reservation

Operational GPU v9 passes all 60 exact continuations after a fresh six-minute
idle observation. The next preflight sees approximately 62.5 GiB of host
MemAvailable, below racecheck's proposed 64 GiB plus mandatory 4 GiB headroom.
No racecheck v5 reservation or workload starts at that refusal.

Before its first attempt, declare 56 GiB sampled host RSS for racecheck v5. Keep
the 4 GiB physical headroom guard, 240-second reservation, three analysis workers,
eight-launch synchronization limit, every instrumented fixture and all fatal
sanitizer errors. The supervisor stops owned work if it reaches the smaller RSS
reservation. This remains within the approved 128 GiB allocation ceiling and
changes no GPU memory guard, numerical implementation or certificate. It does not
admit a later large solve without that solve's own full physical host headroom.
Preserve all earlier failed admissions and their sources/charges unchanged.
