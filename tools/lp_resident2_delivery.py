"""CPU-only final audit of immutable RESIDENT2 artifacts; never reruns a solver."""
import hashlib
import json
from pathlib import Path
import shutil
import statistics

from lp_resident2_common import BASE, ROOT, CPU_CAPS, GPU_CAPS, checked, load, put, ref, require
from lp_resident2_budget import accounting
from lp_resident2_study_v4 import MANIFEST, verify, physical_counts


def audit(auditing_job=None):
    m=load(MANIFEST);verify(m)
    r=load(ROOT/'docs/benchmarks/data/resident2-result-v1.json')
    require(len(r['rows'])==64 and all(x['status']=='completed' for x in r['rows']), 'incomplete cohort')
    matched=0;limits=[]
    for c in r['rows']:
        if c['mode']!='control':continue
        d=next(x for x in r['rows'] if x['mode']=='resident' and all(x[k]==c[k] for k in ('model_id','lifecycle','repetition')))
        for left,right in zip(c['results'],d['results']):
            for result in (left,right):
                checked(result['candidate']);checked(result['certificate'])
            if left['accepted'] and right['accepted']:
                require(left['candidate']['sha256']==right['candidate']['sha256'] and left['iterations']==right['iterations'],
                        'certified native endpoint or iteration differs')
                matched+=1
    for row in r['rows']:
        require(sum(row['phases_ns'].values())==row['elapsed_ns'],'phase partition differs')
        w=load(checked(row['worker']))
        for result,raw in zip(row['results'],w['rows']):
            require(result['counters']==physical_counts(raw),'physical counter reader differs')
            if row['model_id']=='gpup-extension-mixed-65536':
                c=load(checked(result['certificate']));v=load(checked(result['candidate']))
                require(len(v['primal'])==len(v['dual'])==65536 and c['bound'] is None and not c['accepted'],
                        'normal-limit or bound status differs')
                limits.append(dict(candidate=result['candidate'],certificate=result['certificate'],stop=result['stop'],
                    feasible=c['validation']['feasible'],refusal=c['refusal']))
    require(matched==42 and len(limits)==12,'endpoint roster differs')
    prior=load(BASE/'prior-sources.json')
    bridge=load(ROOT/'docs/benchmarks/data/resident2/prerequisite-source-bridge.json')
    allowed={x['path']:x for x in bridge['files']}
    exact=0
    for old in prior['files']:
        now=ref(ROOT/old['path'])
        if now==old:exact+=1;continue
        b=allowed.get(old['path']);require(b is not None,'unbridged historical source change')
        require(b['before_sha256']==old['sha256'] and b['after_sha256']==now['sha256'],'source bridge differs')
        require(ref(ROOT/b['frozen_path'])['sha256']==old['sha256'],'frozen source differs')
    settlements=[]
    for path in sorted((BASE/'resources').glob('*.reservation.json')):
        s=path.with_name(path.name.replace('.reservation.json','.settlement.json'))
        if not s.exists() and path.stem == str(auditing_job)+'.reservation':
            continue  # The enclosing audit job is conservatively charged in accounting below.
        require(s.exists(),'unsettled reservation')
        result=load(s);require(not result['overrun'],'resource overrun')
        resource=load(checked(result['resource']))
        require(resource['guardian_cleanup']['empty'],'guardian cleanup not empty')
        require(resource['result']['cleanup']['empty'],'workload cleanup not empty')
        settlements.append(dict(reservation=ref(path),settlement=ref(s),result=result))
    cpu,gpu=accounting()
    require(all(cpu[k]<=v*10**9 for k,v in CPU_CAPS.items()),'CPU cap exceeded')
    require(all(gpu[k]<=v*10**9 for k,v in GPU_CAPS.items()),'GPU cap exceeded')
    return dict(schema_version=1,kind='lp-resident2-delivery-audit',manifest=ref(MANIFEST),result=ref(ROOT/'docs/benchmarks/data/resident2-result-v1.json'),
        settled_cells=64,endpoints=96,strict_certificates=84,certified_bitwise_pairs=matched,normal_limit_endpoints=limits,
        prior_source_files_exact=exact,source_bridge=ref(ROOT/'docs/benchmarks/data/resident2/prerequisite-source-bridge.json'),
        fixture_bridge=ref(BASE/'fixture-source-bridge-v2.json'),reader_admission=ref(BASE/'reader-admission-v4.json'),
        cpu_caps_seconds=CPU_CAPS,gpu_caps_seconds=GPU_CAPS,cpu_charged_ns=cpu,gpu_charged_ns=gpu,
        total_cpu_ns=sum(cpu.values()),total_gpu_ns=sum(gpu.values()),resources=settlements,
        masked_compile_failure=ref(BASE/'masked-compile-failure.json'),cleanup='All earlier settled resource guardians/workloads empty; the enclosing final audit reservation is finalized separately.', finalization_job=auditing_job,
        acceptance='Full native gate v2 (638 Rust, 515 Python, replay, 190 docs and smoke); exact test-only overflow correction, scoped lint/CPU checks; boundary/controller device comparisons, four independent transport certificates and four zero-error sanitizers; two new physical-counter CPU tests plus existing contracts after artifact-reader correction.',
        retained_failures='Initial compile failure, masked example compilation failure (full reservation supplemented), first full-gate historical-fixture refusal, invalid overflow fixture and stale test-binary selection. Original artifacts and full failed charges retained. No timing cell retried.')


