# Active Task

## C6 Clean-Checkout Verification (2026-09-13)

Objective: verify the C6 branch from a checkout with nothing prebuilt, before any
integration, as the C4, C8 and Track B branches each were.

Status: complete; the branch passes from a fresh clone and one environment-dependent
test was found and fixed by doing so.

Acceptance gate: `bash tools/check.sh` passes in an independent clone with no
`target/` directory, no provisioned HiGHS library and no provisioned device code
object. Resource budget: CPU only, no GPU workloads — which is itself part of what
is being verified.

The verification earned its place. `a_device_no_registered_extension_needs_is_refused`
passed locally and failed in the clone. With a code object present the refusal is
"no extension requires one" and names the device; without one the session fails
earlier with "no device code object at <path>", which names a path. The test was
environment-dependent, and the message was genuinely worse than the test: a caller
who asked for a device and got a message about a file cannot tell which device was
refused. Fixed by making every refusal name the device rather than by weakening the
assertion.

What the clone establishes that a local run cannot. The build script's warning fired
four times, so `cuda_native` was unset throughout and every device path compiled to
its unsupported form: this is SPEC-0010 requirement 37 and ADR-0009's "nvcc is a
provisioning dependency, never a build dependency", observed rather than asserted.
The pinned HiGHS library was built inside the clone from scratch. And the twenty
device tests reported their skips rather than failing, which is what keeps a CPU-only
host a full gate pass.

Evidence (2026-09-13): cloned with `--no-hardlinks` at `6dbaf8c` with no `target/`
present; `bash tools/check.sh` passed there in 1 minute 35 seconds, exit 0, with 300
Rust tests, 68 Python tests and 56 documentation pages — the same counts as the
working tree.

`Cargo.lock` did change across the branch, and the earlier wording here said it had
not. What it gained is the `optimizer-cuda-sys` entry, its one dependency edge on
`libc`, and the edges naming the new crate from `optimizer-cuda` and
`optimizer-schedule-examples`. No third-party crate was added: `libc` was already in
the lockfile transitively, so the workspace still resolves the same eighteen
external packages it did before, which is what `cargo deny --locked check` confirms
on every gate run.

Follow-up: the branch is ready to integrate. C6 itself is not complete: SPEC-0011's
GPU linear-programming backend is accepted and unimplemented, so the backlog line
stays open.

## C6 Bounded Launch Chunks and Host Fallback (2026-09-13)

Objective: reach SPEC-0010 requirements 27 to 30 — bounded launch chunks with a
cancellation check between them, a poisoned context that is not launched into again,
and a device fault that never becomes a solver outcome.

Status: complete. Requirement 29 takes its fall-back-for-the-run option rather than
rebuilding a context, which the specification permits and which is recorded as the
choice it is.

Acceptance gate: a 500-job neighbourhood takes four launches rather than one,
asserted against a counter; the chunked result is identical to the host's; a
pre-cancelled call launches nothing and reports cancellation; a cancelled residency
is still usable afterwards; an input error touches the device at all; the host
fallback produces byte-identical proposals; `bash tools/check.sh` passes with native
acceptance covered. Resource budget: **GPU, one device under the shared host lease**.

What had to be bounded is work, not calls, and the two chunk sizes differ for a
reason worth recording. The batch kernel is one thread per permutation, so 4,096
permutations is 4.1e7 integer operations at the largest supported shape. The
neighbourhood kernel is one block per removed job and each block's recurrence is
serial, so the same block count buys far less parallelism and takes longer; 128 jobs
is 2.6e6 dependent operations. Picking one constant for both would have made one of
them either uselessly small or unboundedly large.

Synchronizing per chunk is what makes the cancellation check mean anything, and that
is not free. Without it the launches queue and the loop finishes before any of them
has run, so the check would test a token nothing had waited on. It is also where a
kernel fault surfaces, which is why the sticky check wraps the synchronize rather
than the launch.

The measurement did not move: a 500-job neighbourhood still runs in the same time it
did as a single launch, because four synchronizes at this size cost microseconds
against milliseconds of work. That is the expected result and it is worth stating,
because a chunking change that *did* move it would mean the chunks were too small.

Requirement 29 offers two responses to a sticky fault and this takes the second.
Rebuilding a context would mean replacing one that the residency's buffers hold
through an `Rc`, which is a lifetime problem rather than a driver one; falling back
for the remainder of the run is permitted, simpler, and loses only a transient
fault's device. The cost is recorded in [known failures](known-failures.md) along
with the honest gap: the decision logic is unit-tested, and recovery from a real
sticky fault is not, because provoking one means corrupting a device.

The producer's fallback closes requirement 24's recorded gap, and the assertion is
the one that matters. The fallback is `optimizer_schedule::insertion_neighborhood`
— the CPU path this project already treats as authoritative, not a second
implementation written to match the kernel — so the two cannot drift, and the
contract asserts the proposals are *identical* rather than equally good. A caller
cannot tell which path ran, which is the definition of a fallback; the `fallbacks()`
counter is how a test can.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the twenty device tests**, exit 0.
Rust tests rose from 295 to 300 and Python remains 68; documentation remains 56
pages. `Cargo.lock` is unchanged; `optimizer-cuda` gained an `optimizer-core` edge
for `CancellationToken`, which requirement 27 names explicitly. Separately,
`bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` passed both device suites —
fourteen kernel contracts and six producer contracts — and all four sanitizers over
both binaries, with zero errors and zero hazards.

Follow-up: none blocking. What remains open on SPEC-0010 is requirement 22's
threshold, which is deliberately not implemented because a dispatch threshold is an
acceptance-shaped number that the benchmark protocol requires an ADR and an
experiment record to commit.

## C6 Device-Backed Candidate Producer (2026-09-13)

Objective: make a search reach a device. Until now the device path existed and was
verified, and nothing outside a test could use it — the same gap C8 closed for
extensions, open again for hardware.

Status: complete; `optimizer schedule solve` with a device named and
`flow-shop-neh-gpu` registered runs the neighbourhood on the device, writes a record
whose provenance names the hardware, and that record re-executes and agrees.

Acceptance gate: every device-produced candidate is feasible by `Model::evaluate`;
the producer applies exactly the best single insertion move by the host's own
computation; repeated proposals are identical; a `gpu` registry entry resolves with
a device and is refused without one, still before construction; a configuration
naming a device that no registered extension needs is refused and writes no record;
`bash tools/check.sh` passes with native acceptance covered. Resource budget:
**GPU, one device under the shared host lease**.

Where the enforcement lives took the most thought. Requirement 6 says a record must
not claim a device the run did not use, and it has two halves that cannot live in
one place. The executive can see that a device is named and no extension is
registered at all, which makes the device certainly unused — that check is
necessary and it is not sufficient, and the code says so rather than implying
otherwise. Whether a *particular* registration uses a device needs the hardware
requirement, which SPEC-0004 deliberately keeps out of an extension's declaration
and SPEC-0009 puts in the registry. So the sufficient half belongs to the surface
that resolved the registry. Splitting it felt like a smell until the alternative was
written down: putting both in the executive would mean teaching it to read registry
entries, which is exactly the coupling ADR-0008 avoided.

The registry's condition is a UUID, not a device handle, so optimizer-registry stays
free of the driver boundary. That is sound because of where the UUID comes from: the
only way to obtain one is `DeviceSession::open`, which leases the host lock, creates
a context and reads the identity back. A caller cannot fabricate `Some` without
having done all three, so "a device is selected" and "a device is held" are the same
statement.

A refactor was needed and is worth recording because it improved the code rather
than merely enabling it. The driver handles borrowed their context with a lifetime,
which a producer cannot satisfy: a `Box<dyn CandidateProducer>` has no lifetime to
borrow from. They now hold `Rc<Context>`, so a context outlives its modules, streams
and allocations by refcount rather than by the borrow checker. That is strictly more
robust — the old arrangement was correct only because every holder happened to be
borrowed from the same scope.

Two mistakes the work caught, both mine.

The first was a wrong test. I asserted the device producer is never worse than
`SchedulingProducer` and it failed on `ta051`, 4059 against 4040. The producer was
right and the test was wrong: the CPU producer runs a full sequential pass, up to one
accepted move per job with each visible to the next, while this one applies a single
best move. Comparing them compares two algorithms, and neither promises to beat the
other. The test now asserts what is actually promised — that the move applied is the
best single move, checked against `insertion_neighborhood` on the host — and the
old assertion is recorded in its doc comment so the next reader does not reinstate
it.

The second was a wrong diagnostic, found by a test helper making the obvious error.
It chose a device from the host inventory, and under `tools/gpu_job.sh` the inventory
and the driver disagree: the wrapper restricts the process to one device, so the
inventory's first entry is usually one the driver cannot see. The message was "no
device with UUID", which is true and sends a reader to check a UUID that is already
correct. There is now a separate `HiddenFromDriver` refusal naming
`CUDA_VISIBLE_DEVICES`, and `visible_uuids()` reports what the driver can actually
see, which is the list a consumer must choose from.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the fifteen device tests**, exit 0.
Rust tests rose from 286 to 295 and Python remains 68; documentation remains 56
pages. `Cargo.lock` is unchanged and one `Cargo.toml` gained one intra-workspace
edge. Separately, `bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` passed both
device suites — eleven kernel contracts and four producer contracts — and all four
sanitizers over both binaries, with zero errors and zero hazards, on an RTX 5090.

End to end on an RTX PRO 6000: a scheduling search with the device producer
registered proved optimality, recorded `gpu_uuid`, `gpu_name` and driver 580.105.08
in its provenance, and `optimizer verify` re-executed it on the same device and
agreed on every compared field.

Follow-up: bounded launch chunks with a cancellation check between them, which is
the part of requirements 27 to 30 an interrupted long device run would notice.

## C6 Device Probe and Driver Version (2026-09-13)

Objective: give the driver version a producer, under SPEC-0006 requirement 1a, and
add `optimizer gpu probe` so a caller can find out whether this build can use a
device without running a search on one.

Status: complete; discovery reports four fields, and a probe creates a real context
under the lease and reports what the driver and the code object actually provide.

Acceptance gate: discovery refuses a row without a driver version rather than
accepting a hole; a probe reads the requested UUID back through the context it
created and reports both; it resolves every kernel this build expects without
launching one; a UUID no device carries, a missing device flag, a repeated flag, an
unknown lease mode and an out-of-range timeout are each refused with exit 2 and no
report; `bash tools/check.sh` passes with native acceptance covered. Resource
budget: **GPU, one device under the shared host lease** for the device-gated tests;
the CPU gate is unchanged and still runs none of them.

Why a probe is a separate command from discovery. Discovery asks management tooling
what hardware exists and never touches the driver, which is why it needs no lease
and runs anywhere. A probe asks the driver, so it creates a context and therefore
must hold the lease. Collapsing the two would have made the cheap question expensive
and the expensive one look free.

The report keeps `requested` and `observed` as separate fields, and that is the
point of it rather than a detail. Requirement 3's check is that they are equal; a
single field would have recorded the answer while recording nothing about whether
anything was compared. The same reasoning put the kernel list in the report: the
probe resolves every entry point this build expects without launching any of them,
so a code object that loads but is missing a kernel is found here rather than by a
first launch.

Two arguments were refused where a lenient reading was available. `--lease` accepts
only `acquire` and `inherited`, and a repeated `--device` is an error rather than
last-one-wins, because a caller who named two devices did not mean either of them
and the lock permits one holder anyway.

The unsafe prohibition caught a design mistake, which is worth recording because it
was mine. The first version of the probe command set the inherited-lease environment
variable so the library would see it. `optimizer-cli` forbids unsafe and
`env::set_var` is unsafe under edition 2024, so it would not compile. The
prohibition was right on the merits, not merely in the way: a command that mutates
its own environment to signal a library is harder to follow than one that passes an
argument. The lease decision is now a `LeaseRequest` parameter, and `LeaseRequest`
is deliberately distinct from the `LeaseMode` the report carries — one is what the
caller asked for, the other is what happened, and `Auto` can produce either.

`--lease acquire` inside a wrapped job is now a bounded refusal rather than a hang.
It waits on the lock its own parent holds and gives up at the timeout, which is the
deadlock requirement 8 exists to prevent, made visible in a test run instead of a
stuck job.

What this does not do, stated because it is easy to read as further along than it
is: `Hardware::driver` in a run record is still null. That is correct rather than
outstanding. Every search this build performs is a CPU search, and SPEC-0007
requirement 9 forbids a CPU record claiming GPU execution; the field takes a value
when a search runs on a device, which is the device-backed producer's work.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the eleven device tests**, exit 0.
Rust tests rose from 277 to 286 and Python remains 68; documentation remains 56
pages. `Cargo.lock` and every `Cargo.toml` are untouched. Separately,
`bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` passed all eleven device
tests and all four sanitizers — memcheck, racecheck, initcheck and synccheck — with
zero errors and zero hazards, on an RTX 5090. A probe on the RTX PRO 6000 reported
compute capability 12.0, 188 multiprocessors, 101,376 bytes of shared memory per
block and driver 580.105.08, with both kernels resolved.

Follow-up: the device-backed candidate producer. It is what would make the
registry's unconditional refusal of a `gpu` hardware requirement worth narrowing,
and the measured crossover worth consulting; until it exists, no search reaches a
device.

## C6 Device Selection Schema Cascade (2026-09-13)

Objective: put the selected device on the search configuration, under SPEC-0010
requirements 40 and 41, so that a device run is describable by a record that
verification can re-execute — and pay the three version bumps that forces rather
than avoiding them by putting the device somewhere verification never reads.

Status: complete; `search-config-v3`, `search-record-v3` and `run-record-v2` are in
both authorities, and a configuration naming a device is refused rather than run on
the CPU.

Acceptance gate: both the Rust parsers and the JSON Schemas accept exactly the same
documents and are asserted to refuse the same four mutations; an earlier version is
refused rather than migrated; a configuration naming a GPU is refused with the
device named and writes no record; the three committed example records still
re-execute and agree; `bash tools/check.sh` passes with native acceptance covered.
Resource budget: CPU only, no GPU workloads.

Why the field is in the configuration and not in provenance. Provenance was the
cheaper answer by a wide margin: `Hardware` already has three nullable GPU fields
and no version would have moved at all. It is the wrong answer because SPEC-0005
verification re-runs a search using only the record's embedded configuration, on
purpose, so that a record cannot confirm its own result. A device recorded only in
provenance is therefore invisible to the thing that repeats the run, and a record
naming a device would be re-executed without one. The cascade is what it costs to
keep the device where a re-execution can see it.

One field moved three versions because the documents nest: a search record embeds
its configuration, and a run record embeds that search record. The solve
configuration deliberately did not move. A relaxation inherits the search's device
because SPEC-0006 requirement 6 permits one lease holder across device selections,
so a search cannot use two devices and a per-solve field could express a
configuration the lease forbids.

Nothing is migrated, and the reason is not conservatism. A version-2 configuration
is exactly a version-3 one with the `device` line deleted, so defaulting an absent
device to `cpu` looks free. It is not: a version-2 record of a device run and a
version-2 record of a CPU run are byte-identical, so a migration would have to
invent the fact that tells them apart. Both authorities refuse, and a test asserts
they refuse the same documents rather than each refusing separately.

The refusal that matters most is the one that looks like an omission. The executive
rejects a configuration naming a GPU, because no search path dispatches to a device
yet. Honouring it by quietly running on the CPU would not have been a smaller
version of the feature; it would have been a false record that *passes*
verification, because verification re-runs from the same configuration, also lands
on the CPU, and agrees — and that agreement would certify a hardware claim nothing
ever checked. The refusal names the device it refused, and the CPU configuration
differing only in that field still runs, so it is discriminating rather than a
blanket failure.

