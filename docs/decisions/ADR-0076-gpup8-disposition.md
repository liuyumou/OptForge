# ADR-0076: Close GPUP-8 negatively and replace its progression gate

Status: accepted planning disposition under the user's 2026-11-15 request
Owner: numerical backend and experiment tooling
Introduced: GPUP-8-DISPOSITION
Last reviewed commit: bootstrap
Supersedes: GPUP-8 completion as a prerequisite for GPUP-9 in forward planning only
Implementation: state/backlog.yaml; no solver or public behavior change
Acceptance: [disposition evidence](../benchmarks/lp-gpup8-disposition.md)

## Decision

Close the exact-component GPUP-8 investigation as **closed_negative**. Its
historical scientific result remains **incomplete, with no certified latency
gain established**. This is administrative closure, not a pass or a proof that
Tensor arithmetic cannot help. Preserve ADR-0042 through ADR-0046, every failed
attempt, missing cell, certificate, source and closed allocation unchanged.
Do not fund another recovery of that frozen cohort.

Replace only the GPUP-8 dependency of GPUP-9 with the new
**GPUP-CERTIFIED-COST-GATE** below. GPUP-9 remains planned and blocked. The
GPUP-7, GPUP-STATE and GPUP-ASSESS dependencies remain; their recorded limitations
remain part of admission. Completing this disposition, CPU preparation work or
the conditional TENSOR2 task cannot by itself open GPUP-9.

