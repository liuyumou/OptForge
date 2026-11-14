# GPUP-DELIVERY3: Isolate delivery costs and confirm scoped gains

Status: next ready implementation task; execution allocation and manifest pending
Date: 2026-11-12
Decision: [ADR-0066](../decisions/ADR-0066-delivery-retention-scope.md)
Evidence: [DELIVERY2](../benchmarks/lp-delivery2.md)
Dependency: GPUP-DELIVERY2 complete at d453675

## Objective

Determine which delivery changes merit retention for cold and prepared solves.
DELIVERY2 shows a substantial dense cold benefit, but its two mechanisms are
coupled and prepared dense512 totals regress. Investigate that regression before
further precision optimization. Preserve original arithmetic, final 1e-7/1e-9
tiers, exact original inputs, independent fresh checking and complete evidence.

## 1. Isolate and diagnose

Create a separate research executor with independent switches:

| Variant | Checker pipe batching | Checker/device setup overlap |
| --- | --- | --- |
| Control | Off | Off |
| Batching only | On | Off |
| Overlap only | Off | On |
| Combined | On | On |

Use identical numerical modules, compiler settings and admitted device image.
Apply each variant equally to nativefast and gridfp4x2 at both final tiers.
First validate exact serialization, signed zeros, response bindings, refusal,
EOF, cancellation and cleanup, including setup failure after spawning a checker.
Reuse sanitizer admission only for the exact unchanged device image.

Use CPU transport measurements and a bounded device diagnostic pilot to separate
checker readiness, device preparation, request encoding/write, independent
assessment, response read/decode, solver work and durable output/teardown.
Record per-trial timestamps and overlapping intervals; never add marginal medians
or double-count overlapping setup. Measure complete totals independently of
diagnostic instrumentation. Do not label unexplained elapsed time as a cause.

The diagnostic pilot includes dense512, coupled-equality, fixed-active-bounds
and irregular-tail-33, all four variants and both lifecycles. Freeze its complete
roster, repetitions, limits and sources before launching. Diagnose contention,
allocation and scheduling effects only where measurements support them. Any
repair gets a new source version and CPU/lifecycle admission; failures remain.

Choose one candidate configuration per lifecycle using diagnosis, before
confirmation. Selection may retain the control for prepared solves. Routing
cannot depend on an observed solve time, lane-specific favorable outcome or
certificate result. Preserve all four diagnostic variants and their results.

## 2. Freeze a separate confirmation cohort

Use all twelve DELIVERY2 families, both lanes and both tiers, cold and prepared,
matched control and selected candidate. Dense-generic-128, -256 and -512 form the
predeclared target class; the other families remain guardrails. The intentional
refusal family remains in coverage and failure-cost reporting, outside certified
speed ratios. This is a constructed development workload, not a production mix.

Plan **32 independently restarted timing blocks**, each containing the complete
roster. Within each block, pair control and candidate closely and counterbalance
their order; randomize family/lane/tier order with a recorded seed. Freeze the
schedule before timing. Record shared-device activity and environment drift;
do not discard slow blocks after seeing their outcome. Independence across blocks
is an inference assumption, not something a fresh process alone proves. If
environmental dependence prevents that assumption, report inference as limited.

Every cold cell starts a fresh process and ends after process exit and durable
response/log delivery. Every prepared cell starts a fresh service session and
performs three freshly reset solves with fresh certificates. Its measurement is
the median complete solve time within that session; the session, not each solve,
is one replicate. Record first-solve and steady behavior, setup, total batch time
and teardown separately. No warm iterates or reused certificates.

This core grid contains 6144 lifecycle cells: 3072 cold solves and 3072 prepared
sessions containing 9216 solves. Fixed sample count means no favorable early
stopping, automatic extension, replacement of failed cells or historical retry.
The implementation package must fund the entire cohort plus admission,
diagnostics, reporting and cleanup before freezing it. If that package cannot
support this design, revise it explicitly before any confirmation timing.

## 3. Prospective retention decision

Evaluate each lane, tier and lifecycle separately. A cold-only route can qualify
even if prepared retention is inconclusive or fails; keep the prepared control
in that case. A combined route must pass both lifecycle guardrails. A prepared
speedup claim requires its own benefit gate. Public defaults remain a later
decision; these are research retention rules.

**Hard correctness and coverage:** all original-model certificates, endpoint
bits, signed zeros, audits, checkpoints, recovery and physical/logical work must
match the corresponding control, with retained-source replay where available.
All eleven bounded families must certify at their declared tier; intentional
refusals must remain refusals. Missing, failed or mismatched cells cannot be
silently excluded. Any such failure prevents retention of the affected route.

**Target benefit:** within each independent block, compute the equal-weight
geometric mean of control/candidate complete-time ratios over the three dense
families. The estimand is the median of these block geometric means. Its lower
simultaneous confidence bound must be at least **1.10x**. This preserves the 10%
benefit target but scopes it to the mechanism's declared workload. Report
absolute milliseconds saved as well. This estimand differs explicitly from
DELIVERY2's geometric mean of five-run model medians.

**Material-regression guard:** for every certified family, form the paired block
quantity `candidate_ms - control_ms - max(0.02 * control_ms, 0.10 ms)`.
The upper simultaneous confidence bound on its median must be at most zero.
The allowance is an engineering policy: 2% relative slowdown, with a 0.10 ms
floor so negligible absolute costs do not veto a route. It is not estimated
noise and does not relax certificate tolerances. At a 20 ms prepared solve it
allows 0.40 ms; DELIVERY2's observed dense512 increases of roughly 1–2 ms would
still require explanation or repair. Do not increase this margin after timing.

Use **95% simultaneous two-sided intervals** across all benefit and family-guard
metrics for all claimed lane/tier/lifecycle routes, declaring that metric list
before confirmation. Use distribution-free order-statistic intervals for each
median: for `n` independent block values and `M` declared metrics, choose the
largest positive `k` for which `P[Binomial(n, 0.5) <= k-1] <= 0.05/(2*M)`;
the interval is sorted values `[k, n-k+1]`, using one-based ranks. If no such
rank exists, the interval is unbounded and cannot qualify. Bonferroni adjustment
does not require independence between metrics; independence between replicate
blocks remains required. Ties are conservative. Validate the reducer and rank
arithmetic before freezing sources. Descriptive ratio-of-medians and bootstrap
plots may supplement, but cannot override, this declared decision.

Report **supported**, **material regression/insufficient benefit**, or
**inconclusive**. A confidence interval crossing a threshold is inconclusive;
an interval wholly on the unfavorable side demonstrates failure of that metric.
No observed tiny slowdown is automatically a material regression, and an
uncertain apparently favorable mean is not automatically a pass.

## Deliverables and resource admission

Deliver the isolated executor, exact differential/lifecycle admission, preserved
factorial diagnosis, frozen candidate/schedule/reducer, complete confirmation
evidence, per-route decision and final accounting. Run the full native gate for
implementation and the isolated package's relevant checks. Keep all historical
sources, scientific outcomes, failed reservations and closed budgets exact.

This plan allocates no execution CPU/GPU funds. Start implementation by declaring
its own phase ceilings and whole-job reservations under the unchanged in-container
supervisor, four CPU slots, at most 16 GiB sampled RSS and 12 GiB device buffers,
and one pinned shared GPU lease. GPU diagnostics require prior CPU/lifecycle
admission. No confirmation run starts until the admitted source image, complete
resource package and immutable manifest exist. GPUP-TENSOR2 remains conditional;
MIXED2 is an independent alternative, and GPUP-9 remains gated.
