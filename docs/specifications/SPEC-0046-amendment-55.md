# SPEC-0046 amendment 55: retain offline build-environment failure

GPU-pack-quality-v1 passes formatting but cannot find sha2 in the default offline
Cargo cache. It never compiles or executes the candidate on GPU. Retain its full
2400 CPU-second charge, source snapshot and empty cleanup. Fresh quality-v2 uses
the existing lp_general_env.sh wrapper and provisioned /tmp Cargo/rustup cache,
matching the previously successful image-v9 build command. No dependency download,
resource-cap change, numerical relaxation or scientific-cell retry occurs.
