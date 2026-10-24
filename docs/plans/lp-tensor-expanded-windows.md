# GPUP-8 expanded state within audit windows

Accepted for implementation by the user, 2026-10-24. This replaces the previous
per-iteration FP64-commit proposal. [ADR-0046](../decisions/ADR-0046-expanded-audit-window-state.md)
defines the exact arithmetic, audit, recovery and evidence boundaries.

## Ordered implementation

1. Record authority, source bridge, retained evidence bindings and a separate
   journal. Test historical-charge inclusion, phase exhaustion, duplicate
   attempts, source/cache mismatches, stage isolation and report equivalence.
2. Implement the independent CPU prototype: expanded vectors survive updates;
   only the penultimate audit input and candidate endpoint become FP64. The
   final candidate/reference updates consume identical FP64-canonicalized input.
   Preserve FP64 adoption, checkpoint ownership, controller metadata and physical
   charging. Implement exact format/product/projection semantics and explicit
   conversion enclosures. No GPU reservation precedes complete CPU admission.
3. Independently test signed zeros, ties, subnormals, overflow, cancellation,
   exponent extremes, fast/fallback equality, residuals, transpose layouts and
   projections. Exercise lengths 1/2/8/31/32, 200-update clipping, conversion
   failure, reference buffer identity, cancellation, sticky promotion, replay,
   stale generations, cross-session checkpoints and malformed physical counts.
4. Implement isolated CUDA and serial host-cost changes. Compile once under the
   native gate; require intended MMA instructions, <=128 registers, zero spills
   and accounted scratch. Run new/affected-source acceptance, reusing unchanged
   historical passes. Evaluate eight models and useful required 400-update dense
   trajectories. Freeze all sources, images, requests, seeds, order and counters.
5. Run six new candidate device jobs once. Preserve product/controller scenario
   coverage and all twelve fixed-work/replay pairs; unchanged control pairs and
   ordinary tests reuse exact valid bindings. Verify each new endpoint once.
6. Run sixteen separate-cohort profiles with contemporaneous controls, never
   retrying historical profiles. Only passing gain and resource gates admit all
   sixty timing cells. No post-observation source/roster replacement.
7. Reuse verification receipts, reconcile every charge and ledger event, verify
   preservation, documentation/links/diff and empty cleanup. Failed stages close
   science and produce an incomplete report. No automatic transfer/retry.

## CPU allocation

| Stage | CPU seconds |
| --- | ---: |
| Authority/provenance/adapters | 400 |
| CPU prototype/window state machine | 2000 |
| Independent proofs/numerical validation | 5600 |
| Host-cost/CUDA implementation | 4000 |
| Native/inventory/CPU model admission | 4800 |
| Device acceptance/verification | 4000 |
| Profiles/verification/forecast | 3200 |
| Timing admission/execution/verification | 6400 |
| Reporting/docs/accounting | 800 |
| Restricted termination margin | 400 |
| Total | 31600 |

The 24000 addition plus 7600 unused seconds raises the ceiling to 77640. Maximum
cumulative consumption is 77502.541829170, leaving 137.458170830 unassigned. The
new journal carries prior CPU consumption 45902.541829170 by exact receipt,
including every historical failure charge. Four-times-wall stage charging gives
998/798/1598 work-wall seconds for acceptance/profiles/timings. Final report work
is bounded to 120 wall seconds within its 800-second allocation. No automatic
borrowing; each failed stage keeps its full reservation.

## GPU and study admission

Caps are acceptance 450, profiles 320, timings 990. Primitive acceptance reserves
84+6 seconds; project differentials/pairs 180+6; memcheck 30+6, racecheck 50+6,
initcheck 30+6 and synccheck 30+6. Total reservation 440; spare 10 authorizes no
extra job. GPUP-8 phase caps are repeatability 1070, ablations 520, screening 1410.
Task and campaign maxima remain 2992.909411024 / 3000 and 24352.495266813 /
25202.574545061. Use the existing ledger and fixed device identity.

Keep two models (dense_block-1024/65536), six configurations (INT8, FP16, BF16,
component SIMT, matched FP64, tuned FP64), four large-model norm/audit ablations,
order seed 17001 and oracle seed 17022. Profile deadlines are 6/18 seconds and
20 seconds for ablations, plus existing reservation overhead. Research profiles
reach 2000 updates; tuned controls keep certificate-stop behavior.

The original forecast requires all sixteen complete verified profiles, useful
integer/floating families and at least one of six candidate/model forecasts
passing. Use first-certificate prefix + fresh final assessment + maximum producer
tail across all sixteen. Thresholds stay 0.415902600 / 5.697919800 seconds.
The budget-only resource amendment changes timing allowance to 990 seconds;
retain estimator inputs, 1.25 multiplier, 120-second admission tail and comparison
against the active 6400-CPU-second timing reservation.

All sixty timing cells retain 5/16-second small/large deadlines and five
repetitions. Completion needs useful nontrivial integer/floating solves, complete
certification/coverage and paired total-latency gain after Bonferroni adjustment
across six comparisons, 95% family confidence, 10000 resamples, seed 17002.
Native-promoted, residual-only, initially host-certified, forecast or primitive
throughput results cannot substitute. Preserve 1e-7 local/1e-9 host criteria.

## Future work

Persistent expansion across audit windows has no CPU/GPU allocation and cannot
start automatically. Propose observation-only audits in a separate ADR, replacing
reference adoption explicitly. Expanded primal/dual state remains authoritative;
FP64 snapshots serve existing audit/controller/certification consumers. Store
full expansion/control/generation metadata in checkpoints. Restart anchors use
accepted controller FP64 snapshots encoded exactly; certify returned FP64 values.

Before implementation, supply cross-window error/recovery arguments covering
accumulation without resets, rounded snapshots, projections, anchors, rollback
and native conversion. Plan adversarial CPU validation of long trajectories,
tiny updates, active constraints, cancellation and exact expansion replay. Use
this attempt's new profiles to separate encoding/conversion/adoption costs from
preparation, assessment and arithmetic. A final certificate alone proves neither
the audit policy nor a speedup. Propose separate funding and a frozen study only
after numerical and cost feasibility; otherwise retain a feasibility refusal.
