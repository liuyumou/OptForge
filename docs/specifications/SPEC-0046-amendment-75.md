# SPEC-0046 amendment 75: explicit deletion of obsolete large objects

The user explicitly says: "You can just delete the old large data and release the
disk space." This supersedes the cold-data archive proposal in amendments 73-74.
Delete obsolete owned large chunk objects directly, without creating a second
large archive. Preserve every chunk required by the four untouched billion inputs
and every returned endpoint still awaiting independent checking. Recompute that
protected set immediately before deleting. Keep small timing/certificate/resource
records, source/image bindings, failure receipts and content-hash metadata.

Use a fresh 90-second cleanup reservation within the remaining cleanup cap after
the passed source compaction. Restrict deletion to planned regular objects/*.bin
files at least 8 MiB, with unchanged inode, size and modification time. Record each
removed path/hash/size and released allocated blocks. Never touch other users'
files. Once the remaining solves and audits complete, the user's authorization
also permits deleting their now-obsolete large objects with a new protected-set
plan and a fresh reservation. No attempted scientific cell repeats.

The already completed source compaction losslessly archives 151015 older snapshot
files; its full hash verification precedes removal of loose copies. Its 394.036800272
CPU-second charge and empty cleanup are retained. Required current sources remain
loose. Future snapshots will share immutable source objects, avoiding repeated
copies. Old raw-data portable replay will no longer work without regenerating the
deleted chunks; reports must state this deliberate user-authorized retention limit.
Strict certificates already checked are not changed or reclassified by deletion.
