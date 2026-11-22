# SPEC-0046 amendment 48: distinguish vendor setup from optimization capacity

Every returned 64 M COPT capacity response, and the returned coupled 256 M CPU
response, records zero simplex, barrier and PDLP iterations. They reach the time
limit during setup. A returned process with a GPU-start log does not validate
active optimizer workspace. Preserve those responses and their descriptive setup
costs; do not silently promote them into billion-scale capacity admission.

Require at least one actual optimization iteration, or an independently strictly
accepted presolve-optimal endpoint, in addition to the existing successful process,
ownership and memory checks. Preserve every interrupted or missing capacity path.
Record optimizer counters and vendor MemPeak beside process HWM and sampled
aggregate RSS. The installed COPT guide defines MemPeak and MemLimit in MB. Compare
those same-unit values directly: a forecast exceeding the admitted 48000 MB vendor
setting also refuses that configured baseline. The soft setting is not a hard
physical enclosure, and vendor MemPeak is not interchangeable with sampled RSS.

No full-scale COPT performance result is claimed from initialization-only evidence.
Any unsupported COPT lane stays visible in the thirty-cell roster, with its exact
reason. Continue all admitted project billion-scale lanes after the complete
capacity dispositions; do not hold them indefinitely for an unadmitted comparator.
All prospective resource reservations, strict certificates, physical/ownership
limits and the no-repeat rule remain. No COPT setting, attempted cell or historical
result is changed. Fresh readiness regressions precede the final classification.
