# ADR-0077: Waive the legacy progression gate and recognize scoped FP4 capability

Status: accepted under the user's 2026-11-15 instruction to waive an inappropriate gate and redesign GPUP-8
Owner: numerical backend and experiment tooling
Introduced: GPUP-8 redesign
Last reviewed commit: bootstrap
Supersedes: ADR-0076's current milestone disposition and GPUP-9 prerequisite; ADR-0042–0046 as forward progression requirements only
Implementation: [SPEC-0043](../specifications/SPEC-0043-gpup8-fp4-capability.md) and state/backlog.yaml
Acceptance: [evidence recognition and validation](../benchmarks/lp-gpup8-redesign.md)

## Assessment of the old gate

The original gate was appropriate for its narrow question: whether a particular
exact-component INT8/FP16/BF16 implementation could reduce fresh-process certified
latency. Original-model checking, useful numerical work, matched controls, full
costs, coverage, uncertainty and preservation of failures remain appropriate.

It was inappropriate as a permanent prerequisite for all subsequent
low-precision research. Requiring multiple specified arithmetic families binds
progress to one implementation hypothesis. Restricting success to cold single
solves excludes useful repeated-model sessions even when setup, independent
checking and teardown are fully counted. An incomplete old experiment cannot
invalidate later evidence for a different, admitted FP4 method.

ADR-0076 correctly preserved history and distinguished within-lane CPU gains
from FP4/native gains. Its replacement gate nevertheless required too much for
research progression: a new cold-gain study, broad regression bounds, external
comparisons, final source/target attribution and hosted CI completion before
GPUP-9. Those requirements answer adoption, portability, infrastructure or
broader competitiveness questions; they need not all precede controlled research.

## Waiver and replacement

The user-authorized waiver takes effect now:

| Previous progression requirement | Current disposition |
| --- | --- |
| Useful INT8 plus FP16/BF16 must qualify | Waived. One admitted low-precision method with useful work and certified value is sufficient for scoped research capability; FP4 qualifies. |
| Cold single-solve gain is the sole qualifying endpoint | Waived. A declared cold or complete prepared-session endpoint may qualify, with its scope retained and every lifecycle cost counted. |
| Recover the unexecuted legacy cohort to continue | Waived. The legacy attempt stays retired and scientifically incomplete; no missing cell is filled or relabeled. |
| ADR-0076's six-condition GPUP-CERTIFIED-COST-GATE | Superseded as a GPUP-9 prerequisite. It is not marked passed. Relevant validation remains attached to the claims and future execution that require it. |
| Another study must reconfirm already frozen, completed results before recognizing capability | Waived for this recognition. Use the existing independent confirmation's unchanged decisions and source-bound acceptance. Changes to an executor still need applicable admission before execution. |
| A universal 1.10x speedup threshold | Not imposed for research capability. It was provisional in MIXED2, not the original ADR-0042 completion threshold. Keep every historical 1.10 result unchanged. |
| PREP3, external solver superiority, full target factorial and hosted CI must all precede GPUP-9 research | Removed as blanket prerequisites. PREP3 is optional optimization; those other checks support their respective future claims and publication. |

Retain independent original-model certification, same-tier controls, useful
nonzero low-precision execution, declared numerical bounds and recovery,
source-bound admission, complete costs, coverage, uncertainty, resource limits
and exact preservation. No mathematical correctness rule is waived.

## Redesigned GPUP-8

GPUP-8 now means **demonstrate useful certified low-precision research capability
on an explicitly scoped workload**, under SPEC-0043. Its status is **complete
for scoped FP4 prepared-session capability**. This is evidence-informed milestone
recognition, not a new prospective confirmation or an old GPUP-8 pass.

The sufficient comparative evidence is MIXED2-CONFIRM2: 32 frozen blocks,
512 complete sessions, 16384 certified solves, and five of eight predeclared
value comparisons passing with simultaneous intervals. Three passing comparisons
are at strict 1e-9: coupled1024, coupled2048 and generic1024. All four coupled
comparisons pass. All eight decisions, the three unestablished comparisons,
the zero provisional 1.10 passes and order sensitivities remain unchanged.

Recognition binds the frozen MIXED2 executor/configurations and admitted host
conditions. It is a whole-executor native-window32 versus FP4x2-window16 result,
not an isolated arithmetic-only effect. CHECKER2 adds exact implementation and
preparation evidence, with 16/16 within-lane gains, but cannot serve as the
FP4/native comparison or transfer the MIXED2 inference to every later build.
Its final source/target attribution gap remains explicit for broader claims.

Keep the old task under **GPUP-8-LEGACY**, with administrative status
`retired_incomplete`, its original acceptance text, charges and artifacts.
ADR-0076 and its report remain immutable historical decisions, including the
earlier `closed_negative` label. The current milestone no longer carries that
label. No historical statistical test or performance outcome is regraded.

## Progression and adoption

**GPUP-9 is dependency-ready**, with GPUP-8's research prerequisite satisfied.
Its next action is to specify its own controlled component/interaction study,
freeze a justified workload and analysis, and allocate resources before launch.
No GPU campaign, held-out access or funding is opened by this redesign.
There is no additional predecessor requiring FP4 to win on cold latency first.

The first GPUP-9 protocol should use same-target native/FP4 controls on the
current selected implementation, declare changing-model prepared sessions as a
target endpoint, and measure cold single solves separately. It should test
whether the established scoped gains survive shared preparation improvements,
include generic and coupled cases and useful cold/small negative controls, and
choose larger problems only after resource admission. Freeze block count,
value floor, multiplicity and independent budget before timing. Retain every
failure and inconclusive cell. Existing constructed streams remain development
data; they cannot be relabeled an unseen holdout.

If that protocol selects a prepared primary endpoint, it must explicitly amend
SPEC-0013's cold-primary/secondary-throughput rules for the new study. Designing
that amendment is part of the now-ready GPUP-9 task; a cold win is not required
before it can do so. Earlier cold experiments and their interpretations stay exact.

PREP3 remains ready as an optional bounded preparation/target study. Its proposed
24000 CPU / zero GPU allocation is unopened and is not a GPUP-9 dependency.
CI-STARTUP stays a separate infrastructure issue. An unavailable hosted runner
does not negate numerical evidence or prevent locally admitted research; normal
hosted checks/protection still govern publication. No bypass is authorized.

GPUP-10 public adoption remains separate. It needs evidence for the actual
deployment workload, target and quality tier; appropriate held-out assessment,
coverage/regression policy, supported-host dispatch/fallback, complete costs,
and normal release validation. Cold gains, external competitiveness and portable
source-only gains require their own matched evidence when claimed. No preset,
default or production-readiness claim follows from this research milestone.

## Resources and delivery

This decision/review uses a new independent **8000 CPU / zero GPU** ceiling:
implementation/admin 1024 (512 preparation), native acceptance 5000, reporting
1408 and cleanup 568 (128 closing). Four CPU slots, 16 GiB sampled RSS, the
unchanged one-second supervisor and all 100 ms advisories apply. Sampled memory
is not a hard peak enclosure. Retain full failed reservations and sources.
Receipts: `artifacts/gpup8-redesign-v1`. Older allocations remain closed.

Run the full local native gate, verify historical byte preservation, recompute
the existing comparison decisions from retained statistics, and check the new
dependency graph and documentation. No numerical study is rerun. Commit locally.
