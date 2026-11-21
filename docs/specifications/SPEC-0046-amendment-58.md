# SPEC-0046 amendment 58: retain fixture-type compile failure

GPU-pack-quality-v4 rejects an ambiguous integer type in the new standalone
packing comparison fixture. Retain its full 1920 CPU-second charge and empty
cleanup. Annotate the fixture dimensions as usize; no kernel or solver arithmetic
changes. Fresh quality-v5 uses four build workers within the unchanged four CPU
slots and a 140-second native acceptance reservation. Previous successful full
quality runs consumed about 95–105 seconds with one build worker. Every prior
failure remains retained; allocation and phase caps remain unchanged.
