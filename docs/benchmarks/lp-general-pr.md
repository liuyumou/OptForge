# General low-bit LP PR integration

The user authorizes preserving the completed results and publishing and merging
the implemented features through a pull request. The feature branch contains
eight original commits after `3377bf96eeb52d356299dfcdc27fd40abda9a921`, ending at
`0bb384b`. They deliver GPUP-9, the general sparse LP executor, actual FP4 Tensor
Cores, kernel and surrounding-work improvements, the benchmark scale design and
the COPT scale evaluation. Integration preserves their commit ancestry, numerical
sources, historical criteria, failures, missingness and scientific results.

Public solver defaults remain unchanged. The broad single-solve LP objective,
including meaningful FP4 benefit, remains active; merging research capability
does not establish broad FP4 superiority or complete its confirmation.

## Retained COPT comparison

The following table summarizes the already recorded final scale observations.
It adds no new solver run or retrospective pass criterion. These are complete
fresh-process costs through independent original-model certification on the three
coupled-family seeds at each scale, all with actual FP4 work. Times are separate
medians; speedup is the median of paired COPT GPU PDLP / our FP4x2 time ratios.

| Original matrix nonzeros | Our FP4x2 median seconds | COPT GPU median seconds | Paired speedup |
| ---: | ---: | ---: | ---: |
| 1 M | 1.458464401 | 2.044698405 | 1.365892251 |
| 4 M | 5.247641977 | 5.487860623 | 1.045776493 |
| 16 M | 21.531605286 | 21.163264272 | 0.982893007 |

Across all jointly certified cases, the FP4-configured solver's median ratios
are 1.242367612 (14 pairs), 0.938054269 (12 pairs) and 1.093671095 (six pairs).
Many of those cases use no FP4, so those ratios do not establish FP4 arithmetic
benefit. The 16 M population is capacity-selected, with all unsupported cases
retained. COPT GPU certifies 15/18 full-roster 4 M models versus our 12/18 and
certifies square31 and scpm1 where our solver does not. COPT CPU has no jointly
certified generated cases under its declared limit, so no successful-solve CPU
speedup is inferred. Our research lane includes intermediate-trajectory
serialization; COPT returns a final endpoint. Shared-host measurements are
descriptive, and the stopping-budget boundaries differ.

Sources: [scale results](lp-general-scale-results.json),
[16 M results](lp-general-scale-frontier-results.json),
[model identities](lp-general-scale-models.json), and the complete
[methods, failures and diagnosis](lp-general-scale.md). All original files remain
byte-identical. The previously committed GPUP-9 archive parts remain tracked;
the newer general-study content-addressed bundles remain local and retained.

## Integration acceptance and resources

Refresh `tools/check.sh`, isolated CPU acceptance, source/history preservation
and documentation checks. Existing source-bound GPU admission, all four
sanitizers and extracted-root numerical replay remain applicable when their
numerical source hashes are unchanged. No GPU study or scientific retry occurs.
Inspect hosted checks at the published head and merge normally without changing
or bypassing protection. The existing hosted `startup_failure` remains separate
from local acceptance; a local pass is never reported as hosted success.

A separate 16,000 CPU / zero GPU-second integration ceiling uses four slots,
16 GiB sampled RSS, unchanged one-second supervision and all 100 ms advisories.
Caps are implementation 1,000 (including 512 preparation), native 8,000,
research 2,000, reporting 4,000 and cleanup 1,000 seconds. The complete cleanup
allowance is conservatively reserved upfront for publication and closing
administration. Receipts and failed attempts are retained under
`artifacts/gpup-general-pr-v1`. The general scientific allocation remains open
and unchanged at 181311.318401148 CPU / 23462.140788896 GPU seconds.

## Final local acceptance

[PR #28](https://github.com/liuyumou/OptForge/pull/28) retains all eight original
feature commits. The refreshed full native gate passes 638 repository Rust tests,
827 Python tests, format/Clippy/dependency checks, committed-record replay,
documentation/link checks and smoke. The isolated package passes 37 Rust tests,
format and Clippy. All 2,407 other original files remain byte-identical; the four
updated navigation/handoff files preserve their historical text. Public crates,
root dependency locks and hosted workflows match remote main.

The current scientific source and both admitted host images remain exact. Hash
verification passes for all 139 local archive parts / 10,749,532,394 compressed
bytes and the retained source-bound admission/replay receipts. Existing GPU
admission, all four sanitizers and the extracted-root replay of 92,050 files /
10,457 assessments remain applicable; no numerical execution is repeated.

The [integration receipt](lp-general-pr-validation.json) binds the checks,
historical preservation and accounting. Integration is closed at
3309.763244320 / 16,000 CPU seconds, zero GPU, including the conservative 1,000
closing-administration seconds. All supervised jobs pass and cleanup is empty.
The scientific allocation and all earlier charges remain unchanged.

GitHub's [initial PR run](https://github.com/liuyumou/OptForge/actions/runs/43990482802)
reports `startup_failure` with zero jobs, matching the existing infrastructure
limitation. Protection inspection returns HTTP 403 because the repository plan
does not expose that feature. The PR is mergeable through the normal path; no
protection is changed or bypassed. The final published head's hosted status and
normal-merge receipt are retained under `artifacts/gpup-general-pr-v1` and
reported on the PR. Local acceptance is not reported as hosted success.
