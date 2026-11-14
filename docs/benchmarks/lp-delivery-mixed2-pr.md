# DELIVERY and MIXED2 integration acceptance

The user requests integrating all unmerged features through a pull request,
merging and safe cleanup. The branch contains eleven original commits after
`8fe3a20753f641b160e88b2f521d3ebe7c290297`, ending at
`2008aa91f7617dcc11479c94f08127191cd67972`. They cover DELIVERY2, the revised
delivery protocol, DELIVERY3 and its diagnosis, DELIVERY4, MIXED2 CPU admission,
the diagnostic GPU pilot, FP4 implementation, scenario reuse and both confirmation
continuations. The original commit ancestry and every scientific record remain.

## Scope and findings

This integration changes no numerical sources, original-model checker authority,
public solver defaults, historical performance decisions or closed allocations.
The final [MIXED2 confirmation](lp-mixed2-confirm2.md) completes 512 sessions and
16384 certified solves. Five of eight scoped comparisons pass, while none passes
the provisional 1.10x lower-bound criterion. Earlier incomplete cohorts and
negative results remain visible. GPUP-8 remains incomplete and GPUP-9 gated.

The current branch descends directly from remote main. The older GPUP-8,
GPUP-BASELINE and GPUP-RESIDENT2 branches are already merged. The unique
`codex/gpup-baseline-before-ci-manifest` branch is a historical pre-integration
snapshot and will be preserved. The obsolete adaptive-cost worktree has a merged
commit, no tracked or untracked edits, and only generated caches and dependency
symlinks. Cleanup follows verified remote merge and preserves scientific artifacts.

## Validation and resource boundary

The full native gate passes 638 Rust and 781 Python tests, committed-record
replay, dependency policy, documentation/link checks and smoke. All seven isolated
research packages pass 172 Rust and 50 Python tests; those Python tests are a
subset of the 781. The rational CPU oracle checks 1049 requests / 5121 outputs.
Total Rust coverage is 810 tests. The separate Git checkout runs 770 Python
cases with three missing-build skip entries (two class setup skips and one test).
After compiling all three prerequisite executables from source, all 12 affected
process cases pass; the combined clean runs cover all 781 cases. No original
project executable or study artifact is copied into that checkout.

Clean-checkout replay reproduces DELIVERY3 diagnosis, DELIVERY4 decisions,
MIXED2 complete-cost and pilot analysis, the FP4 study, scenario reuse and both
confirmation attempts. The final archive verifies 16384 responses and 9543
evidence files. It checks committed portable evidence without requiring the
original runtime artifact tree. Final historical preservation is recorded below. The clean checkout
shares immutable Git objects and the pinned HiGHS dependency installation;
it receives no historical study artifacts or project executables.

A separate CPU-only ceiling of 48000 seconds covers implementation 2000 (512
preparation), native 16000, research 8000, portability 8000, publishing 10000,
reporting 3000 and cleanup 1000 (all reserved for closing publication/merge/cleanup). Four CPUs, 16 GiB sampled RSS and
the unchanged admitted one-second supervisor apply; 100 ms observations remain.
Receipts live under `artifacts/gpup-delivery-pr-v1`. Failed reservations retain
full charges and sources. No GPU study or historical funding transfer occurs.

GitHub currently denies branch-protection/ruleset inspection with HTTP 403,
reporting that the private repository requires an upgraded plan. Prior Actions
runs report startup failure without running jobs. [PR #25](https://github.com/liuyumou/OptForge/pull/25) is mergeable through the
normal path. Its [initial hosted run](https://github.com/liuyumou/OptForge/actions/runs/43568950701)
reports startup failure with zero jobs at the original feature head. Final-head
status is recorded separately during publication; local acceptance is not a
hosted pass. Integration uses a normal
merge commit without changing or bypassing protection.

The first native launcher selected a virtual environment missing declared NumPy
and fastjsonschema dependencies. Its full 7200 CPU-second reservation and sources
are retained. The corrected launcher uses the existing pinned dependency
environment. Before rerunning, 6000 CPU seconds were moved prospectively from
unused research/publishing headroom to native acceptance within the unchanged
48000-second ceiling; historical allocations remain closed.

## Final local acceptance

All required local checks pass. Exactly 2153 historical tracked files remain
byte-exact; all four updated navigation/handoff files preserve their older text.
Public crates, CUDA sources, root dependency locks and hosted workflows match
remote main exactly. The eleven original feature commits retain their ancestry.

The independent allocation is closed at **15254.309796244 / 48000 CPU seconds**,
including the full 7200-second failed environment reservation and a conservative
1000-second closing-administration reserve. GPU usage is zero. All supervised
cleanup is empty. A prematurely queued review was cancelled before reservation;
its record is retained. No closed scientific allocation is reused.

[Acceptance](data/delivery-mixed2-pr-acceptance-v1.json),
[accounting](data/delivery-mixed2-pr-accounting-v1.json),
[historical preservation](data/delivery-mixed2-pr-history-v1.json), and
[portable integration receipts](data/delivery-mixed2-pr-evidence-v1.tar.gz).

[PR #25](https://github.com/liuyumou/OptForge/pull/25) receives this acceptance
commit before normal merge. The final hosted-check and cleanup receipts are
retained under `artifacts/gpup-delivery-pr-v1`; the PR reports hosted status
separately. Verified merged branches and disposable checkouts may be removed;
the unique archival branch and scientific artifacts remain preserved.
