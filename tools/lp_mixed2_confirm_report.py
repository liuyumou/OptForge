"""Durable findings, historical preservation, and independent allocation closure."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from lp_mixed2_confirm_common import BASE, PRIOR, ROOT, BINARY, IMAGE, CPU_CAPS, GPU_CAPS, NS, load, put, ref, require
from lp_mixed2_confirm_budget import accounting, admission_open
from lp_mixed2_confirm_analysis import ANALYSIS, ARCHIVE, DATA, verify as replay
from lp_mixed2_confirm_evidence import INDEX as EVIDENCE, CHECK as EVIDENCE_CHECK

REPORT=ROOT/'docs/benchmarks/lp-mixed2-confirm.md'
ACCEPTANCE=DATA/'mixed2-confirm-acceptance-v1.json'
ACCOUNTING=DATA/'mixed2-confirm-accounting-v1.json'


def preserve():
    h=load(BASE/'history.json');preserved={}
    for path,digest in h['files'].items():
        require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,'historical file changed: '+path)
        preserved[path]=digest
    for name in ['AGENTS.md','docs/plans/gpu-lp-precision-roadmap.md']:
        old=(BASE/(name.replace('/','_')+'.before')).read_text()
        text=(ROOT/name).read_text();tail=old.split('\n',2)[2]
        require(tail in text,'historical handoff text changed: '+name)
    old=(BASE/'state_backlog.yaml.before').read_text();text=(ROOT/'state/backlog.yaml').read_text()
    require(old.split('tasks:\n',1)[1] in text,'historical backlog entries changed')
    a=(ROOT/'research/lp-mixed2-fp4/src/main.rs').read_text()
    b=(ROOT/'research/lp-mixed2-reuse/src/main.rs').read_text()
    body=lambda s:s[s.index('    fn solve('):s.index('    fn command(')]
    require(body(a)==body(b),'numerical solve body changed')
    result=dict(status='passed',baseline=h['baseline'],preserved=preserved,
                old_handoffs_exact=True,old_backlog_entries_exact=True,numerical_solve_body_exact=True)
    path=DATA/'mixed2-confirm-history-v1.json'
    if path.exists():require(load(path)==result,'historical preservation changed')
    else:put(path,result)
    return result


def receipts():
    rows=[]
    for p in sorted((BASE/'resources').glob('*.reservation.json')):
        stem=str(p).replace('.reservation.json','');s=load(stem+'.settlement.json');r=load(stem+'.resource.json')
        require(not s['overrun'] and r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],
                'resource overrun or incomplete cleanup')
        rows.append(dict(identity=p.name.removesuffix('.reservation.json'),reservation=load(p),settlement=s,
                         resource=ref(Path(stem+'.resource.json')),reason=r['result']['reason']))
    return rows


def close():
    admission_open();require(load(ACCEPTANCE)['status']=='passed','acceptance required')
    require(load(BASE/'resources/final-acceptance-v3.settlement.json')['status']=='passed','final acceptance settlement')
    cpu,gpu=accounting();cpu['cleanup']+=128*NS
    require(all(cpu[k]<=v*NS for k,v in CPU_CAPS.items()) and
            all(gpu[k]<=v*NS for k,v in GPU_CAPS.items()),'allocation exceeded')
    rows=receipts();manifest=load(BASE/'packaging-v1/manifest.json')
    packaged={r['path']:r for r in manifest['files']}
    # Packaging and final acceptance create later source snapshots. Preserve
    # these as well, rather than silently omitting the closing versions.
    late_sources={str(p.relative_to(ROOT)):p.read_text() for p in (BASE/'sources').rglob('*')
                  if p.is_file() and str(p.relative_to(ROOT)) not in packaged}
    late_root_files={str(p.relative_to(ROOT)):p.read_text() for p in BASE.iterdir()
                     if p.is_file() and p.suffix in ('.py','.sh','.json','.md') and
                     str(p.relative_to(ROOT)) not in packaged}
    resource_files={str(p.relative_to(BASE)):p.read_text() for p in sorted((BASE/'resources').iterdir()) if p.is_file()}
    target=DATA/'mixed2-confirm-resources-v1.json.gz'
    with target.open('xb') as out:
        out.write(gzip.compress(json.dumps(dict(receipts=rows,resource_files=resource_files,
                  late_sources=late_sources,late_root_files=late_root_files),sort_keys=True,separators=(',',':')).encode(),mtime=0))
    failed=[r for r in rows if r['settlement']['status']!='passed']
    value=dict(status='closed',cpu_caps_seconds=CPU_CAPS,gpu_caps_seconds=GPU_CAPS,cpu_ns=cpu,gpu_ns=gpu,
        cpu_seconds=sum(cpu.values())/NS,gpu_seconds=sum(gpu.values())/NS,
        closing_administration_cpu_seconds=128,failed_jobs=len(failed),
        failed_cpu_seconds=sum(r['settlement']['cpu_ns'] for r in failed)/NS,
        failed_gpu_seconds=sum(r['settlement']['gpu_ns'] for r in failed)/NS,
        failed_reservations=[r['identity'] for r in failed],full_receipts=ref(target),evidence=ref(EVIDENCE),
        evidence_verification=ref(EVIDENCE_CHECK),historical_transfers=0,cleanup_empty=True)
    put(ACCOUNTING,value);put(BASE/'CLOSED.json',dict(accounting=ref(ACCOUNTING)))
    report();print(value,flush=True)


def verify():
    replay();h=preserve();a=load(ANALYSIS);f=load(BASE/'confirmation-freeze.json')
    from lp_mixed2_confirm_confirmation import bindings
    require(f['sources']==bindings() and f['binary']==ref(BINARY) and f['image']==ref(IMAGE),'frozen source drift')
    for item in [*f['admissions'],f['models'],f['diagnosis']]:
        require(ref(ROOT/item['path'])==item,'admission binding drift')
    for name in ['native-v5','serial-final-v1','exact-final-v1','analysis-v1','evidence-v1','evidence-check-v1']:
        require(load(BASE/'resources'/(name+'.settlement.json'))['status']=='passed','final admission: '+name)
    log=(BASE/'resources/native-v5.resource.json.log').read_text()
    rust=sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed;',log))
    require(rust==666 and 'Ran 742 tests' in log and
            'committed run records re-executed and verified: passed' in log,'full native coverage')
    serial=load(BASE/'serial-final-v1/result.json');prior=load(BASE/'serial-admission-v1/result.json')
    diagnosis=load(DATA/'mixed2-confirm-diagnosis-v1.json')
    require(serial['status']=='passed' and serial['responses']==prior['responses']+diagnosis['all_retained_responses'],
            'independent serial coverage')
    exact=load(BASE/'exact-final-v1.json')
    require(exact['status']=='passed' and exact['responses']==diagnosis['all_retained_responses'],'complete retained trajectory comparison')
    identities=lambda value:{(r['endpoint']['sha256'],r['certificate']['sha256'],r['tier']) for r in value['records']}
    require(identities(serial)==identities(prior),'final/audit endpoint or original certificate identity differs from admission')
    evidence_check=load(EVIDENCE_CHECK)
    require(evidence_check['status']=='passed' and evidence_check['index']==ref(EVIDENCE) and
            evidence_check['all_response_bytes_exact'] and evidence_check['responses']==exact['responses'],
            'complete and partial response evidence verification')
    for p in (BASE/'resources').glob('*.settlement.json'):
        s=load(p);r=load(ROOT/s['resource']['path'])
        require(not s['overrun'] and r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup/overrun')
    portable=load(BASE/'portable-v4.json')
    require(load(BASE/'resources/portable-v4.settlement.json')['status']=='passed' and
            portable['status']=='passed' and portable['original_artifacts_absent'],'portable replay admission')
    for item in portable['bindings']:
        require(ref(ROOT/item['path'])==item,'portable replay source/evidence drift')
    put(ACCEPTANCE,dict(status='passed',scientific_confirmation=a['status'],production_adoption=False,
        binary=ref(BINARY),image=ref(IMAGE),analysis=ref(ANALYSIS),archive=ref(ARCHIVE),evidence=ref(EVIDENCE),
        history=ref(DATA/'mixed2-confirm-history-v1.json'),historical_files=len(h['preserved']),
        rust_tests=638,python_tests=742,isolated_rust_tests=28,supervisor_contracts=36,
        serial=ref(BASE/'serial-final-v1/result.json'),serial_responses=serial['responses'],
        serial_requests=serial['assessment_requests'],serial_unique=serial['unique_assessments'],
        exact_trajectories=ref(BASE/'exact-final-v1.json'),all_original_endpoint_and_certificate_bytes_match_admission=True,
        portable_replay=True,portable_replay_receipt=ref(BASE/'portable-v4.json'),
        cleanup_empty=True,native=ref(BASE/'resources/native-v5.settlement.json')))
    print(dict(status='passed',historical_files=len(h['preserved']),serial_responses=serial['responses']),flush=True)


def report():
    a=load(ANALYSIS);f=load(BASE/'confirmation-freeze.json');d=load(DATA/'mixed2-confirm-diagnosis-v1.json')
    passing=[r for r in a['rows'] if r.get('useful_scoped_gain')]
    provisional=[r for r in a['rows'] if r.get('provisional_110_lower_pass')]
    lines=['# MIXED2 independent confirmation','',
        '[SPEC-0040](../specifications/SPEC-0040-mixed2-confirm.md) / [ADR-0073](../decisions/ADR-0073-mixed2-confirm.md).','',
        f"Status: **{a['status']}**. **{a['sessions']} / {a['planned_sessions']} sessions**, **{a['solves']} certified solves**.",
        f"All {len(d['blocks'])} planned blocks were attempted; {len(a['failed_blocks'])} blocks have resource refusals. There are {len(a['missing_cells'])} missing complete-session cells and {d['all_retained_responses']-a['solves']} retained responses outside complete sessions.",
        f"The scoped value criterion passes in {len(passing)} of eight family/tier comparisons; {len(provisional)} pass the separate provisional 1.10x lower-bound comparison.",
        'This independent cohort uses the unchanged scenario-reuse executable and CUDA image.',
        'Earlier incomplete cohorts, sources, decisions and closed charges remain exact; no pooling or retry.',
        'Public defaults remain unchanged. These constructed workloads do not establish production adoption.','',
        '## Complete session results','',
        'Each fresh session cycles four original-model RHS/objective scenarios eight times. The endpoint',
        'includes parsing, independent checker/cache/representation setup, model switching, all 32 solves,',
        'original-model certification, durable responses, EOF and destruction. FP64 state resets each solve.',
        'Native and FP4 receive the same delivery, preparation overlap and CPU placement.','',
        '| Family | Tier | Available pairs | Native ms | FP4 ms | Paired speedup [simultaneous interval] | Saved ms [interval] | Scoped criterion |',
        '| --- | --- | ---: | ---: | ---: | --- | --- | --- |']
    if a['failed_blocks']:
        lines[7:7]=['Resource refusals prevent a complete-coverage or adoption pass. Intervals below describe',
                    'available complete pairs conditional on observed coverage; missingness may be informative.',
                    'These observations must not be presented as confirmed speedups.']
    fmt=lambda x:'unbounded' if x is None else f'{x:.3f}'
    for r in a['rows']:
        if 'speedup' not in r:continue
        v=r['speedup'];s=r['saved_ms'];n=r['summaries']['native'];x=r['summaries']['fp4x2']
        lines.append(f"| {r['family']} | {r['tier']} | {len(r['blocks'])} | {n['session_ms']:.3f} | {x['session_ms']:.3f} | {v['median']:.3f} [{fmt(v['lower'])}, {fmt(v['upper'])}] | {s['median']:.3f} [{fmt(s['lower'])}, {fmt(s['upper'])}] | {'passes' if r['useful_scoped_gain'] else 'not established'} |")
    lines += ['',
        'The frozen seed is 400073: 32 blocks, balanced 16/16 lane order for every family/tier.',
        'Exact binomial median intervals cover eight paired ratios and eight absolute savings using',
        'Bonferroni alpha 0.05/16. For the planned complete 32-block comparison, rank 8 gives at least 95%',
        'simultaneous coverage conditional on independent blocks; at least 25 blocks must exceed a threshold',
        'for its lower bound to exceed that threshold. Available-pair intervals use their actual retained count.',
        'Within-session solves are not independent samples. Marginal medians need not divide to the paired ratio.',
        'Shared GPU/host activity and temporal dependence limit the statistical interpretation.',
        'The predeclared scoped criterion requires complete coverage, every original-model certificate,',
        'ratio lower bound above 1.0 and savings lower bound above 10 ms per session (0.3125 ms/request).',
        'That absolute floor is exploratory workload value, not a production SLO. The separate 1.10x',
        'comparison remains provisional. Every block, first-16 sensitivity and order split is retained.','',
        '## Measured costs and remaining work','',
        '| Family / tier | Native / FP4 setup ms | Native / FP4 request ms | Native / FP4 GPU phase ms | Native / FP4 physical updates per request |',
        '| --- | ---: | ---: | ---: | --- |']
    for r in a['rows']:
        if 'summaries' not in r:continue
        n=r['summaries']['native'];x=r['summaries']['fp4x2']
        lines.append(f"| {r['family']} / {r['tier']} | {n['setup_ms']:.3f} / {x['setup_ms']:.3f} | {n['request_ms']:.3f} / {x['request_ms']:.3f} | {n['gpu_ms']:.3f} / {x['gpu_ms']:.3f} | {n['work']} / {x['work']} |")
    lines += ['', 'Setup is per session; request and nested GPU times are medians per solve. Brackets list',
              'the distinct observed physical update counts, including correction work.',
              '', 'For strict coupled2048, aggregate complete-session cost shares are:', '']
    for r in a['rows']:
        if r['family']=='dense-coupled-2048' and r['tier']=='certified-1e-9' and 'summaries' in r:
            for lane,s in r['summaries'].items():
                p=s['aggregate_cost_ns'];t=s['aggregate_session_ns']
                lines.append(f"- {lane}: setup {100*p['setup']/t:.1f}%, independent checker {100*p.get('solver/checker',0)/t:.1f}%, original audit {100*(p.get('solver/audit',0)+p.get('solver/initial_audit',0))/t:.1f}%, iteration {100*p.get('solver/iteration',0)/t:.1f}%.")
    lines += ['',
        'These are nonoverlapping host-clock partitions. GPU event diagnostics are nested and must not',
        'be added to them; they include submitted windows and host/launch gaps, not isolated tensor throughput.',
        'Preparation and independent checking remain candidates for exact-cost reduction. Removing either',
        'in a forecast would not establish an attainable speedup. Generic and coupled families remain separate;',
        'small-family historical regressions and cold-solve findings are unchanged. No universal preset follows.','',
        '## Supervision diagnosis and limitations','',
        'The historical guardian tested receive freshness before draining queued sample messages. A controlled',
        '180 ms guardian pause reproduced its refusal while the sampler remained healthy (maximum gap 5.858 ms).',
        'The isolated correction drains the queue first and validates monotonic sample timestamps. Queued',
        'stale traffic cannot renew freshness; malformed, discontinuous, stalled or dead streams still refuse.',
        'Resource, cadence, death, deadline and cleanup checks remain exact apart from notification placement',
        'and an added 100 ms scan-duration guard. The sampler publishes its start timestamp at the start',
        'of scanning. The earlier correction published it afterward: two valid 60 ms scans could then cause',
        'a false stale notification. The controlled boundary probe reproduces that refusal; the final version',
        'passes with a 66.885 ms maximum cadence and 61.823 ms scan work. A 150 ms scan still refuses,',
        'including the terminal scan when the guardian is delayed. A progress notification never grants a pass.',
        'All 36 contracts pass, including live delay/stall, resource, cancellation, transport and cleanup cases.',
        'This is evidence for the observed design defect and tested correction, not the cause of old failed instants.','',
        'Three native attempts refused notification freshness, including with lower worker priority and separate',
        'Rust-worker placement. They do not establish that actual sampling cadence exceeded 100 ms. The first guardian',
        'continued observing (maximum loop gap 11.714 ms), so the queue-order correction alone is not universal',
        'availability. All failed reservations and partial logs are retained. A separate instrumented three-worker',
        'diagnostic passed all 72 experiment-library tests, and a traced full native gate passed on the intermediate',
        'source. Final admission reruns the complete gate without tracing on the final source. It restricts Rust workers',
        'to three CPUs and lowers worker priority while keeping four CPUs for nested Python resource contracts. Scientific',
        'sessions retain the prior three-worker / fourth-control-CPU placement and normal priority.',
        f"Across this cohort, maximum reported sampler gap is {d['max_sample_gap_ns']/1e6:.3f} ms, scan work {d['max_sample_work_ns']/1e6:.3f} ms, guardian loop gap {d['max_guardian_gap_ns']/1e6:.3f} ms, and sample delivery lag {d['max_delivery_lag_ns']/1e6:.3f} ms.",
        'These are separate timer boundaries. Sampler-work and RSS maxima use completed coordinator reports;',
        'refused runs retain guardian observations and may lack terminal sampler metrics.',
        'Admission passes did not establish uninterrupted availability',
        'for the frozen cohort. Its refusals remain binding, with all partial outputs and full charges retained.',
        'The observed control stalls are not assigned to a kernel, scheduler or memory cause without evidence.',
        'Further confirmation should follow low-disturbance sampling-phase and scheduling diagnosis; another',
        'repeated cohort is not a substitute for resolving this operational limitation.',
        'Coarse temperature, clock, power and utilization observations are retained without exclusions or causal claims.','',
        '## Acceptance and reproducibility','',
        'Full native gate: 638 repository Rust / 742 Python tests, 28 isolated Rust tests, Clippy, dependency',
        'audit, committed-record replay, artifact/documentation validation and smoke. Fresh same-image admission',
        'compares 64 smoke and 512 full-pilot outputs exactly with original scenario results. Prior device and',
        'four-sanitizer arithmetic and scenario-switch admissions are reused only for the unchanged source/image.',
        'The original independent serial checker reassesses all retained unique final and audit endpoint/tier pairs.',
        'Six analysis-corruption guards reject changed work, configuration, response bytes, original authority,',
        'cost partitions and duplicate cells; resource failures or missing sessions suppress the coverage decision.',
        'The first supervisor contract run exposed a reason-string compatibility mismatch; its full failed charge',
        'and source are retained. No scientific cell is retried.','',
        '[Analysis](data/mixed2-confirm-analysis-v1.json), [diagnosis and block ledger](data/mixed2-confirm-diagnosis-v1.json),',
        '[portable response archive](data/mixed2-confirm-records-v1.json).',
        'Replay: `python3 tools/lp_mixed2_confirm_analysis.py verify`.',
        'GPUP-8 remains incomplete and GPUP-9 gated. No follow-on execution or allocation is released.']
    post=DATA/'mixed2-confirm-postdiagnosis-v1.json'
    if post.exists():
        observed=load(post);lines += ['', '## Post-cohort CPU diagnosis', '',
            'The admitted post-refusal recorder collects process state and requests a Python stack only after',
            'the guardian has already decided to refuse. Two controlled contracts verify that refusal and',
            'cleanup remain intact. It adds no per-sample tracing; signal capture is not a complete kernel trace.', '',
            '| Probe | Result | Reason | Peak sampled RSS MiB |', '| --- | --- | --- | ---: |']
        for row in observed['rows']:
            peak='unavailable' if row['peak_rss_bytes'] is None else f"{row['peak_rss_bytes']/(1<<20):.1f}"
            lines.append(f"| {row['name']} | {row['status']} | {row['reason']} | {peak} |")
        lines += ['',
            'Both hashing paths check all 20 original model hashes for 12 rounds. Hashing alone did not reproduce',
            'the refusal. Their fixed order and different memory behavior do not establish a causal performance',
            'improvement or a remedy for the frozen failures. The CPU experiment workload does reproduce the',
            'progress refusal, so GPU execution is not a necessary trigger.',
            'At the first post-refusal observation the coordinator is marked runnable; no Python stack arrives',
            'during the requested 15 ms capture sleep. A versioned follow-up records scheduler counters and',
            'pending signals before and after that sleep. These observations retain their capture delay and',
            'do not by themselves assign a scheduler, memory or kernel cause.',
            '[Post-cohort observations and capture records](data/mixed2-confirm-postdiagnosis-v1.json).']
        for row in observed['rows']:
            if row.get('capture_observation_span_ns') is not None:
                lines += ['',f"For {row['name']}, the enclosing observations are {row['capture_observation_span_ns']/1e6:.3f} ms apart; scheduler counters unchanged: {row['scheduler_counters_unchanged']}. The captured status retains the pending-signal masks and the stack file retains its partial output. This is consistent with delayed execution, not a complete attribution of the earlier failed interval."]
    if ACCEPTANCE.exists():
        x=load(ACCEPTANCE);lines += ['',f"Independent serial checking covers {x['serial_responses']} response files / {x['serial_requests']} assessments / {x['serial_unique']} distinct endpoint/tier pairs. Every retained numerical trajectory matches admission exactly; final/audit endpoints and original certificate bytes match the admitted set. Portable replay passes without the original artifacts tree; all {x['historical_files']} historical files and previous handoff/backlog entries remain exact."]
    closing_diagnosis=DATA/'mixed2-confirm-closing-diagnosis-v1.json'
    if closing_diagnosis.exists():
        lines += ['', 'The first final CPU verification also refused notification freshness. Its full reservation,',
            'source and capture are retained. The post-refusal stack identifies the coordinator\'s 5 ms pidfd',
            'wait; the runnable-state observations and unchanged scheduler counters bracket about 24.745 ms.',
            'The capture occurs after refusal and does not establish where the entire missed interval was spent.',
            'Portable replay and final aggregation therefore settle as separate CPU verification steps, with',
            'all source and artifact bindings checked and lower-priority verification workers. A separate',
            'packaging attempt failed because hardlinks crossed filesystems; the corrected helper retains',
            'the copy fallback. Its failed source and full reservation remain recorded. No scientific cell',
            'or timing decision is retried. A later staging check caught an extra trailing blank line in',
            'the report helper; its failed source and full charge are retained, with formatting corrected.',
            '[Closing verification diagnosis](data/mixed2-confirm-closing-diagnosis-v1.json).']
    if ACCOUNTING.exists():
        x=load(ACCOUNTING);lines += ['',f"Allocation closed at {x['cpu_seconds']:.9f} CPU / {x['gpu_seconds']:.9f} GPU seconds, including 128 closing CPU seconds. All {x['failed_jobs']} failed reservations retain full charges and sources; cleanup is empty. Historical funding transfers: zero.",
            '[Acceptance](data/mixed2-confirm-acceptance-v1.json), [accounting](data/mixed2-confirm-accounting-v1.json),',
            '[development evidence](data/mixed2-confirm-evidence-v1.json), [complete resource receipts](data/mixed2-confirm-resources-v1.json.gz).']
    REPORT.write_text('\n'.join(lines)+'\n')


def handoff():
    a=load(ANALYSIS);x=load(ACCEPTANCE);c=load(ACCOUNTING)
    d=load(DATA/'mixed2-confirm-diagnosis-v1.json')
    require(x['status']=='passed' and c['status']=='closed' and len(d['blocks'])==32,'closed delivery required')
    partial=d['all_retained_responses']-a['solves']
    header='## MIXED2 confirmation attempts complete; coverage refused (2026-11-14)'
    entry=f'''{header}

SPEC-0040 / ADR-0073 execute all 32 independent frozen blocks. Scientific status:
{a['status']}; {a['sessions']} / 512 complete sessions, {a['solves']} certified
solves, {partial} additional retained partial-session responses, {len(a['missing_cells'])} missing cells
and {len(a['failed_blocks'])} refused blocks. No scientific retry, historical pooling or regrading.
No scoped confirmation or adoption pass; available-pair intervals are conditional
on observed coverage and missingness may be informative. Public defaults stay exact.

Two controlled defects are corrected in an isolated supervisor: drain queued
sample messages before freshness assessment, and publish sample-start timestamps
at the start of scanning. Cadence/freshness stay at 100 ms; an additional 100 ms
scan-work guard covers the terminal scan. All 36 supervision contracts pass.
The frozen cohort still has progress refusals. These do not establish a kernel,
scheduler or memory cause. Diagnose control stalls before further confirmation;
successful bounded probes are not production-availability evidence.
Two CPU-only workload probes also refuse, so GPU execution is not a necessary
trigger. Hash-only probes do not reproduce the refusal. Post-refusal runnable
state, pending signals and unchanged scheduler counters support delayed execution
as a hypothesis, with capture delay and incomplete stack evidence retained.

Final uninstrumented native acceptance: 638 repository Rust / 742 Python and
28 isolated Rust tests. Fresh smoke/pilot: 576 exact original-scenario comparisons.
Independent original serial checking covers {x['serial_responses']} responses /
{x['serial_requests']} assessments / {x['serial_unique']} distinct endpoint/tier pairs.
All {d['all_retained_responses']} retained cohort trajectories match admission exactly,
including partial-session outputs; every archived response byte is verified.
Portable replay passes without the original artifacts tree. All {x['historical_files']}
historical files and older handoffs/backlog entries remain exact; cleanup is empty.

Independent allocation closed at {c['cpu_seconds']:.9f} CPU /
{c['gpu_seconds']:.9f} GPU seconds, including 128 closing CPU seconds.
Final ceiling 90000 CPU / 9000 GPU includes the recorded prospective native-only
extension. All {c['failed_jobs']} failed reservations retain full charges and sources;
no historical funding transfer. GPUP-8 incomplete, GPUP-9 gated. No follow-on
execution is released. Commit locally only. Report: [confirmation](docs/benchmarks/lp-mixed2-confirm.md).

'''
    for name in ['AGENTS.md','docs/plans/gpu-lp-precision-roadmap.md']:
        p=ROOT/name;s=p.read_text();require(header not in s,'handoff already written')
        value=entry if name=='AGENTS.md' else entry.replace('(docs/benchmarks/','(../benchmarks/')
        title,rest=s.split('\n',1);p.write_text(title+'\n\n'+value+rest.lstrip('\n'))
    p=ROOT/'state/backlog.yaml';s=p.read_text()
    start=s.index('  - id: GPUP-MIXED2-CONFIRM\n');end=s.index('  - id: GPUP-MIXED2-REUSE\n',start)
    task=f'''  - id: GPUP-MIXED2-CONFIRM
    title: Execute independent MIXED2 confirmation under corrected supervision
    status: complete
    depends_on: [GPUP-MIXED2-REUSE]
    specification: docs/specifications/SPEC-0040-mixed2-confirm.md
    acceptance: "All 32 frozen blocks attempted; scientific confirmation incomplete with {a['sessions']} complete sessions / {a['solves']} certified solves, {partial} additional partial-session responses, {len(a['missing_cells'])} missing cells and {len(a['failed_blocks'])} resource refusals. Controlled supervision fixes, 36 contracts, uninstrumented native acceptance, 576 exact smoke/pilot comparisons, original serial checking and portable replay pass. Preserve every failure/full charge and all history. No scientific retry, confirmed speedup, public default or GPUP-9 release. Report: docs/benchmarks/lp-mixed2-confirm.md."
'''
    s=s[:start]+task+s[end:]
    s=s.replace('next_ready_task: GPUP-MIXED2-CONFIRM','next_ready_task: GPUP-8-DISPOSITION',1)
    p.write_text(s)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['report','preserve','verify','close','handoff'])
    globals()[p.parse_args().action]()
