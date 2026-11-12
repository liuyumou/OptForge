# DELIVERY3 research executor

Independent checker batching and device/checker preparation overlap. Numerical
modules remain imported from retained packages; the solver state machine is a
byte-exact copy of DELIVERY2. See [SPEC-0034](../../docs/specifications/SPEC-0034-delivery3.md).

Set `GPUP_DELIVERY3_VARIANT` to `control` (default), `batch`, `overlap`, or
`combined`. Optional `GPUP_DELIVERY3_PROFILE=1` records diagnostic delivery spans;
confirmation runs disable it. No public solver default changes.
