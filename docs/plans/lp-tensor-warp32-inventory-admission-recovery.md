# Proposed correction of GPUP-8 inventory admission

Status: proposed, not accepted. No new admission, compilation or GPU work is
authorized by this document. Preserve the accepted inventory-continuation plan,
all historical receipts and the newly failed 64-CPU-second setup reservation.

The artifact-only adapter incorrectly requires `.cargo-checksum.json` in Cargo's
extracted cache. Read-only diagnosis verifies all 26 retained crate archives
against Cargo.lock and every extracted member against its archive. All 26 lack
that metadata file. The failure is in the adapter's provenance assumption, not
an observed dependency change. The 11 focused adapter checks already passed.

The unexecuted artifact draft inventory_admission_recovery_draft_v2.py replaces
only dependency validation: require one retained archive/source directory per
locked registry package, hash the archive against Cargo.lock, compare every
member byte for byte, reject unsupported/duplicate/unsafe members and additional
source files other than Cargo's `.cargo-ok` marker. Preserve the failed source.
Before running it, select a new journal, pin the exact updated documentation
allowlist and new resource receipt names, and add focused tests for corrupt
archive bytes, altered or extra extracted files and missing archives. Reuse the
already passed software checks; run no tools/check.sh gate again.

No additional CPU seconds are proposed. Transfer 36 unused worker CPU seconds
to implementation. This adds to the 28 remaining setup seconds, providing a
64-second correction envelope: 8 for preparation, 32 for one corrected
source/provenance admission with focused checks, and 24 for later composition.
Leave the inventory allocation at 400 and the worker allocation at 3964 CPU
seconds. Reporting retains its measured unused balance; the restricted 400-second
termination margin is unchanged. No refund or implicit stage transfer is allowed.
The cumulative ceiling stays 39640 and continuation allocation stays 9840.

If the corrected admission passes, run the existing compile-only inventory once
under its separate 400-second reservation. If it passes, validate the explicit
composite acceptance record under the remaining setup reservation. Then freeze
and run the existing conditional device/profile/forecast/timing sequence under
3964 worker CPU seconds and the unchanged 790-GPU-second cap. The worker envelope
allows 991 wall seconds including finalization; its 989 work seconds leave 199
outside leases if all 790 GPU seconds are used. Existing 120-second tail and
resource-fit checks still apply and may refuse early.

Keep every completion criterion from the [accepted continuation proposal](lp-tensor-warp32-inventory-continuation.md)
unchanged, including all six acceptance jobs, all 76 study cells, independent
endpoint verification, useful integer/floating solves and the multiplicity-
adjusted certified latency gain. No retry follows a failed new attempt. No
bootstrap, supervisor or host/container change; no numerical or latency
relaxation, extra GPU allocation, GPUP-9, publication or merge.
