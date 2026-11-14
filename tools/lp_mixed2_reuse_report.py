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
from lp_mixed2_reuse_common import BASE, OLD, ROOT, BINARY, IMAGE, CPU_CAPS, GPU_CAPS, NS, load, put, ref, require
from lp_mixed2_reuse_budget import accounting, admission_open
from lp_mixed2_reuse_analysis import ANALYSIS, ARCHIVE, DATA, verify as replay
from lp_mixed2_reuse_evidence import INDEX as EVIDENCE, CHECK as EVIDENCE_CHECK

REPORT=ROOT/'docs/benchmarks/lp-mixed2-reuse.md'
ACCEPTANCE=DATA/'mixed2-reuse-acceptance-v1.json'
ACCOUNTING=DATA/'mixed2-reuse-accounting-v1.json'


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
    path=DATA/'mixed2-reuse-history-v1.json'
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


def verify():
    replay();h=preserve();a=load(ANALYSIS);f=load(BASE/'confirmation-freeze.json')
    from lp_mixed2_reuse_confirmation import bindings
    require(f['sources']==bindings() and f['binary']==ref(BINARY) and f['image']==ref(IMAGE),'frozen source drift')
    for item in [*f['admissions'],f['models'],f['diagnosis']]:
        require(ref(ROOT/item['path'])==item,'admission binding drift')
    for name in ['final-native-v1','serial-final-v1','analysis-v1','evidence-v1','evidence-check-v1']:
        require(load(BASE/'resources'/(name+'.settlement.json'))['status']=='passed','final admission: '+name)
    log=(BASE/'resources/final-native-v1.resource.json.log').read_text()
    rust=sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed;',log))
    require(rust==666 and 'Ran 706 tests' in log and
            'committed run records re-executed and verified: passed' in log,'full native coverage')
    serial=load(BASE/'serial-final-v1/result.json')
    diagnosis=load(DATA/'mixed2-reuse-diagnosis-v1.json')
    prior=load(BASE/'serial-admission-v3/result.json')
    require(serial['status']=='passed' and
            serial['responses']==prior['responses']+diagnosis['all_retained_responses'],'independent serial coverage')
    require(load(EVIDENCE_CHECK)['status']=='passed' and load(EVIDENCE_CHECK)['index']==ref(EVIDENCE),'evidence verification')
    for p in (BASE/'resources').glob('*.settlement.json'):
        s=load(p);r=load(ROOT/s['resource']['path'])
        require(not s['overrun'] and r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup/overrun')
    # Replay the committed artifacts in an isolated tree with no original
    # artifacts directory. Hardlinks avoid copying large immutable archive parts.
    with tempfile.TemporaryDirectory(prefix='mixed2-reuse-portable-') as temp:
        dest=Path(temp);(dest/'tools').mkdir()
        for p in (ROOT/'tools').glob('*.py'):shutil.copy2(p,dest/'tools'/p.name)
        files=[ANALYSIS,ARCHIVE,EVIDENCE]+[ROOT/r['path'] for index in (ARCHIVE,EVIDENCE) for r in load(index)['parts']]
        for p in files:
            target=dest/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
            try:target.hardlink_to(p)
            except OSError:shutil.copy2(p,target)
        for tool,action in [('analysis','verify'),('evidence','portable')]:
            subprocess.run([sys.executable,'-B',f'tools/lp_mixed2_reuse_{tool}.py',action],cwd=dest,check=True)
        require(not (dest/'artifacts').exists(),'portable replay depended on artifacts')
    put(ACCEPTANCE,dict(status='passed',scientific_confirmation=a['status'],production_adoption=False,
        binary=ref(BINARY),image=ref(IMAGE),analysis=ref(ANALYSIS),archive=ref(ARCHIVE),evidence=ref(EVIDENCE),
        history=ref(DATA/'mixed2-reuse-history-v1.json'),historical_files=len(h['preserved']),
        rust_tests=638,python_tests=706,isolated_rust_tests=28,
        serial=ref(BASE/'serial-final-v1/result.json'),serial_responses=serial['responses'],
        serial_requests=serial['assessment_requests'],serial_unique=serial['unique_assessments'],
        portable_replay=True,cleanup_empty=True,native=ref(BASE/'resources/final-native-v1.settlement.json')))
    print(dict(status='passed',historical_files=len(h['preserved']),serial_responses=serial['responses']),flush=True)


def close():
    admission_open();require(load(ACCEPTANCE)['status']=='passed','acceptance required')
    require(load(BASE/'resources/final-acceptance-v1.settlement.json')['status']=='passed','final acceptance settlement')
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
    target=DATA/'mixed2-reuse-resources-v1.json.gz'
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


def report():
    a=load(ANALYSIS);r=load(BASE/'reliability-v1.json');f=load(BASE/'confirmation-freeze.json')
    lines=['# MIXED2 changing-model reuse: reliability and complete-session confirmation','',
        '[SPEC-0039](../specifications/SPEC-0039-mixed2-reuse.md) / [ADR-0072](../decisions/ADR-0072-mixed2-reuse.md).',
        'The isolated executor caches four independently checked original models with an identical matrix,',
        'switches RHS/objective/bounds, and resets FP64 state on every request. Both native and FP4 receive',
        'the same cache, CPU preparation overlap and worker placement. The CUDA image and numerical solve',
        'body remain unchanged. Public defaults remain unchanged.','',
        f"Confirmation status: **{a['status']}**; **{a['sessions']} / {a['planned_sessions']} sessions**,",
        f"**{a['solves']} solves / {a['certificates']} original-model certificates**.",
        'The new operational stop prevents a confirmation pass. Only one or two complete pairs remain',
        'per comparison, giving no finite simultaneous confidence bounds. Generic complete-session',
        'ratios are near parity; coupled ratios are descriptively about 1.03–1.06x. These are incomplete',
        'observations, not established speedups or evidence that the availability problem is repaired.',
        'The earlier SPEC-0038 cohort remains incomplete and is never pooled, retried or regraded.','',
        '## Complete 32-request sessions','',
        'Each fresh session cycles four distinct RHS/objective scenarios eight times at one final tier.',
        'The primary endpoint includes model parsing, checker/cache/representation preparation, switching,',
        'all solves and independent certification, durable response delivery, EOF and destruction.',
        'These are constructed finite-scenario streams, not production traces or warm-start solves.','',
        '| Family | Tier | Native session ms | FP4 session ms | Paired speedup [simultaneous interval] | Saved ms [interval] | Scoped value criterion |',
        '| --- | --- | ---: | ---: | --- | --- | --- |']
    for row in a['rows']:
        if 'speedup' not in row:continue
        v=row['speedup'];s=row['saved_ms'];ns=row['summaries']['native'];fs=row['summaries']['fp4x2']
        fmt=lambda x:'unbounded' if x is None else f'{x:.3f}'
        lines.append(f"| {row['family']} | {row['tier']} | {ns['session_ms']:.3f} | {fs['session_ms']:.3f} | {v['median']:.3f} [{fmt(v['lower'])}, {fmt(v['upper'])}] | {s['median']:.3f} [{fmt(s['lower'])}, {fmt(s['upper'])}] | {'passes' if row['useful_scoped_gain'] else 'not established'} |")
    lines += ['',
        'Ratios and savings are paired within block; marginal medians need not divide to the paired ratio.',
        'Exact binomial median intervals cover eight ratios and eight absolute savings simultaneously',
        'by Bonferroni (nominal at least 95%, conditional on independent session blocks). The shared GPU',
        'and temporal conditions limit independence. Within-session requests are not independent samples.',
        f"The predeclared 32-block interval uses rank {f['statistics']['rank']}; at least {f['statistics']['positive_blocks_needed']} blocks must exceed a threshold for its lower bound to exceed it.",
        'The 10 ms/session absolute floor (0.3125 ms/request) is an exploratory workload-value criterion,',
        'not a user production SLO. A scoped pass requires complete coverage, all certificates, a speedup',
        'lower bound above parity and a savings lower bound above 10 ms. The provisional 1.10x comparison',
        'is reported in the machine analysis; neither criterion automatically authorizes adoption.',
        'Every block, first-16 sensitivity and pair-order split remains visible. No scientific retry.','',
        '## Component costs and preparation','',
        '| Family / tier | Native / FP4 setup ms | Native / FP4 request ms | Native / FP4 GPU-phase ms | Native / FP4 physical updates |',
        '| --- | ---: | ---: | ---: | --- |']
    for row in a['rows']:
        if 'summaries' not in row:continue
        n=row['summaries']['native'];x=row['summaries']['fp4x2']
        lines.append(f"| {row['family']} / {row['tier']} | {n['setup_ms']:.3f} / {x['setup_ms']:.3f} | {n['request_ms']:.3f} / {x['request_ms']:.3f} | {n['gpu_ms']:.3f} / {x['gpu_ms']:.3f} | {n['work']} / {x['work']} |")
    for row in a['rows']:
        if row['family']=='dense-coupled-2048' and row['tier']=='certified-1e-9' and 'summaries' in row:
            lines += ['', 'For the largest strict coupled stream, aggregate complete-session cost shares are:', '']
            for lane in ['native','fp4x2']:
                summary=row['summaries'][lane];parts=summary['aggregate_cost_ns'];total=summary['aggregate_session_ns']
                checker=parts.get('solver/checker',0);audit=parts.get('solver/audit',0)+parts.get('solver/initial_audit',0)
                lines.append(f"- {lane}: setup {100*parts['setup']/total:.1f}%, independent checker {100*checker/total:.1f}%, original audit {100*audit/total:.1f}%, delivery/bookkeeping {100*parts['delivery_and_bookkeeping']/total:.1f}%.")
            lines += ['', 'These are measured nonoverlapping aggregate host-clock partitions. GPU events are nested',
                      'diagnostics and are not added to this partition. Removing a component is not an attainable-speedup claim.']
    lines += ['',
        'Request times include model switching and durable solve delivery. GPU values enclose submitted',
        'windows, including launches and host gaps; they are not isolated tensor throughput. All work,',
        'local-budget recoveries, promotions and checkpoint state are retained. Small-family historical',
        'regressions are unchanged; this study selects no universal FP4 replacement or cold-solve preset.','',
        'Version 1 prepared four 2048 scenarios serially in roughly 10–11 seconds. Version 2 starts the',
        'independent CPU checker while preparing the host model; both controls receive this overlap.',
        'Observed version-2 admission preparation is roughly 6.0–6.6 seconds. In the available strict',
        'coupled2048 FP4 sessions, setup and independent checking together consume about 80% of full',
        'session time. This leaves exact host preparation/checking as larger cost targets than tensor',
        'arithmetic, after the availability problem is resolved.',
        'Original-model admission still precedes CUDA. The versioned admission measurements are exploratory,',
        'not an independent causal performance confirmation. Version 1 and its deadline refusal remain visible.','',
        '## Reliability diagnosis','',
        'A fresh CPU-only fixture preparation again missed the unchanged 100 ms heartbeat, despite limiting',
        'numerical workers to three CPUs. GPU execution is therefore not a necessary trigger. Separating',
        'guardian/coordinator placement onto the fourth CPU is a mitigation, not an availability guarantee.',
        'The successful instrumented preparation reached a 75.5 ms sampling gap. Its largest observed',
        'heartbeat gap was about 63.3 ms, with about 53.0 ms accumulated coordinator runqueue wait. These',
        'are different timer boundaries; the scheduling observation is from a successful run, not the',
        'historical failed instant. Instrumentation disturbance and shared-host activity remain limitations.','',
        'A later independent serial CPU reassessment also missed the heartbeat with pinned controls.',
        'That failed reservation retains its partial certificates and full charge. A new diagnostic',
        'reassessment with supervisor and parent scheduling telemetry passed all retained requests;',
        'this does not establish why the uninstrumented attempt failed or prove pinning sufficient.','',
        'All sixteen predeclared racecheck probes passed across historical/current hosts, native/FP4,',
        'all-process/application-only instrumentation and both CPU placements. The earlier exit 11 did not',
        'reproduce. This is not a root-cause finding or proof of repair. New scoped sanitizer admission',
        'covers the root CUDA executor; the independent checker is separately CPU-admitted. No production-',
        'readiness claim follows. Primary confirmation uses no added supervisor telemetry and retains the',
        'original supervisor source, 100 ms limit, resource ceilings and cleanup requirements.','',
        '## Acceptance, failures and reproducibility','',
        'Full CPU/native acceptance: 638 repository Rust / 706 Python tests, plus 28 isolated Rust tests,',
        'Clippy, dependency audit, native replay, artifact validation, documentation and smoke. The current',
        'host also receives CPU original-endpoint/norm admission, 130 device cases / 2304 rational outputs,',
        'four arithmetic/lifecycle sanitizer suites and four scenario-switch sanitizer suites. Cached',
        'scenarios, repeated returns, recovery and native promotion are compared with fresh sessions.',
        'All retained final/audit points covered by serial validation are reassessed using the original',
        'independent serial checker; portable timing replay is a separate check, not a new solver run.','',
        'Failed development reservations preserve sources, partial output and full charges. The 128 MiB',
        'legacy reader refusal was corrected to the admitted 384 MiB model cap. A three-CPU launch of the',
        'repository gate incorrectly prevented its four-CPU supervisor tests; the full gate subsequently',
        'passed with four CPUs. The first all-family scenario admission reached its reserved work deadline;',
        'subsequent admission is split by family. An additional full-trajectory scenario racecheck also',
        'reached its work deadline. The final scenario sanitizer suite uses bounded switch/reset/step/',
        'restore comparisons, while full converged trajectories are separately admitted. The complete',
        'original 97-case arithmetic/lifecycle suite remains covered by every sanitizer. None of these',
        'development corrections replaces a scientific sample.','',
        '[Analysis](data/mixed2-reuse-analysis-v1.json), [portable session records](data/mixed2-reuse-records-v1.json).',
        'Replay: `python3 tools/lp_mixed2_reuse_analysis.py verify`.',
        'The archives retain original responses and model inputs, all failed versions and resource receipts.',
        'Historical source/evidence and prior handoffs remain exact. GPUP-8 remains incomplete; GPUP-9 gated.',
        'Further production evaluation needs representative workload traces and an explicit disposition',
        'of the unresolved process/scheduling reliability limits. No follow-on allocation is released.']
    diagnosis=DATA/'mixed2-reuse-diagnosis-v1.json'
    if diagnosis.exists():
        d=load(diagnosis);lines += ['', '## Complete coverage and reliability disposition', '',
            f"Retained responses: {d['all_retained_responses']}; {d['complete_session_responses']} belong to completed sessions and {len(d['partial_responses'])} are partial-session files.",
            f"Missing session cells: {len(d['missing_cells'])}. Failed block indices (zero-based): {d['failed_blocks']}.",
            f"Unattempted block indices after the operational stop: {d['unattempted_blocks']}.",
            '[Retained-record diagnosis and full block ledger](data/mixed2-reuse-diagnosis-v1.json).']
        probe=d['postfailure_cpu_probe'];lines += ['',
            f"After the operational stop, the bounded CPU preparation probe completed {probe['completed_preparations']} model preparations with external parent telemetry and the original supervisor. Its result is {probe['status']}; maximum supervisor sampling gap is {probe['max_sample_gap_ns']/1e6:.3f} ms.",
            'The probe does not reproduce the failed instants or establish a repair. Observer gaps and',
            'shared-cgroup throttle/memory counters remain in the diagnosis; they are separate boundaries.']
        if all(t['cgroup_throttled_periods_delta']==0 and t['cgroup_throttled_usec_delta']==0
               for t in probe['telemetry']):
            lines += ['No CPU-throttle counter increase was observed during these successful probe phases;',
                      'this does not establish the counter behavior at either failed scientific instant.']
        if d['failed_blocks']:
            lines += ['', 'The frozen cohort is incomplete. All intervals describe available complete pairs,',
                'conditional on observed coverage; missingness may be informative. No scoped confirmation,',
                'retention or adoption pass is claimed. Failed blocks are not retried. Two consecutive',
                'untouched blocks failed supervision, so the remaining 29 blocks were not launched.',
                'This operational stop was independent of measured speedup. The frozen source and',
                'analysis remain exact; a separate explicit coverage adapter records unattempted cells',
                'without inventing resource reservations or regrading the frozen criterion.', '',
                '| Block index | Supervisor reason | Complete sessions | Full CPU / GPU charge seconds |',
                '| ---: | --- | ---: | ---: |']
            for b in d['blocks']:
                if b['status']=='refused':lines.append(f"| {b['block']} | {b['reason']} | {b['sessions']} | {b['cpu_ns']/NS:.3f} / {b['gpu_ns']/NS:.3f} |")
            lines += ['', 'The prospective CPU placement mitigation did not eliminate heartbeat failures.',
                'Primary timings contain no added supervisor telemetry, so the failed instants remain',
                'unassigned. Further independent confirmation should follow a resolved and admitted',
                'availability strategy; repeating scientific cohorts is not a substitute for diagnosis.']
    if ACCEPTANCE.exists():
        x=load(ACCEPTANCE);lines += ['',f"Independent serial validation covers {x['serial_responses']} response files / {x['serial_requests']} assessment requests / {x['serial_unique']} distinct original-model endpoint/tier assessments. Portable evidence and timing replay pass without the original artifacts tree; {x['historical_files']} historical files and every prior handoff/backlog entry remain exact."]
    if ACCOUNTING.exists():
        x=load(ACCOUNTING);lines += ['',f"Allocation closed at {x['cpu_seconds']:.9f} CPU / {x['gpu_seconds']:.9f} GPU seconds, including 128 closing CPU seconds. All cleanup is empty.",
            '[Acceptance](data/mixed2-reuse-acceptance-v1.json), [accounting](data/mixed2-reuse-accounting-v1.json),',
            '[portable development evidence](data/mixed2-reuse-evidence-v1.json), [resource receipts](data/mixed2-reuse-resources-v1.json.gz).']
    REPORT.write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['report','preserve','verify','close']);a=p.parse_args()
    globals()[a.action]()