One thing nearly went wrong and is worth recording. The three committed example
records are synthetic: an all-zero revision, `dirty: false`, a fixed identifier and
a warning saying they are not measurement evidence. Regenerating them with
`optimizer search` was the obvious way to move them to the new version and would
have silently replaced all four of those properties with real ones from a dirty
working tree. They were version-bumped in place instead, with only their
configuration input's path and checksum updated, and all three still re-execute and
agree.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the eight device tests**, exit 0.
Rust tests rose from 273 to 277 and Python from 63 to 68. Documentation remains 56
pages. `Cargo.lock` and every `Cargo.toml` are untouched.

Follow-up: the surfaces that make the field do something — `optimizer gpu probe`,
the driver version SPEC-0006 requirement 1a needs, a device-backed candidate
producer, and narrowing the registry's unconditional refusal of a `gpu` hardware
requirement. Until one of those lands, the device field is honoured only by being
refused.

## C6 Device Boundary and Batched Schedule Evaluation (2026-09-13)

Objective: implement SPEC-0010's device path far enough to answer the question the
whole capability exists for — whether a device agrees with the host exactly, and
where the crossover is — without granting the device any authority.

Status: complete for the boundary, the kernels and the evidence; incomplete for the
surfaces that would let anything outside a test reach a device. Both halves are
recorded in [known failures](known-failures.md) rather than one of them implied.

Acceptance gate: device makespans equal `optimizer_schedule::makespan` exactly, at
tolerance zero, over the whole ADR-0011 sweep; the device neighborhood equals both
the accelerated CPU path and a full recomputation; a repeated evaluation is bitwise
identical; a residency uploads once, asserted against a counter; a nonexistent UUID
and an absent code object are each refused by name; the ordinary gate stays CPU-only
and green with no device. Resource budget: **GPU, one device under the shared host
lease**, which is the first task in this project whose budget is not CPU only.

The boundary is `dlopen`, not a link. `optimizer-cuda-sys` opens `libcuda.so.1` and
resolves about twenty entry points, so `cargo build --workspace --all-features` keeps
working on a host with no toolkit and no device, and an absent driver is a typed
`DriverUnavailable` rather than a link error. That is what makes requirement 37
reachable rather than aspirational, and it added no third-party crate: `libc` was
already in the lockfile transitively. `optimizer-cuda` keeps `unsafe_code = "forbid"`
and keeps discovery, the lease and residency, so the crate every GPU consumer already
depends on did not become unsafe.

Both kernels are pure `unsigned int`, and that choice is forced twice over. The
hardware runs FP64 at one sixty-fourth of FP32 and issues integer and
floating-point instructions on one pipeline, so integer code runs at the full lane
rate. And the head and tail tables are 80,000 bytes at 500 jobs by 20 machines,
inside the 99 KB a block may address at compute capability 12.0, where 64-bit tables
would be 160,000 and would not fit on any block of this hardware. Both numbers were
checked rather than assumed: the driver reports the 99 KB limit and `ptxas -v`
reports 31 registers with zero spill for the batch kernel, inside the 42 that 48
resident warps allow.

Agreement is exact. Not "within a tolerance" — the assertion is `assert_eq!` on
`u32` values, over 64 permutations of each of the twelve instances and over every
job of every instance's neighborhood, plus a full cubic recomputation on the
twenty-job instances so the two head-and-tail implementations cannot share a wrong
idea of what an insertion costs. This is the strongest form of the CPU/GPU agreement
evidence Stage 4 asks for, and it is available only because the arithmetic is
integer; SPEC-0011's floating-point path will not have it.

The crossover is measured and both of its findings are inconvenient. The device
loses at twenty jobs by a factor of four, crosses over at roughly fifty, peaks at
16x on 200x20 — and then falls back to 9.5x at 500x20, because the 80 KB tables
leave one block resident per multiprocessor and two threads build the recurrence
while 254 wait. Context creation costs about 148 ms, which dwarfs every other number
in the table including the largest CPU time. The losing row and the falling tail are
both why the table is believable: SPEC-0010 names the first as the expected outcome,
and a sweep stopping at 200 jobs would have reported a monotonic trend that does not
hold. The full table is in [known failures](known-failures.md).

What is deliberately not done: the max-plus scan that would parallelise the
recurrence across machines. It is named in the kernel comment and left undone,
because correctness came first and an unmeasured optimisation would have had no
baseline to be measured against. Now it has one.

Device tests are opt-in behind `AI_OPTIMIZER_GPU=1`. Every earlier task record in
this project states "CPU only, no GPU workloads", and a suite that silently took the
host lease and ran kernels would have made those records false; it would also contend
on a lock that permits one holder for the whole host. The ordinary gate therefore
reports eight explicit skips naming the variable, which is the same shape as the
native-library skip and is never counted as coverage.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the eight device tests**, exit 0.
Rust tests rose from 253 to 273 and Python remains 63; documentation remains 56
pages. `Cargo.lock` gained `libc` as a direct dependency of the new crate and nothing
else. Separately, `AI_OPTIMIZER_GPU=1 bash tools/gpu_job.sh <uuid> cargo test
--release -p optimizer-cuda --test device` passed all eight on both an RTX 5090 and
the RTX PRO 6000, under an inherited lease. No device test has run in CI, because the
labeled runner is still not provisioned, and that is recorded rather than glossed.

Sanitizers (2026-09-13, added after the boundary landed): `bash tools/gpu_check.sh`
under the wrapper runs the device suite and then all four `compute-sanitizer` tools.
memcheck 0 errors, racecheck 0 hazards, initcheck 0 errors, synccheck 0 errors on an
RTX 5090. Racecheck was the one worth having: the neighborhood kernel has two threads
writing disjoint halves of one dynamically sized shared array while 254 others wait on
a barrier, which is exactly the shape a reviewer cannot check by reading. The script
refuses to run without an inherited lease rather than taking one, so it cannot escape
the wrapper that names a single device.

Follow-up: the schema cascade — `device` on the search configuration, and the
`search-config-v3`, `search-record-v3`, `run-record-v2` versions it forces — then the
CLI probe and the device-backed producer, then `compute-sanitizer`. Nothing reaches a
device from outside Rust test code yet, which is the same gap C8 closed for
extensions and is open again here.

## C6 Scale Split (2026-09-13)

Objective: add a frozen flow-shop split that spans published instance shapes, so the
crossover SPEC-0010 requirement 22 makes the CPU default depend on can be located
rather than merely bounded from below.

Status: complete; ADR-0011 is accepted, twelve instances are committed with their
derivations, and the manifest validates under both authorities.

Acceptance gate: the manifest validates against the SPEC-0007 schema; every committed
document is reproduced from its recorded seed by an independently written generator
and matches its checksum; the reproduction check is shown to fail for a wrong seed
and for a transposed loop order; the development subset is byte-identical to before;
`bash tools/check.sh` passes with native acceptance covered. Resource budget: CPU
only, no GPU workloads.

Why a new split rather than a larger one: SPEC-0008 requirement 24 and the benchmark
protocol both require a decision record before a split changes, and the development
subset's own documentation says enlarging it is such a change. Enlarging it would
also have altered the split a completed capability's evidence cites, for a reason
that has nothing to do with that capability. ADR-0011 therefore adds a split and
leaves C5's untouched.

Why one instance per shape rather than ten: the two splits answer different
questions. C5 asks whether an encoding and a recurrence are correct, and correctness
does not vary with shape, so ten instances of one shape exercise the same paths ten
times and that is the right sample. C6 asks how cost grows with shape, so the sample
has to move along the axis that varies. Ten per class would have committed twelve
times the bytes to answer a question about within-shape variance that nothing in C6
asks — and would have invited averages over a split never designed to support them.

The smallest shape is in the split deliberately. Twenty jobs by five machines is
where a device is expected to lose, so it is the crossover measurement's own
falsification check: a report showing the device winning everywhere is evidence the
measurement excluded transfers, not evidence the device is fast. A sweep starting at
the large end could not produce that signal.

One property of the source caught a wrong assertion before it was written. Taillard
reuses time seeds across classes — `ta051` and `ta071` are both 1539989115 — so the
development subset's "seeds must be unique" assertion is true only within one shape.
Carrying it over would have failed on the published table itself rather than on a
mistake. Both the Rust and the Python contracts now assert uniqueness of the seed
together with its shape, and the reason is recorded beside them.

The seed table was transcribed from the same OR-Library source the development subset
cites, and the ten seeds already in the repository matched it exactly, which is a
cross-check on both rather than on neither.

With the split in place the Phase 1 measurement was retaken over all twelve
instances, replacing the earlier table that reported shapes without naming instances.
The numbers are materially unchanged, which is the expected result — processing times
are drawn from the same distribution regardless of seed — but the rows now name
instances that exist. The full table is in [known failures](known-failures.md).

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips**, exit 0. Rust tests rose from 252 to 253 and
Python tests from 60 to 63; documentation rose from 55 to 56 pages, which is ADR-0011
and nothing else. `Cargo.lock` and every `Cargo.toml` are untouched. The tracked
instance documents add roughly 280 KB, which is the cost of checkable provenance.

Follow-up: SPEC-0010's device phases. The next is the CUDA driver boundary and the
provisioning script, which must leave an ordinary `cargo build` working on a host
with no toolkit and no device.

## C6 Tuned Flow-Shop Baseline (2026-09-13)

Objective: implement Taillard's exact head and tail acceleration inside `neh` and
`insertion` so that Stage 4's entry condition — baselines are tuned before any
intervention is measured — holds before any device work is measured against them.

Status: complete; both heuristics score insertion positions from head and tail
arrays, the returned permutations are asserted identical to the pre-change
algorithm's, and the measurement is recorded.

