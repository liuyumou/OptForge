# ADR-0026: COPT Comparison and Component-Cost Diagnosis

Status: accepted by the maintainer on 2026-09-26 before implementation.
Scope: development-only study under SPEC-0013; gpup-copt-comparison-v1.

## Frozen comparison

Use the twelve existing development models plus all four unchanged ADR-0022
extension models. Final tolerances are 1e-9, threads one, seed 17; original method
settings, code objects and arithmetic remain unchanged. Ordinary process deadlines
are 10 seconds, extensions 30 seconds, cleanup two seconds. Project physical work
is capped at 50000. Preserve original-model host certification as the only authority.

Seventeen configurations: six established controls (HiGHS, host, legacy CUDA,
matched/tuned/precision FP64); five fixed modes (storage/products/accumulation,
master-correction32, working-correction32); adaptive FP64, sticky accumulation to
FP64, full gradual working-state demotion; COPT default CPU LP, CPU/GPU PDLP.
Adaptive interval 32, all audit tolerances 1e-7; demotion four clean windows and
margin 0.25. COPT 8.0.6 uses LpMethod=-1 and default crossover for default CPU LP,
LpMethod=6 and Crossover=0 for PDLP, explicit GPUMode, Threads=1, FeasTol/DualTol
1e-9 and PDLPTol=1e-9 where applicable. Record native simplex/barrier/PDLP counts;
aggregate above 50000 is work-limited. These are not equivalent to project physical
updates; unavailable COPT hard iteration/seed controls remain explicit.

Freeze 1140 attempts: 816 timings (17 x 16 x 3); 144 repeated profiles (6 x 8 x 3);
88 remaining profiles (11 x 8); 72 short-work diagnostics (6 x 4 x 3); 20 traces
(5 x 4). Repeated profile modes: all COPT modes, tuned FP64, sticky accumulation,
gradual working demotion. Models: four previous profile models plus all extensions.
Short modes: tuned/precision FP64, accumulation FP32, adaptive FP64, sticky
accumulation and gradual working. Trace modes: tuned FP64, accumulation FP32,
sticky accumulation, gradual working and COPT GPU. Short/trace models: small-4,
irregular-2048, extension irregular-32768 and mixed-65536. Short work limit 200
physical updates; preserve convergence/guards and compare actual work, never force
an equal count. Sequence: acceptance, timing repetition zero, repeated profiles,
short work, remaining profiles, traces, timing repetitions one and two. Reproducibly
randomize within instance/repetition using seed 17001. Retain every attempted ID;
no retries, erased failures, changed settings or held-out evaluation.

## Observations and interfaces

Fresh-process launch through certified output is primary latency. Profiles/traces
are separate diagnostics, not timing samples. Add optional hierarchical wall scopes
with inclusive/exclusive costs, counts and explicit unattributed residuals in a
strict separately versioned artifact. Record input/representation/hashing;
preconditioning/norm/operator preparation; context/module/kernel lookup; memory and
transfers; submission/synchronization/readback; control/KKT/restarts; working-state
narrowing; correction/checkpoints/audits/adoption/rollback/transitions/probes/replay;
feasibility/objective/certificate/gap checks; endpoint verification/output/teardown.
Per-rung and rejected/replay observations explicitly retain overlapping subsets.
No extra device synchronization or changed numeric path is authorized for timing.

COPT scopes cover import, environment/license, model/variables/constraints/objective,
parameters, solveLP, extraction, host certification and output. Collect native
SolvingTime/MemPeak, iterations, original/presolved dimensions and available logs.
Native attributes, coarse log observations and opaque internals are distinct.
GPU confirmation requires execution evidence. Do not infer internal arithmetic
precision or exact phase boundaries from names/coarse logs. Preserve import guards.

Use Nsight Systems CUDA/NVTX observations where available, retained raw traces and
offline exports. Include allocations, copies, launches, graph/correlation handling,
streams, busy interval unions and overlap. Do not add host wall time to device
activity or parent time to children; missing is unavailable, never fabricated zero.
Keep profile overhead visible. Preserve trace solver deadlines, add 15 supervisor
seconds for instrumentation/finalization, and permit trace-only 512 MiB output.
Retain partial traces and profiler failures. Do not alter counter permissions.

Add experimental lp-study solve sharing ordinary solve behavior, with explicit
study-only model limit at most 128 MiB and matching study verification. Ordinary
16 MiB CLI input remains unchanged. Add external witness/endpoint v2 for method
identity/native counters; retain v1. Add campaign/trial v6 and cost artifacts;
legacy records and schemas preserve their meanings. Hash effective per-instance
limits before admission; subsequent CPU verification has a 120-second bound.
Freeze source, schemas, binaries, model hashes, COPT identities, profiler identity
and all four required discovery/execution images; never archive licenses.

## Resources and acceptance

Allocate timings 4800 s ablations; profiles/short work 3000 s repeatability;
traces 600 s baseline; acceptance 300 s repeatability; combined 8700 s. No borrowing.
Chain a 3600-second ceiling extension to ADR-0025: 14402574545061 + 3600000000000
= 18002574545061 ns. Preserve 13056 events, prefix SHA-256
6db55153153e66ed5c2398417d008e4edd278e11153cf87b975345f1a574d34d, and
8912494084146 consumed ns. Existing output binding, every prior prefix, 28800 s
campaign and all phase caps remain authoritative. Reserve complete bounds; stop
at any cap and report incomplete cells. Serialize all GPU jobs under the host lease.
Four build jobs and four CPU validation hours; CPU-only costs separately visible.

Require full pinned-native tools/check.sh, regular device acceptance, strict
external evidence, min/max/offset/guard/cancel/work tests; input/deadline/legacy
compatibility; nested/overlapping/partial cost tests; profile-on/off fixed-work
numerical equivalence with non-binding deadlines; clean-checkout synthetic budget
and authority tests. Carry forward sanitizer receipts only for unchanged code and
retain historical tuned_cases racecheck/large-model limitations.

Report independent endpoints, every planned cell, paired medians and 95% bootstrap
intervals (seed 17002, 10000 resamples), component tables/charts and separate GPU
timelines. Report per-work costs only for comparable units, convergence amplification,
profile overhead and opaque costs. Rank future changes by measured contribution,
affected workloads, defensible Amdahl bounds/assumptions, correctness risk and next
experiment. Three development repetitions establish no preset. Optimization,
relaxed tolerances, repeated sessions and remote publication are outside scope.
Commit locally only after acceptance; retain negative and incomplete results.
