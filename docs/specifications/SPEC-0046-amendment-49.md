# SPEC-0046 amendment 49: separate COPT GPU configuration without presolve

The approved 320000 CPU / 35000 GPU-second allocation and all physical, ownership,
idle and strict-certificate limits remain unchanged. The original thirty-cell
billion roster is already frozen and executing. Every original COPT capacity
failure, setup-only response and unsupported billion slot remains unchanged.
This amendment identifies a separate development configuration, not a retry of
any attempted scientific cell or a replacement for the original baseline.

The separate adapter uses the same installed COPT 8.0.6 library, original binary
arrays, exact C-API import and objective/dual mapping, four threads, GPU PDLP,
no crossover, MatrixTol=0, FeasTol=DualTol=1e-9 and PDLPTol=1e-12. The single
algorithmic setting change is Presolve=0. MemLimit remains 48000 MB for capacity
and full-scale work and remains explicitly soft; it is not a physical enclosure.
The source is `tools/lp_billion_copt_nopresolve.py`. Its admission has a distinct
source-bound result and preserves the original adapter unchanged.

First finish the already frozen project billion cohort. Then admit the separate
configuration using the original twelve small GPU fixtures, including exact
sparse/bounds/objective roundtrips, both objective senses, infeasible/unbounded
and preparation-deadline cases, and six generated families. Check every returned
endpoint independently against the unchanged original-model 1e-9 criterion.
The 450-second admission process contains a directly owned child cutoff at 420
seconds, preserves all failures and has no retry. Nine parameter/status/capacity contracts
must pass beforehand. Original numerical kernels and admissions remain exact. The known infeasible and
unbounded fixtures may report their correct terminal status, an explicit ambiguous
status, or an unresolved time limit; neither ambiguity nor a limit is counted as
a proof. A contradictory status or accepted optimality proof is rejected. The
feasible min/max and empty-matrix fixtures still require strict accepted optima.

Prospectively freeze each entire subsequent capacity stage, including solve,
strict endpoint checking and storage reservations: six 64 M families, the two
existing 256 M families, then the two existing 512 M families. The respective
process ceilings are 240/360/600 seconds with directly owned child cutoffs thirty
seconds earlier; requested vendor solver allowances are 90/180/300 seconds. Final
checks reserve 90/180/300 seconds. All capacity science uses development time,
all independent checks use reporting time. Failure retains the full reservation;
no missing or setup-only response admits optimization workspace. The longer
requested solver allowances are prospective and aim to observe optimization after
setup; they do not regrade or repeat any default-presolve capacity attempt.

Admission to a new billion slot requires every smaller observed path for that
family to pass supervision and demonstrate optimization iterations or a strictly
accepted optimal endpoint. It also requires an actual GPU marker and owned GPU
allocation. Use the maximum observed per-nonzero process HWM and owned GPU peak
across all observed scales, extrapolated to one billion with 15 percent growth
and fixed allowances of 8 GiB host and 4 GiB device. Retain the sampled aggregate
host peak separately and verify its constant coordinator allowance. Reject a
forecast above 128 GiB host, 80 GiB device or the 48000 MB vendor soft setting;
check the independent adapter import-array bound as well. These are empirical
admission checks, not hard bounds on opaque vendor internals. Continuous physical
guards remain authoritative. Any failed scale path keeps that family unsupported.

Freeze all six original billion families as a separate GPU lane, retaining every
unsupported cell. Supported cells use the same requested 600-second solver wall
allowance and strict final check as the original roster. Process ceilings are
900 seconds, or 1100 for wide, with thirty-second child cleanup margins. These
prospective process ceilings allow 300 seconds beyond the requested solver wall
(500 for wide), including input and teardown, and retain every interrupted cell. Include
all six supported solve, final-check and endpoint/repaired-witness storage costs
in the prospective stage reservation, plus 1200 CPU seconds for final reporting.
If the full stage does not fit remaining time, it cannot start. No allocation is
increased by this amendment. All completed-cell sources and outcomes are frozen.

Report the new configuration by name and keep its preparation/total/peak-memory
results separate from the original automatic-presolve COPT slots. Include input,
CSC conversion/import, opaque vendor solve, extraction/teardown and cold independent
final proof. Do not label adapter preparation as all vendor preprocessing. Preserve
actual wall overshoots, uncertified outcomes, missing responses and every refusal.
No public defaults, publication or certified-solve superiority claim is authorized.
