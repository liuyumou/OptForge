# Adaptive dual-range certificate extension

The [main factorized-geometry study](lp-sp-pricing-factor.md) retains all original outcomes. Its fixed exponent 48 limited the dual base to magnitude 16, which rejected returned default-scaling COPT duals before proof construction. This additional common policy chooses a smaller exponent when needed, preserving at most 52 integer magnitude bits. The unchanged independent exact checker decides acceptance.

The policy applies to every original roster endpoint: accepted certificates are retained; only dual_base_range failures receive adaptive reconstruction; all other outcomes remain unchanged. No LP solver is rerun. This extension was specified after the range limitation was observed. Every extra cold construction and proof process is added to the original complete cost, including the original unsuccessful reconstruction. These are composed pipeline totals from phases measured at different times, without cache flushing. Corruption challenges remain separate research validation costs.

3 endpoints trigger the common rule; 3 receive exact certificates. See [full alternative-pipeline evidence](lp-sp-pricing-factor-range-results.json).

| Seed | Both timely and exact | Optimized candidate complete s | Default-scaling COPT plus certificate complete s | COPT / candidate |
| ---: | --- | ---: | ---: | ---: |
| 124401 | True | 11.310 | 8.916 | 0.788× |
| 124421 | True | 10.297 | 9.408 | 0.914× |
| 124439 | True | 10.292 | 7.755 | 0.753× |

Original raw 1e-9 assessments and native solver statuses are unchanged. These results concern a rigorously corrected implicit dual, not raw COPT certification. The additional negative-dual and zero-inverse challenges reject every accepted extension certificate; zero-inverse checks scan the full original matrix.

The main regression suite includes three adaptive-range tests: large positive null-space duals, a non-dyadic exact dual, and invalid/extreme inputs. Final resource accounting includes both studies, all failures and this extension.
