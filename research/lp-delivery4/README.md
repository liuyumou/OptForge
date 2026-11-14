# GPUP-DELIVERY4 isolated cold executor

Implements [SPEC-0035](../../docs/specifications/SPEC-0035-delivery4.md).
`GPUP_DELIVERY4_VARIANT=control|candidate` selects the DELIVERY3 overlap control
or exact SHA-256 acceleration; the default is control. Both retain unbuffered
transport, independent original-model checking, identical numerical state
machines and input validation before CUDA setup. Public solver defaults stay exact.

`GPUP_DELIVERY4_PROFILE=1` enables optional hierarchical lifecycle diagnostics.
It is disabled in confirmation. Complete cold measurements end after process
exit and durable output. Prepared reuse is admitted but is not a throughput claim.

Run `bash tools/check_delivery4_cpu.sh` from the repository with its provisioned
Rust/native/Python environment. That script includes the isolated dependency policy and metadata audit rejecting
external wildcards. The task receipt launcher separately writes once into its
independent artifact allocation.
Device execution requires the pinned inherited lease and separately admitted
source-bound protocol; these commands do not release a new experiment.

[Delivery and retained findings](../../docs/benchmarks/lp-delivery4.md).
