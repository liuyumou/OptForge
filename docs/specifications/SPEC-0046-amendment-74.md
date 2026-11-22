# SPEC-0046 amendment 74: compact evidence storage and source deduplication

The source archive plan identifies 151015 redundant loose snapshot files containing
1.617 GiB of source bytes. Perform this user-requested cleanup in a fresh 180-second
cleanup reservation (720 CPU seconds fits the remaining 862.847932184), rather
than the preliminary implementation-phase estimate in amendment 73. This is
verified evidence compaction, not a relabeled build or numerical acceptance job.
All protected images, operational source bindings and current campaign snapshots
remain loose. Cold-object archive packaging/verification retains the prospective
900-second reporting reservation, subject to the exact remaining audit budget.

Future source retention should store each unique byte sequence once in an immutable
content-addressed source store, with one manifest per reservation. Each manifest
retains the same original and retained size/SHA-256 references. Existing snapshots
and archives remain unchanged. Test reuse, changed contents and corrupted-object
rejection before fresh operational CPU v29 / GPU v23 admit the changed budget
source. The native disk counter, complete traversal, all time/memory/ownership
limits and numerical image-v11 stay unchanged. Preserve every prior failure.
