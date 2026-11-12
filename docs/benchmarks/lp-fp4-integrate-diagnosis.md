# FP4 integration overhead and recovery diagnosis

The dense case is a useful positive result: FP4 x4 accelerates the actual coupled
iterations while reaching the same independently checked 1e-7 tier. Complete
latency is dominated by host delivery and research-evidence construction. The
recovery-heavy cases expose a different limitation: repeated block encoding of
the state loses useful low-order information, and the controller responds late.
The ill-scaled failure is primarily a convergence problem shared by native FP64.
The retained evidence does not indicate a Tensor instruction or hardware defect.

This diagnosis analyzes the completed [integration study](lp-fp4-integrate.md).
It does not change its source, policy, acceptance, timing results or charges.
It adds a separately supervised CPU-only serialization microprofile and CPU
re-encoding of retained endpoints. No solver, checker or GPU job was rerun.

## Where complete time goes

For dense-rich-65 at 1e-7, both native and FP4 x4 certify after 200 updates, with
no recovery. The following are **arithmetic means of all three prepared trials**,
so the phase rows add to the total. The prior report uses model medians for its
retention decision; that decision is unchanged.

| Measured component | Native, ms | FP4 x4, ms |
| --- | ---: | ---: |
| GPU iteration events | 3.716 | 2.766 |
| Remaining iteration call time | 0.411 | 0.478 |
| Python numerical preparation | 0.152 | 1.226 |
| Original-A residual observations | 0.315 | 0.273 |
| Independent checker phase, including evidence writes | 10.592 | 12.717 |
| Exports | 4.919 | 4.715 |
| Transport and unclassified controller coordination | 27.208 | 29.215 |
| Work outside the controller timer | 4.052 | 4.112 |
| **Complete measured solve** | **51.365** | **55.502** |

The GPU saves **0.950 ms**; all other work together adds **5.086 ms**. The native
and FP4 median solve times are 51.119 and 55.567 ms, respectively, reproducing the
reported 0.919954x complete ratio. The GPU iteration median ratio is 1.343738x.
These three-trial phase differences do not establish that FP4 inherently makes
the independent checker slower; the checker phase includes serialization and
timing variation as well as mathematical checking.

The label `transport` is too broad for diagnosis. Of its 29.215 ms FP4 mean,
**24.167 ms is the controller's explicit unclassified coordination remainder**,
not a measured PCIe transfer. Source inspection locates model construction,
model/evidence serialization, hashes, checkpoint assembly and other Python work
there. Only 5.048 ms remains in the explicitly timed service/load/save/finish
portion, which itself includes CPU work and allocations as well as transfers.
It would be incorrect to describe 29 ms as GPU transfer latency or bandwidth.

The new CPU-only microprofile repeats the same host operations on retained
payloads, with nine repetitions and the existing four-CPU supervisor. For dense
x4, median costs are:

| Host operation | Median, ms | Detail |
| --- | ---: | --- |
| Reconstruct immutable model | 1.644 | Done again inside every prepared solve |
| Format original model as indented JSON | 14.951 | 380,447 bytes |
| Durably write original model | 16.004 | **Includes** the preceding JSON formatting, file write, fsync and hash |
| Durably write certificate | 2.274 | 54,390 bytes, including formatting |
| Durably write checkpoint | 1.331 | 34,867 bytes, including formatting |
| Durably write result | 0.493 | 7,712 bytes, including formatting |

Model reconstruction plus its durable write alone costs about **17.65 ms** in
this separate microprofile, over six times the historical 2.77 ms FP4 iteration
time. The dense model's JSON formatting is the main part of that operation;
fsync is not the main cause. The sparse equality model's corresponding durable
write is only 2.242 ms. These are new host microbenchmarks, not a retroactive
exact decomposition or a measured optimized-solver speedup. Their fixed warm
operation order and nine repetitions are disclosed in the machine record.

Additional concrete avoidable work remains in the source:

- Prepared sessions reuse the CUDA context/module and checker process, but each
  solve still rebuilds matrix representations and makes fourteen GPU buffer
  allocations/uploads plus two events. Promotions repeat this work; `finish`
  destroys the per-solve engine. Original matrix decoding/validation and both
  sparse orientations are also reconstructed on each load.
- The persistent checker reparses the original model and reconstructs its
  `LinearProgram` for every assessment. Keeping an immutable, hash-bound parsed
  original model would preserve independent checking without this repeated setup.
- Each 32-update window waits for flags and metrics, using separate synchronized
  downloads and a JSON request/response. An export additionally downloads all
  five vectors, codes and exponents. The terminal endpoint is exported again
  after the certifying audit even when unchanged. Certificate reuse already
  avoids a second mathematical check, but does not avoid that export.