Acceptance gate: every existing SPEC-0008 contract passes unchanged; a new contract
test compares both heuristics against the pre-change algorithm over the fixed grid
and all ten frozen Taillard instances and requires the same permutation rather than
the same makespan; that test is confirmed able to fail; `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, no GPU workloads.

Why this first, before any kernel: the pass being replaced was `Theta(n^3 m)`, and a
device measured against it would have been measured against the clone-and-re-evaluate
loop rather than against the algorithm. That is the failure mode Stage 4's entry
condition exists to prevent, and it would have been invisible in the result: a large
speedup is exactly what a strawman baseline produces.

Where the acceleration lives is a contract question rather than a style one. The
value it computes is a makespan, and SPEC-0008 requirement 8 makes the recurrence
module the sole authority on what a schedule costs by keeping it architecturally
independent of everything that proposes one. Putting head and tail arrays in
`heuristic` would have given a heuristic its own cost model that happens to agree,
which is the shape of argument requirement 8 exists to refuse. They are in
`evaluate`, and `head[i]` is by construction the row `partial_completion_times`
would leave after `i` jobs.

The assertion is on permutations, not costs, and the difference is load-bearing.
Requirement 17 fixes which of several tied permutations a caller receives, so two
implementations can return different sequences of equal makespan and a
cost comparison would pass. The test therefore compares sequences, and it was
confirmed able to fail by relaxing the insertion tie-break from strictly-less to
less-or-equal — the exact mistake this rewrite invites, because it is the rewrite
that moves that comparison. Under that mutation the new test fails and
`construction_is_deterministic_including_under_ties` still passes, which is the
evidence that the existing suite could not have caught it: a deterministic wrong
answer is still deterministic.

`insertion` stays sequential. An accepted move is visible to the next job, so the
jobs cannot be scored independently of one another, and only the scoring of one
job's positions is accelerated. This is worth stating because the obvious next
optimization — evaluate all removals in parallel — would silently change which moves
the pass accepts, and it is the reason the device workload SPEC-0010 specifies is a
new producer rather than a faster `insertion`.

Measured on the development host, release build, best of three after a warmup, with a
0.41% noise floor from an identical binary. The full table is in
[known failures](known-failures.md). A 100-job, 20-machine improvement pass falls
from 32.66 ms to 0.92 ms, and a 200-job, 10-machine pass from 98.87 ms to 1.88 ms;
the ratio grows from roughly 3x at 20 jobs to roughly 50x at 200, which is what an
`O(n)` factor should do. The smallest instance is in the table on purpose: a single
large instance would have supported almost any claim about the shape of the
improvement.

What the numbers are not: a benchmark result or evidence. They are a development
diagnostic on one host, comparable only against another run of themselves, and
SPEC-0008 requirement 26 continues to forbid this slice recording a performance
claim. What they do change is C6's starting position, and not in a convenient
direction: a device now has to beat 23.86 ms of tuned single-threaded CPU work at 500
jobs rather than the several seconds the naive pass would have taken, so the
crossover will sit further out than it would have.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips**, exit 0. Rust tests rose from 251 to 252, the
one new test being the naive-comparison contract; Python tests remain 60 and
documentation remains 55 pages. `Cargo.lock` and every `Cargo.toml` are untouched: no
crate was added and no dependency edge changed.

Follow-up: SPEC-0010's remaining phases. The next dependency-ready one is the scaled
workload, because a crossover measured only on the frozen 20-by-5 subset would report
that the CPU wins and would establish nothing about where the crossover lies.

## C6 Heterogeneous Computation Specification (2026-09-13)

Objective: write and accept the C6 contracts before any public GPU or
backend-selection API exists, as required by AGENTS.md, CONTRIBUTING.md and the
Stage 4 scope. No C6 behavior is implemented by this change.

Status: complete; SPEC-0010, SPEC-0011, ADR-0009 and ADR-0010 are accepted and the
project records that reference C6 are synchronized.

Acceptance gate: each specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation and link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and **unchanged test counts**, because no behavior
changes. Had either count moved, this change would be doing something it claims not
to. Resource budget: CPU only, no GPU workloads; the device inventory was read once
through `nvidia-smi` for the hardware table below, which creates no CUDA context and
needs no lease.

Scope decided before implementation: C6's backlog line bundles two distinct
contracts, and CONTRIBUTING.md mandates one complete vertical slice, so they are
separated. SPEC-0010 owns heterogeneous computation itself — device selection,
residency, batching, transfer timing, arithmetic width, lease ownership, fallback,
cancellation, reset recovery and equivalence — and the batched integer schedule
evaluator that is its first workload. SPEC-0011 owns the GPU linear-programming
backend, which needs a capability concept on the solve contract that nothing in C1
through C8 required. Both are C6; neither is complete without the other, and the
first can be accepted, implemented and measured while the second is still a draft.

Why two decision records: they authorize different things. ADR-0009 amends
ADR-0003's single-unsafe-boundary rule, which is a workspace-wide structural change
and the same blocker C3, C8 and C9 each recorded rather than crossed. ADR-0010
decides that an approximate first-order solution never carries mathematical
authority, which is a numerical-authority decision that would still be needed if the
device were a CPU. Bundling them would let approval of the second imply approval of
the first.

The development host was observed with three Blackwell devices, compute capability
12.0, under driver 580.105.08 and CUDA 13.0.88: two GeForce RTX 5090 with 32,607 MiB
each and one RTX PRO 6000 Blackwell Server Edition with 97,887 MiB. This is recorded
because four properties of that compute capability are load-bearing in SPEC-0010's
requirements rather than incidental to them, and a reader checking the requirements
on sm_100 hardware would find different numbers: FP64 runs at one sixty-fourth of
FP32; INT32 and FP32 share one execution pipeline, so integer code runs at the full
lane rate; a thread block may address at most 99 KB of shared memory; and thread
block clusters are accepted by the assembler while `cluster.sync` degenerates to a
no-op, which is a silent-failure mode rather than a missing feature.

Three decisions inverted what the roadmap paragraph assumed, and each is recorded in
the contract that made it rather than only here. The first workload is integer
because of that FP64 ratio and that shared pipeline, which also means its CPU/GPU
equivalence is an exact identity at tolerance zero rather than an agreement within a
tolerance — the strongest form of the agreement evidence Stage 4 asks for, available
only because the arithmetic is integer. The same ratio does *not* disqualify GPU
linear programming, which is the opposite of what a peak-throughput reading suggests:
a sparse matrix-vector product is bounded by memory bandwidth at this intensity, with
roughly fivefold headroom before the FP64 rate could bind, so first-order methods are
viable here and factorizing ones are not. And "approximate results remain candidates
or warm starts until justified bounds exist" is met by constructing the justification
rather than by deferring it, because the justification is short and deferring it would
have left the backend's value impossible to evaluate except on throughput.

Two prerequisites were found while reading the code and are recorded in
[known failures](known-failures.md) rather than absorbed. The flow-shop heuristics
evaluate every insertion position by cloning the sequence and re-running the whole
recurrence, which is Theta(n^3 m) where Taillard's head/tail acceleration is
Theta(n^2 m); that was the right choice for C5, which forbids performance claims, and
it becomes a strawman the moment a device is measured against it, so Stage 4's entry
condition requires it be tuned first. And the frozen C5 subset is 20 jobs by 5
machines, roughly 1.3e4 integer operations for a full construction, so a crossover
measured only there would report that the CPU wins and would have established
nothing about where the crossover lies.

One correction was made during drafting and is worth recording because it nearly
shipped. An early draft claimed the contract needed no schema version, on the grounds
that a `device` field already existed. It does — in `run-config-v1`, which is the
benchmark manifest's configuration, not the search configuration a run record embeds.
A device recorded only in provenance would describe a run that `optimizer verify`
could not repeat, because SPEC-0005 verification reads only the record's embedded
configuration. SPEC-0010 requirements 40 and 41 therefore accept the version cascade
this actually costs: `search-config-v3`, `search-record-v3` and `run-record-v2`. The
solve configuration stays at version 1, because SPEC-0006 requirement 6 permits one
lease holder across device selections, so a search cannot use two devices and a
per-solve device would be a configuration able to express something the lease forbids.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips**, exit 0, in 29 seconds. Rust tests remain 251
and Python tests remain 60, which is the acceptance gate for a contract with no
behavior: had either moved, this change would be doing something it claims not to.
Documentation moved from 51 to 55 pages, which is the four new contract documents and
nothing else. `cargo deny` reports advisories, bans, licenses and sources ok with no
lockfile change, because no crate was added; `optimizer-cuda-sys` and its `libc`
dependency arrive with the implementation, not with the contract.

Expected changes: docs/specifications/SPEC-0010-heterogeneous-computation.md,
docs/specifications/SPEC-0011-gpu-lp-backend.md,
docs/decisions/ADR-0009-cuda-driver-boundary.md,
docs/decisions/ADR-0010-certified-gpu-lp.md, state/backlog.yaml, AGENTS.md,
state/known-failures.md, implementation-plan.md, wiki/status.md, README.md,
docs/architecture/overview.md, docs/architecture/testing.md, docs/operations/gpu.md,
cuda/schedule_eval/README.md, the forward references in SPEC-0006 and SPEC-0009, and
this record. No CHANGELOG.md entry: the changelog records user-visible changes and an
accepted contract with zero behavior is not one, matching the C2, C5 and C8
specification commits.

Also corrected here rather than left to be decoded: SPEC-0006, `docs/operations/gpu.md`
and `cuda/schedule_eval/README.md` deferred kernel work to a milestone named M5, which
the roadmap later renamed C6. Nothing else in the repository uses that name, so those
references pointed at a milestone a reader could not look up.

Follow-up: SPEC-0010's implementation phases, beginning with the tuned CPU baseline
that Stage 4's entry condition requires before any intervention is measured.

## Local Track B Integration (2026-09-12)

Objective: verify the Track B node-path branch from a clean checkout, integrate it
into local main, and delete the feature branch after confirming its commits are
retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip e8fcd7b; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-12): the branch was cloned with `--no-hardlinks` and no `target/`
directory present, and `bash tools/check.sh` passed there in 2 minutes 3 seconds
with **zero test skips**, building the pinned HiGHS 1.11.0 library inside the clone
and running 251 Rust and 60 Python tests. main fast-forwarded from 5beccfd to
e8fcd7b with no conflicts and no history rewriting; `git diff e8fcd7b main` is
empty, `git merge-base --is-ancestor` confirms the reviewed tip is retained, and
`git branch -d` removed the fully merged branch. The bootstrap smoke was rerun on
the integrated revision, recording e8fcd7b with `dirty: false`.

`Cargo.lock` and `Cargo.toml` are untouched by the whole branch. No crate was
added and no dependency edge changed, which is why this integration did not need
the stronger justification the C4 and C8 clean-checkout runs did — it was run
anyway, because `Model::rebound` is new public API and the branch rewrote a path
every search takes.

One item was found and fixed before integration rather than carried onto main.
SPEC-0001 gained requirement 2a in 5fe8ba3, but its review marker still named
9e6dc86 — a GitHub synchronization record that never touched the file — so the
specification claimed review at a revision predating a normative requirement it
now contains. This is the same staleness 95c1d81 and f0af453 corrected for C8 and
C5. Worth recording is how nearly it was missed: an audit comparing every marker
against its file's last-change commit reported all eighteen specifications and
ADRs as stale, which is a useless answer, because the commit that sets a marker is
itself a change to the file and no correct marker can ever match. The check was
discarded and the one real case identified by reading the history instead.

No remote refs were changed. main is now 13 commits ahead of origin/main and
remains unpushed pending the maintainer's authorization; the publication state is
recorded in [known failures](known-failures.md).

Follow-up: C6, heterogeneous computation and GPU feasibility, is the next
dependency-ready capability and still has no accepted specification. Write one
before introducing any public GPU or backend-selection API. The two deferred
per-node items — the constraint clone in `node::relaxation` and cross-node `Highs`
instance reuse — are recorded in [known failures](known-failures.md) with the
measurement each would need.

## Track B: Node-Path Measurement and Waste Removal (2026-09-12)

Objective: make solver timing measurable, then remove work the branch-and-bound
node path does and discards, without changing any conclusion.

Status: complete; the harness, all five removals and the multi-node gate fixture
are in place and gated. Every item this track set out to do is done, and the two
it declined are recorded below with their reasons.

Acceptance gate: every compared field and node counter is identical before and
after each change, asserted by the harness rather than by eye; every diagnostic
whose text is touched is pinned byte-exactly by a test written against unmodified
code; and `bash tools/check.sh` passes with native acceptance covered after each
commit. Resource budget: CPU only, no GPU workloads.

There was no way to measure a solver change before this. `benches/` held a
placeholder and `tools/benchmark_smoke.py` times `optimizer hello`. The bottleneck
ranking recorded in the plan was therefore static analysis, and the first task was
to replace it with numbers.

The unit of work is a fixed node budget with `time_limit_ms` null, over ta001 to
ta003 from the frozen Taillard set. A time limit would couple the outcome to host
speed, so before and after would explore different trees — the comparison would be
meaningless and the ten fields SPEC-0005 requirement 11 compares would
legitimately move. A node budget holds the work constant, and every run terminates
at the limit and claims nothing.

Measured, minimum of three runs after a warmup, release build, same host:

| change | ta001 | ta002 | ta003 |
| --- | --- | --- | --- |
| baseline | 8028.9 ms | 4186.1 ms | 5369.7 ms |
| basis extracted only on request | -5.8% | -10.4% | -8.9% |
| evaluation diagnostics built lazily | -11.5% | -22.5% | -17.3% |
| structural diagnostics built lazily | -1.0% | -3.5% | -2.4% |
| candidate borrowed when already canonical | -1.3% | -2.3% | -1.8% |
| node relaxation rebounded, not rebuilt | -0.3% | -0.7% | -0.4% |
| **cumulative** | **-18.8%** | **-35.0%** | **-28.1%** |
| *noise floor, identical binary* | *0.1%* | *0.2%* | *0.1%* |

The noise floor is in that table on purpose. The last row of real work is
-0.3% to -0.7% against a repeat-measurement spread of 0.1% to 0.2%, so it is
roughly two to three times noise and no more. Reporting it alone would overstate
it; reporting it beside the floor lets a reader judge it. The first three items
are large enough that the distinction does not arise.

What the numbers are not: they are a development diagnostic, not evidence. The
tool records `"claim": "none"`, defines no threshold, and is comparable only
against another run of itself on the same host. Nothing here is a benchmark result
and no performance property is claimed of the engine.

The largest single item was pure waste. Node relaxations are always continuous, so
the backend extracted an LP basis on every node; extraction computes the model's
canonical fingerprint, which serializes the entire model with
`serde_json::to_string_pretty`. The encoded ta001 model is 567,565 bytes, so a
256-node search serialized and discarded roughly 145 MB — to build a value
`Backend::solve` dropped on the next line and that SPEC-0003 requirement 23
forbids reusing anyway.

The second was diagnostics nobody reads. `checked` took `&str`, so `expression`
formatted about four `String`s per matrix nonzero on the success path and
`check_bound` two to three per call. At 5,175 nonzeros and two to three
evaluations per node that is tens of thousands of allocations per node for text a
valid model never produces. `Model::new`'s per-nonzero context had the same shape
and is on the same path, because `node::relaxation` rebuilds and revalidates a
model per node.

The last two were the smallest and are worth recording for what they cost rather
than for what they saved. `Candidate::canonical` cloned and re-sorted a candidate
a backend had just built by iterating the model's own sorted variables; it now
returns `Cow` and borrows when the input is already canonical. `node::relaxation`
went through `Model::new`, which re-sorted and revalidated every row and the
objective once per node for data the node did not touch; it now goes through
`Model::rebound`, which validates the supplied bounds and refuses any variable
list that is not the original's IDs.

That refusal is the whole basis for skipping the row checks, and it is stated as
SPEC-0001 requirement 2a rather than left implicit in code. The skipped checks
decide two things — coefficients are finite, and every term names a variable the
model has — and the first is carried from a document that already passed while the
second is exactly what the ID requirement preserves. This follows how SPEC-0003
requirement 12a and SPEC-0004 requirement 9a were recorded when implementation
found a rule the contract had not stated. No ADR: the change is strictly narrowing
and reverses nothing accepted.

Method worth keeping: characterization first. Eleven tests pinning the byte-exact
text of every diagnostic these commits touch were written and passed against
unmodified code before any of it moved, and the two candidate-canonicalization
contracts were written the same way, against the clone-always implementation. Three
of the eleven were wrong on the first attempt in an instructive way — the fixtures
aimed at a constraint-level message and hit the variable-level one, because
variables are checked first. Discovering that from a failing characterization test
is the cheap version of discovering it from a changed error message in production.

Every behavior change here was also verified by reinstating the defect rather than
by assertion alone. An unconditional canonical fast path fails the signed-zero
contract with bits 9223372036854775808 against 0 and takes three pre-existing
contracts with it; disabling `rebound`'s ID refusal fails the refusal contract.

Two traps avoided rather than survived. `checked` returns `zero(value)`, not
`value`, and that negative-zero normalization is observable through
`VariableCheck.value` and therefore every serialized validation report; a lazy
rewrite that returned the raw product would have changed committed records. The
same trap reappeared in the candidate fast path, where borrowing a candidate
holding `-0.0` would publish a different number than the owned path does, which is
why the fast path tests for negative zero and not merely for sorted-and-distinct.
And the harness compares conclusions itself and fails outright if any moved, so a
timing win accompanied by a counter change is reported as a bug rather than a
speedup.

A blind spot found while closing the track, and the reason the last commit is a
test rather than a removal: both committed run records reported `nodes_explored:
1`. `tools/verify_committed_record.py` is the only check that re-executes a record
against a later build, and it had therefore never descended past the root node —
while every change on this branch was on the per-node path. A generated 5x3
instance exploring 37 nodes, pruning 23 by bound and proving optimality now closes
that. Its counters are asserted against the committed record rather than the
verdict, which does not carry them, so swapping in a single-node record fails
loudly instead of passing quietly.

Not attempted, and why: reusing the `Highs` object across nodes is legal under
requirement 23, which forbids reusing a *basis* rather than the instance, and is
the obvious next item — deferred pending the measurement that now exists. The
constraint and objective clone in `node::relaxation` also remains and is now
likely the dominant per-node cost, since `rebound` removed the validation beside
it but not the copy; eliminating it needs shared ownership inside `ModelDocument`,
which is a public type change with a wide ripple and belongs behind its own
measurement. Cross-node warm start and any parallelism remain out of scope; both
are forbidden by accepted contracts (SPEC-0003 requirement 23, SPEC-0002
requirement 5) and need their own decision records.

Evidence (2026-09-12): `bash tools/check.sh` passed after each of the three
commits with the pinned HiGHS 1.11.0 library linked and **zero test skips**, exit
0. Rust tests rose from 247 to 251 — two candidate-canonicalization contracts and
two `rebound` contracts — while Python tests remain 60 and documentation 51 pages.
The last commit adds a gate step and fixtures rather than contracts, so it moves
neither count, which is the expected result for what it claims to do.

Follow-up: Track B is closed. C6, heterogeneous computation and GPU feasibility,
is the next dependency-ready capability and still has no accepted specification;
write one before introducing any public GPU or backend-selection API. The two
deferred per-node items above are recorded in
[known failures](known-failures.md) rather than carried as intentions.

## Local Track A Integration (2026-09-12)

Objective: verify the C8 follow-up branch from a clean checkout, integrate it into
local main, and delete the feature branch after confirming its commits are
retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 8cddb44; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-12): the branch was cloned with `--no-hardlinks` and no `target/`
directory present, and `bash tools/check.sh` passed there in 1 minute 33 seconds
with **zero test skips**, building the pinned HiGHS 1.11.0 library inside the clone
and running 234 Rust and 60 Python tests. main fast-forwarded from dfdc245 to
8cddb44 with no conflicts and no history rewriting; `git diff 8cddb44 main` is
empty, `git merge-base --is-ancestor` confirms the reviewed tip is retained, and
`git branch -d` removed the fully merged branch. The bootstrap smoke was rerun on
the integrated revision, recording 8cddb44 with `dirty: false`.

One process note worth recording rather than hiding: the first commit on this
branch used `git add -A` and captured all of Track A under a message describing
only the review-marker fix. It was split into two honest commits before anything
was integrated. The branch was local and unpushed, so no shared history was
rewritten.

Publication state changed outside this work. The maintainer pushed the work
through `dfdc245` to origin, so every milestone up to and including C8 is now
published. Records dated before that push describe main as unpushed pending
authorization; they were accurate when written and are left as written rather than
backdated. [Known failures](known-failures.md) now carries the current state. The
two Track A commits are local and unpushed, and remain so pending the maintainer's
own push.

Follow-up: Track B, the measurement harness and the behaviour-preserving waste
removal on the per-node path, is next. C6 still has no accepted specification.

## C8 Follow-Up Items (2026-09-12)

Objective: close the three items the C8 integration record left open — SPEC-0009
requirement 14's overstated wording, requirement 20's possibly-unreachable
verification branch, and the stale C5 review markers.

Status: complete; the full gate passes with native acceptance covered.

Acceptance gate: requirement 14 is narrowed to what the implementation can
actually guarantee; requirement 20's branch is either reached by a test or
recorded as unreachable with a decision; the C5 markers name the implementing
revision; and `bash tools/check.sh` passes with native acceptance covered.
Resource budget: CPU only, no GPU workloads.

Requirement 20's branch is reachable, and the earlier doubt came from testing it
the wrong way round. Restamping the *registry* is refused by the declaration check
first, because the extension still reports the version it always did — the existing
test's own comment says so. The rule the requirement describes runs the other
direction: a record naming a version the current build no longer declares, which is
what happens when a record outlives the build that produced it and the extension's
version has since moved. A new contract restates the version in the record's
extension summary, leaves the registry alone so resolution succeeds, and reaches
the comparison. Disabling the branch makes it fail, so it is not vacuous. Nothing
was deleted.

That diagnosis found a second defect, in the acceptance gate itself.
`tools/verify_committed_record.py` restamped the registry and then asserted only
that `9.9.9` appeared in stderr. Resolution's declaration-mismatch message contains
that string too, so the check passed on the wrong error and never reached
requirement 20 — while its comment claimed to "isolate the version refusal". The
gate now covers both rules separately, each asserting the message its own rule
produces, and the requirement 20 case is checked across a commit boundary as
SPEC-0009's acceptance section says it is. Verified by disabling the branch: the
gate step now fails where it previously passed. This is the same class of defect
the C8 clean-checkout run found — a check passing for a reason other than the one
it names — and it is worth recording that it was found by pulling on a thread
about a *different* requirement.

Requirement 14 was wrong as written rather than under-implemented. It claimed
resolution never constructs a refused extension, but `Extension::declare` is the
authority a declaration mismatch compares against and the provider is what supplies
the role, so both mismatches are necessarily decided after construction. The rule is
now split: requirement 14 governs invocation and holds everywhere; requirement 14a
governs construction and names the refusals decided before it — a gpu hardware
requirement, an unsatisfied data requirement, an unpermitted experimental entry and
a failed promotion check are all decided before the provider is consulted, while an
unprovided identity consults the provider but constructs nothing. The
implementation did not change, and the acceptance mapping now says which refusals
can be asserted against a construction counter and why the others cannot.

Evidence (2026-09-12): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0. Rust tests
rose from 233 to 234, the requirement 20 contract. Python tests remain 60 and
documentation 51 pages.

Follow-up: C6 remains the next capability and still has no accepted specification.
The remaining thin spots in SPEC-0009's acceptance mapping — requirement 20's
nondeterministic-record case, requirement 21's positive diagnostic case,
requirement 22's forfeited registry-backed record, `optimizer search --registry`
with a non-empty policy, and the document-level parse cases — stay recorded in
[known failures](known-failures.md); each needs a fixture this build does not have.

## Local C8 Integration (2026-09-12)

Objective: verify the feat/extension-registry branch from a clean checkout,
integrate it into local main, and delete the feature branch after confirming its
commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 7757af6; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-12): the branch was cloned with `--no-hardlinks` and no `target/`
directory present, and `bash tools/check.sh` passed there in 2 minutes 2 seconds
with **zero test skips**. That run built the pinned HiGHS 1.11.0 library from the
checksum-verified upstream archive inside the clone, producing `libhighs.a` at
10,186,956 bytes, ran 233 Rust and 60 Python tests, re-executed the committed run
records against the freshly built binary, validated 51 documentation pages, and
passed cargo-deny, artifact validation and bootstrap smoke.

This clean-checkout pass is the acceptance evidence for the integration, and it was
not a formality. The first attempt **failed**, at
`a_registry_does_not_change_a_search_that_names_no_extension`, and the cause was a
record identifier derived from measured elapsed time rather than anything the
registry does. Every warm-tree gate run during C8 had passed because both searches
finished in the same millisecond. That defect, its fix and the reasoning are
recorded above under the C8 verification follow-up. C8 adds a crate, a dependency
edge and a lockfile change, which is the case the C4 record identifies as the one
where a clean checkout earns its cost; this time it earned it for a different
reason than a stale lockfile.

main was fast-forwarded from 08ed424 to 7757af6 without conflicts or history
rewriting, so the integrated tree is byte-identical to the verified revision, which
`git diff 7757af6 main` confirms as empty. `git merge-base --is-ancestor` confirmed
the reviewed tip is retained, and `git branch -d` removed the fully merged
feat/extension-registry branch, which refuses a branch whose commits are not
reachable. The worktree is clean and the bootstrap smoke was rerun on the integrated
revision, recording 7757af6 with `dirty: false` for clean revision-bound provenance.

The branch held five commits: d48ce11 specifying the registry, 6cf6d5e implementing
it, 95c1d81 correcting the two review markers to name the implementing revision,
bb13f67 narrowing the requirement 17 contract when the clean checkout failed, and
7757af6 fixing the identifier derivation and restoring that contract to a whole
record comparison. bb13f67 is partly superseded by 7757af6 and was kept rather than
rewritten, because the intermediate state is what motivated the fix and shared
history is not rewritten.

No remote refs were changed. main is now 5 commits ahead of origin/main and remains
unpushed pending separate authorization; the origin remote and its outstanding
protection settings are recorded in [known failures](known-failures.md).

Follow-up: C6, heterogeneous computation and GPU feasibility, is the next
dependency-ready task and has no accepted specification. Write one before
introducing any public GPU or backend-selection API. Two items recorded during C8
are worth picking up with it or before it: SPEC-0009 requirement 14's "MUST NOT
construct" is narrower in practice than it reads and wants a wording correction, and
the requirement 20 version comparison at verification may be unreachable and should
be diagnosed rather than deleted on inspection. SPEC-0008 and ADR-0007 also still
name 5157786, the C5 specification commit, rather than its implementing commit
08ed424, which is the same marker staleness 95c1d81 fixed for C8.

## C8 Verification Follow-up: Clock-Derived Record Identifier (2026-09-12)

Objective: remove measured elapsed time from a run record's identifier, and specify
what the identifier is so the derivation cannot regress.

Status: complete; the full gate passes with native acceptance covered, and the
clean-checkout verification that found the defect now passes.

Acceptance gate: two runs of the same model and configuration produce the same
identifier; a changed configuration and a changed model each produce a different
one; the SPEC-0009 requirement 17 contract compares whole records again with only
elapsed time normalized; the contract fails with the old derivation reinstated; and
`bash tools/check.sh` passes with native acceptance covered. Resource budget: CPU
only, no GPU workloads.

How it was found, because the method is the point: every gate run during C8 used a
warm `target/` and passed. The clean-checkout verification, run before integrating
the branch, failed at
`a_registry_does_not_change_a_search_that_names_no_extension`. The registry was not
the cause. `record_id` was built as `run-{model_id}-{elapsed_ms}`, both searches
finished in 0 ms on the warm tree so their identifiers matched, and in the
independent clone one took 0 ms and the other 1 ms. The contract had been failing
on the clock since it was written and passing by luck.

The defect is older than C8. `search.rs` and `schedule.rs` have derived the
identifier this way since C4 and C5 respectively; the C8 contract was simply the
first thing to compare two whole records produced by separate invocations. A record
identifier that moves with the clock makes a record's identity a property of how
busy the machine was, which SPEC-0005 requirement 12 already excludes from meaning,
and it collides for unrelated searches that happen to take equally long.

What was decided rather than assumed: the identifier now derives from the SHA-256
digests of the input documents the record already carries. Two runs of the same
model and configuration therefore share an identifier, and that is the intended
reading rather than a residual collision — the identifier names the inputs a record
describes, and whether two such runs agree is what `optimizer verify` exists to
answer. `revision` and `model_fingerprint` stay separate fields, so the identifier
does not duplicate the build or the model dimension. The rule is now SPEC-0005
requirement 1a, added rather than left implicit, matching how SPEC-0003 requirement
12a and SPEC-0004 requirement 9a were recorded when implementation found a rule the
contract had not stated.

Why this needed no record version and no ADR: `record_id` is not among the ten
fields requirement 11 compares, so agreement is untouched and SPEC-0005's rule that
a change to the compared fields is breaking does not apply. The field, its type and
its schema constraint are unchanged, no exit code or stderr category moved, and the
committed example records carry hand-written identifiers rather than generated
ones, so none of them changed. The schema gains a description only.

Evidence (2026-09-12): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0. Rust tests
rose from 232 to 233, the new identifier contract. Python tests remain 60 and
documentation 51 pages. The fix is verified by reinstating the defect rather than by
assertion alone: with `run-{model_id}-{elapsed_ms}` restored the new contract fails
at the changed-configuration assertion, and with the fix it passes. Restoring the
requirement 17 contract to a whole-record comparison is the second check, since it
now compares `record_id` like every other field.

## C8 Extension Registry Implementation (2026-09-12)

Objective: implement C8 under the accepted SPEC-0009 and ADR-0008: the registry
document and its strict parser, resolution with each refusal path in its own
category, the reusable conformance suite and its record, the CLI provider table and
`registry` subcommands, registry integration in `search`, `verify` and
`schedule solve`, the two JSON Schemas with committed examples, and a gate step
re-executing a committed registry-backed scheduling record.

Status: complete; the specification preceded the implementation, and the full gate
passes with native acceptance covered.

Acceptance gate: each resolution refusal is asserted separately in its own
`ErrorKind` category; a promoted entry is refused when its conformance record is
absent, tampered with, failing or naming another version; a scheduling run
registering the NEH producer writes a record that verifies by re-execution, both in
Rust and across a commit boundary in the gate; a registry supplied to a search
naming no extension changes nothing; the conformance suite runs and its committed
record regenerates; and `bash tools/check.sh` passes with native acceptance
covered. Resource budget: CPU only, no GPU workloads.

Evidence (2026-09-12): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0, with no
native-uncovered warning. Rust tests rose from 191 to 232 and Python tests from 45
to 60. Documentation rose from 48 to 51 pages: SPEC-0009, ADR-0008 and the
register-an-extension tutorial. No checks were waived; the RustSec advisory fetch
recovered through the cached database as already recorded.

`Cargo.lock` changed only by adding the new optimizer-registry crate and local
dependency edges. No external package version changed and no new external
dependency was introduced. The registry crate depends on the published core,
extension and executive APIs and on no crate supplying a concrete extension, so the
provider seam is enforced by the build rather than asserted: the concrete table
lives in optimizer-cli.

Correctness evidence, stated as what was actually checked:

- Every refusal path is asserted in its own `ErrorKind` category: an unprovided
  identity; a declaration disagreeing with its entry on version, category, host
  contract version, problem class, determinism and limits, each individually; a
  provider returning the wrong role; an authority not implied by the category; the
  transformation category; an unmet data requirement; a gpu hardware requirement;
  an absent required identity; a declared conflicting pair; a promoted entry whose
  record is absent, tampered with, failing, or names another extension or version;
  and an experimental entry without permission.
- Refusal is total. A two-entry registry in which one entry is refused refuses the
  whole set, and the CLI writes no record for such a run.
- The refusals decided before construction are asserted against the provider's own
  construction counter, so neither can pass because nothing was ever built.
- A scheduling run registering the NEH producer through a registry writes a record
  that verifies by re-execution and exits 0. The gate re-executes such a record
  committed at an earlier revision, which is the property no in-process test can
  establish.
- A registry whose entry names a different producer version is refused at
  verification as unsupported rather than reported as divergence, so the verifier
  does not blame a record for a property of its own inputs.
- An experimental entry is refused without `--allow-experimental` and, with it,
  the written record carries a warning naming it.

Findings during implementation, each recorded rather than patched silently:

The conformance suite had no test at all. `conformance::run` and
`optimizer registry check` had exactly one caller between them, the production code
path, so requirements 23 to 25 had no evidence and the committed
`examples/conformance-record-v1.json` was a frozen artifact that was internally
consistent and correctly checksummed but never re-derived. That is the specific
failure the suite exists to prevent: `examples/extension-registry-v1.json` promotes
`flow-shop-neh` by citing that file's SHA-256, so a producer that regressed would
have kept citing a passing record while every check still agreed with it. New CLI
contracts now regenerate the record through `registry check` and compare it byte for
byte, and the assertion was shown to fail by perturbing the committed file. The
suite's own invariance comparison is unit-tested against each of the six fields it
compares, because SPEC-0004's containment means no extension reachable through the
host can move them — a broken comparison would otherwise be indistinguishable from
a conforming extension.

`entry_order_does_not_affect_resolution` was vacuous. Its adviser entry recorded an
identity its declaration did not match, so both orders were refused on the first
policy and the test asserted only that two identical errors were identical; it
passed with both identity sorts deleted. It now resolves two entries successfully in
both orders and asserts the identity and role sequences the host receives, and it
was shown to fail with the sort removed. The refusal-determinism case it used to
cover is kept as a separate test, because a test that only ever observes refusals
cannot see the ordering it claims to check.

Requirement 17 had no test. An empty extension policy with a registry supplied must
still take the extension-free entry point, which is the compatibility claim the
whole slice rests on, and it was asserted only in a code comment. A run surface
contract now compares the two records field by field apart from elapsed time.

`docs/architecture/testing.md` claimed that every refusal test asserts the
extension's own construction or invocation counter. Two did, and the invocation
counter was written and never read. The claim is now accurate, the dead
instrumentation is removed, and the reason the declaration-mismatch paths cannot
assert it is stated: resolution has to construct the extension and call `declare`
to discover the disagreement, which means requirement 14's "MUST NOT construct" is
narrower in practice than it reads. That narrowing is recorded in
[known failures](known-failures.md) as a specification correction to make, not a
code change to sneak in.

Recorded and not closed, because each needs a decision rather than a patch:
requirement 20's nondeterministic-record refusal has no fixture that can produce
one; requirement 20's version comparison at verification may be unreachable, since
resolution has already equated the declaration with the entry, and the branch is
left in place rather than deleted on inspection alone; requirement 21's positive
diagnostic case, requirement 22's forfeited registry-backed record, and
`optimizer search --registry` with a non-empty policy are all untested, the last
because both provided extensions are flow-shop producers that cannot be built from
a bare model. All are in [known failures](known-failures.md).

Scope boundary held: no schema version changed anywhere, no existing document
gained or lost a field, and the compared fields stay the ten SPEC-0005 fixed. The
committed C4 example record still re-executes and verifies inside the gate. An
extension summary difference is a diagnostic note that does not change an exit code,
matching the existing environment-difference rule.

What is deliberately not claimed: no performance, runtime or solution-quality
result. Promotion means the contract conformance suite passed, never that the
extension improves a search, which stays C7's question. The conformance record
carries no timing field, and a test asserts its absence so one cannot arrive
quietly.

Follow-up: C6, heterogeneous computation and GPU feasibility, is the next
dependency-ready task and has no accepted specification; write one before any
public GPU or backend-selection API. C9 and C10 are also unblocked now that C8 is
complete, and both keep their recorded blockers.

## C8 Extension Registry Specification (2026-09-12)

Objective: write and accept the C8 contract before any public registry API exists,
as required by AGENTS.md, CONTRIBUTING.md and the Stage 3 scope. No C8 behavior is
implemented by this change.

Status: complete; SPEC-0009 and ADR-0008 are accepted and the project records that
reference C8 are synchronized.

Acceptance gate: the specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation and link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and **unchanged test counts**, because no behavior
changes. Had either count moved, this change would be doing something it claims not
to. Resource budget: CPU only, no GPU workloads.

Why C8 and not C6: Stage 4's entry condition is that Stage 3 provides reproducible
workflows, and C8 is Stage 3's last open item. It is also the seam two recorded
known-failures point at, so it blocks rather than merely precedes: the registry does
not exist, and a C5 scheduling run performed with the NEH producer is not verifiable
by re-execution at all. C6's dependencies are met, but starting it would leave
Stage 3's reproducibility claim partial.

Scope decided before implementation: the registry alone. C8's backlog line bundled
three deliverables and CONTRIBUTING.md mandates one complete vertical slice, so the
Python SDK becomes C9 with its pyo3/ADR-0003 blocker unchanged and the comparative
experiment runner becomes C10. Existing references to "C8's registry" stay accurate
because C8 keeps the registry.

Two contract decisions worth recording, because both are the kind a later
implementation could get quietly wrong:

The registry resolves; it does not load. An entry names an extension the build
already provides through a caller-owned `Provider` seam, which is the same pattern
as `&dyn Backend` and `&[Registration]`. Dynamic native loading needs a second
unsafe boundary ADR-0003 prohibits, so it stays deferred; the registry now makes
that absence more visible rather than closing it.

No document version changes and agreement is untouched. An extension is identified
in a record by the `extension_id` and `version` its `ExtensionSummary` already
embeds verbatim, so a record naming an extension is re-resolvable without a new
field. Adding the registry to the compared fields would change what agreement means
for every existing record, which SPEC-0005 reserves for a new record version plus an
ADR. A resolved-version mismatch and a nondeterministic summary are therefore
refused as *unsupported* rather than reported as divergence, which is the same
distinction the C5 implementation drew when it turned a misleading divergence into a
refusal.

Expected changes: docs/specifications/SPEC-0009-extension-registry.md,
docs/decisions/ADR-0008-registry-resolution.md, state/backlog.yaml, AGENTS.md,
state/known-failures.md, implementation-plan.md, wiki/status.md, the forward
references in SPEC-0004, SPEC-0005 and SPEC-0008, and this record. No CHANGELOG.md
entry: the changelog records user-visible changes and an accepted contract with zero
behavior is not one, matching the C2 and C5 specification commits.

Follow-up: C8 implementation is dependency-ready under SPEC-0009. It requires the
optimizer-registry crate with the strict registry document, resolution with each
refusal path in its own category, the reusable conformance suite over a fixed grid,
the CLI provider table and subcommands, registry integration in `search`, `verify`
and `schedule solve`, the two JSON Schemas with committed examples, and a gate step
re-executing a committed registry-backed scheduling record so the closed gap is
established across a commit boundary rather than within one process.

## C5 Flow-Shop Scheduling Implementation (2026-09-11)

Objective: implement C5 under the accepted SPEC-0008 and ADR-0007: flow-shop
instances, the makespan recurrence, the positional encoding, deterministic NEH and
insertion producers, a scheduling command surface, and a frozen generated Taillard
development subset.

Status: complete; the specification preceded the implementation, and the full gate
passes with native acceptance covered.

Acceptance gate: the optimum the executive proves on an encoded model equals the
minimum found by exhaustive permutation enumeration over a fixed grid; the recurrence
agrees with an independently written oracle; the generator reproduces Taillard's
published verification instance exactly; a producer whose proposals are refused
leaves the outcome, proven optimum, dual bound, forfeiture state and both prune
counters unchanged; a scheduling run writes a verifiable run record; and
`bash tools/check.sh` passes with native acceptance covered. Resource budget: CPU
only, no GPU workloads.

Evidence (2026-09-11): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0 in 16 seconds
on a warm build directory, with no native-uncovered warning. Rust tests rose from
159 to 191 and Python tests from 39 to 45. Documentation remains 48 pages, because
SPEC-0008 and ADR-0007 were added by the specification commit. The
`AI_OPTIMIZER_SKIP_NATIVE=1` configuration also passed with all 191 tests and its
uncovered-acceptance warning. No checks were waived; the RustSec advisory fetch
recovered through the cached database as already recorded.

`Cargo.lock` changed only by adding local dependency edges and the new
optimizer-schedule-examples crate. No external package version changed and no new
external dependency was introduced: the Lehmer generator is Taillard's own published
algorithm rather than a general-purpose RNG crate, which is a correctness
requirement and not a dependency preference.

Correctness evidence, stated as what was actually checked:

- Over a fixed grid of tiny instances with no randomness, the executive's proven
  optimum on the encoded model equals the minimum from exhaustive enumeration of
  every permutation, and the decoded winner re-evaluates through the recurrence to
  that same value. Three independent views must agree, so neither the encoding nor
  the recurrence can be wrong alone without failing. The grid sizes are asserted so
  they cannot silently shrink.
- The recurrence agrees with a separately written oracle over 5,232
  instance-permutation pairs. The independence is architectural rather than
  asserted: `evaluate` imports neither `encode` nor `heuristic`, and the test oracle
  is a second implementation in the test file.
- The generator reproduces Taillard's published `ta001` matrix exactly from seed
  873654221, checked in Rust against the published matrix and independently in
  Python against a second implementation of the generator. Both a wrong seed and a
  transposed loop order are shown to disagree, so the check can fail.
- Every one of the ten frozen instances regenerates from its manifest-recorded seed
  and parameters to the committed bytes, and its committed checksum is verified.
- A producer whose every proposal is refused leaves the outcome, proven optimum,
  dual bound, forfeiture state and both prune counters identical to the
  producer-free run, with the refusal recorded as rejected rather than absorbed.
- Every scheduling test that depends on a producer asserts the producer's own
  proposal counter first, so none can pass because the producer was never consulted.
- Decoding refuses a fractional assignment, a position selecting two jobs, a
  position selecting none, one job filling two positions, a candidate naming another
  model, and a candidate missing a variable. None is rounded or repaired.
- The end-to-end surface was exercised on the built binary: a 5-job, 3-machine
  instance reported `proven_optimal` with objective 372, matching independent
  brute-force enumeration of all 120 permutations, and its record verified.

Two findings during implementation, both recorded rather than patched silently:

An early test asserted that an *honest* producer left both prune counters unchanged.
It failed, correctly: `nodes_pruned_bound` went from 0 to 1 because an accepted
incumbent legitimately prunes more by bound, which is the entire purpose of a
candidate producer. SPEC-0008 requirement 20 was already scoped to a refused or
absent proposal, so the contract was right and the test was wrong. A
`RefusedProducer` was added to test the invariance claim for what it actually says,
and the honest producer is now asserted against requirement 19's promise instead.
C3's identically worded rule is consistent, because it was established with hostile
extensions whose proposals are all refused. The specification's acceptance section
now records this rather than leaving the scope looking arbitrary.

`optimizer verify` reported a *divergence* for a record produced with the producer
registered, naming a node-count difference. That diagnosis was misleading:
verification re-executes through the extension-free entry point, so it reproduced a
search the record does not describe and the counters differed for that reason alone.
SPEC-0005 requirement 14 already refuses such a configuration on the search path, so
the same rule now applies to verification and the record is refused as unsupported
instead. The consequence is real and is recorded in
[known failures](known-failures.md): a scheduling run performed with the producer is
not verifiable by re-execution today, and the seam is C8's registry.

Scope boundary held: no schema version changed anywhere, no new record type was
introduced, and no existing document gained or lost a field. `RunRecord`,
`SearchRecord`, `Model` and `optimizer verify` are untouched apart from the
verification refusal above, which is why the committed C4 example record still
re-executes and verifies inside the gate.

What is deliberately not claimed: no performance, runtime or solution-quality
result. Proven optimality is asserted only where exhaustive enumeration is the
oracle; a node-limited run over `ta001` is asserted to report its limit rather than
an optimum, and its incumbent is asserted feasible through the recurrence. No
best-known bound is committed, because a committed bound is an acceptance threshold.
The positional encoding's weak relaxation and the suboptimality of permutation
schedules beyond three machines are both recorded in
[known failures](known-failures.md).

Follow-up: C6 (heterogeneous backend and GPU feasibility) now has its dependencies
met, and C8 (registry, SDK and comparative runner) remains unblocked. Both need
their specifications written before any public API.

## C5 Flow-Shop Scheduling Specification (2026-09-11)

Objective: write and accept the C5 contract before any public scheduling API
exists, as required by AGENTS.md, CONTRIBUTING.md and the Stage 3 scope. No C5
behavior is implemented by this change.

Status: complete; SPEC-0008 and ADR-0007 are accepted and the project records that
reference C5 are synchronized.

Acceptance gate: the specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation and link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and unchanged test counts, because no behavior changes.
Resource budget: CPU only, four Cargo workers, no GPU workloads.

Evidence (2026-09-11): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0 and no
native-uncovered warning. Rust tests remain 159 and Python tests remain 39, which
is the expected result for a contract with no behavior: had either count moved,
this change would have been doing something it claims not to. Documentation rose
from 46 to 48 pages, SPEC-0008 and ADR-0007, with internal links and anchors
validated. The RustSec advisory fetch failed and recovered through the cached
database, the condition already recorded in [known failures](known-failures.md).
No checks were waived.

The diff is documentation plus one doc comment. `Cargo.lock`, `Cargo.toml`,
`schemas/`, `tools/` and `examples/` are untouched, and the only change under
`crates/` replaces the stale placeholder comment in optimizer-schedule that claimed
its specification was unassigned. No CHANGELOG.md entry accompanies this change:
the changelog records user-visible changes, and an accepted contract with zero
behavior is not one, matching the C2 specification commit. C5 enters the changelog
when its behavior ships.

Three claims in these documents were verified before being written down rather than
reasoned about, because each is the kind a later implementation could get quietly
wrong. Taillard's generator, reimplemented from the OR-Library transcription of the
1993 EJOR paper, reproduces his published ta001 matrix exactly from seed 873654221.
The positional encoding's optimum equals the makespan recurrence for a fixed
permutation, and its minimum over all permutations equals brute-force enumeration,
over 300 randomly generated instances. And permutation schedules are genuinely
suboptimal for the general flow shop beyond three machines: on a 3-job, 4-machine
instance the best permutation schedule costs 50 while the best general schedule
costs 47, which is why SPEC-0008 states the permutation restriction is part of the
problem rather than an approximation. The exhaustive-oracle bound was also measured:
enumerating 8 jobs is 40,320 permutations in roughly 130 ms, so the fixed grid in
the acceptance tests is affordable at n ≤ 8.

Resolved while writing: the first gate run failed rustdoc with an unresolved
intra-doc link, because the new module comment linked to `optimizer_core` while
optimizer-schedule still declares no dependencies. Adding that dependency edge
belongs to the implementation commit, not to a spec-only change, so the comment now
uses plain backticks. Worth recording because the failure was the workspace's
warnings-as-errors rustdoc correctly catching a documentation claim that referenced
something not yet in scope.

Noted and not changed: `state/backlog.yaml` retains one `status: ready`, which is
now C5's own and is correct. The benchmark protocol gained a paragraph stating when
a generated suite satisfies its freezing rule without download tooling, because the
rule as written required download tooling and ADR-0007 deliberately takes the other
route; leaving the two in apparent conflict would have made the protocol read as
overridden rather than extended.

Follow-up: C5 implementation is now dependency-ready under SPEC-0008. It requires
the instance document and its strict parser, the recurrence evaluator kept
independent of the encoding, the Lehmer generator with the pinned published seeds,
the positional adapter, the NEH and insertion producers in their own crate so the
independence evidence comes from the workspace build, a CLI surface, the frozen
manifest with committed instances and checksums, and the exhaustive permutation
grid that is the slice's load-bearing assertion.

Expected changes: docs/specifications/SPEC-0008-flow-shop.md,
docs/decisions/ADR-0007-flow-shop-encoding.md, state/backlog.yaml,
docs/benchmarks/protocol.md, implementation-plan.md, docs/architecture/overview.md,
docs/architecture/testing.md, README.md, wiki/status.md, AGENTS.md, the stale
placeholder doc comment in optimizer-schedule, and this record.

Two decisions are settled before implementation because both are the kind a later
implementation could get quietly wrong, and both were verified rather than
assumed.

The positional encoding is exactly linear. Makespan is not linear in a raw
permutation, but the positional formulation with binary job-position assignment
and continuous completion times needs no big-M constant. Checked over 300 random
instances: the encoded optimum for a fixed permutation equals the makespan
recurrence, and the minimum over all permutations equals brute-force enumeration.
The consequence is that C5 reuses `Model`, `Model::evaluate`,
`optimizer_solver::search`, `RunRecord` and `optimizer verify` unchanged, with no
new record type and no schema version bump.

The frozen Taillard subset is generated from published seeds rather than
downloaded. Taillard's documented Lehmer generator reproduces his published ta001
matrix exactly from seed 873654221, checked against the OR-Library transcription
of the EJOR paper. The canonical instance host timed out from this environment, so
generating from pinned seeds removes a network dependency from the gate instead of
adding one. `schemas/benchmark-manifest-v1.schema.json` already carries the shape
this needs: `instances[].generator` accepts a name, seed and parameters, so no
schema change is required.

What C5 must not claim: the positional encoding's LP relaxation is weak and a
20x5 Taillard instance is 400 binaries, so the executive will not prove optimality
at that size. Proven-optimal assertions are therefore confined to tiny instances
where exhaustive permutation enumeration is the independent oracle, and the frozen
subset carries feasibility, determinism and validated-incumbent assertions only.
Best-known upper bounds are deliberately not committed, because recording one
would create an acceptance threshold that the benchmark protocol says requires its
own ADR and experiment record.

Also in scope: `state/backlog.yaml` still names C4 as the current and next-ready
milestone and marks it `ready` while every other record in the repository says C4
is complete. It is the only file carrying that staleness. The benchmark protocol's
planned-suites table also still dates the two flow-shop suites in the retired
M-numbering.

## Local C4 Integration (2026-09-11)

Objective: verify the feat/run-surface branch from a clean checkout, integrate it
into local main, and delete the feature branch after confirming its commits are
retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 6725d93; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-11): the branch was cloned to /tmp/c4-final with
`--no-hardlinks` and no `target/` directory present, and `bash tools/check.sh`
passed there in 1 minute 56 seconds with zero skip messages. That run built the
pinned HiGHS 1.11.0 library from the checksum-verified upstream archive inside the
clone, ran 159 Rust and 39 Python tests, re-executed the committed run record
against the freshly built binary, validated 46 documentation pages, and passed
cargo-deny, artifact validation and bootstrap smoke.

Two stale claims were found and fixed before integration rather than carried onto
main. AGENTS.md still stated that C3 was the current scope and had no accepted
specification; it is the first file an agent reads, so a stale scope there
misdirects work rather than merely aging. And the three review markers named
692e19f, the parent the documents were written against, rather than the
implementing revision whose content was reviewed.

main was fast-forwarded from 692e19f to 6725d93 without conflicts or history
rewriting, so the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained, and
`git branch -d` removed the fully merged feat/run-surface branch.

No remote refs were changed. main is now 5 commits ahead of origin/main and
remains unpushed pending separate authorization.

Follow-up: C5, the flow-shop scheduling vertical slice, is dependency-ready.
Write its specification before introducing any public scheduling API. C8, the
local registry, SDK and comparative experiment runner, is also unblocked; the SDK
needs an ADR amending ADR-0003 before any binding code.

## C4 Follow-up: Gated Re-execution and Engine Diagnostics (2026-09-11)

Objective: close three gaps found reviewing the C4 slice — a gate that never
re-executed a committed record, a divergence that could not distinguish a changed
engine from a wrong result, and a non-native build recording a backend version it
never called.

Status: complete; the full gate passes with native acceptance covered, and the
non-native configuration passes separately.

Acceptance gate: the committed example record re-executes against the current
build inside `bash tools/check.sh`, with both refusal directions asserted there
too; a record naming a different revision or compiler still verifies while
reporting the difference; a divergence carries that difference as a note without
changing its exit code; a build linking no native library records `unavailable`
rather than the pinned version, shown by a test that fails when the old code is
reinstated. Resource budget: CPU only, no GPU workloads.

Scope boundary: consulting engine identity as an *explanation* is within
SPEC-0005 as accepted, because requirement 11 fixes the ten compared fields and
requirement 13 forbids strengthening a claim; neither constrains diagnostic text.
Deciding that a version mismatch makes divergence *tolerable* would change the
meaning of agreement, which SPEC-0005's compatibility section says requires a new
record version and an ADR. That remains open and is recorded, not implemented.

Evidence (2026-09-11): the complete gate passed with the pinned library linked and
zero skip messages. Rust tests rose from 156 to 159: two environment-difference
contracts in optimizer-experiment and one CLI contract asserting the diagnostic
does not decide agreement. Python tests remain 39 and documentation 46 pages. The
new `tools/verify_committed_record.py` step reports
`committed run record re-executed and verified: passed`.

`AI_OPTIMIZER_SKIP_NATIVE=1 bash tools/check.sh` also passed with all 159 tests,
still printing its uncovered-acceptance warning, and correctly skipping the
committed-record step because a build with no library cannot solve at all.

The backend-version fix is verified by reinstating the defect rather than by
assertion alone: with `PINNED_VERSION` restored on the pre-cancelled path, the
non-native test fails at backend.rs:172; with the fix, it passes. The same test
runs in both configurations, so the native path is covered by the same assertion.
`interrupted_record` was the reachable path, because a pre-cancelled solve returns
a record without touching the library.

Why the gate step exists: every Rust re-execution test produces its record moments
earlier in the same process against the same binary, so none of them exercised the
property SPEC-0005 actually claims, that a record outlives its author. The gate now
re-runs a record committed at an earlier revision, and asserts the fingerprint
refusal and a counter divergence there as well, so the passing case is not the
only thing checked.

Noted: the example record's own provenance differs from any current checkout by
construction, since it carries the all-zero revision. That made it the natural
fixture for the diagnostic — verifying it now reports `environment_differs: true`
while still agreeing and exiting 0, which is exactly the separation between
explanation and decision that this change is about.

## C4 Agent-Independent Run Surface (2026-09-11)

Objective: implement the first C4 slice under a new SPEC-0005: expose the C2
executive and C3 extension host through the CLI, wrap each search in a
provenance-bearing run record, and add a verification command that re-runs a
search from its record alone and fails on disagreement.

Status: complete; the specification preceded the implementation, and the full
gate passes with native acceptance covered.

Acceptance gate: a search performed through the CLI writes a schema-valid run
record carrying source revision, dirty state, hardware, toolchain, backend
identity and version, the canonical model fingerprint and hashed inputs; that
record is re-executable by `optimizer verify` using only its embedded
configuration and the model it names; verification detects a mutated outcome,
objective, dual bound, forfeiture flag and each node counter individually, and
rejects a model whose fingerprint changed while its `model_id` did not;
elapsed time alone never fails verification; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Scope boundary, decided before implementation: the backlog's C4 line bundles
four deliverables and CONTRIBUTING.md mandates one complete vertical slice. This
slice delivers the CLI run surface and pinned reproducible runs. The local
registry and the Python SDK are deferred to their own specifications and gates
and are recorded in [known failures](known-failures.md) rather than dropped
silently. The SDK deferral has a technical basis: pyo3 expands to unsafe code,
the workspace forbids it, and ADR-0003 permits unsafe only inside
optimizer-highs, so an SDK needs an amending decision record.

Expected changes: new SPEC-0005 and ADR-0006; `crates/optimizer-experiment`
gains its first types and dependencies; new `schemas/run-record-v1.schema.json`
and `schemas/search-record-v2.schema.json`; `crates/optimizer-cli` gains
`search` and `verify` over new optimizer-solver and optimizer-experiment
dependencies; new tests in optimizer-cli, optimizer-experiment and
tests/integration; `examples/run-record-v1.json`;
`tools/validate_artifacts.py`; README.md, CHANGELOG.md,
docs/architecture/{overview,testing}.md, a new run-and-verify tutorial,
docs/operations/build.md, wiki/{status,glossary}.md, schemas/README.md,
cuda/schedule_eval/README.md, implementation-plan.md, state/backlog.yaml,
state/known-failures.md and this record.

Evidence (2026-09-11): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library built and linked, with **zero skip messages**, in 20
seconds on a warm build directory: format, warnings-as-errors Clippy over all
targets, 156 Rust tests, workspace build, warnings-as-errors rustdoc, cargo-deny
(advisories, bans, licenses, sources all ok), artifact validation, 39 Python
tests, 46-page documentation and link validation, and bootstrap smoke. No checks
were waived.

Rust tests rose from 132 to 156: 11 run surface CLI contracts in optimizer-cli,
11 run record contracts in optimizer-experiment, and 2 SHA-256 unit tests.
Python tests rose from 20 to 39: 12 run record and search record schema
contracts plus 2 checksum-agreement tests, counted with subtests as unittest
reports them. Documentation pages rose from 43 to 46: SPEC-0005, ADR-0006 and
the run-and-verify tutorial.

Cargo.lock changed only by adding local dependency edges: optimizer-cli on
optimizer-experiment and optimizer-solver, and optimizer-experiment on
optimizer-core, optimizer-solver, serde and serde_json. No external package
version changed, and no new external dependency was introduced.

Reproducibility evidence, stated as what was actually checked rather than as a
property claimed in prose:

- `optimizer search` over examples/model-v1.json reported
  `outcome: proven_optimal`, `objective: 2.5`, `dual_bound: 2.5`, `forfeited:
  false` and exit 0, matching the C1 solve of the same model exactly. The record
  carried a 40-hex revision, the model fingerprint `fnv1a64:cc63f58b64d1c205`,
  and a SHA-256 for each of the two input documents.
- `optimizer verify` on that record re-ran the search and agreed, exit 0, naming
  all ten compared fields in its verdict.
- Verification was shown to be able to fail, in both directions it must. A model
  whose objective coefficient changed from 2.0 to 2.5 while keeping
  `model_id: tiny-mixed` was refused before any search ran:
  `document: model fingerprint mismatch`, exit 2. A record whose objective was
  edited to 1.5 was refused after re-running:
  `divergence: numerical: objective: recorded 1.5, reproduced 2.5`, exit 2.
- Each of the ten compared fields is asserted to fail when it alone is mutated,
  and the list of mutated field names is asserted equal to
  `RunRecord::compared_fields()`, so a field cannot be dropped from the
  comparison without a test failing.
- A record differing only in `elapsed_ms` by 987 seconds still verified with exit
  0, which fixes elapsed time as diagnostic rather than contractual.
- A node-limited search wrote its record, reported `outcome: node_limit` and exit
  1, and that record verified as still limited. A forfeited search that verifies
  is asserted to remain forfeited and to fail `proves_completion`.

Why the SHA-256 is implemented rather than taken from a crate: `sha2` and its
dependencies would add six external packages under `deny.toml`'s
`multiple-versions = "deny"` policy for one well-specified function. It is
implemented in safe Rust and checked against the FIPS 180-4 published vectors,
including the three padding edge cases at 55, 56 and 64 bytes and the
one-million-character vector, then independently against Python's `hashlib` over
the committed example documents and over a freshly generated record. Agreement
between the two implementations is verified rather than assumed.

Both normative authorities accept the same documents. The new schemas give C2 and
C3 records their first schema coverage, and `RunRecord::from_json` validates the
embedded search record's version on the parse path, so the divergence that
produced commit 6516a6f cannot recur here.

Resolved during implementation: an early assertion that a record with absent
measurements contains no `null` at all was wrong and was narrowed. Search
configuration serializes an absent budget as an explicit `null` meaning
unlimited, which is SPEC-0003's stated convention; the omit-rather-than-null rule
governs measurements. The test now asserts the three measurements are absent and
that `node_limit` is still explicitly null beside them.

Noted and not changed: the example record is generated from a real search and
then rewritten with the all-zero revision and example hardware, matching how
examples/experiment-result.json marks itself as a shape rather than evidence. Its
input hashes are the real ones and are verified against the committed files by
both the validator and a Python test.

Scope split recorded in the backlog: C4's original line covered four
deliverables. C4 is now the run surface and the registry, SDK and comparative
runner are backlog item C8, which depends on C4. C5, C6 and C7 keep their
dependency on C4, which remains meaningful because the run surface is what they
build on. The four deferrals are recorded in
[known failures](known-failures.md) with their blockers.

Clean-checkout verification, which is the stronger C1 and C3 standard and the
case that matters here because this change adds four crate dependency edges where
a stale lockfile or a missing manifest entry would otherwise hide behind a
populated `target/`: the branch was cloned to /tmp/c4-verify with
`--no-hardlinks` and no `target/` directory present, and
`bash tools/check.sh` passed there in 1 minute 36 seconds. That run built the
pinned HiGHS 1.11.0 library from the checksum-verified upstream archive inside
the clone and ran the same 156 Rust and 39 Python tests. The only lines matching
"skip" were CMake's own `Check for working CXX compiler - skipped` probes, not
test skips, so native acceptance was genuinely covered rather than inherited from
a warm build directory.

On the clean committed tree the run surface produces evidence-grade provenance:
`optimizer search` recorded revision c0eac20 with `dirty: false`, and
`optimizer verify` reported `agreement: true` with `evidence: true` and exit 0.
The dirty mid-implementation runs reported `evidence: false`, which is the
requirement 5 rule working rather than a defect.

No remote refs were changed and nothing was pushed; main remains unpushed pending
separate authorization. The branch feat/run-surface holds two commits, 8775da1
specifying the surface and c0eac20 implementing it.

## Local C3 Integration (2026-09-09)

Objective: verify the reviewed feat/extension-runtime branch from a clean
checkout, integrate it into local main, and delete the feature branch after
confirming its commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 6516a6f; the
feature branch is deleted and the worktree is clean. Resource budget: CPU only,
four Cargo workers, no GPU workloads.

Evidence (2026-09-09): the branch was cloned to /tmp/c3-verify with no `target/`
directory present, and `bash tools/check.sh` passed there in 1 minute 44 seconds
with **zero skip messages**, so native acceptance was genuinely covered rather
than inherited from a warm build directory. That run built the pinned HiGHS
1.11.0 library from the checksum-verified upstream archive inside the clone,
producing both `libhighs.a` (10.2 MB) and the standalone reference executable
(5.0 MB). It ran 132 Rust tests and 20 Python tests, validated 43 documentation
pages, and passed cargo-deny, artifact validation and bootstrap smoke.

The clean clone also solved examples/model-v1.json to `termination: optimal`,
`objective: 2.5`, `backend_version: 1.11.0` with an independently validated
feasible incumbent and exit 0, matching the workspace result exactly.

This clean-checkout pass is the acceptance evidence for the integration. It was
run because C3 adds two crates and a new dev-dependency edge, which is exactly
the case where a stale lockfile or a missing manifest entry hides behind a
populated `target/`. The C2 integration relied on its pre-integration gate pass
instead; this record restores the stronger C1 standard.

main was fast-forwarded from b934dbd to 6516a6f without conflicts or history
rewriting, so the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained on main,
`git rev-parse` confirmed main is exactly the verified revision, and
`git branch -d` removed the fully merged feat/extension-runtime branch. The
worktree is clean and the bootstrap smoke was rerun on the integrated revision
for clean revision-bound provenance.

The RustSec advisory-database fetch failed in the clean clone and recovered
through the cached database, as recorded in [known failures](known-failures.md).
Bans, licenses and sources were checked normally. No checks were waived.

No remote refs were changed. main is now 3 commits ahead of origin/main and
remains unpushed pending separate authorization; the origin remote and its
outstanding protection settings are recorded in
[known failures](known-failures.md).

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

## C3 Review Follow-up: Test Provenance and Nested Versions (2026-09-09)

Objective: resolve three problems found reviewing the C3 commit — a history that
made four mandatory test repairs indistinguishable from weakened ones, a
replacement test helper that asserted on serializer whitespace, and Rust record
parsers laxer than the JSON Schemas about nested document versions.

Status: complete; the branch is three commits and the full gate passes with
native acceptance covered.

Acceptance gate: the test repair compiles and passes on its own at search
schema version 1, proving it is not a consequence of the version bump; the
repaired assertions are shown to fail when the helper is sabotaged, so none is
vacuous; a record with a wrong nested version is rejected by both
`from_json` and `tools/validate_artifacts.py`; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Expected changes: the branch history; `crates/optimizer-core/src/{lib,solve}.rs`;
`crates/optimizer-solver/src/search.rs`; contract tests in optimizer-core,
optimizer-solver and optimizer-extension-examples; SPEC-0002 requirement 11,
SPEC-0003 requirement 22, SPEC-0004 requirement 23 and their acceptance
mappings; CHANGELOG.md and this record.

Evidence (2026-09-09): the branch is `b934dbd` → `9a2eda5` (test repair) →
`a85da69` (C3) → this commit. `git diff c3-pre-split a85da69` touches only the
test helper, confirming the split preserved the reviewed C3 content byte for
byte elsewhere; the pre-split tip is retained as tag `c3-pre-split`. The repair
commit's 22 contracts pass at version 1 with no extension field present, which
is what establishes that the repair was independent of the feature rather than
produced by it. Sabotaging `retarget_version` to a no-op makes both version
tests fail, so neither is vacuous.

The complete `bash tools/check.sh` gate passed with the native library built and
linked, with **zero skip messages**. Rust tests rose from 130 to 132: one nested
version contract in optimizer-core and one in optimizer-solver, plus extension
document coverage folded into the existing round-trip test. Cargo.lock changed
only by adding a `serde_json` dev-dependency edge for
optimizer-extension-examples; no external package version changed.

Why the parser change needed no ADR: `schemas/solve-record-v1.schema.json`
already pins the nested candidate's `schema_version` to `const 1` and pins
`options` by `$ref`, and those schemas are normative under SPEC-0007. The Rust
parsers checked only their own top-level version, so the two enforcement paths
disagreed and `tools/validate_artifacts.py` rejected documents the Rust parser
accepted. This change brings code into line with an accepted contract rather
than deciding anything new, and it is strictly narrowing: no document valid
under both paths becomes invalid. Verified by parsing one fixture with a wrong
nested version through both paths and confirming both reject it.

`Candidate::canonical` is deliberately not called on the parse path. It also
sorts and range-checks values, and parsing a record must reject a wrong version
without silently rewriting the document it was handed.

Resolved during implementation: the acceptance suite needed `serde_json` as a
dev-dependency to mutate a parsed document by field path. It is test-only, so
the examples crate's runtime dependencies remain optimizer-core and
optimizer-extension alone, and the independence evidence is unaffected.

Noted and not changed: `crates/optimizer-core/tests/solve.rs` still replaces
every `"schema_version": 1` occurrence in one assertion, which passes only
because the top-level check fires first. It is not wrong today and its
assertion is the top-level rule, so it is left alone; the new nested-version
contract beside it covers what the replacement cannot distinguish.

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

## C3 Extension Runtime and Authority Model (2026-09-09)

Objective: implement C3 under a new SPEC-0004: an extension runtime with a
declared authority model, candidate producers and search advisers, whose actions
the core validates and whose failures are recorded rather than absorbed.

Status: complete; the specification preceded the implementation, and the full
gate passes with native acceptance covered.

Acceptance gate: independently authored extensions build and run against the
published APIs with no engine-internal change; invalid candidates, invalid
advice, incompatible versions, panics and budget abuse each produce a typed
record entry; the proven optimum and the proof claim are identical with and
without extensions, including adversarial ones; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Expected changes: new SPEC-0004 and ADR-0005; new crates optimizer-extension and
optimizer-extension-examples; optimizer-solver contracts, executive and hooks;
`SEARCH_SCHEMA_VERSION` 1 to 2; the C2 search and native executive tests;
SPEC-0003 compatibility and exclusion clauses; implementation-plan.md, README.md,
docs/architecture/{overview,testing}.md, wiki/{status,glossary}.md, CHANGELOG.md,
state/backlog.yaml, state/known-failures.md and this record.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked, with **zero skip messages**: format,
warnings-as-errors Clippy, 130 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny (advisories/bans/licenses/sources), artifact validation, 20
Python tests, 43-page documentation/link validation and bootstrap smoke. Rust
tests rose from 84 to 130: 27 new extension runtime contracts, 18 new
independent-extension acceptance contracts, and 1 new native end-to-end
contract. No checks were waived.

The RustSec advisory-database fetch failed on the final run and recovered
through the cached database, as recorded in
[known failures](known-failures.md). Bans, licenses and sources are offline and
were checked normally; the advisory check ran against the cache rather than a
fresh fetch.

Cargo.lock changed only by adding local dependency edges for
optimizer-extension (optimizer-core, serde, serde_json),
optimizer-extension-examples (optimizer-core, optimizer-extension, and
optimizer-solver as a dev-dependency), the optimizer-solver dependency on
optimizer-extension, and optimizer-highs dev-dependencies on both new crates.
No external package version changed.

Correctness evidence, stated as what was actually checked:

- Three honest extensions and three hostile ones covering 17 distinct
  misbehavior modes (7 bad proposals, 4 bad actions, 6 unadmittable
  declarations) live in optimizer-extension-examples, which depends on the
  published extension and core APIs and takes optimizer-solver only as a
  dev-dependency. That the
  workspace builds is the evidence that a third-party extension needs no
  engine-internal change; it is not an assertion in prose.
- Over a fixed 25-model grid covering both senses, integer and binary domains,
  three capacities, two coefficient settings and a proven-infeasible case, every
  hostile extension leaves the outcome, the
  proven optimum, the dual bound, the forfeiture state and both prune counters
  identical to the extension-free run, which itself agrees with brute-force
  enumeration of the whole assignment space. These comparisons use unlimited
  node and time budgets deliberately: a hostile adviser spending a node budget
  on unpromising nodes legitimately changes which outcome a *budgeted* search
  reaches, so a budgeted assertion would be flaky by design rather than a real
  correctness check.
- An empty extension policy reproduces the extension-free record exactly, apart
  from measured elapsed time. That is the direct check that C3 did not perturb
  C2, and all 22 C2 contracts still pass unchanged in substance.
- Refusals are typed and recorded: infeasible, out-of-bounds, wrong-model,
  incomplete and nonfinite candidates; advice naming a nonexistent node, an
  unknown variable or an integral variable; both directions of host-contract
  mismatch; a refused transformation category; an unclaimed problem class;
  contained panics in `propose`, `advise` and even `declare`; and exhausted
  invocation and proposal budgets. A refused extension is never invoked at all,
  which is asserted against a call counter the extension itself maintains.
- A producer's claimed objective is never read. The out-of-bounds producer
  offers a candidate with an enormous objective and the record still reports the
  true optimum from independent recomputation.
- Recorded diagnostics stay bounded: 10,000 distinct rejections leave the
  counter exact at 10,000 and the retained messages capped at 8.
- The native end-to-end test drives the real executive over pinned HiGHS with a
  lying producer, a ghost-node adviser and a panicking adviser registered
  simultaneously, and still proves the optimum independent enumeration finds.

Resolved during implementation:

- The first acceptance run showed a search adviser being consulted for a
  continuous model, which requirement 20 forbids. Root cause: the node-selection
  hook ran whenever the frontier was non-empty, including when it held exactly
  one node and there was no choice to make. Fixed by not consulting an adviser
  for a decision with one possible answer, and recorded as SPEC-0004
  requirement 9a rather than patched silently. Consulting there could only
  manufacture rejections describing the hook rather than the extension.
- Three acceptance tests initially asserted against models whose LP relaxations
  happen to be integral, so no branching occurred and no adviser was ever
  consulted; they were passing or failing for reasons unrelated to their names.
  They now use a model with a genuinely fractional relaxation and assert
  `nodes_explored > 1` first, so a future change that removes the branching
  cannot make them vacuous.
- Three C2 record tests needed repair rather than renumbering. Two mutated "the
  first `schema_version` in the JSON", which at version 2 is the nested
  candidate's or is absent entirely, so they would have parsed successfully and
  panicked on `unwrap_err`. A third hand-wrote a complete configuration object
  plus an unknown field; with a new required field it would have been rejected
  for the *missing* field while still passing, silently ceasing to test
  unknown-field rejection. All three now target the document's own version or
  build their base from a serialized valid configuration.

Deferred and recorded rather than hidden: the extension host is in-process, so
containment covers panics but not a process abort, stack exhaustion or a memory
fault, and no per-extension memory budget is enforced. Process isolation and the
versioned C boundary for dynamically loaded native components are specified as
deferred and need their own decision record, because a second unsafe boundary
would amend ADR-0003. No CLI subcommand exposes extensions yet, no JSON Schema
covers search or extension records, and no performance claim is made: C3
establishes safety only, and whether advisers improve search is C7's question.

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

Contract decisions worth recording, because they are the ones a later
implementation could get quietly wrong:

- No extension path may reach forfeiture, a search-loop break, or an `Err`
  return from `search`. An adversarial extension must not be able to deny a
  proof the engine would otherwise complete. C2 forfeits when a *backend*
  misbehaves because its bounds become untrustworthy; a bad extension candidate
  implies nothing about bounds, so it is a recorded rejection and a disable.
- A proposed candidate is validated by `Model::evaluate` against the original
  model, and the record's objective is the recomputed one. A producer's claimed
  objective is never read.
- An advised branching variable must lie in the recomputed fractional set. This
  is a termination requirement, not a preference: branching on an integral
  variable yields two children that do not tighten the box, which is the same
  hazard SPEC-0003 requirement 12a exists to prevent.
- Extension budgets are counted in invocations and proposals, never wall clock,
  so the search path cannot depend on machine speed and requirement 21's replay
  guarantee survives.
- The `backend` category is not introduced: `optimizer_core::Backend` is already
  public and replaceable under SPEC-0002, and declaring the category only to
  refuse it would read as a regression of an accepted contract.
- `transformation` is refused at declaration time, so no code path for it
  exists until its validity has its own contract.

## Local C2 Integration (2026-09-09)

Objective: integrate the reviewed feat/solver-executive branch into local main
and delete the feature branch after confirming its commits are retained.

Status: complete; fast-forward integration and feature-branch cleanup finished.

Acceptance gate: fast-forward integration preserves the reviewed tip 5a74184;
the feature branch is deleted and the worktree is clean. Resource budget: CPU
only, no GPU workloads.

Evidence (2026-09-09): main fast-forwarded from c742064 to 5a74184 without
conflicts or history rewriting, so the integrated tree is byte-identical to the
revision whose complete gate pass is recorded below. `git merge-base
--is-ancestor` confirmed the reviewed tip is retained on main, and `git branch
-d` removed the fully merged feat/solver-executive branch. The worktree is clean
and the bootstrap smoke was rerun on the integrated revision for clean
provenance.

No remote refs were changed. main remains unpushed pending separate
authorization; the origin remote and its outstanding protection settings are
recorded in [known failures](known-failures.md).

## C2 Owned Solver Executive Implementation (2026-09-09)

Objective: implement C2 under SPEC-0003: an owned branch-and-bound executive in
optimizer-solver that consumes the C1 backend contract as a relaxation service
and owns proof completion.

Status: complete; executive, contract documents, node representation and
acceptance tests are in place and the full gate passes with native acceptance
covered.

Acceptance gate: exhaustive tiny-model search compared against independent
enumeration, termination semantics, budgets, cancellation, proof completion, and
`bash tools/check.sh`. CPU only, four Cargo workers, no GPU workloads.

Expected changes: optimizer-solver runtime and tests, an end-to-end test in
optimizer-highs, SPEC-0003 implementation/test links, project records, changelog
and this task record.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked, with **zero skip messages**: format,
warnings-as-errors Clippy, 84 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny (advisories/bans/licenses/sources, fetched successfully this
run without the cached-database fallback), artifact validation, 20 Python tests,
41-page documentation/link validation and bootstrap smoke. Rust tests rose from
58 to 84: 22 new search contracts and 4 new native end-to-end contracts. No
checks were waived.

Cargo.lock changed only by adding local dependency edges for optimizer-solver
(optimizer-core, serde, serde_json) and the optimizer-highs dev-dependency on
optimizer-solver. No external package version changed.

Correctness evidence, stated as what was actually checked:

- 192 tiny discrete models over a fixed coefficient, bound and row-limit grid,
  both objective senses, integer and binary domains, agree with brute-force
  enumeration of the entire assignment space on the proven optimum and on proven
  infeasibility. The grid is fixed with no randomness, so a failure reproduces.
- Every non-optimal relaxation termination (time, iteration and node limits,
  interruption, feasible-without-proof, numerical failure, backend failure,
  unsupported) forfeits the proof claim and prunes nothing by bound.
- The executive runs entirely on test backends, which is what demonstrates
  backend neutrality; the end-to-end test over pinned HiGHS lives in
  optimizer-highs so optimizer-solver keeps that guarantee. Both agree with
  independent enumeration.

Resolved during implementation:

- The first test run did not terminate. A backend that returns the same
  fractional solution regardless of node bounds caused the executive to
  regenerate an identical child forever. Root cause: the executive trusted the
  relaxation solution to lie inside the node it asked about. Fixed by checking
  every relaxation solution against its own node before branching, which makes
  termination independent of backend correctness. Recorded as SPEC-0003
  requirement 12a rather than fixed silently.
- A record test asserted no `null` anywhere in the serialized record. That
  conflated two rules: absent *measurements* are omitted, while an absent
  *budget* stays an explicit null meaning unlimited, matching the C1
  configuration convention. The assertion now targets measurements by name.

Deferred and recorded rather than hidden: checkpoint restart is specified in
shape and deliberately unimplemented; no CLI subcommand exposes search yet; no
performance claim is made and no comparison against another solver was run.
Cross-node basis reuse remains Stage 5 reoptimization work.

Follow-up: C3, the extension runtime and authority model, is dependency-ready.
Write its specification before introducing any public extension API.

## C2 Solver Executive Specification (2026-09-09)

Objective: write and accept the C2 contract before any owned search API exists,
as required by AGENTS.md and the Stage 2 entry condition. No C2 behavior is
implemented by this change.

Status: complete; SPEC-0003 and ADR-0004 are accepted and the project records
that reference C2 are synchronized.

Acceptance gate: the specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation/link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and unchanged test counts, because no behavior changed.
Resource budget: CPU only, four Cargo workers, no GPU workloads.

Expected changes: docs/specifications/SPEC-0003-solver-executive.md,
docs/decisions/ADR-0004-owned-search.md, state/backlog.yaml, README.md,
implementation-plan.md, docs/architecture/overview.md, wiki/status.md, the two
stale placeholder doc comments in optimizer-solver and optimizer-schedule, and
this record.

Contract decisions worth recording, because they are the ones a later
implementation could get quietly wrong:

- A relaxation objective is admitted as a dual bound only when that relaxation
  reported `Termination::Optimal`. Any limit, interruption or failure leaves the
  node bound unavailable, forbids pruning that node by bound, and permanently
  forfeits the search's proof claim, recorded as `forfeited` in the record. This
  is what stops a timeout inside a child solve from silently discarding an
  optimal solution.
- `SearchOutcome` is a new type rather than a reuse of `Termination`. The two
  express different claims: one relaxation solve versus an exhausted node tree.
- The executive consumes the C1 `Backend` trait and must not depend on
  optimizer-highs, so the pruning and forfeiture rules are testable against a
  stub backend without the native library.
- `Tolerances.integrality` governs both incumbent acceptance and the decision to
  branch, so the two cannot disagree.
- Checkpoints are specified in shape only; restart is deliberately not part of C2
  and needs its own acceptance evidence.

Numbering: no spec-numbering convention exists in the repository, so SPEC-0003
and ADR-0004 take the next free sequential numbers. Two placeholder doc comments
referenced the retired M0-M6 scheme and dangled at nonexistent specifications;
optimizer-schedule's stale "SPEC-0003" claim would have collided with this
specification and now names C5 with an unassigned number.

No CHANGELOG.md entry accompanies this change: the changelog records user-visible
changes, and an accepted contract with zero behavior is not one. C2 enters the
changelog when its behavior ships.

Follow-up: C2 implementation is now dependency-ready under SPEC-0003. It requires
a stub-backend test crate for the bound-validity and forfeiture rules plus
exhaustive tiny-model comparison against independent enumeration.

## Local C1 Integration (2026-09-09)

Objective: verify the reviewed feat/highs-backend branch from a clean checkout,
integrate it into local main, and delete the feature branch after confirming its
commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip c8bb6f3; the
feature branch is deleted and the worktree is clean. Resource budget: CPU only,
four Cargo workers, no GPU workloads.

Evidence (2026-09-09): the branch was cloned to /tmp/c1-verify with no populated
target/native, and `bash tools/check.sh` passed there in 1 minute 43 seconds.
That run built the pinned HiGHS 1.11.0 library from the checksum-verified
upstream archive, produced both libhighs.a and the standalone executable, and ran
58 Rust and 20 Python tests with **zero skip messages**, so native acceptance was
genuinely covered rather than bypassed. The clean clone also solved
examples/model-v1.json to `termination: optimal`, `objective: 2.5`,
`backend_version: 1.11.0` with an independently validated feasible incumbent and
exit 0, and wrote a smoke record bound to revision c8bb6f3 with `dirty: false`.

This clean-checkout pass is the acceptance evidence for the integration. main was
fast-forwarded from 9b42b62 to c8bb6f3 without conflicts or history rewriting, so
the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained on main, and
`git branch -d` removed the fully merged feat/highs-backend branch. No remote refs
were changed; main remains 9 commits ahead of origin/main and unpushed, pending a
separate authorization to push.

The advisory database fetch failed again during the clean-clone run and recovered
through the cached database, as recorded in
[known failures](known-failures.md). No checks were waived.

Follow-up: C2, the owned solver executive, is dependency-ready. Its specification
is now accepted as SPEC-0003; see the C2 record at the top of this file. No C2
behavior existed at the time of this integration.

## C1 Backend-Neutral Solve Contract and HiGHS Adapter (2026-09-09)

Objective: implement C1 under SPEC-0002: backend-neutral solve/session types,
HiGHS adapter boundary, strict solve configuration and structured records.

Status: complete; contract, native adapter, solve CLI, schemas and acceptance
tests are in place and the full gate passes with native acceptance covered.

Acceptance gate: core and adapter contract tests, strict CLI solve flow,
status/cancellation/limits/warm-start behavior, reproducible records, and
`bash tools/check.sh`. CPU-only; native HiGHS setup uses the pinned 1.11.0
source and at most four build workers.

Expected changes: optimizer-core, optimizer-highs, optimizer-cli, experiment
schemas, specifications, changelog, tests, and task state. No GPU workload.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked: format, warnings-as-errors Clippy, 58 Rust
tests, workspace build, warnings-as-errors rustdoc, cargo-deny
(advisories/bans/licenses/sources), artifact schema/provenance, 20 Python tests,
38-page documentation/link validation and bootstrap smoke. No checks were waived.

Native provisioning and FFI: `tools/setup_highs.sh` builds the pinned static CPU
library under `target/native/highs-1.11.0/install` from the checksum-verified
upstream archive. A hand-written private FFI module links it; no `highs-sys`
dependency is introduced. `Highs_version()` reports 1.11.0 and the compile-time
assertion confirms a 4-byte `HighsInt`, matching the pinned `HIGHSINT64=OFF`.

Differential acceptance: the standalone executable, built from the same source,
is driven as a separate process over generated LP files and agrees with the
adapter on status and objective for LP, objective-offset, equality, ranged, MILP
and infeasible cases. Disagreement fails the test rather than deferring to the
adapter. The reference is run in a sandbox directory with its log redirected, so
native output cannot litter the tree.

Correctness contracts verified: all 18 native model statuses map explicitly with
no catch-all arm; extracted candidates are re-validated through SPEC-0001 before
publication and a validation failure becomes a numerical failure rather than an
optimality claim; a pre-cancelled solve returns interrupted without creating
native state; limits and interruptions never satisfy `proves_completion`; binary
bounds intersect [0,1] regardless of declared bounds; coefficients below the
native small-matrix threshold are rejected instead of being silently dropped; a
basis is bound to a canonical-model fingerprint, so changed data under an
unchanged `model_id` is rejected.

Resolved review findings during implementation:

- The workspace `unsafe_code = "forbid"` made ADR-0003's native boundary
  unimplementable: `forbid` cannot be relaxed by an inner crate
  (`E0453 overruled by previous forbid`). optimizer-highs now declares its own
  `[lints.rust]` block with `unsafe_op_in_unsafe_fn` denied.
- `serde_json` serializes a nonfinite `f64` as `null`, which is indistinguishable
  from an absent field, so SPEC-0002's absent-not-null rule cannot rely on a
  serializer error. Records omit absent measurements and reject nonfinite ones
  explicitly as numerical failures.
- The stub adapter's pre-cancellation path required a provisioned library, which
  contradicted requirement 6. The check now precedes native dispatch and is
  answered identically with or without the library. Found by running the gate
  with the library deliberately absent.
- A no-op `.max()` in bound conversion and an unfulfilled lint expectation were
  caught by Clippy and removed.

Deferred and recorded rather than hidden: sanitizer runs over repeated native
lifecycles are not yet in the gate; presolve, scaling and reoptimization remain
Stage 5 work; owned search remains C2.

## Roadmap redesign (2026-09-09)

Objective: replace the narrow M0-M6 implementation sequence with the
architecture-driven C1-C7 capability roadmap in implementation-plan.md.

Status: complete; plan and backlog metadata synchronized.

Acceptance gate: roadmap is decision-complete, preserves M0/M1 evidence, keeps
HiGHS as the first replaceable backend, defines executive/extension/SDK/GPU
gates, and bash tools/check.sh reaches the required gate.

Evidence: implementation-plan.md, state/backlog.yaml, README.md, and CHANGELOG.md
now describe C1-C7 and the next dependency-ready task is C1. `git diff --check`
passes. `bash tools/check.sh` reaches preflight but cannot start Cargo because
the environment cannot create its sandbox namespace; no Rust checks were waived.

## M2 Backend Contract and Implementation (2026-09-09)

Objective: implement the approved M2-M6 plan sequentially, starting with the
HiGHS backend contract, safe lifecycle, validated solving and reproducible records.

Status: superseded; see the C1 record at the top of this file. The M2-M6 sequence
was replaced by the evidence-staged roadmap, and this objective was delivered as
C1 under the same SPEC-0002 and ADR-0003 contracts.

Acceptance gate: accepted SPEC-0002 and supporting ADR; standalone HiGHS
differential LP/MILP tests, explicit statuses, cancellation/limits, warm starts,
lifecycle sanitizers, structured records, and bash tools/check.sh. Inspect and
fix review findings before committing.

Expected changes: optimizer-highs, core solve contracts, CLI, experiment schemas,
native build/validation tooling, tests, specifications, ADRs and project state.
Resource budget: CPU only, at most four workers, bounded deterministic
tests and benchmark batches of at most 30 minutes. GPU work will use one shared
host GPU lease at a time. Existing M0/M1 defaults remain unchanged.

Follow-up order under the current roadmap: C2 owned executive, C3 extension
runtime, C4 SDK/registry, C5 flow shop, C6 GPU feasibility, C7 adaptive research.
No remote publication is included.

## Local M1 Integration (2026-09-08)

Objective: merge the reviewed feat/model-validation branch into local main and
delete the feature branch after confirming its commits are retained.

Status: complete; local integration and feature-branch cleanup finished.

Acceptance gate: fast-forward integration preserves reviewed commit 27b1b3a;
bash tools/check.sh passes on main; the merged feature branch is deleted and the
worktree is clean after recording evidence. Expected changes: local Git refs and
this task record. Resource budget: CPU only, four Cargo workers, no GPU workloads.

Evidence (2026-09-08): main fast-forwarded from 9e6dc86 to reviewed tip 27b1b3a
without conflicts or history rewriting. git merge-base --is-ancestor confirmed
the reviewed tip is retained on main, and git branch -d removed the fully merged
feat/model-validation branch. No remote refs were changed.

The unchanged runtime passed the complete acceptance gate before integration,
as recorded below. Two post-merge attempts passed format, Clippy, all 29 Rust
tests, workspace build and rustdoc, then stopped because the RustSec advisory
database could not be fetched. These attempts do not constitute a new full-gate
pass; the successful pre-integration gate remains the full acceptance evidence.
The only additional tracked change is this integration record, validated with
the documentation/link builder and git diff --check before committing.

## Repeated Branch Review (2026-09-08)

Objective: review the complete feature branch against main, fix any substantiated
findings, and repeat until the final review has no unresolved actionable findings.

Status: complete.

Acceptance gate: inspect every changed runtime path and the SPEC-0001/ADR-0002
contracts, verify relevant regression coverage, and run bash tools/check.sh.

Expected changes: this review record and any bounded fixes supported by reproduced
failures. Resource budget: CPU only, at most four Cargo workers, deterministic
tests, no GPU workloads. Review base: local main at 9e6dc86; starting HEAD: 58df6bb.

Current finding: model validate panics with exit 101 when a model/candidate path
contains non-UTF-8 bytes because main uses env::args. Preserve native paths with
args_os and report malformed non-path text as an argument error. Expected fix:
CLI parsing, Unix path/error regression tests, specification and release notes.
Follow-up finding: incomplete/unknown model commands returned bare usage without
the required argument category. Add a categorized dispatch error and regression.

Evidence (2026-09-08): both new regressions failed before their fixes and pass
afterward. Native model/candidate filenames retain their OS representation;
non-UTF-8 command, flag and tolerance text returns an argument error with exit 2.
Incomplete and unknown model commands now return the same error category.
Unix regressions cover real non-UTF-8 filenames, successful reports and missing
files. Specifications, tutorial, changelog and regression instructions agree.

The final complete bash tools/check.sh gate passed: format, warnings-as-errors
Clippy, 29 Rust tests, workspace build, rustdoc, cargo-deny, artifact validation,
8 Python tests, 36-page documentation/link validation and bootstrap smoke.
Temporary RustSec advisory-fetch failures recovered; no checks were waived.
Cargo preflight checks also passed for missing Cargo (exit 127 with a diagnostic)
and the rustup-only PATH fallback to the pinned Rust 1.93.1 toolchain.

Final review against local main at 9e6dc86534de2efa414205752ca58d7584976052
found no unresolved actionable findings. Coverage included strict JSON parsing,
canonical model construction, candidate coverage, arithmetic and tolerance
contracts, report output, CLI errors, dependencies, specifications and fixtures.
The existing independent dense oracle covers 18,522 evaluations and the f64
round-trip suite covers 968 values. Resource use remained CPU-only with four
Cargo workers; scope remains M1. Commit after acceptance, then rerun bootstrap
smoke to record the clean committed revision.

## M1 Review Contract Fixes (2026-09-08)

Objective: reject alternate JSON representations for all model/candidate input
types and return categorized CLI I/O errors when report output fails.

Status: complete.

Acceptance gate: regressions for positional records, object-wrapped enums,
and failed stdout writes; full bash tools/check.sh under SPEC-0001 and ADR-0002.

Expected changes: optimizer-core document parsing, optimizer-cli report output,
contract tests, minimized fixtures, specification clarifications, changelog,
and this task record. Resource budget: CPU only, four Cargo build workers,
bounded deterministic tests, no GPU workloads.

Evidence (2026-09-08): new regressions reproduced accepted alternate JSON forms
and exit 101 on failed stdout before their fixes. Public record types and tagged
bounds now reject positional arrays; domain/objective enums require strings.
Direct and nested parsing tests pass, preserving unknown/duplicate-field rejection
and f64 round trips. CLI tests verify categorized io errors and exit 2 for /dev/full
and closed pipes in structural and candidate modes. Output writes and flushes
are fallible; the specification clarifies that delivered bytes cannot be retracted.

The complete bash tools/check.sh gate passed: format, warnings-as-errors Clippy,
26 Rust tests, workspace build, rustdoc, cargo-deny, artifact validation, 8 Python
tests, 36-page documentation/link validation, and bootstrap smoke. No checks were
waived. Rust 1.93.1, four Cargo workers, and CPU-only simulations were used.
Minimized JSON fixtures and reproduction instructions are in tests/regression/.
Both review findings are resolved; no dependency or numerical-policy changes.

## Commit and Branch Review (2026-09-08)

Objective: validate and commit the pending acceptance-script diagnostic change,
then review the complete feature branch against local main in PR style.

Status: complete; committed as 4981aef and reviewed against local main.

Acceptance gate: run bash tools/check.sh before committing; inspect the complete
main-to-branch diff against SPEC-0001 and ADR-0002 and report actionable findings.

Expected changes: the pending tools/check.sh change and this task record.
Resource budget: CPU only, at most four Cargo build workers; no GPU workloads.

Evidence (2026-09-08): the complete bash tools/check.sh gate passed with Rust
1.93.1 and four Cargo workers: format, Clippy, 22 Rust tests, workspace build,
rustdoc, cargo-deny, artifact validation, 8 Python tests, 36-page documentation
build/link validation, and bootstrap smoke. No checks were waived. Review found
alternate JSON representations and panicking stdout writes, resolved by the M1
review contract fixes above. The comparison base was local main
at 9e6dc86534de2efa414205752ca58d7584976052 (also origin/main locally).

## Current diagnostic fix (2026-09-08)

Objective: make the acceptance gate locate the repository-pinned Rust toolchain and report executor failures clearly.

Status: complete.

Acceptance gate: shell syntax and toolchain preflight behavior pass; existing Rust gate remains unchanged after Cargo is resolved.

Evidence (2026-09-08): `bash -n tools/check.sh` passed. With Cargo absent, the gate exits 127 with an actionable diagnostic instead of an opaque `command not found`; with the pinned toolchain bin directory available, the existing Rust checks remain the executed gate.

Expected changes: tools/check.sh and this task record.

Resource budget: CPU only; no GPU workloads.


Objective: implement M1 core models, candidate validation, versioned JSON, and CLI.

Status: complete.

Acceptance gate: accepted SPEC-0001 and ADR-0002; independent property/exhaustive
model tests, serialization and numerical boundary tests, CLI contracts, and
the complete bash tools/check.sh gate. Commit locally after acceptance.

Expected changes: optimizer-core, optimizer-cli, model fixtures/examples,
specification and ADR, current scope/status documentation, changelog, task state.
Resource budget: CPU only, at most four Cargo build workers, bounded deterministic
tests; no GPU workloads. Existing smoke seeds and configuration remain unchanged.

Evidence (2026-09-08): accepted SPEC-0001 and ADR-0002 preceded implementation.
The complete bash tools/check.sh gate passed after the final runtime/test edits:
format, warnings-as-errors Clippy, 22 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny advisories/bans/licenses/sources, artifact schema/provenance,
8 Python artifact tests, 36-page documentation/link build, and bootstrap smoke.
No checks were waived. The 14 new Rust contracts include 18,522 independent dense
oracle evaluations, generated model ordering properties, 968 finite f64 values
round-tripped through both model and candidate JSON, numerical/domain boundaries,
edge-model fixtures, CLI exit/report behavior, and exact 16 MiB file boundaries.

Resolved regression: Serde internally tagged unit variants accepted an unknown
field on infinite bounds. Strict bound deserialization now rejects the minimized
fixture in tests/regression/infinite-bound-extra-field.json; its contract test passes.

Environment: Rust 1.93.1 and cargo-deny 0.19.0 under /tmp/ai-optimizer-cargo,
RUSTUP_HOME=/tmp/ai-optimizer-rustup, Python tooling /tmp/ai-optimizer-venv,
CARGO_BUILD_JOBS=4. Core contracts completed in 0.17 s and CLI model contracts in
0.78 s in the final gate. Work was CPU-only; lease tests used temporary locks and
simulated jobs. Cargo.lock only adds local core/CLI dependency edges; no external
package versions changed. Serde JSON's float_roundtrip feature preserves f64 input.

Provenance: the precommit gate's smoke honestly records a dirty working tree.
The local feature commit is followed by a smoke rerun for clean revision-bound
provenance at artifacts/bootstrap-smoke.json. This remains CLI startup evidence,
not solver or GPU performance. No push or hosting changes are part of M1.

Follow-up: M2 is dependency-ready. Write SPEC-0002-backend-contract.md before
implementing HiGHS lifecycle, status mapping, cancellation, limits and solve records.
No M2 behavior is implemented here.

## Previous Repository Synchronization

Objective: synchronize the project to https://github.com/liuyumou/OptForge.git.

Status: complete.

Acceptance gate: origin points to the requested repository; main is pushed with
upstream tracking; the remote main revision matches local HEAD; the worktree is
clean. Preserve existing history and validate updated documentation.

Expected changes: Git remote/tracking configuration and repository hosting/task
records. Resource budget: bounded CPU checks and Git operations; no GPU work.

Evidence: the original main history was pushed successfully and main now tracks
origin/main. The complete tools/check.sh gate passed, including 8 Rust tests,
8 artifact tests, dependency policy, documentation, and smoke validation. Hosting
records identify the remote. The synchronization includes this documentation
update; remote revision equality and clean worktree are checked after its push.

## M0 Bootstrap Evidence

Objective: implement M0 from implementation-plan.md.

Status: complete.

Acceptance gate: pinned Rust workspace builds; format, Clippy, tests, dependency
policy, rustdoc, documentation links/build, schemas, and benchmark smoke pass.
GPU discovery must report available UUIDs or an explicit unavailable state.
Simulated jobs must serialize and release ownership after cancellation or exit.

Expected changes: repository bootstrap, crates, tools, schemas, CI, documentation,
examples, benchmark fixtures, and task state. Preserve both original plans.

Resource budget: CPU-only builds and bounded tests; GPU discovery only, no kernels.
One developer, one bounded milestone. M1-M6 remain dependency-ordered backlog.

Evidence before initial commit: Rust workspace build, format, warnings-as-errors
Clippy, 8 Rust unit/integration tests, rustdoc, cargo-deny (advisories, bans,
licenses, sources), 8 Python artifact tests, schema/provenance validation, shell
syntax, and a 33-page documentation/link build passed. Discovery returned all
three expected physical GPU UUIDs without launching kernels.

Clean-checkout acceptance: the complete tools/check.sh gate passed on revision
a628c0c8605dd2434cdf7fd775fae85e96423a31 in an independent local clone at
/tmp/ai-optimizer-m0-verification. It rebuilt every crate and generated a validated
measured smoke record with dirty=false. No acceptance checks were waived.

Verified lease cases: competing-process timeout and serialization, normal release,
SIGINT while waiting, SIGTERM while holding, SIGKILL recovery, and interoperability
with the shell runner's flock primitive. All were CPU simulations. Inventory
reported two RTX 5090 devices and one RTX PRO 6000 by their expected UUIDs.

Artifacts: the clean-clone record is at
/tmp/ai-optimizer-m0-verification/artifacts/bootstrap-smoke.json. The workspace
runner can reproduce artifacts/bootstrap-smoke.json. Records measure CLI startup
only; no solver or GPU performance result is claimed.

Environment: Rust 1.93.1 and cargo-deny 0.19.0 were installed under
/tmp/ai-optimizer-cargo with RUSTUP_HOME=/tmp/ai-optimizer-rustup. Documentation
and schema tooling use /tmp/ai-optimizer-venv. Hosting workflows are configured
but were not run on GitHub; remote protection and GPU-runner provisioning remain
external setup, as documented in state/known-failures.md.

Follow-up: M1 is dependency-ready. Write SPEC-0001-model-and-validation.md, then
implement the original-model numerical authority boundary and its independent
property/exhaustive tests. No M1 behavior has been implemented as part of M0.

## Toolchain recovery (2026-09-09)

The pinned Rust toolchain was present under `/tmp/ai-optimizer-cargo` and
`/tmp/ai-optimizer-rustup` but absent from the default PATH. `tools/check.sh`
now discovers those locations and sets `RUSTUP_HOME` automatically, and the
search order is overridable through `AI_OPTIMIZER_CARGO_HOME` rather than being
hardcoded to one machine's layout.

Superseded detail: this record previously stated that the gate stopped at
artifact validation for a missing Python `jsonschema`. That diagnosis is stale.
`jsonschema` is present and artifact validation passes; the missing module was
`Markdown`, which `tools/requirements.txt` already pins. The gate now checks both
imports as a precondition, so this class of failure is reported in seconds rather
than after several minutes of compilation. C1 native HiGHS and solve CLI
implementation are now complete; see the C1 record at the top of this file.
