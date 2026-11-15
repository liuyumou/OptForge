# GPUP-8 redesign: recognize certified FP4 research capability

Decision: [ADR-0077](../decisions/ADR-0077-gpup8-fp4-redesign.md).
Contract: [SPEC-0043](../specifications/SPEC-0043-gpup8-fp4-capability.md).
Date: 2026-11-15.

**GPUP-8 is complete for scoped FP4 prepared-session research capability.**
The user authorizes waiving an inappropriate historical progression gate.
The old exact-component investigation remains scientifically incomplete under
GPUP-8-LEGACY. No historical experiment is relabeled successful.

## Why the gate changes

The old gate asked a useful but narrow question about exact INT8/FP16/BF16 and
cold latency. Making those particular formats and that lifecycle mandatory for
all subsequent precision research ignored later certified FP4 session gains.
ADR-0076 preserved the distinction but added adoption and infrastructure demands
to research progression. The new decision removes those blanket prerequisites.

Correctness, original authority, useful work, fair comparisons, complete costs,
coverage and honest uncertainty remain mandatory. GPUP-9 is now dependency-ready
to define and fund its own study. PREP3 and hosted CI repair are separate work;
public adoption remains gated under GPUP-10. No new experiment is executed here.

## Retained evidence and exact scope

MIXED2-CONFIRM2 is the qualifying comparative evidence. Its **32 frozen blocks,
512 complete sessions and 16384 certified solves** cover every planned cell.
Both lanes use the same original models, compiler target, preparation/delivery
work and resource conditions. Native window32 and FP4x2 window16 are declared
whole-executor policies. Each fresh session cycles four constructed scenarios
eight times and resets FP64 state each solve; this is not warm-start evidence.
The endpoint includes setup, every solve/check, durable output, EOF and teardown.

The retained acceptance binds one executor binary and CUDA image for the two
lanes. It records exact trajectory matching, portable replay and original serial
verification of 17984 response files / 58448 assessments / 144 distinct
endpoint/tier pairs, including admission responses. Numerical/device/fault
admission and all 39 supervisor contracts remain part of that evidence; this
review does not rerun or silently extend their scope.

| Family | Tier | Paired speedup [simultaneous interval] | Saved ms [simultaneous interval] | Original decision |
| --- | --- | --- | --- | --- |
| dense-coupled-1024 | certified-1e-7 | 1.0506 [1.0432, 1.0585] | 246.163 [209.503, 280.377] | passes |
| dense-coupled-1024 | certified-1e-9 | 1.0651 [1.0574, 1.0706] | 374.508 [330.955, 405.901] | passes |
| dense-coupled-2048 | certified-1e-7 | 1.0367 [1.0325, 1.0412] | 559.042 [494.213, 624.595] | passes |
| dense-coupled-2048 | certified-1e-9 | 1.0489 [1.0402, 1.0541] | 874.323 [718.962, 966.019] | passes |
| dense-generic-1024 | certified-1e-7 | 1.0135 [1.0001, 1.0287] | 39.168 [0.396, 82.724] | not established |
| dense-generic-1024 | certified-1e-9 | 1.0214 [1.0082, 1.0410] | 61.130 [23.824, 115.704] | passes |
| dense-generic-2048 | certified-1e-7 | 1.0057 [0.9975, 1.0181] | 53.625 [-24.012, 173.083] | not established |
| dense-generic-2048 | certified-1e-9 | 1.0045 [0.9991, 1.0142] | 43.229 [-8.262, 132.889] | not established |

The table preserves all eight original family/tier decisions. The simultaneous
exact median intervals use Bonferroni protection across eight ratios and eight
savings endpoints. Scoped value requires ratio lower bound >1 and savings lower
bound >10 ms/session. Five comparisons pass, including three strict 1e-9 cases.
None passes the provisional 1.10 lower bound. Generic1024/1e-7 does not meet the
savings floor; both generic2048 intervals include parity. No result is censored.

Recognition of this already completed, predeclared study is an **evidence-informed
milestone decision**. The new capability definition was not preregistered before
that study. No new p-value, confirmation, favorable subgroup test or changed
threshold is claimed. Pair-order/first-16 sensitivity and shared-host/temporal
dependence remain as reported in the [original confirmation](lp-mixed2-confirm2.md).

