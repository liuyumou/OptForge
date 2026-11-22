# SPEC-0046 amendment 39: final isolated-host memory accounting

The completed source review distinguishes the isolated host derivative from the
public preconditioner. The isolated Pock implementation already streams one line
per worker; it does not retain the public implementation's per-row/per-column term
graphs. Formula 5's graph-based Pock estimate is conservative but unnecessarily
loose and incorrectly describes the active implementation. Preserve that formula,
its operational plans, all original reservations and observations unchanged.

After the diagnostic tail settles, refine only the prospective Pock bound for the
actual isolated source. Across four workers, retained maximum-line capacities sum
to at most twice the orientation's nonzeros plus minimum-capacity slack. Include
worker outputs, aggregate totals, old diagonals and reduction scratch. The existing
resident allowance plus explicit reduction scratch covers this stage. The separate
CPU construction-clone bound remains mandatory and sets the coupled requirement
at 64 GiB host plus 4 GiB physical headroom. No reservation is reduced in flight.

Fresh source-bound CPU contracts must verify the final bound. Bind the final
capacity source in future snapshots/freezes and retain all previous plans. No
numerical code, diagnostic executable, strict certificate, failed charge, scientific
cell identity, GPU admission or total/phase allocation changes. Final reporting
must distinguish reduced packing residency from unchanged measured CPU high-water
memory and retain the measured preparation-time regressions.
