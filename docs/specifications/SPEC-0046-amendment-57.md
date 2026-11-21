# SPEC-0046 amendment 57: preserve explicit-configuration test compile failure

GPU-pack-quality-v3 compiles the library but finds two explicit integration-test
Config initializers missing the new opt-in gpu_packing field. Retain its full
1920 CPU-second charge, raw compiler output, source snapshot and empty cleanup.
Set gpu_packing=false in both legacy-path tests and retain their existing
assertions. Fresh native quality-v4 repeats complete candidate acceptance under
a distinct reservation. Public defaults and numerical behavior remain unchanged;
no GPU candidate or scientific timing has run and no allocation cap changes.
