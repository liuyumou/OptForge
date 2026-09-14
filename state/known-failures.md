# Known Failures and Limitations

## LP certification can lose the roundoff allowance at zero reduced cost

Resolved by GPUP-1 on 2026-09-14. Discovered during the GPU LP precision design
review and preserved by GPUP-0, this affected the shared host certification used
by both host-lp and cuda-lp, independently of future quantization. The original
counterexample below is retained for reproduction against the previous revision.

The previous variable loop in `crates/optimizer-lp/src/certify.rs` used bound zero
when a computed reduced cost rounded to zero, then multiplied the reduced-cost
error allowance by that chosen bound. The reduced cost can be nonzero in exact arithmetic
over the stored binary64 coefficients, so the required allowance is lost.

Reproducer (continuous variables, equality constraint):

```text
minimize 0.1*x1 + 0.30000000000000004*x2
subject to x1 + 3*x2 = 0
-3e16 <= x1 <= 3e16
-1e16 <= x2 <= 1e16
dual multiplier y = [0.1]
feasible candidate x = [3e16, -1e16]
```

The pre-repair built-library diagnostic returned bound 0 with allowance 0. The
candidate passes the existing feasibility check; ordinary FP64 objective evaluation
reports -0.5. Exact rational evaluation of the *stored binary64* coefficients at
that candidate is `-152587890625/549755813888`, approximately
-0.27755575615628914. Thus zero is an invalid lower bound even for a finite boxed
model; the ordinary objective's -0.5 also illustrates why objective/gap arithmetic
needs review. These values are a correctness counterexample, not timing evidence.

