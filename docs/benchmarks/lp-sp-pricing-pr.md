# Certified pricing research: PR integration review

[PR #30](https://github.com/liuyumou/OptForge/pull/30) integrates the evaluated
pricing research and [COPT comparisons](lp-sp-pricing-comprehensive.md), together
with the preceding opt-in certificate-scratch/storage-supervision work. The
production CLI, workspace dependency lockfile and default solver paths are
unchanged. The pricing package has its own Cargo workspace, disables CUDA by
default and is not published as a supported production backend.

## Scope boundary

The integration branch is prepared from `main`, with the original research
branch retained locally. It excludes 38 files: the paused RTX 5090 launcher and
checkpoint, billion-scale orchestration and associated tests, and three GPU
extensions that have not passed device admission. No GPU experiment or monitor
is run for this review. The first-pass report remains as a record of CPU input
preparation, not a billion-scale solver result or an included runnable extension.

Historical campaign drivers remain explicitly tied to their original budgets,
device identities and evidence. They are not general launch commands for a new
machine. Benchmark JSON/CSV evidence describes generated synthetic models;
no private input data, vendor installation, license or compiled binary is added.
The review's credential-pattern scan found no matches. This scan is one review
check, not a guarantee that arbitrary future artifacts are safe to publish.

## Review and portability fixes

Certificate scratch preserves the original reduction tree, padding and first
refusal. Final-assessment reuse is opt-in and binds rollback generation plus
physical/logical iteration; deadline and failure tails recompute. Independent
original-model checks remain the acceptance authority. The README preserves
failed/uncertified counts and the scaled-tall cases where COPT is faster.

The first clean-checkout SP test run exposed missing native CPU libraries and a
fixture dependent on the local study directory/private checker. CPU acceptance
now builds six libraries from source against the local GMP 6 runtime. The
rectangular test constructs its own model and store in a temporary directory
and uses the independent source checker. Historical measured sources and data
remain preserved on the original branch; no numerical solver or checker code
is changed by these portability fixes.

All 156 SP tests then pass with zero skips in a test interpreter that refuses
private evidence reads and vendor/GPU library loading. Both the failed first
reservation and its full 720 CPU-second charge remain in local evidence.
Full native workspace acceptance and isolated Rust checks are still pending.

## Hosted checks

GitHub's initial CPU, documentation and smoke jobs have no executed steps and
report an account billing lock. Local acceptance is recorded separately; it is
not hosted success. Branch protection must remain enabled and a merge must use
the normal PR mechanism without administrative bypass.
