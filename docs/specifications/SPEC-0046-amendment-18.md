# SPEC-0046 amendment 18: prospective independent-audit host reservations

Both image-v3 256 M scientific cells complete under supervision. Before their
independent audit starts, its proposed 64 GiB host reservation plus 4 GiB headroom
does not fit the approximately 62.6 GiB currently available. No audit reservation
or attempted audit result exists at this preflight refusal.

The retained image-v2 audits on these same original arrays use the same image-v1
independent checker. Measured peak aggregate RSS is 8.751 GiB for the two 256 M
cases and 17.392 GiB for the two 512 M cases. Prospectively declare 32 GiB for the
never-started 256 M audit and 40 GiB for the never-started 512 M audit. These
reservations leave substantial margin above the retained peaks and retain the
mandatory physical 4 GiB headroom and sampled-RSS stops. Their 900/1800-second
time reservations and three-core numerical placement remain unchanged.

Every final and intermediate assessment still executes through the unchanged
independent original-model checker. This alters no numerical source, certificate,
scientific cell, timing eligibility or memory limit of a solve. All old receipts,
failed reservations, full charges and missing results remain.
