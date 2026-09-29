# ADR-0028: Immutable Model Reuse Within Fresh LP Solves

Status: accepted by the maintainer on 2026-09-29 before implementation.
Scope: GPUP-HOST under SPEC-0016 and SPEC-0013; gpup-host-v1.

## Decision

Implement the user-approved model-only boundary: an opaque LpInput owns a validated
Model and borrows the exact input bytes, provides read-only model access, and is
consumed for endpoint construction. Keep LpEndpoint::new compatible. Sparse LP
construction, candidate evaluation, original-model dual certification and gap
assessment remain fresh; standalone verification reconstructs independently.
No backend, numerical, kernel, schema/default, session or adaptive preparation change.

## Frozen comparison

Archive baseline revision 1818cdb5405fe466728c9cfb1719c67e22f660a5 and the repaired
source/binary separately. Twenty-four fresh timings compare these executables on
small-4, irregular-32768, irregular-65536 and dense_block-65536, three repetitions.
Both use compact-v1 evidence, tuned FP64 resident/necessary/warp32_v1/separate,
the unchanged GPUP-EVIDENCE method, solver seed 17, one thread and CPU affinity [0],
all tolerances 1e-9, 50000 updates, a 30-second solve deadline, two-second cleanup,
8 GiB host/device bounds and 32 MiB per-file output cap. Model/evidence reads allow
128 MiB and independent CPU verification is bounded at 120 seconds. Device UUID
is GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48. Order seed is 18001; paired median ratios
use 10000 bootstrap resamples with seed 18002 and 95% intervals.
Four separate profiles compare both executables on irregular-32768 and
dense_block-65536. Profile invocation counts establish reconstruction removal;
exclusive scope times avoid double-counting. Profiles are not primary timings.

Acceptance uses regular device tests plus 200-update old/new comparisons for tuned
FP64, fixed FP32 accumulation and gradual adaptive recovery on small-4 and
irregular-2048, and compact replay. Compare binary64 numerical/work state, excluding
clocks and memory observations, and independently verify with both executables.
Retain all unsuccessful/partial attempts and incomplete pairs; do not retry identities.
Archive source, binary, schema snapshot and all four code images before admission.
Existing sanitizer receipts retain their original scope and historical gaps.

## Authority and resources

Initial charge 15071710156489 ns; 15392 events; prefix SHA-256
6a30c1954ff9bc80c733364d8e8a7c0fc4c4439d70b959d2c10996d71993e518.
Preserve the 18002574545061 ns cumulative ceiling, original 28800-second campaign,
all phase caps and original output binding. Additional allowance is zero.
Timing: 900 seconds in ablations; profiles: 200 seconds in repeatability;
acceptance: 300 seconds in repeatability; combined 1400 seconds. No borrowing.
Each study attempt reserves 36 seconds (30 + 2 + 4), totaling 864 for timings and
144 for profiles. Admission reserves full bounds and uncertain work is fully charged.
All GPU jobs use the shared host lease. Four build jobs and four CPU-hours cover
build, validation and analysis with measured receipts; CPU verifier costs are separate
from GPU lease costs. No new external solver, held-out evaluation or GPU allowance.

## Acceptance and handoff

Full pinned-native tools/check.sh and exact-rational tests precede GPU admission.
Constructor/CLI/schema/provenance and clean-checkout synthetic-ledger tests must pass.
Both executables independently verify complete endpoints. Report certified coverage,
complete fresh-process latency, reconstruction/assessment counts and memory without
imputing failed pairs or requiring a speedup. Preserve old evidence and limitations.
Record acceptance and consumption, commit locally and advance next_ready_task to
GPUP-ADAPTIVE-COST without beginning it. No push or external publication.