The [evidence map](../benchmarks/lp-gpup8-disposition.md#requirements-and-evidence)
is the basis for this decision. MIXED2-CONFIRM2 passes five of eight scoped
prepared-session value comparisons, but none of the provisional 1.10 bounds.
CHECKER2's 1.1348–1.2832x gains compare implementations **within each lane** and
combine CPU source and compiler-target changes. Neither result satisfies the
old INT8/FP16/BF16 fresh-process requirement or establishes general FP4 superiority.

## Replacement progression gate

All six conditions MUST pass in a new, independently funded development study
before a separate GPUP-9 protocol and allocation can be accepted:

1. **Original authority and useful work.** Independently certify every claimed
   strict result on the original model at absolute/relative 1e-9, with explicit
   primal, dual, gap, status and refusal checks. A 1e-7 tier remains separate.
   Admit numerical bounds, rollback/promotion, malformed-input handling,
   cancellation, cleanup and every supported fallback. GPU candidates must
   demonstrate useful nonzero device work. Native promotion alone cannot be
   reported as low-precision success. Current CPU/native, device and four scoped
   sanitizer admission must bind the selected source, binary and image.
2. **Fair controls and attribution.** Compare the finalist with the current
   admitted native implementation at the same compiler target, tolerance,
   resources and lifecycle. Retain the unchanged tuned-FP64 reference to expose
   algorithm changes. Separate final-source and compiler-target effects on the
   complete endpoint before making portable or source-only claims. Include pinned
   HiGHS and available COPT/cuOpt references with conversion, export and checking
   costs; report algorithm/thread differences. Vendor native-return rows stay
   separate from strict certified rows. Do not pool historical timings.
3. **Complete cold cost and coverage.** Primary latency is fresh-process single
   solve through independent certification, durable output, EOF and destruction.
   Count setup, transfers, audits, rejected work, recovery and fallback. Prepared
   sessions are a separate endpoint. Every planned finalist cell must complete
   with a retained outcome; require certificates for every repetition in each
   claimed winning comparison and no loss of certified coverage versus native
   on the entire frozen guard roster. Missing cells or resource refusals block
   the gate. Expected numerical refusals remain outcomes, never fast successes.
4. **Prospective value and uncertainty.** Freeze workload rationale, family
   weighting, order, independent blocks, source identities and analysis before
   timing. Use at least ten independent blocks and a prospective sample-size
   justification; solves within a session are not independent samples. Require
   simultaneous 95% lower bounds above 1.0 for paired cold speedup and above a
   declared positive, workload-justified absolute savings floor on at least one
   preselected target family. Across every other predeclared guard family,
   require the simultaneous speedup lower bound above 1/1.05 (excluding more than
   5% slowdown); an inconclusive guard blocks progression. Multiplicity includes
   all targets, guards and savings endpoints. Report the provisional 1.10x
   comparison separately; it is not a universal adoption threshold. The concrete
   savings floor and block count must be accepted before the study, never chosen
   from its outcomes. A CPU-only gain supports that exact implementation; an FP4
   claim additionally needs a direct same-target FP4/native comparison.
5. **Operational and evidence closure.** Use a fresh finite allocation, full
   reservation accounting, four CPU slots, 16 GiB sampled RSS and, if applicable,
   12 GiB owned device buffers and one pinned shared lease. Retain the admitted
   one-second sampling/freshness/scan policy and all 100 ms advisories; sampled
   RSS is not a hard peak enclosure. All owned cleanup must be empty. Preserve
   failures and all planned cells, independently replay portable evidence and
   verify historical preservation. No automatic scientific retry or transfer
   from old allocations is allowed.
6. **Explicit release review.** Record each condition as passed, failed or
   unresolved in a source-bound report and a new release ADR. Resolve hosted CI
   startup availability and obtain a full hosted CPU gate pass for the release
   source; local acceptance is separate evidence. Then accept GPUP-9's own
   bounded component/interaction protocol, frozen finalists, unseen grouped
   holdout and independent budget under SPEC-0013. This gate grants no held-out
   access, public preset, default change or GPUP-10 adoption by itself.

This replacement explicitly removes the obligation to make INT8 plus FP16/BF16
win before broader precision research can progress. Native or mixed precision
may earn progression on certified complete cost. It does not lower the old gate
retroactively or designate the old task complete. A fully executed negative or
inconclusive study can close its own task, but cannot pass this replacement gate.

## Next bounded task

Select **GPUP-PREP3**, CPU-only final-source/compiler-target attribution and exact
preparation development, under the [prospective plan](../plans/lp-prep3.md).
Setup accounts for 40.5% and independent checking 34.8% of aggregate strict
coupled2048 FP4 session cost after CHECKER2. These identify work to measure;
they do not demonstrate another optimization. The existing six-block factorial
used an earlier tree checker and excludes full-session setup and teardown.

The proposed independent ceiling is **24000 CPU / zero GPU seconds**. No study
is launched or allocation opened by this disposition. The next implementation
request must accept the frozen numerical/resource protocol before execution.
A complete-session or larger GPU follow-up needs its own protocol, sample-size
case and budget; neither PREP3 nor unused historical headroom releases it.

## Alternatives and consequences

| Alternative | Disposition |
| --- | --- |
| Extend the old large-model profile deadline | Reject for this task: operational completion would not address the unfavorable small-profile cost, and the frozen cohort stays closed. |
| Resume exact INT8/FP16/BF16 recovery | Defer indefinitely: proof/device progress is real, but no complete-cost forecast supports another recovery now. |
| Mark GPUP-8 passed using CHECKER2 | Reject: its comparison, arithmetic families and prepared lifecycle differ from the historical requirement. |
| Open GPUP-9 from scoped MIXED2 wins | Reject: cold latency, stronger controls, attribution and operational release remain unmet. |
| Close negatively and require a new complete-cost gate | Select: preserves the failed investigation while allowing evidence-supported native or mixed progress. |

The current slice changes planning and evidence navigation only. Its independent
16000 CPU / zero GPU ceiling covers implementation/admin 1024 (512 preparation),
native acceptance 12000, reporting 2048 and cleanup 928 (128 closing).
Receipts: `artifacts/gpup8-disposition-v1`. Use the unchanged admitted supervisor;
failed reservations retain full charges and source snapshots. Commit locally.
