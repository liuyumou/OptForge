# Portable GPUP-8 CPU test fixtures

The manifest binds exact copies of eight historical metadata files and the
17,412-event ledger prefix required by the expanded-window authority. The gzip
contains only ledger JSON; no binary, vendor installation or credential is here.
These are inputs for CPU regression tests, not new campaign execution receipts.
The live ledger and all original artifacts remain unchanged.

`tools/lp_gpup8_test_support.py` builds isolated temporary trees. Authority tests
use the real authorization, accounting, journal and ledger, with a clearly
synthetic two-file source tree to exercise preserved-source/hash guards. Warp32
tests check the actual CUDA source contracts and historical numerical hashes,
using synthetic image bytes solely to test image-hash rejection. They do not
claim to reproduce the original CUDA image or whole-campaign preservation gate.
Study composition tests use the exact archived campaigns, roster and execution
metadata, with a temporary ledger and mocked authority already covered by the
authority tests. No scientific gate is reopened or reported as rerun.
