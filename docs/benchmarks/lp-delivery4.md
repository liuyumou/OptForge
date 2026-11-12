# Exact provenance hashing and cold lifecycle costs — GPUP-DELIVERY4

Status: implemented; all pilot and confirmation cells complete
Contract: [SPEC-0035](../specifications/SPEC-0035-delivery4.md)
Decision: [ADR-0068](../decisions/ADR-0068-delivery4.md)

No comparison meets all predeclared retention requirements. Dense target block-
ratio medians are **1.0760–1.0869x**. Strict dense512 cold medians improve from
**512.561 to 444.136 ms** for native and **516.338 to 448.920 ms** for FP4.
The public default remains unchanged.

## Measured CPU startup opportunity

The isolated executor preserves the DELIVERY3 overlap control and all numerical
state-machine operations. The candidate replaces only selected original-byte
SHA-256 calculations through the pinned sha2 0.10.9 safe API. The original checker
arithmetic and its internal model binding remain unchanged. Model validation
still completes before CUDA setup. Both variants apply equally to native and FP4
at both final certification tiers; the public default is unchanged.

The [SHA-256 API](https://docs.rs/sha2/0.10.9/sha2/) returns the same cryptographic
digest; CPU-dependent implementation selection changes its cost. No digest is
cached across different byte inputs, truncated, replaced or weakened. Original
sources remain exact. Warm constructor measurements include object destruction,
are exploratory, and are not complete cold-latency observations.

| Warm median CPU operation | Original ms | Candidate ms |
| --- | ---: | ---: |
| Dense128 solver data | 6.191 | 2.970 |
| Dense256 solver data | 24.317 | 11.496 |
| Dense512 solver data | 110.875 | 53.163 |
| Dense512 model SHA-256 | 61.304 | 9.775 |
| Device image SHA-256 | 7.714 | 1.279 |
| Executable SHA-256 | 5.140 | 0.898 |

The independent checker's constructor stays near 109–112 ms because its internal
original-model hash is retained. Its readiness model rehash is accelerated, but
that work was already overlapped with CUDA startup. Earlier diagnosis identified
about 74 ms after checker construction; these new CPU measurements show that a
model rehash, rather than executable hashing alone, is a major contributor.
The critical-path opportunity is the serial solver preparation and image binding.

## Admission and inference boundaries

All 27 isolated Rust tests pass. CPU admission passes 612 fresh assessments of
102 archived original serial endpoints, 48 exact scaled/unscaled model
representations and 42 configuration/process cases. Nine prospective Python
contracts cover statistical thresholds, exact source preservation and transport
failure handling. The dependency audit passes with exact external versions and
five source-bound local path wildcard exceptions ([policy limitation](https://embarkstudios.github.io/cargo-deny/checks/bans/cfg.html#allow-wildcard-paths)); original repository manifests
and policy remain unchanged. Cargo-deny's path exception applies only to private
crates, so the isolated policy is supplemented by a metadata audit rejecting
every external wildcard and every out-of-repository path.

The full native repository gate passes 638 total Rust tests (637 direct workspace
tests plus one buffered-transport test) and 678 Python tests, dependency checks,
committed replay, artifacts, documentation and smoke. Device admission passes
84 lifecycle cases, four module-startup failures, six invalid-model refusals
before CUDA creation, and 64 prepared smoke sessions / 192 solves. The original
four-sanitizer admission is reused only for its unchanged source-bound device
image; no new sanitizer run is claimed. Final confirmation and accounting follow
completion of their separate bounded reservations.

## Direct lifecycle findings from the two profiled blocks

The measured strict dense512 outer cost is now mostly attributed. Owned Session
destruction averages about **74 ms** in both variants and lanes; its nested CUDA
context destructor takes **69 ms**, checker EOF/reaping about **4.1 ms**, device
buffer free about **0.20 ms**, module unload about **0.31 ms**, and stream teardown
about **0.009 ms**. These nested durations explain their parent and must not be
added to it. Response construction beyond the solve costs about **0.39 ms**,
response emission **0.9–1.2 ms**, and durable output **1.2–1.6 ms**.

A further **37–38 ms** is outside the measured Rust main body but inside the
parent's launch-to-reap interval. It includes runtime/process entry and exit,
final diagnostic output, collection and any post-main library cleanup. These
timers do not distinguish those causes. It is not attributed to CUDA teardown.
Every profile has an exact nonoverlapping partition summing to its complete
parent timer; nested child/checker and GPU event intervals are never added twice.
Only two instrumented repetitions support these descriptive means, and profile
output overhead remains included. Uninstrumented confirmation decides retention.

The candidate's strict dense512 native setup averages 296 ms in these profiles.
Its context scope is about **222 ms**: driver initialization 113 ms, context
creation 107 ms, and library loading about 1.3 ms. Module loading is about 4.4 ms.
Original-byte hashing across setup falls from 77.4 to 11.0 ms, while JSON parsing
stays near 32 ms and sparse construction near 12–13 ms (nested validation and
compression must not be added again). The control's driver-initialization mean
is about 19 ms higher in just these two profiles; that difference is not itself
proved to be caused by hashing. These measurements rank remaining work, rather
than assigning every observed setup saving to the selected change.

The uninstrumented four-block pilot completes all 128 cold cells. Its dense512
paired geometric ratio is **1.158897x**, above the predeclared 1.01 continuation
threshold. The separate 3072-cell confirmation uses all twelve original families,
both lanes and tiers, complete exit/durability cost, and 32 balanced blocks.
Its 48 simultaneous metrics use exact median ranks **7 and 26**. The pilot is
not a retention conclusion, and the 1.10 confirmation target remains unchanged.

## Frozen confirmation results

All **3072 fresh cold cells** complete: **2816 certificates** across all eleven
bounded families and both tiers, plus **256 intentional infinite-bound refusals**.
All endpoints, certificates, audits, checkpoints, recovery and physical/logical
work match the retained originals. The separate 192 pilot cells also complete.
No scientific identity was retried and no observation is excluded.

The estimand is the median of 32 block geometric control/candidate ratios over
dense128/256/512. All 48 benefit/guard metrics use simultaneous 95% binomial
median intervals, ranks 7 and 26. Each benefit lower bound must reach 1.10x;
each of eleven family-guard upper bounds must be at most zero after subtracting
max(2% of control, 0.10 ms) from paired excess candidate time.

| Lane | Tier | Dense ratio median | Simultaneous interval | Complete decision |
| --- | --- | ---: | --- | --- |
| Native | 1e-7 | 1.0869x | [1.0650, 1.1002] | inconclusive |
| FP4 | 1e-7 | 1.0760x | [1.0609, 1.0864] | insufficient-benefit |
| Native | 1e-9 | 1.0786x | [1.0594, 1.0963] | insufficient-benefit |
| FP4 | 1e-9 | 1.0773x | [1.0633, 1.0906] | insufficient-benefit |

Family guards: **43 supported**, **1 inconclusive**, **0 material regressions**. Uncertain guards remain unresolved. No comparison meets all predeclared retention requirements.

Strict cold family medians (the last column is a ratio of marginal medians, not
the block-level primary estimand):

| Family | Lane | Control ms | Candidate ms | Ratio of medians |
| --- | --- | ---: | ---: | ---: |
| dense-generic-128 | Native | 365.868 | 354.924 | 1.0308x |
| dense-generic-128 | FP4 | 367.055 | 355.095 | 1.0337x |
| dense-generic-256 | Native | 393.671 | 371.036 | 1.0610x |
| dense-generic-256 | FP4 | 393.214 | 372.181 | 1.0565x |
| dense-generic-512 | Native | 512.561 | 444.136 | 1.1541x |
| dense-generic-512 | FP4 | 516.338 | 448.920 | 1.1502x |

Even deleting every recorded GPU event interval from the candidate, while
keeping all other work unchanged and adding no cost, gives only
**1.0098–1.0103x** geometric cold gain on the dense target.
This is an optimistic descriptive bound, not a viable accelerator forecast.
Cold follow-up should focus on measured startup/context lifecycle and the
unresolved process boundary. Existing MIXED2 remains a separately ready CPU
contract/cost alternative for prepared workloads. No follow-on execution is
released by this allocation.

Unresolved family guards: nativefast / certified-1e-9 / coupled-inequality (inconclusive).

## Scope and limitations

The twelve constructed development families and original bounded executor (at
most 512 coordinates per direction) do not establish performance on arbitrary
large LPs. Cold means a fresh solver process/session, not a machine reboot or
flushed OS/driver caches. Its timer begins immediately before process launch and
ends after exit plus durable stdout/stderr; prewritten request files and study
bookkeeping are outside, consistently with the retained control protocol.

The device is shared. Restarted processes, balanced pair order and randomized
strata reduce some confounding but do not establish independence between blocks.
The simultaneous median intervals assume independent, comparable block effects;
telemetry and descriptive lag correlations remain available without excluding
unfavorable observations. Warm CPU attribution uses five repetitions in separate
control/candidate processes and makes no independent statistical retention claim.
Prepared reuse passes admission; no new prepared performance cohort was run.

No public preset, numerical precision policy or final tolerance changed. Each
comparison uses the same final tier. Original model bytes, signed zeros, all
certificates/audits, checkpoint/recovery state and physical work remain authoritative.

## Evidence, failures and resource closure

The [machine result](data/delivery4-result-v1.json) binds all 39 portable archives,
raw startup measurements, profiler records, original comparison values, CPU
features/compiler/dependencies, selection and all decisions. Run
`python3 tools/lp_delivery4_replay.py` from a checkout to recheck every numerical
record, reproduce all four decisions and the lifecycle partitions without a
solver, compiler, original artifact directory or GPU. The current executable and
two earlier development executables are archived by content hash; reconstruction
does not rerun any scientific cell.

Three failed CPU reservations remain intact and fully charged: the first
dependency audit (2000 CPU seconds), its ineffective public-path exception
(120 seconds), and the source-comparison assertion that did not account for
Rustfmt moving the replacement import (1440 seconds). Their **3560 CPU seconds**,
logs and exact source versions are preserved. No numerical or GPU failure is
relabeled as passing. The corrected dependency audit rejects external wildcards
and binds the five allowed repository paths; the corrected source guard permits
only the deliberate hash-import substitution and requires every other model line
to remain exact.

Independent ceiling: 64000 CPU / 4800 GPU seconds, four CPU slots, 16 GiB sampled
RSS and 12 GiB owned device buffers, one pinned shared lease and the unchanged
in-container supervisor. Sampled RSS is not a hard cgroup memory limit. Historical
allocations stay closed, with no transfer. The allocation is **closed at 12602.090947756 CPU / 1311.837400940 GPU seconds**,
including 512 preparation and 128 closing-administration CPU seconds. All
supervisor cleanup is empty, and **1767 historical files** plus all other backlog
entries remain exact. The [acceptance](data/delivery4-acceptance-v1.json),
[history](data/delivery4-history-v1.json) and [accounting](data/delivery4-accounting-v1.json)
retain the complete receipts and development source versions.

[Isolated portability validation](data/delivery4-portability-v1.json) passes all
3264 cells, four decisions and lifecycle partitions with only Python tooling and
portable evidence copied to a temporary directory; no original `artifacts` or
`research` directory is present. Final source/binary checks, 244 documentation
pages, internal links, artifact schemas and whitespace checks pass. Local commit
only; no push, publication, public preset or GPUP-9 release.