- Dense model generation, indented evidence, repeated hashing and full checkpoint
  serialization remain on the measured path. The outer timer also includes result
  hashing/writing. Cold execution adds process/import, CUDA context and teardown
  costs; pooled cold solves take about 566 ms. The records do not separately
  identify every cold startup subcomponent.

On this dense native endpoint, all GPU iterations account for only 7.24% of
complete time. Holding everything else fixed, even removing them entirely would
give only **1.078x** complete acceleration. Extreme kernel tuning alone cannot
reach the existing 1.10x complete-latency target on this implementation.

## What actually triggers recovery

Across all 576 performance cells and all six starting lanes, there are **288
local-budget recoveries and 126 stagnation recoveries**. Every recorded restore
matches its accepted checkpoint exactly. There are no recorded conversion
failures, nonfinite failures, ambiguous-projection recoveries or residual-growth
recoveries in this cohort. Outcomes are 432 certified solves and 144 limits.
The injected admission tests are separate from these counts.

Thus the relevant failures are failure to finish at the starting precision, and
failure to converge/certify within the update cap. The rollback/conversion
mechanism itself did not fail in the measured solve cohort.

### Encoding loss, rather than matrix multiplication, drives the FP4 promotions

The operational allowance is

`max(final_tolerance, min(1, last_audited_residual)) * state_scale / 64`.

It is recomputed after original-A audits, which currently occur every 200 accepted
updates. A large previous residual permits large local encoding losses throughout
that interval. The new, smaller allowance then rejects the next update. For the
x4 starts below, all triggering windows contain exactly one update, so the term
values are not maxima accumulated across different updates.

| Model / precision before promotion | Last audited residual | Local allowance | Largest reported encoding term |
| --- | ---: | ---: | ---: |
| Ranged, x4 | 2.63214e-4 | 4.11272e-6 | 2.38478e-4 |
| Ranged, x8, strict tier | 2.79397e-8 | 4.36557e-10 | 2.75686e-8 |
| Active bounds, x4 | 1.27377e-4 | 1.99026e-6 | 8.04663e-5 |
| Active bounds, x8, strict tier | 1.27416e-8 | 1.99087e-10 | 7.27596e-9 |
| Dense, x4, strict tier | 8.88935e-10 | 1.56250e-11 | 1.89603e-11 |

At these events the operator, instruction, scalar, projection and discarded-term
fields are zero; the combine estimate is approximately 1.4e-12 to 2.2e-12.
Encoding dominates. A zero instruction field is the admitted empirical estimate,
not a proof of exact arithmetic or a global error enclosure.

Every update re-encodes the full primal, dual and extrapolated vectors into a
fixed number of E2M1 components with a shared scale per 32 values. The low-order
remainder after the final component is discarded. More iterations cannot
reliably accumulate corrections that are repeatedly lost this way. Promotion
preserves the current represented state; it cannot reconstruct prior lost bits.

The chosen trajectory matters. Re-encoding the retained strict native endpoints
with the exact-residual CPU encoder gives:

| Retained endpoint | Dominant vector | x4 maximum encoding error | x8 maximum encoding error |
| --- | --- | ---: | ---: |
| Ranged | primal x | 1.09975e-4 | 1.38965e-8 |
| Active bounds | dual y | 2.18840e-4 | 2.92216e-8 |
| Dense | primal/dual | below 1.7e-16 | below 1.7e-16 |

The dense equality fixture converges to the constructed eighth-integer primal
and dual targets. Those values are particularly easy for the component encoding.
The ranged primal and active-bound dual converge to other members of their
solution sets, with less representable values. This is evidence about this
trajectory and block representation, not a proof that no other FP4-representable
optimal point exists. It also means the dense accuracy result should not be
generalized solely from matrix density; generic dense solution values remain
an important future test.

### Delayed decisions and expensive promotion amplify the cost

Ranged and active-bound x4 starts at 1e-7 use 201 x4 plus 200 x8 updates, while
native certifies at 200. At 1e-9 they use 201 x4, 201 x8 and 200 native updates:
602 physical updates and 600 logical updates. **Only two updates are lost to
rollback**. The larger cost is spending complete audit intervals at insufficient
state precision, then rebuilding and converting before the next interval. The
records do not identify the earliest certifiable update within those intervals.

