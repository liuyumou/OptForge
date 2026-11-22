# SPEC-0046 amendment 20: measured racecheck host reservation

The borrowed-storage image passes all 66 exact preparation comparisons, 60 exact
continuations and the complete memcheck suite. Its racecheck host preflight then
refuses the proposed 56 GiB declaration plus 4 GiB headroom; available host memory
is approximately 58 GiB. No memory-racecheck-v1 reservation or attempt exists.

The previous complete array-racecheck-v6 uses the same preparation CUDA, solve
CUDA, fixtures, original 20 power iterations, three analysis workers and eight-
launch synchronization setting. Its measured peak aggregate RSS is 7.604 GiB
(and peak summed process high-water marks 7.718 GiB). Prospectively declare
32 GiB host RSS for the never-started borrowed-storage racecheck. Keep all original
checks, the 600-second time ceiling, sampled-RSS supervision and 4 GiB physical
headroom. No GPU guard, solve reservation or certificate criterion is changed.
No existing scientific cell or failed reservation is repeated. Prior admission
results and every historical failure and full charge remain intact.
