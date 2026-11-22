# SPEC-0046 amendment 82: retained capacity-report collision and corrected aggregation

All twelve startup diagnostics and seven new selected-configuration capacity
cells completed, including independent endpoint/no-endpoint audit dispositions.
The last 512 M irregular run reached 2680 GPU PDLP iterations and returned an
interrupted status without an endpoint. Its original 604.093-second native
solver elapsed time exceeds the requested 600 seconds and remains explicit.
This confirms optimization workspace, not a timely strict solution.

After all completed large chunks were removed, `copt-fair-readiness-v1` failed
because the report attempted to use `capacity` for both the forecast map and its
source binding. Preserve its original failed receipt, empty cleanup and full
240 CPU-second charge. No numerical measurement or audit is repeated.

The separate aggregation module `tools/lp_billion_copt_fair_capacity.py` retains
the original runner source unchanged and names the policy binding
`capacity_policy`. It writes the previously uncreated disposition file under a
fresh reporting reservation `copt-fair-readiness-v2`. A regression checks that
the forecast, policy source and original runner binding coexist. The source-bound
completed drivers are never run again. All settings, approval caps, physical
limits, ownership/idle guards, certificates and deadline classifications remain.
