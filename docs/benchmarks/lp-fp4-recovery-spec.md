# FP4 recovery contract: GPUP-FP4-RECOVERY-SPEC

[SPEC-0029](../specifications/SPEC-0029-fp4-recovery-policy.md) and
[ADR-0061](../decisions/ADR-0061-fp4-operational-recovery.md) implement the CPU
recovery contract. The selected policy uses original-model residual observations
to guide bounded FP4 precision promotion and native recovery. It does not claim
a proved global trajectory enclosure or convergence guarantee.

The local arithmetic oracle separately charges pair rounding and representation
error, including cancellation and underflow. A scoped rational Lyapunov identity
confirms that the retained scalar signed recurrence contracts even while the old
absolute recurrence grows. This explains a weakness of that bound without
claiming a theorem for general projected LP trajectories.

The operational policy requires audits by 200 updates, submissions no longer
than 32 updates, complete rollback and 2 -> 4 -> 8 -> native escalation. All
failed work and deadlines remain outside rollback. Three stalled audits or
excessive residual growth trigger recovery; zero residual without certification
does not bypass this rule. Original-model checking at explicit 1e-7/1e-9 tiers
remains the only final certificate authority. The contract validates receipt
bindings but does not implement or run the future checker adapter.

The [policy](../../benchmarks/configs/lp-fp4-recovery-v1.json) includes 96 proposed
integration diagnostic cells, twelve safety cases, four sanitizers and an
itemized **51760 CPU / 5880 GPU-second proposal**. It is non-executable. Exact
model generators, source/device bindings and the concrete allocation belong to
GPUP-FP4-INTEGRATE. Nontrivial coupled trajectories, actual recovery costs and
complete certified solve performance remain unmeasured.

## Acceptance and accounting

All **30 new recovery tests** pass. The neighboring FP4 suite passes **107 tests**,
and the repository Python integration suite passes **624 tests**. Final review
corrected the terminal monitor to retain the actually certified checkpoint and
iteration; all 30 focused tests pass on that final source. The full-suite source
snapshot and the exact later delta remain preserved. Artifact/schema/provenance
checks and **214 documentation pages/internal links** pass. No Rust, kernel or
checker source changed; their earlier native/device acceptance is retained.

The [acceptance record](data/fp4-recovery-acceptance-v1.json) binds each test/log
and its source version. The [final evidence](data/fp4-recovery-evidence-v2.json)
binds the delivered contract and verifies **1539 historical files unchanged**,
plus exact prior dated handoff text. The four permitted edits to existing files
are current roadmap/backlog/handoff navigation. All supervisor cleanup receipts
are empty; no failed reservation occurred. The earlier
[evidence snapshot](data/fp4-recovery-evidence-v1.json) remains retained.

This delivery changes no
historical numerical implementation, original-model checker or public default.
The twelve old prototype cells remain refused; neither they nor old GPU studies
are rerun. Native control stays supported; FP4-PROTO and GPUP-8 stay incomplete,
and GPUP-9 remains gated.

The independent current ceiling is **16000 CPU / zero GPU seconds**, including
256 conservative preparation/packaging seconds. Four CPU slots, 6 GiB sampled
host RSS and the unchanged in-container supervisor apply. Every reservation,
including a failure if any, is charged separately from closed historical work.
GPUP-FP4-INTEGRATE is now next ready. Delivery is committed locally without push/publication.

[Final accounting](data/fp4-recovery-final-accounting-v1.json) closes the allocation
at **910.83174292 / 16000 CPU seconds and zero GPU seconds**, including all
six settled reservations and the preparation/packaging charge. Unused funds do
not release another task. The [source bridge](data/fp4-recovery-source-bridge-v1.json)
retains the exact earlier passing source versions.
