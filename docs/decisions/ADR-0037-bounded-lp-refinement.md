# ADR-0037: Bounded original-residual LP refinement

Status: accepted bounded admission and implementation contract, 2026-10-22
Owner: numerical backend
Introduced: GPUP-REFINE
Last reviewed commit: bootstrap
Superseded by: none

## Decision

The user accepts the native-FP64-outer subset of SPEC-0021. Admit CPU proof and
oracle validation before runtime/device work. A reproducible numerical or
resource admission failure closes this bounded investigation with the exact
counterexample and failed gate; do not implement or execute dependent paths.
This is a bounded method investigation, not a convergence theorem or a preset.

Canonicalize the original LP as minimization, including its offset; use
v=(x,z), B=[A,-I], g=(c,0), b=0 and the original variable/row box bounds.
Introduce no finite substitute for infinity. Residuals are rp=b-Bv and
rd=g-B^T y. The correction objective is Delta_d*rd, equality right-hand side
Delta_p*rp and box Delta_p*(l-v) <= d <= Delta_p*(u-v). Publish
v_next=v+d/Delta_p and y_next=y+w/Delta_d through original-model mappings.
Original-model host certification remains the sole authority.

Delta_p and Delta_d are positive powers of two. Normalize the corresponding
maximum residual magnitude toward [1,2); use one for zero residuals. Reduce the
exponent when required for representable transformed data, and refuse if no
admissible exponent remains. Track all shift, scaling, anchor and update errors;
finite endpoints cannot silently become infinite, and nonzero values cannot
silently disappear. The accurate path uses original FP64 data with outward
host enclosures, not residuals of the represented matrix.

### Merit and bounded oracle

Freeze s_v[j]=max(1,abs(initial v[j]), magnitudes of finite box endpoints),
s_g[j]=max(1,abs(g[j])) and s_p[i]=max(1,sum_j abs(B[i,j])*s_v[j]).
All are original-unit quantities. The merit is the maximum of equality residual
abs(b-Bv)/s_p, box violation/s_v, and projected stationarity
abs(v-project_box(v-(s_v/s_g)*(g-B^T*y)))/s_v. Evaluate outward intervals for
the exact real definitions at the represented master values. Unrepresentable
normalizers or intermediate bounds refuse; an uncertain merit is not zero.
This projected residual replaces explicit bound multipliers in this subset.
Its exact zeros must be equivalent to box stationarity, including fixed/free
and one-sided coordinates. It must not be interpreted as a certificate.

An uncertified correction requires merit_next.upper <= merit_anchor.lower/2.
Use the minimum requested positive feasibility/gap tolerance as the merit floor;
at/below the floor require original certification, with only the remaining
declared native recovery if certification fails. Allocate at most one eighth
of the anchor merit to propagated numerical error: representation,
product/reduction, anchor/transform and state/update each receive one thirty-second.
The CPU admission proof must establish the maps and conservative error accounting
before accepting an inner oracle. Observed progress is checked, never assumed.

At most 32 outer corrections, 2000 physical updates per correction attempt and
50000 physical updates globally are admitted. Keep the inherited 200-update
assessment schedule, plus correction-boundary and final assessments. Failed work
remains charged. Native FP64 iterates, updates and controller state are retained;
the low-precision candidates use FP32 coefficients, sparse products and reductions.
The implicit identity remains an explicitly accounted analytic block.

The inner method uses the existing PDHG/Halpern recurrence and recorded
restart/weight settings, with prepared transformed preconditioning and checked
correction-vector rebinding. Both orientations derive from one canonical matrix
and transpose map. Restrict steps using conservative original/represented norms,
including scaling error and the activity block. Anchors maintain deltas directly
and bind products, scales, error summaries and generation. Refresh before
committing an inadmissible step, with at most eight refreshes per correction
attempt. One charged, sticky FP32-to-FP64 promotion may restart the current
correction from its outer anchor. Native failure terminates; cancellation,
deadline expiry and device failure never start recovery work.

### Interface and compatibility

If CPU admission passes, implement isolated, feature-gated host/device refinement
modules and image, lp-refine-v1 settings and strict request/evidence schemas,
and a study-only lp_precision_refine solve|verify|replay example. Checkpoints
contain every numerical/controller/anchor/scale/assessment field and identity.
Restoring them cannot reduce physical work or extend deadlines. Evidence binds
the original model, settings, source, executable, image and executed device, with
separate update/correction/refresh/promotion/certification counters. Old APIs,
defaults, kernels and records retain their meanings. No new unsafe or external
solver boundary is admitted; ordinary builds need no toolkit/device.

Expansion masters, FP32 working state, selective precision, assessment scheduling,
sessions, persistence and supported presets are outside this decision.

## Resource authority

Allocate 3600 GPU seconds within the existing 21602.574545061-second cumulative
ceiling: timing/screening 2300, profiles/ablations 450 and acceptance/repeatability
850. Existing phase caps 1800/9500/7650/4450/9000 and overall 28800 persist.
The complete 16452-event prefix SHA-256 is
24949150272600fe58364f25ebbf7bf892f7454da342edc268d50684568c5f18;
cumulative consumption is 17665.546083611 seconds. Preserve every historical byte.

After numerical admission, freeze tuned FP64, refinement FP64, refinement FP32
and anchored refinement FP32 over the eight GPUP-EXEC development models, three
timing repetitions and twelve 200-update profiles. Preserve seeds, tolerances
and 10/30-second deadlines. Reserve deadline+6 seconds per job: at most 2256
timing, 432 profile and 762 initial acceptance seconds (three 120-second jobs
and four 90-second sanitizers). Failures remain charged and primary identities
are not retried. All jobs use the shared host lease and activity admission on
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48; no automatic device substitution.

CPU cap 21600 seconds/four jobs, host RSS 8 GiB, device resident/preparation
1/2 GiB, new artifacts 32 GiB. Original dimensions are at most 65536 each and
stored nonzeros at most 2^23; count n+m transformed variables and nnz(A)+m
logical entries, both sparse views, all anchors, checkpoints, error summaries
and promotion peak before allocation. No historical headroom creates another task.

## Acceptance

Independent rational tiny-LP forward/reverse feasibility, objective/offset and
dual maps; projected KKT equivalence; both product orientations and conservative
error envelopes precede runtime admission. Exercise inaccurate/stalled oracles,
all bound shapes and objective senses, extreme scales/subnormals, overflow,
memory, stale generations, cancellation and monotonic-work checkpoint recovery.
The full pinned-native tools/check.sh gate is mandatory. Admitted kernels also
require actual generated instruction/resource review, CPU differentials,
fresh-process repeatability, fixed-work replay and four scoped sanitizers.
Retain every failed attempt and report full fresh costs and coverage. A CPU
admission refusal reports no device/runtime acceptance or measured solver benefit.
