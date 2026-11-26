# Rigorous interval labels for synchronized auxiliary searches

This opt-in path accelerates proposal checking. It uses the same original
rational calibrated matrix, box constraints, quarter threshold and preproved
opposite-slot implication as the GMP checker. The original-model final exact
certificate and independent 1e-9 audit are unchanged.

## Enclosing the original data

`enclosure` compares the numerator and denominator of the binary64 conversion
against the original rational using integer arithmetic. The converted number
and, when necessary, its adjacent representable neighbor enclose that rational.
This applies to every matrix coefficient, H and epsilon. No numerical tolerance
is used to declare equality.

The native checker requires round-to-nearest and disabled flush-to-zero and
denormals-are-zero modes. Otherwise it asks the GMP checker to decide. Each
ordinary rounded sum or product is widened outward with `nextafter`. Exact
zero identities can skip arithmetic. Overflow, nonfinite proposals and uncertain
decisions fall back rather than creating an accepted label.

## Primal test

The checker first requires the raw dyadic vector to lie inside the inner H box.
If clipping against the exact rational H might be necessary, it falls back.
It encloses each coordinate of `y = x B` and the exact homothetic scale used by
the original checker:

`alpha = min(1, min_{y_j > 2} 2/y_j, min_{y_j < -epsilon} -epsilon/y_j)`.

For an upper-bound constraint, an interval `[lo, hi]` gives a lower scale bound
from `2/hi` when `hi > 2`, and an upper scale bound from `2/lo` when `lo > 2`.
For a lower-bound constraint, the corresponding bounds use epsilon's lower and
upper enclosures and the negated coordinate endpoints. Directed widening of
the ratios and the minimum enclose the exact alpha. Multiplying these intervals
encloses the original checker's exactly feasible scaled witness.

A coordinate is positive only when its lower enclosure is at least 1/4.
An opposite-slot witness establishes a negative label only when the oracle's
existing exact separation argument permits that implication. If a threshold
lies inside an interval, GMP resolves it; exact threshold equality is tested.

## Dual test

For the requested objective c and arbitrary dyadic u, the same rigorous bound is

`U = H * ||c - B u||_1 + sum_j (2*u_j if u_j >= 0 else -epsilon*u_j)`.

Interval matrix products, absolute values and nonnegative sums enclose U.
An upper enclosure strictly below 1/4 establishes a negative label. A lower
enclosure at least 1/4 proves that this particular dual proposal cannot establish
one. Since all contributions are nonnegative, the latter decision can stop
the residual scan early. This rejects a proposal, not the original LP.

## Scheduling and lifetime

All signed auxiliary objectives share one matrix and transpose and advance
through common 64/256/final iteration checkpoints. The larger-matrix kernel
reuses each fetched coefficient across four right-hand sides. Completed targets
are removed from the active index list. A graph reads the current active count,
so changing that count does not require rebuilding the graph.

One solve-scoped session retains the stream, events and a growing device arena
across pricing queries. Numerical states reset when the calibrated matrix changes.
Matrix preparation uploads coefficients and controls once; state zeroing stays
on device. Host buffers are passed directly to the batched checker. Only uncertain
proposals are materialized for the independent GMP fallback.

CUDA initialization can run concurrently with the first CPU geometry/market
phase. Both its duration and time waiting for completion are recorded. Complete
cold-process measurements include initialization, waiting, and session teardown;
overlap is not treated as excluded work. Pricing rounds themselves remain
sequential because later prices depend on preceding labels and wealth updates.
