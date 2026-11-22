# SPEC-0046 amendment 86: finalization admission correction

CPU v33 passes all 75 original supervisor tests, but three new finalization fault
tests detect a cleanup-scope defect. The real resource sampler includes the owned
guardian for accounting; the new cleanup observer incorrectly treated that
additional identity as a descendant to terminate. Only this job's owned guardian
was targeted. No GPU or scientific LP cell ran. Explicitly exclude the guardian
from cleanup targets while retaining it in resource accounting. The positive
slow-I/O tests must pass, and actual stall/scan/deadline failures must still fail.

Preserve CPU v33's refused settlement, absent final resource receipt, false cleanup
flag and full 960 CPU-second charge. Its original CPU journal, coordinator result,
coordinator-failure result, test log and source snapshot remain immutable. Bind
an additive cleanup proof only after every exact retained identity is absent.
The existing non-overrun recovery path supports this disposition; no new overrun
exception or rewritten failure is introduced.

Fresh CPU v34 supersedes failed v33. GPU v26 remains untouched. Plans v69–v74
retain all six cleanup dispositions and require CPU v34 / GPU v26. The complete
seven-cell timing/audit worksheet from amendment 85 remains unchanged, as do all
total and phase caps. A renewed 2400 CPU / 180 GPU admission envelope fits after
the failed charge; reserve it prospectively along with the full remaining work.
Numerical image-v11, the installed COPT library, original inputs and strict
original-model 1e-9 certificates remain exact. No scientific cell is repeated.