For dense at 1e-9, both native and FP4 x4 fail the gap check at update 200, despite
feasible points and residuals below 1e-9. Their conservative gap uppers are almost
identical: 2.33690e-8 native and 2.33745e-8 FP4. Residual tolerance alone is not the
final certificate. Native certifies at 400; x4 promotes to x8 at 201 and certifies
at 401 physical / 400 logical updates. Recovery loses only one update here.

Dense strict x4's mean GPU iteration time becomes 7.705 ms versus native's
7.470 ms. Its mean rollback plus conversion is 6.437 ms, and numerical preparation
is 2.993 ms versus 0.150 ms native. Complete mean time becomes 77.099 versus
67.422 ms. The strict failure is therefore a marginal local guard crossing,
more expensive x8 arithmetic, and a heavyweight promotion; it is not evidence
that dense x4 inherently cannot satisfy 1e-9 under any other validated policy.

### The ill-scaled recovery mistakes slow progress for a precision problem

The policy declares stagnation after three successive audits improve the residual
by less than 10%. Immediately before x8-to-native recovery, improvement is
**9.862%, 9.918%, and 9.974%**. That is **26.90% residual reduction across the
three intervals**, yet the policy rejects the last 200 updates and restores
logical update 7600.

Recomputing those 200 updates natively from the restored checkpoint produces
residual 0.000743737669, almost the same as the rejected x8 result
0.000743735530. Raising arithmetic precision does not address the cause. At the
10,000-physical-update cap, native from the start also fails: residual
4.30347e-4, versus 4.67737e-4 for the x4 recovery trajectory with only 9799 retained
logical updates. This is a globally fixed-step, unpreconditioned research
recurrence on differently scaled rows. Equilibration, suitable diagonal steps
and convergence control are the appropriate investigation, rather than further
precision escalation alone. The production adaptive native solver is separate.

The other uncertified family intentionally has a zero matrix column, an unbounded
variable and nonzero objective coefficient. It cannot yield a finite optimality
certificate; precision recovery cannot fix that model. An explicit unboundedness
path would avoid wasting the full update cap without changing certification.

## Performance direction supported by this diagnosis

1. Reuse immutable model bytes, hashes, parsed original checker state, GPU
   allocations and prepared operator fragments. Use compact evidence/transport
   with explicit ownership instead of regenerating indented JSON every solve.
   Preserve durable evidence and report any asynchronous drain/delivery costs;
   merely moving work outside the timer is not a speedup.
2. Address state encoding loss before tuning MMA further: investigate retained
   correction tails or error feedback, block scaling/grouping and precision
   selection driven by per-vector encoding loss. FP4 tensor products can remain
   the main arithmetic even if a small higher-precision correction state is
   necessary. These are proposed designs, not measured improvements or proofs.
3. Make precision/check decisions responsive near the noise floor, while retaining
   independent original-model certification and the 200-update maximum audit
   separation. Reusing prepared representations can make monotone promotion much
   cheaper. Avoid a forced failed update immediately after each audit.
4. Replace the arbitrary progress-rate cliff with a versioned rule that separates
   encoding-limited progress from ordinary slow convergence; investigate scaling
   and adaptive steps on ill-conditioned models. Do not loosen final certificates
   or retroactively change the frozen policy/results.
5. Test genuinely large dense workloads and nontrivial solution significands.
   The current 65-coordinate dense case runs one CTA with 96 padded coordinates,
   hence uses at most one SM at a time. It establishes a useful arithmetic win,
   not device-wide throughput. Sparse cases need a sparse-aware path; densifying
   rows with three nonzeros adds work that the native control already avoids.

The next useful work is therefore host-path reuse and state/convergence design,
followed by admitted larger dense measurements. More GPU time by itself will
not remove these bottlenecks. No next scientific execution or public preset is
released by this diagnosis.

## Reproducibility and accounting

- [Source-bound retained analysis, exact phase means and recovery traces](data/fp4-integrate-diagnosis-v1.json).
- [Separate CPU serialization measurements](data/fp4-integrate-host-serialization-v1.json).
- [Diagnosis accounting and delivery checks](data/fp4-integrate-diagnosis-accounting-v1.json).
- [Analysis source](../../tools/lp_fp4_integrate_diagnose.py).

The new independent envelope is 512 CPU seconds / zero GPU seconds, including
256 conservative preparation seconds and separate 128-second reservations for
analysis/profile and delivery. The unchanged in-container supervisor enforces
four CPU slots and a 2 GiB sampled host RSS ceiling. The original 96000 CPU /
14400 GPU allocation remains closed, with its exact charges unchanged. New
accounting and cleanup are linked above: **283.137759816 CPU seconds and zero GPU
seconds**, with both jobs passing and empty cleanup. Delivery is local; no push/publication.