def report_text():
    r=load(ROOT/'docs/benchmarks/data/resident2-result-v1.json')
    rows=r['rows'];names=list(dict.fromkeys(x['model_id'] for x in rows))
    lines=['# GPUP-RESIDENT2: native resident execution and complete delivery costs','',
        'Status: bounded implementation and comparison complete, 2026-11-11; performance retention gate fails.','',
        'Decision: keep the matched tuned native control. The resident candidate preserves certified coverage and reduces synchronization, but does not establish the required complete-delivery improvement. Its cold model-median geometric mean is **%.6fx**; four of seven certified model medians are below 1.0. No supported preset or faster-arithmetic claim follows.'%r['cold_geomean'],'',
        'Contract: [SPEC-0024](../specifications/SPEC-0024-native-resident-execution.md) and [ADR-0053](../decisions/ADR-0053-native-resident-execution.md). [Machine results](data/resident2-result-v1.json), [frozen manifest](data/resident2-manifest-v4.json), [delivery audit](data/resident2-acceptance-v1.json), and [source bridge](data/resident2/prerequisite-source-bridge.json).','',
        '## Implementation and endpoints','',
        'The feature-gated [runtime](../../crates/optimizer-lp-cuda/src/resident2.rs) adds immutable prepared models and a separate resident session. Cold workers include model parsing, preparation, context creation and import. Prepared batches reuse the same immutable model/residency for three fresh projected-zero solves; every solve has a fresh controller, working buffers and independent original-model certificate.','',
        'The candidate precomputes at most 200 exact native FP64 coefficient pairs. One buffer carries their binary64 bits and disjoint u64 sticky flags. Warp32 fused kernels retain the original arithmetic order, predicate failed coordinates, and submit no more than 200 updates before observation. Host adoption is transactional: read both vectors and all flags into scratch, reject a flagged/nonfinite window, preserve the complete host checkpoint and charge attempted work. Cancellation is polled every 64 submissions and after readback; required host control checks remain every 200 updates.','',
        'The [driver](../../crates/optimizer-lp-cuda/examples/lp_resident2.rs) exports actual original-unit vectors on normal limits. The active coordinator is [study v4](../../tools/lp_resident2_study_v4.py); v1–v3 and all failed acceptance artifacts remain immutable. Existing backends, numerical bodies, public defaults and the strict 1e-9 checker are unchanged.','',
        '## Frozen comparison','',
        'Eight development models, two modes, three paired cold repetitions and one prepared batch of three per mode/model produce **64 completed cells and 96 endpoints**. No cell was retried or omitted. Each mode certifies **42/48 endpoints**; all 42 certified control/resident pairs have identical candidate bytes and iteration counts. The remaining twelve mixed-model endpoints are delivered and uncertified.','',
        'All jobs use the RTX PRO 6000 UUID pinned in the manifest, four CPU slots, one shared GPU lease, 50000 update allowance and an eight-second native deadline. Cold cells reserve 60 wall seconds and prepared cells 100, including the independent checker. Native limits remain limits. Parent elapsed includes process startup/teardown, durable worker output and independent checker delivery; the final parent receipt write is excluded. Native host-cost instrumentation is enabled identically in both modes and adds no device synchronizations. Nested native costs are subsets, never added again to phase totals.','',
        'Ratios are control/resident: above one favors resident. The range is the three observed paired ratios, not a confidence interval. Three repetitions do not establish a general performance ranking. Prepared throughput has one batch per mode/model and no independent repetition uncertainty.','',
        '| Model | Control cold median (s) | Resident cold median (s) | Median paired ratio | Observed ratio range | Strict endpoints per mode |','| --- | ---: | ---: | ---: | --- | ---: |']
    for name in names:
        c=[x for x in rows if x['model_id']==name and x['mode']=='control' and x['lifecycle']=='cold']
        d=[x for x in rows if x['model_id']==name and x['mode']=='resident' and x['lifecycle']=='cold']
        pairs=[p['ratio'] for p in r['pairs'] if p['model_id']==name and p['lifecycle']=='cold' and p['ratio'] is not None]
        ratio=f'{statistics.median(pairs):.6f}' if len(pairs)==3 else 'ineligible'
        span=f'{min(pairs):.4f}–{max(pairs):.4f}' if pairs else '—'
        count=sum(t['accepted'] for x in rows if x['model_id']==name and x['mode']=='control' for t in x['results'])
        lines.append(f"| {name.removeprefix('gpup-development-').removeprefix('gpup-extension-')} | {statistics.median(x['elapsed_ns'] for x in c)/1e9:.6f} | {statistics.median(x['elapsed_ns'] for x in d)/1e9:.6f} | {ratio} | {span} | {count}/6 |")
    lines+=['','The predeclared retention rule requires no coverage loss, improvement in every fully certified cold model median, a geometric mean of at least 1.05, and useful work. Coverage is preserved; the latency conditions fail. Mixed-model durations above are delivery observations, not certified speedups.','',
        '## Where complete time goes','',
        'Dense-65536 illustrates the remaining host/evidence cost. These are separate phase medians (their sum need not equal the median of the total); each individual row has an exact disjoint partition including an unattributed residual.','',
        '| Phase | Control median (s) | Resident median (s) |','| --- | ---: | ---: |']
    for phase in ['conversion','preparation','import','native','export','check','output','unattributed']:
        values=[]
        for mode in ['control','resident']:
            values.append(statistics.median(x['phases_ns'][phase] for x in rows if x['model_id']=='gpup-extension-dense_block-65536' and x['mode']==mode and x['lifecycle']=='cold')/1e9)
        lines.append(f'| {phase} | {values[0]:.6f} | {values[1]:.6f} |')
    lines+=['','The residual includes process startup/teardown, provenance hashing and metadata work. It is reported, not assigned to arithmetic. In the nontrivial admission trace both modes submit 2800 kernels for 1400 updates. Control/resident synchronize 58/44 times; upload bytes rise from 262144 to 513920 and readback bytes from 229376 to 481152. Fewer waits alone do not guarantee lower total cost.','',
        '| Model | Control prepared seconds/solve | Resident prepared seconds/solve | Control cold / prepared | Resident cold / prepared |','| --- | ---: | ---: | ---: | ---: |']
    for name in names:
        data=[]
        for mode in ['control','resident']:
            batch=next(x for x in rows if x['model_id']==name and x['mode']==mode and x['lifecycle']=='prepared')
            per=batch['elapsed_ns']/batch['solves']
            cold=statistics.median(x['elapsed_ns'] for x in rows if x['model_id']==name and x['mode']==mode and x['lifecycle']=='cold')
            data.append((per/1e9,cold/per))
        lines.append(f"| {name.removeprefix('gpup-development-').removeprefix('gpup-extension-')} | {data[0][0]:.6f} | {data[1][0]:.6f} | {data[0][1]:.4f} | {data[1][1]:.4f} |")
    lines+=['','Prepared numbers amortize setup and are throughput observations, not single-solve speedups. Mixed-model throughput remains uncertified.','',
        '## Normal limits and bound authority','',
        'All twelve mixed-65536 endpoints export 65536 primal and 65536 dual entries. They remain native limits with no strict certificate. The independent checker refuses a finite contribution for variable 3 because its reduced-cost enclosure requires an infinite variable-bound side. Primal feasibility does not supply a finite dual bound, and this refusal does not prove the model unbounded. No bound clipping, artificial finite bound, tolerance relaxation or optimizer-based repair is introduced.','',
        '## Acceptance, failures and accounting','',
        'The full native CPU integration gate passes 638 Rust tests, 515 Python tests, pinned HiGHS build, Clippy/format, workspace build/docs, dependency policy, artifact checks, committed-record replay, 190 documentation pages and CPU smoke. New focused coverage includes two CPU coefficient/preparation tests and five Python timing/counter tests. The test-only overflow correction has scoped lint/CPU validation and an exact production-source bridge.','',
        'Device acceptance covers bitwise window endpoints at 1/63/64/65/199/200 updates, 2000-update restart/controller trajectories, repeated prepared solves, cancellation, sticky overflow refusal and whole-window host preservation. Four nontrivial endpoint exports certify independently and match bitwise. Memcheck, racecheck, initcheck and synccheck each pass with zero errors/hazards.','',
        'Retained failures: initial enum-name compilation failure; an example compilation failure masked by a shell lacking `set -e` (the missing full reservation is separately charged); the first full CPU gate refusing stale historical source rosters; a nonoverflowing overflow fixture; and a correction attempt bound to the stale test executable. No arithmetic failure is inferred from those fixture/build errors. The original records, binaries and charges remain. The artifact reader was corrected before timing because the legacy diagnostics deliberately omit execution counters; actual disjoint native-cost scopes supply the counts without a device rerun.','',
        'The new envelope is 32000 CPU / 1800 GPU seconds, independent of historical ledgers. GPU charge is **598.631222067 seconds**: acceptance 247.592544461 (including both full failed 60-second reservations), study 351.038677606. Exact final CPU totals, every reservation and empty cleanup checks are in the delivery audit. Host memory is sampled under the unchanged in-container supervisor; this is not hard cgroup containment. Device allocations are admitted against 12 GiB.','',
        'The six changes to pre-existing source files are additive module/example/atomic-guard registration and test-only historical fixture adaptation. All other prior source hashes and all prior scientific results/charges remain exact. No vendor binary, credential or experiment directory is committed.','',
        '## Handoff','',
        'GPUP-RESIDENT2 is complete as a bounded negative optimization result with working lifecycle/phase instrumentation and normal-limit export. Keep the native control for subsequent comparisons. GPUP-MIXED2 is the next contract/implementation slice; this delivery reserves no work for it. GPUP-8 remains incomplete and GPUP-9 remains gated.']
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    import sys
    if sys.argv[1]=='report':
        target=ROOT/'docs/benchmarks/data/resident2-manifest-v4.json'
        require(not target.exists(),'immutable public manifest exists');shutil.copyfile(MANIFEST,target)
        (ROOT/'docs/benchmarks/lp-resident2-gpup-resident2.md').write_text(report_text())
    else:
        put(ROOT/'docs/benchmarks/data/resident2-acceptance-v1.json',audit('final-audit-v1'))
