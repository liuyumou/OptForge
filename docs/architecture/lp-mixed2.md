# MIXED2 CPU reference boundaries

[SPEC-0036](../specifications/SPEC-0036-mixed2.md) defines the isolated
`research/lp-mixed2` package. The public solver and independent checker have no
new dependency on it. No CUDA context, device allocation or solver service exists
in this package. The JSON-lines executable is a differential-test interface. Admission caps both
dimensions at 65,536 and nonzeros at 4,194,304 before product allocation, so a
small sparse request cannot declare an unbounded transpose output.

## Product enclosure

Let original coefficients be a[k], widened stored FP32 coefficients be b[k], and
input FP64 coordinates be x[k]. The recurrence is
`c[k+1] = RN_FMA(b[k], x[k], c[k])`, starting from positive zero. In exact real
arithmetic, the difference from the original dot is a sum of `(b-a)*x` and each
FMA rounding error. Therefore the triangle bound is
`sum(abs(a-b)*abs(x)) + sum(abs(delta_fma))`.

The implementation computes outward bounds on each nonnegative term and sum.
For a finite rounded FMA result c, `u/(1-u)*abs(c) + min_subnormal`, with `u=2^-53`,
is a conservative bound including gradual underflow. The ratio and all positive
products/sums round outward; zero products remain exact zero. An overflowing
result or bound refuses. FP32 widening is exact, and CSR transpose traversal
uses the same coefficient array. Separate representation and rounding bounds
are checked against exact Python rational dots, alongside the combined bound.

This enclosure concerns one product and supplied vector. It does not bound
accumulated solver state error, guarantee convergence, or certify feasibility,
dual validity or optimality. FP32 subnormals require gradual underflow; no GPU
FTZ behavior has been admitted. Scaling is identity and original coefficients
remain available. Future scaling needs an explicit reversible contract.

## Window transaction

`Controller::finish` publishes candidate checkpoint bytes only for positive work,
a finite local error allowance, and at least 1% improvement in both positive
original-model primal and dual residuals. Error failure, bad audit, zero work or
stagnation restores the original bytes and permanently promotes to native.
Cancellation restores bytes without promotion. Reported physical work remains
charged after every refusal, including an attempted call after native promotion.
Counter overflow returns before any state mutation.

The checkpoint is opaque to this reference. A future executor must demonstrate
that its serializer covers iterates, averages, counters, step sizes, weights,
restart and recovery state, including signed zeros. Tests here establish byte
restoration, not completeness of a nonexistent executor's state. The deliberately
conservative progress guard may promote when one residual is already zero or
plateaus; it is an operational policy, not a proof of stagnation or convergence.
Fresh original-A audits and an independent original-model 1e-9 certificate are
required by a future solver admission. No reference API can issue a certificate.

## Reproduction and cost decision

Run `bash tools/check_mixed2_cpu.sh <new-receipt-path>` inside a new CPU resource
reservation. The script checks formatting, lint, tests, the independent rational
oracle and isolated dependencies without a device. Oracle output is exclusive:
choose a fresh path and retain earlier results. The [report](../benchmarks/lp-mixed2.md)
links the immutable cost record; `python3 tools/lp_mixed2_cost.py --verify`
recomputes it from committed portable archives without the original artifacts.
All new jobs need a new allocation once the delivered one is closed.
