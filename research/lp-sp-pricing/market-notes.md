# Exact practical market implementation

This is an implementation-specific reformulation of the finite practical expert
pool. The reference algorithm continues to use implicit expert cells and its
rational ellipsoid interface. No strongly polynomial claim is made for the
native successive-shortest-path implementation.

For positive expert weights, the market is

\[
\Phi(y)=\sum_e w_e\max(0,\max_{(i,h,a)\in e}(a-hy_i)).
\]

Give each expert an explicit outside option with demand and sign zero. Its LP
dual allocates nonnegative mass to options:

\[
\max\sum_{e,s} a_s\lambda_{e,s},\qquad
\sum_s\lambda_{e,s}=w_e,\qquad
\sum_{e,s:i_s=i}h_s\lambda_{e,s}=0.
\]

Common denominators turn all weights into integer capacities. Utility comparisons
also use a common integer price denominator, avoiding a Fraction object for every
option comparison.

## Signed-network double cover

Create two nodes per expert, two nodes per coordinate, and one zero node.
Supply each expert's positive node with its weight and demand that weight at its
negative node. For option (i,h,a), add an edge from the positive expert node to
coordinate (i,h), and an edge from coordinate (i,-h) to the negative expert node.
Both edges have cost -a. Outside-option edges go through the zero node with cost
zero. Internal capacities exceed total supply, so they never restrict a feasible
market allocation or its potential dual.

Average the two mirrored option flows to obtain each allocation. Expert flow
conservation gives its mass constraint. Coordinate flow conservation gives the
signed balance constraint. The network cost is minus twice the allocation
objective. Conversely, every feasible allocation induces a feasible symmetric
cover flow with that cost, proving equivalence.

If node potentials satisfy every residual edge inequality, define a price by
half the potential difference between its negative and positive coordinate
nodes. Define an expert height by half the potential difference between its
positive and negative expert nodes. The two option-edge inequalities imply
that this height dominates a minus h times the price. Outside edges imply a
nonnegative height. Flow/potential equality therefore gives a market optimum.

The Python boundary checks every expert's allocation mass, every signed
coordinate balance, and exact equality with the directly evaluated market.
A numerical residual or an approximate objective never substitutes for these
identities.

## Lexicographic prices and limits

The residual graph describes the full optimal potential face through difference
constraints. A shortest-path bound fixes the least feasible difference for the
next price coordinate. Add its reverse equality constraint and repeat in
coordinate order. Integer costs keep the resulting prices half-integral.
Differential tests compare the complete price vector with the independent exact
cut-LP oracle, including degeneracy and nonuniform rational weights.

The native implementation uses checked 128-bit capacities and conservative
64-bit cost/potential bounds. It has explicit scan, time and path-depth limits.
Unsupported integer ranges can use the exact cutting-plane path in automatic
mode; resource failures remain incomplete results. No failed native result is
treated as an optimal market.

## Why the current implementation stays on CPU

The original profile spent about 85–90% of its time evaluating experts through
rational scalar operations. Integer comparisons remove those allocations; the
flow formulation removes repeated epigraph LP solves. After these changes,
auxiliary labels and their exact checking dominate the larger development cases.
GPU work therefore targets concurrent auxiliary states and matrix products.
Potential updates and successive lexicographic face restrictions retain their
dependencies, and no GPU market speedup is claimed.

The [measurement report](../../docs/benchmarks/lp-sp-pricing.md) contains the
development progression and complete original-LP comparison. Component speedups
and solver superiority are reported separately.