Resolution: [GPUP-1](../docs/plans/gpu-lp-precision-roadmap.md#implementation-slices)
replaces the scalar allowance estimate with finite outward enclosures for every
product, reduction, reduced cost, bound contribution, and final sum. Uncertain
signs use both variable-bound sides; an unusable infinite side yields no finite
certificate. Exact zero remains usable even for a free variable. Both backends
share an outward objective/gap check with the correct maximization direction and
finite conservative tolerance arithmetic. The reported objective and the existing
feasibility tolerance policy are unchanged.

Evidence is in [active task](active-task.md). The original cancellation and free
variable cases failed before the repair. Independent rational fixtures, the full
native CPU gate, all regular device suites, all full memcheck suites, and scoped
checks under all four sanitizers cover the repair. The broad sanitizer invocation
was stopped during the long existing racecheck case; it is not recorded as a full
sanitizer-gate pass. No GPU kernel or experimental precision mode changed.

Remaining limit: outward enclosures can be wider than necessary because they lose
correlations. A finite boxed model may refuse certification after intermediate
overflow, and uncertainty can prevent certification on an infinite side even when
the exact reduced cost is zero. This is a conservative refusal, not a proof that
the LP is unbounded. Feasibility and the objective field remain tolerance-based
binary64 computations, not exact-rational primal certificates. See
[the numerical argument](../docs/architecture/lp-certification.md).

## GPU LP precision experiments and recipes are not implemented

The user approved the [GPUP roadmap](../docs/plans/gpu-lp-precision-roadmap.md),
with single-solve latency as the primary objective and an eight GPU-hour first
campaign. GPUP-0 records the roadmap and drafts; GPUP-1 repairs the existing
certification and gap calculations. There is no
`cuda-lp-quantized` backend, precision-settings schema, study harness, frozen LP
study partition, measured winning recipe, or supported new preset yet. Draft
SPEC-0012/SPEC-0013 must be completed and accepted before their behavior is added.
The generic C10 comparative runner remains unspecified and is not implemented by
this LP-only study. Existing Taillard timing/structure observations are development
diagnostics and cannot be relabeled held-out validation.

Next: follow the dependency chain in [the backlog](backlog.yaml). Record each
slice's gates and resource use separately. Certification repair is complete;
establish measurement before performance claims and preserve unsuccessful trials and
negative results. The approved direction permits evaluating formats/scales/rounding;
it does not preselect FP8 or Tensor Cores as the final recipe. Repeated-solve
throughput and full MILP search performance need separate specifications and budgets.

No known implementation failure has been accepted as a waived gate.

## Source planning references

The preserved ai-native-optimizer-plan.md references optimizer-survey.md and
llm-or-survey.md from another session; neither is present. Reproduction:
inspect its Background links. Next diagnostic step: recover those source surveys
if research work needs them. The maintained documentation book excludes the two
original planning inputs from recursive link validation.

## External configuration

The origin remote is https://github.com/liuyumou/OptForge.git. Protected main,
labeled GPU runner provisioning, and artifact retention still require hosting
administration. Next step: configure these settings separately from Git syncing.

Publication state, because several earlier records state the opposite and were
true when written: the work through `dfdc245` — every milestone up to and
including C8 — has been pushed to origin by the maintainer. Records dated before
that push describe main as unpushed pending authorization; that was accurate at
the time and is left as written rather than backdated. Anything after `dfdc245`
is local until the maintainer pushes it, and AGENTS.md's prohibition on
publishing without authorization is unchanged.

## No dispatch threshold is committed, for either specification

SPEC-0010 requirement 22 and SPEC-0011 requirements 18 and 19 ask the same thing of
two different decisions, and neither is answered by a committed number.

The crossover is recorded below and no default reads it. Dispatch is the caller's
explicit `device` field, or for a backend the explicit `--backend` flag: there is no
threshold anywhere that compares a model against a measurement and chooses. "CPU
remains the default below the measured crossover" therefore holds because CPU is the
default everywhere, not because anything measured.

For SPEC-0011 the position is the same and the mechanism is even simpler: there is no
threshold document, no `Default` for one, and no code path that could promote a solve
to another backend. The pinned CPU backend is what runs when nothing is named.

That is deliberate rather than outstanding work. A dispatch threshold is an
acceptance-shaped number -- it decides what runs where, on evidence from one host --
and the benchmark protocol requires an ADR and an experiment record before a
threshold like that is committed. Recording the measurement and leaving the choice
to the caller is the honest intermediate state.

Reproduction: `grep -rn "crossover" crates/` finds only comments, and
`optimizer solve` with no `--backend` reaches `highs`, asserted positively by
`the_default_configuration_reaches_the_pinned_backend`. Next step: an ADR proposing
a threshold, with the held-out evidence Stage 4 asks for rather than the single-host
diagnostic recorded here. One ADR can cover both decisions or they can be split;
what neither may do is commit a number without that evidence.

## A fallback cannot be verified field for field

SPEC-0011 requirement 20 requires an availability failure to fall back to the CPU
backend and produce "the same conclusion". That is satisfiable for the conclusion and
is not satisfiable for the record. A fallback writes a record naming `highs` where the
caller asked for `cuda-lp`, so `backend`, `backend_version` and `lp_settings` all
differ, and `optimizer verify` compares those fields.

So a run that fell back is reproducible only in the sense that re-running it reaches
the same answer, not in the sense that its record matches one from a run that did not
fall back. `an_availability_failure_falls_back_to_the_pinned_backend` asserts the
conclusion and asserts explicitly that the two records name different backends, rather
than asserting an agreement that does not hold.

The related entry above -- verification assuming an unchanged native library -- is the
same shape of limit arriving from a different direction.

Reproduction: point `CudaLpBackend::open_with_code_object` at an absent code object and
compare the record it writes with the pinned backend's. Next step: none proposed. A
record that recorded "asked for A, ran on B" would make the divergence describable, but
that is a SPEC-0005 change and needs its own contract.

## A device that cannot be opened is refused, not fallen back from

The two rules meet here and the boundary between them is a choice this implementation
made rather than one either specification states outright. A device that cannot be
*opened* -- absent, hidden by `CUDA_VISIBLE_DEVICES`, or not leased -- is a refusal,
because SPEC-0010 requirement 3 forbids a record claiming a device the run did not use
and the C6 device work already established that a GPU-naming configuration is refused
rather than silently run on the CPU. A device that opens and then cannot do the work --
no code object, not enough memory -- is an availability failure and falls back under
requirement 20.

Both are defensible and they are not the same rule. A caller who mistypes a UUID gets
an error; a caller on a correctly named device with an unprovisioned code object gets a
CPU answer and a diagnostic. That difference is worth knowing before relying on either.

Reproduction: `optimizer solve --backend cuda-lp --device GPU-does-not-exist` versus
the same command with `AI_OPTIMIZER_CUDA_DIR` pointed at an empty directory. Next step:
none proposed; if the distinction proves confusing in use it belongs in SPEC-0011's
Errors and Recovery section rather than in code.

## Tolerances are reused as an optimality-gap policy

SPEC-0011 requirement 14 closes `Optimal` when a certified bound and a validated
candidate agree "within the caller's tolerances", and the only tolerances a caller
supplies are `absolute`, `relative` and `integrality` on the solve configuration. Those
are documented as a *feasibility* policy: they decide whether a candidate satisfies the
model. Using them as a duality-gap policy overloads them.

The practical consequence is that a caller who wants a strict feasibility check and a
loose optimality gap, or the reverse, cannot express it. Nothing is wrong today because
both uses want small numbers, and a gap field cannot be added without changing
`solve-config-v1`, which SPEC-0011 deliberately leaves at version 1.

Reproduction: read `assess` in `crates/optimizer-lp/src/backend.rs` against
`Tolerances`'s documentation in `crates/optimizer-core/src/evaluate.rs`. Next step: a
gap tolerance on the solve configuration, which is a schema change with the cascade
into `search-config-v3` that SPEC-0011's Compatibility section avoided.

## CPU/GPU bitwise identity is this project's property, not the contract's

SPEC-0011 requirement 8 asks only that a result be bitwise reproducible on a fixed
device and code object. The device suite asserts something stronger: that the device's
iterates equal the host engine's bit for bit. That is deliberate -- a tolerance on an
iterative method is nearly untestable, since one loose enough to pass at iteration ten
thousand hides a real defect at iteration ten -- but it is not contractual.

It holds because `-fmad=false` removes the device's only contraction, because Rust
never contracts, and because `log`, `exp` and `sqrt` are computed host-side and passed
in as scalars. A toolchain that broke any of those would break the assertion without
breaking the specification.

Reproduction: rebuild `lp_pdhg.cubin` without `-fmad=false` and run
`the_device_iterates_match_the_host_engine_bitwise`. Next step, if it ever breaks:
record which operation diverged and narrow the assertion to that operation, rather than
widening everything to a tolerance and losing the instrument.

## The LP device suite does not run in CI either

The entry above about device acceptance applies unchanged to the three device suites,
not two. `tools/gpu_check.sh` now runs `optimizer-cuda`, `optimizer-schedule-examples`
and `optimizer-lp-cuda`, and sanitizes all three under each of the four tools, but the
labeled GPU runner is still unprovisioned. Every result recorded for SPEC-0011's device
half is a local run on one host.

Reproduction: `.github/` contains no device job. Next step: unchanged -- provision a
labeled runner, or keep recording device evidence as local.

## A weak certified bound will have two causes

SPEC-0011's open question is whether a certified bound is ever strong enough to prune
usefully. On this project's own models that question cannot be answered cleanly yet,
because the flow-shop encoding's linear relaxation is already weak before any method
touches it -- which the entry on that encoding records.

So a weak bound on an encoded scheduling instance has two candidate explanations, the
relaxation and the certification, and attributing it to either without an instance
family whose relaxation is known to be tight would be wrong.

Reproduction: none needed; it follows from the two contracts. Next step: if the
question is pursued, measure on instances whose relaxation quality is known
independently, not on the frozen scheduling subset.

## Rebuilding a poisoned context is not implemented

Requirement 29 permits two responses to a sticky fault: destroy and rebuild the
context, or fall back for the remainder of the run. This implementation takes the
second. A residency that observes a sticky driver status marks itself poisoned and
refuses every later call without touching the device, and the device producer's
sweeps go to the host from then on.

The consequence is that one sticky fault costs a run its device even if the fault
was transient. Rebuilding would need the residency to replace a context its buffers
hold through an `Rc`, which is a lifetime problem rather than a driver one, and the
specification does not require it. Reproduction: there is no test that faults a real
device, because provoking a genuine sticky fault means corrupting one, so the
poisoning path is covered by unit tests over `DriverStatus::is_sticky` and
`DeviceError::poisons_context` rather than end to end. That gap is the honest one to
record: the decision logic is tested, the recovery from a real fault is not.

## Resolved: device sanitizer coverage runs and is clean

`bash tools/gpu_check.sh`, run under `tools/gpu_job.sh`, executes the device suite
and then all four `compute-sanitizer` tools over it. On 2026-09-13 on an RTX 5090:
memcheck 0 errors, racecheck 0 hazards, initcheck 0 errors, synccheck 0 errors.

This mattered more than a formality. The kernels are hand-written and index shared
memory from computed offsets, and the neighborhood kernel has two threads writing
disjoint halves of one dynamically sized array while 254 others wait on a barrier --
which is precisely the shape racecheck exists to find and precisely the shape a
reviewer cannot check by reading.

The script refuses to run without an inherited lease rather than taking one itself,
so it cannot be invoked outside the wrapper that names a single device. It is
deliberately not part of `tools/check.sh`: that gate is CPU-only and must stay so,
because almost every task record in this project states a "CPU only, no GPU
workloads" budget that a kernel-running gate would make false.

What is still uncovered: the C1 native-library sanitizer gap below is unrelated and
unchanged, and none of this has run in CI, because the labeled runner is not
provisioned. A local run is recorded as a local run.

## Device acceptance does not run in CI

The device suite is opt-in behind `AI_OPTIMIZER_GPU=1` so the ordinary gate stays
CPU-only and no task record's "CPU only, no GPU workloads" budget is made false by
it. The consequence is that device evidence exists only where someone ran it by
hand: the labeled GPU runner is still not provisioned, so no device test has ever
run in CI. Evidence recorded from a local run is recorded as such and must not be
read as a CI pass.

## Deferred hardware evidence

HiGHS differential tests are implemented and passing under C1; see
[active task](active-task.md). No solver performance or hardware claim is made, and
the crossover recorded below is a development diagnostic on one host rather than a
benchmark result.

## The device loses below roughly fifty jobs, and context creation dominates

The first crossover measurement, recorded here because both of its findings are
inconvenient and would be easy to leave out.

Measured on one RTX 5090, compute capability 12.0, 170 multiprocessors, release
build, best of three after a warmup, over the ADR-0011 scale split. The workload is
one full insertion neighborhood: for every job, the cost and position of its best
reinsertion. The CPU column is the tuned `insertion_neighborhood`; "resident" is the
device with the instance already uploaded and the context already created; "with
setup" is end to end from nothing, which is what the benchmark protocol requires be
reported and which no kernel-only number may replace.

| instance | shape | cpu tuned | device resident | device with setup | ratio |
| --- | --- | --- | --- | --- | --- |
| ta001 | 20x5 | 0.010 ms | 0.041 ms | 151.6 ms | 0.25x |
| ta011 | 20x10 | 0.019 ms | 0.043 ms | 151.7 ms | 0.45x |
| ta021 | 20x20 | 0.037 ms | 0.054 ms | 148.4 ms | 0.69x |
| ta031 | 50x5 | 0.063 ms | 0.054 ms | 143.9 ms | 1.17x |
| ta041 | 50x10 | 0.122 ms | 0.074 ms | 163.4 ms | 1.64x |
| ta051 | 50x20 | 0.230 ms | 0.087 ms | 162.3 ms | 2.63x |
| ta061 | 100x5 | 0.250 ms | 0.079 ms | 148.2 ms | 3.19x |
| ta071 | 100x10 | 0.478 ms | 0.095 ms | 147.1 ms | 5.03x |
| ta081 | 100x20 | 0.916 ms | 0.134 ms | 149.9 ms | 6.85x |
| ta091 | 200x10 | 1.898 ms | 0.159 ms | 146.8 ms | 11.97x |
| ta101 | 200x20 | 3.749 ms | 0.232 ms | 147.0 ms | 16.15x |
| ta111 | 500x20 | 23.868 ms | 2.507 ms | 148.7 ms | 9.52x |

The device loses at twenty jobs, by a factor of four. That row is the reason the
measurement is believable: SPEC-0010's acceptance list states it as the expected
outcome, and a report winning everywhere would have been evidence that transfers
were excluded. The crossover sits at roughly fifty jobs on this hardware, and
requirement 22 makes the CPU the default below it.

Context creation costs about 148 milliseconds and dwarfs every other number in the
table, including the largest CPU time. A device is therefore worth reaching only
when the context is amortized across many calls, which is requirement 16's residency
rule arriving as a measurement rather than as a design preference. Nothing in the
project currently amortizes it, because nothing dispatches to a device outside a
test.

The ratio peaks at 200 jobs and then falls, from 16.15x to 9.52x. That is not noise
and the cause is known: the head and tail tables are 80,000 bytes at 500 jobs by 20
machines, so only one block is resident per multiprocessor, and the per-block
recurrence is built by two threads while the other 254 wait. The kernel comment says
so and names the fix -- a max-plus scan across machines per step -- which is
deliberately not done, because correctness came first and an unmeasured optimization
would have had nothing to be measured against. The falling tail is what makes the
table worth keeping: a sweep that stopped at 200 jobs would have reported a
monotonic trend that does not hold.

These numbers are a development diagnostic on one host. They are not a benchmark
result, not evidence, and not a claim about the engine, and SPEC-0010 requirement 36
forbids reading the crossover as evidence that device execution improves a search.

## A device fault is outside every containment claim this project makes

The C3 extension host contains panics. A device fault is not a panic: an illegal
memory access in a kernel poisons the context, and a driver-level fault can end the
process. ADR-0009 records this as a cost of the boundary rather than solving it, and
SPEC-0010's security section states it rather than implying containment. A
device-backed extension therefore cannot be contained the way a CPU extension is, and
no per-device memory budget is enforced. Next step: the same process-isolated workers
the panic-only entry below already names, which would cover both cases and needs its
own decision record.

## Resolved: the flow-shop heuristics are a tuned baseline

`neh` and `insertion` evaluated each candidate insertion position by cloning the
sequence and re-running the whole recurrence, which is `Theta(n^3 m)` where
Taillard's exact head and tail acceleration is `Theta(n^2 m)`. That was the right
choice for C5, which claims correctness and forbids a performance claim, and it
became a problem only because Stage 4's entry condition requires baselines be tuned
before any intervention is measured: a device speedup over the naive pass would have
measured the pass.

The acceleration is implemented in
[the recurrence module](../crates/optimizer-schedule/src/evaluate.rs) rather than in
the heuristics, so requirement 8's rule that nothing proposing a schedule owns a
second definition of its cost still holds. The returned permutations are unchanged
and that is asserted by `accelerated_scoring_returns_the_naive_permutations`, which
compares against the pre-change algorithm scored by the independent oracle and
requires the same sequence rather than the same makespan. The weaker assertion would
have passed a real break: requirement 17 fixes which of several tied permutations a
caller receives, and two different permutations can tie.

The test was confirmed able to fail. Relaxing the insertion tie-break from strictly
less to less-or-equal — the exact mistake the acceleration invites, because the
rewrite moves that comparison — fails it, while
`construction_is_deterministic_including_under_ties` still passes, since a
deterministic wrong answer is still deterministic.

Measured on the development host, release build, best of three after a warmup, over
the whole ADR-0011 scale split, with a 0.19% noise floor from an identical binary:

| instance | shape | construction | improvement pass |
| --- | --- | --- | --- |
| ta001 | 20x5 | 0.18 ms to 0.03 ms | 0.16 ms to 0.04 ms |
| ta011 | 20x10 | 0.07 ms to 0.01 ms | 0.16 ms to 0.02 ms |
| ta021 | 20x20 | 0.12 ms to 0.02 ms | 0.31 ms to 0.04 ms |
| ta031 | 50x5 | 0.33 ms to 0.04 ms | 0.84 ms to 0.06 ms |
| ta041 | 50x10 | 0.64 ms to 0.07 ms | 1.70 ms to 0.12 ms |
| ta051 | 50x20 | 1.52 ms to 0.13 ms | 4.23 ms to 0.23 ms |
| ta061 | 100x5 | 2.29 ms to 0.13 ms | 6.26 ms to 0.25 ms |
| ta071 | 100x10 | 4.67 ms to 0.25 ms | 13.24 ms to 0.47 ms |
| ta081 | 100x20 | 11.26 ms to 0.48 ms | 32.49 ms to 0.92 ms |
| ta091 | 200x10 | 34.33 ms to 0.97 ms | 99.13 ms to 1.89 ms |
| ta101 | 200x20 | 87.05 ms to 1.89 ms | 257.39 ms to 3.75 ms |
| ta111 | 500x20 | naive not run; 11.98 ms | naive not run; 23.86 ms |

The improvement pass speeds up by roughly 4x at twenty jobs and roughly 69x at two
hundred, and the ratio tracks the job count rather than the machine count: ta061 and
ta091 differ only in jobs and their ratios differ by a factor of two, while ta061 and
ta081 differ mostly in machines and their ratios are much closer. That is what an
`O(n)` factor should look like, and it is the reason the whole sweep is in the table
rather than one row: any single instance would have supported almost any claim about
the shape of the improvement. The naive pass was not run at five hundred jobs, where
it takes minutes; that row reports the tuned time only and says so.

These are a development diagnostic on one host, not a benchmark result and not
evidence.

What this changes for C6 is worth recording, because it is the opposite of
convenient. The number a device now has to beat at 500 jobs is 23.86 ms of tuned
single-threaded CPU work, not the several seconds the naive pass would have taken.
The crossover, when it is measured, will sit further out than it would have against
the old baseline, and that is the honest position to measure from.

## Intermittent advisory database fetch

`cargo deny check advisories` fetches the RustSec database from github.com, which
has repeatedly been unreachable in this environment. The acceptance gate now
falls back to the cached database rather than failing spuriously or skipping the
check; an absent cache is still a hard failure. Reproduction: run
`cargo deny --locked check` without network egress to github.com. Next step: seed
the advisory database in CI so the check does not depend on egress at gate time.

## Native acceptance can be skipped explicitly

`AI_OPTIMIZER_SKIP_NATIVE=1 bash tools/check.sh` runs without the pinned HiGHS
build and prints a prominent warning that native acceptance was not covered. Such
a run is not a complete acceptance gate pass and must not be recorded as one.

## Sanitizers not yet in the gate

SPEC-0002's acceptance list mentions running repeated native lifecycle tests under
available sanitizers. The repeated-lifecycle test exists and passes, but no
sanitizer run is part of `tools/check.sh` yet. This is an uncovered part of the C1
acceptance list, recorded rather than waived silently.

## Extension containment covers panics only

The C3 extension host runs extensions in-process and contains panics with
`catch_unwind`. It cannot contain a process abort, stack exhaustion or a memory
fault, and it enforces no per-extension memory budget. A hostile extension can
therefore still take down the process, even though it cannot affect a search's
mathematical conclusion. Reproduction: an extension calling
`std::process::abort` ends the test process. Next step: process-isolated
workers, which SPEC-0004 defers and which need their own decision record. The
host also requires the unwind panic strategy; no repository profile sets
`panic = "abort"`, and nothing currently pins that.

## Python SDK is deferred with a stated blocker

SPEC-0005 delivers the C4 run surface through the CLI and defers the Python SDK
to its own specification. The blocker is concrete rather than a matter of
sequencing: pyo3 expands to unsafe code, the workspace sets
`unsafe_code = "forbid"`, and ADR-0003 permits unsafe only inside
optimizer-highs. An in-process binding therefore requires a decision record
amending ADR-0003, plus maturin packaging and a Python test layer in the gate.
AGENTS.md also states that Python under tools/ is validation tooling and not the
SDK. Reproduction: add a pyo3 dependency to any runtime crate and build. Next
step: decide the SDK's shape in its own specification, now backlog item C9; a
subprocess wrapper over the versioned run records needs no unsafe boundary and is
the cheaper option if an SDK is wanted before that decision.

## Resolved: the local extension registry is implemented

This was recorded from C4 through C5 and is now closed by C8 under
[SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md) and
[ADR-0008](../docs/decisions/ADR-0008-registry-resolution.md). `optimizer search`,
`optimizer verify` and `optimizer schedule solve` resolve a configuration's
extension policy through a registry document the caller names with `--registry`,
and registration, promotion, licenses, compatibility, authority basis and
inter-extension requirements are all checked rather than parked. The declaration
fields SPEC-0004 deliberately left unread — data needs, hardware and dependencies —
now have checked meanings.

Retained as the limits the implementation actually has, each recorded rather than
absorbed:

- A run record names each extension's identity and version but not the registry
  document that resolved it, so licenses and promotion state are auditable through
  the registry rather than through the record. Closing this needs a run-record v2
  and an ADR, because SPEC-0005 makes a change to the compared fields breaking.
- An extension is identified by identity and version, so two different builds of one
  version are indistinguishable. This is the same limitation already recorded for
  the pinned native library, and it is why the summary-difference diagnostic exists.
- The registry resolves only extensions this build provides. It cannot name a
  dynamically loaded native extension, and it refuses an entry requiring a GPU;
  both refusals are explicit and both remain recorded below.
- Provider construction happens before SPEC-0004's guarded host exists, so a
  provider that panics while constructing an extension is outside the
  panic-containment claim. The host's containment of `declare`, `propose` and
  `advise` is unchanged.
- Conformance establishes contract invariance only. A passing record means the
  contract held, never that the extension improved a search, which stays a C7
  question.

## Resolved: a scheduling run record with a producer registered now verifies

Recorded from C5 and closed by C8. `optimizer verify` previously re-executed every
record through the extension-free search entry point, so a record whose
configuration named an extension policy was refused as unsupported: re-running
without the named producer would have reproduced a search the record does not
describe, and its node counters would have differed for that reason alone.

Under [SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md)
requirement 19 the verifier reconstructs the producer a record names, through a
registry the caller passes with `--registry`. Reproduction of the closed case:
`optimizer schedule solve` with a configuration naming `flow-shop-neh` and a
registry, then `optimizer verify` on the resulting record with the same registry;
it agrees and exits 0. The gate re-executes such a record across a commit boundary
in `tools/verify_committed_record.py`. A record naming an extension policy with no
`--registry` is still refused, which is requirement 18 rather than a limitation.

## Resolved: a run record's identifier no longer depends on the clock

`optimizer search` built `record_id` as `run-{model_id}-{elapsed_ms}` and
`optimizer schedule solve` built `schedule-{model_id}-{elapsed_ms}`. The
identifier was a pure function of a measurement the project excludes from meaning
everywhere else: SPEC-0005 requirement 12 fixes elapsed time as diagnostic rather
than contractual, and verification ignores it. Two runs of the same search on the
same machine got different identifiers whenever the host spent a different number
of milliseconds, and two unrelated searches that took equally long collided.

Found by the C8 clean-checkout verification, which is the case it takes to see it:
the requirement 17 contract compares a record produced with a registry against one
produced without, and both runs completed in 0 ms on a warm working tree but in 0
and 1 ms on the clean clone.

Closed by SPEC-0005 requirement 1a, which now states that an identifier is derived
only from what the record describes. Both commands derive it from the SHA-256
digests of the input documents the record already carries, so a different model or
a different configuration yields a different identifier and a repeated run yields
the same one. Two runs of the same inputs sharing an identifier is the intended
reading rather than a residual collision: the identifier names the inputs, and
whether two such runs agree is what `optimizer verify` answers. Reproduction of the
closed case: run `optimizer search` twice over the same model and configuration and
compare the two `record_id` values; the contract test asserts this and was shown to
fail with the old derivation reinstated.

## Resolved: two SPEC-0009 acceptance gaps closed by diagnosis

Both were recorded when C8 was integrated and both are now closed, one by a
specification correction and one by a test that reaches a branch previously
believed possibly dead.

Requirement 14 said resolution "MUST NOT ... construct" a refused extension, which
was not true of the declaration- and role-mismatch paths: `Extension::declare` is
the authority being compared and the provider is what supplies the role, so both
are necessarily decided after construction. The rule is now split. Requirement 14
governs invocation, which holds everywhere. Requirement 14a governs construction
and names the three refusals that can be decided before it — an unprovided
identity, an unsatisfied data requirement and a gpu hardware requirement — and
states that a mismatch is constructed, read and then refused without ever being
invoked. This was a specification correction, not a code change; the
implementation was already right.

Requirement 20's record-versus-resolved version comparison is **reachable**, and
is now tested. The earlier doubt came from testing it the wrong way round:
restamping the *registry* is refused by the declaration check first, because the
extension still reports the version it always did. The rule the requirement
actually describes runs the other direction — a record naming a version the
current build no longer declares, which is what happens when a record outlives the
build that produced it. Restating the version in the record's extension summary
reaches it, and disabling the branch makes that test fail. The branch is not dead
and was not removed.

That diagnosis also found a defect in the acceptance gate itself.
`tools/verify_committed_record.py` restamped the registry and asserted only that
the restamped version appeared in stderr — but resolution's declaration-mismatch
message contains that version too, so the check passed on the wrong error and
never reached requirement 20. Its comment claimed an isolation it did not achieve.
The gate now covers both rules separately and each asserts the message its own
rule produces; with the requirement 20 branch disabled the gate step fails, where
before it passed. This is the same class of defect the C8 clean-checkout run
found: a check that passes for a reason other than the one it names.

## C8 requirements whose acceptance tests are thinner than the specification

SPEC-0009's acceptance section describes cases that the implementation does not
yet assert. These are recorded rather than quietly downgraded, because the
specification is accepted and its own test mapping is the thing out of date.

- Requirement 20's nondeterministic-record refusal has no test. Neither example
  extension declares nondeterminism, so producing such a record needs a fixture
  that does not exist in the CLI's provider table.
- Requirement 21's positive case — a run that agrees while reporting an extension
  summary difference as a diagnostic note — is asserted only in its negative form,
  that no difference is reported when none exists. `ExtensionDifference` has no
  unit test.
- Requirement 22's forfeited registry-backed record is not produced by any test.
  The forfeiture rule itself is covered without a registry under SPEC-0005.
- Requirement 18 is asserted for `optimizer schedule solve` but not for
  `optimizer search --registry` with a non-empty policy, because both extensions
  this build provides are flow-shop producers that cannot be constructed from a
  bare model. A search-command case needs a provider that takes no auxiliary
  instance.
- Requirement 1's document-level missing-field refusal and requirement 3's
  duplicate-field rejection are covered for entries but not for the document
  itself.

## Verification assumes an unchanged native library

`optimizer verify` re-runs a search and compares the two records field by field. A
divergence now reports whether the backend library, source revision or compiler
differs from the record's, so a changed engine is distinguishable from a wrong
result *in the diagnostic*. What remains unresolved is whether such a mismatch
should ever be **tolerated**: verification still fails, because deciding otherwise
would change the meaning of agreement and needs a new record version plus an ADR
under SPEC-0005's compatibility rule. Cross-host reproducibility is separately
untested, because floating-point behavior and library builds may differ between
machines, and closing it needs a second machine in CI rather than local code.
Agreement therefore remains evidence of determinism on one host over time, which
is what ADR-0006 claims and no more.

## Per-node work Track B measured and deliberately did not remove

Track B removed five items from the branch-and-bound node path without changing
any conclusion; see [active task](active-task.md) for the measurements. Two
candidates were identified, reasoned about and left in place, and both are
recorded here so they read as decisions rather than as oversights.

`node::relaxation` still clones the original model's constraints and objective
once per node — 5,175 nonzeros for the encoded ta001. `Model::rebound` removed the
revalidation that sat beside that copy but not the copy itself, and the copy is
now likely the dominant per-node cost. Reproduction: profile a node-budgeted
`schedule solve` over ta001 and attribute time inside `node::relaxation`. Next
step: sharing the rows between a model and its relaxations needs an `Rc` or `Arc`
inside `ModelDocument`, which is a public type in a crate other crates deserialize
through; that is a wide change and needs its own measurement before it is worth
making, not a follow-on commit.

Reusing the `Highs` object across nodes is permitted — SPEC-0003 requirement 23
forbids reusing a *basis*, not the instance — and is the obvious next per-node
item. It was deferred because the measurement harness that would justify it did
not exist when the ranking was made. Cross-node warm start and parallel search
remain forbidden by SPEC-0003 requirement 23 and SPEC-0002 requirement 5
respectively, and each needs its own decision record; neither is blocked on
measurement.

Also worth recording, because it is a gate property rather than an engine one:
until Track B's last commit both committed run records reported `nodes_explored:
1`, so `tools/verify_committed_record.py` had never re-executed a branching search
across a commit boundary. A multi-node fixture now closes that. Its
`nodes_pruned_infeasible` is 0 and is deliberately not asserted, because the
positional encoding's relaxation was feasible at every size tried and choosing a
fixture to hit that counter would be choosing it for the wrong reason.

## Checkpoint restart is still unimplemented

C2 defines and serializes `Checkpoint` and SPEC-0003 states that restart is not
implemented. The C4 run surface does not add a restart entry point either, so a
long search cannot be resumed and a run record cannot be continued. Verification
re-runs from the beginning under the record's own budgets. Reproduction: no CLI
command consumes a checkpoint. Next step: restart needs its own acceptance
evidence before any public entry point exists.

## The flow-shop encoding is correct but weak

Two limits recorded before implementation, both confirmed by it.

The positional encoding is exactly linear and its optimum equals the instance's
minimum makespan by construction, but its linear relaxation is weak and the model
is quadratic in the job count: a 20-job, 5-machine Taillard instance is 400 binary
variables. The executive is not expected to prove optimality at that size, so the
specification confines proven-optimal claims to tiny instances checked against
exhaustive permutation enumeration and confines the frozen subset to feasibility,
determinism and validated-incumbent evidence. This is a stated scope boundary, not
a defect, and it is why requirement 26 forbids recording a performance claim.
Reproduction: encode any 20-job instance and run the executive without a budget; a
node-limited run over `ta001` is asserted in the CLI contracts to report its limit
rather than an optimum. Next step: a stronger formulation or a scheduling-specific
bound would each need its own contract, and the evidence justifying one does not
exist yet.

Permutation schedules are also not optimal for the general flow shop beyond three
machines, confirmed by direct enumeration on a 3-job, 4-machine instance where the
best permutation schedule costs 50 and the best general schedule costs 47. The
permutation restriction is part of the problem C5 solves rather than an
approximation it makes, and nothing in the slice should be read as solving the
general flow shop.

## Dynamically loaded native extensions are not implemented

SPEC-0004 specifies host-contract-version negotiation and implements it in safe
Rust, but the versioned C-compatible boundary for separately distributed native
components is deliberately absent. It needs a second unsafe boundary, which
ADR-0003 prohibits outside optimizer-highs, so it requires an amending decision
record plus its own lifecycle, ABI-stability and crash-isolation evidence. This
is a recorded deferral, not a gap discovered late.

[SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md) does not change
this. Its registry *resolves* a named identity to an extension the build already
provides and refuses one it does not, so the registry is now the obvious place a
dynamically loaded extension would be named and deliberately cannot name one. That
makes the deferral more visible rather than closing it.