| Evidence | Contribution | Limit |
| --- | --- | --- |
| MIXED2 FP4 numerical/device/recovery admission | Useful FP4 tensor increments, FP64 state/original-A references, conservative bounds, exact rollback/promotion and original-model checking | Admission is source/image specific; no recovery event in the final cohort does not prove general recovery. |
| MIXED2-CONFIRM2 | Direct, quality-matched native/FP4 comparison with five passing complete-session value comparisons and full coverage | Constructed development streams; no cold, portable, held-out or general FP4 dominance claim. |
| CHECKER2 | 512 complete sessions / 16384 certified solves; 16/16 scoped within-lane implementation gains, 1.1348–1.2832x; exact preparations and certificates | Combines source and compiler target. Not the qualifying FP4/native comparison; descriptive lane ratios cannot transfer the earlier inference to all final builds. |
| Original GPUP-8 | Corrected proof/device progress and useful small-profile observations | Nine profiles and all 60 final timing cells remain unexecuted; legacy working-family/gain gates stay false. |
| Hosted CI | Prior reviewed runs report startup_failure with zero jobs | Still unresolved; this redesign neither obtains a hosted pass nor diagnoses its root cause. |

## Current progression

The original gate is **waived for progression**, and ADR-0076's replacement
GPUP-CERTIFIED-COST-GATE is **superseded**, not passed. The redesigned GPUP-8
capability is accepted from the retained evidence. GPUP-9 keeps GPUP-7,
GPUP-STATE and GPUP-ASSESS predecessors and now depends on this GPUP-8 capability.
Their prior completion states and limitations remain unchanged.

Next: write GPUP-9's versioned component/interaction protocol and independent
allocation. Use direct same-target native/FP4 controls on the selected current
implementation; test changing-model prepared sessions and report cold solves
separately. Broaden workloads only with prospective resource and statistical
admission. Existing inspected models remain development data. Frozen finalists
and unseen grouped holdout remain a later part of that protocol. No legacy retry
or historical budget transfer is authorized.

PREP3's proposed 24000 CPU / zero GPU preparation/target experiment remains
optional and unopened. Source/target attribution is still needed for source-only
or portable gain claims. Cold evidence is still needed for cold gain claims,
external comparisons for competitiveness claims, and normal CI/release checks
for publication. None becomes an automatic pass from this redesign.

## Validation and accounting

The full local native gate passes **638 Rust / 785 Python tests**, format,
Clippy, dependency policy, artifact validation, committed-record replay,
**278 documentation pages** with links/anchors, and smoke. The Rust count is
637 workspace cases plus one buffered-transport case run by Python.

All **2248 historical files outside eight explicit planning edits**
remain byte-exact against `3b64b08ed21f39b8ef49f3429c991ca610e1bdb9`, including
ADR-0076 and the original studies. All earlier handoff text and **66 unrelated
backlog task blocks** remain exact. Original legacy and prior replacement-gate
acceptance strings remain preserved. The new dependency graph is acyclic, and
all four GPUP-9 predecessors are complete. No numerical source or default changes.

The review independently recomputes all eight retained comparison decisions
from their 32 block values, exact median intervals and original 16-endpoint
multiplicity correction. It reproduces five scoped passes, three strict passes
and zero provisional 1.10 passes. This checks the retained statistical evidence;
it is not another scientific cohort or fresh independent certificate replay.

The independent **8000 CPU / zero GPU** review allocation closes with empty
owned cleanup and no historical transfer. The unchanged one-second supervisor,
four slots, 16 GiB sampled RSS and all 100 ms advisories remain in force.
Sampled RSS is not a hard peak-memory enclosure. Actual charges, failed
reservations if any, source bindings and cleanup are in
[acceptance/accounting](data/gpup8-redesign-acceptance-v1.json).

[Evidence recognition](data/gpup8-redesign-verification-v1.json) and the
[source/log/resource archive](data/gpup8-redesign-evidence-v1.tar.gz) preserve
the verifier, historical file manifest, source snapshots, native/final receipts
and closed journal. GPUP-9's scientific allocation and PREP3's proposed allocation
remain unopened. This change is committed locally; no publication is performed.
