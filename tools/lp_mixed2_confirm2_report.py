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
from lp_mixed2_confirm2_common import BASE, PRIOR, ROOT, BINARY, IMAGE, CPU_CAPS, GPU_CAPS, NS, load, put, ref, require
from lp_mixed2_confirm2_budget import accounting, admission_open
from lp_mixed2_confirm2_analysis import ANALYSIS, ARCHIVE, DATA, verify as replay
from lp_mixed2_confirm2_evidence import INDEX as EVIDENCE, CHECK as EVIDENCE_CHECK

REPORT=ROOT/'docs/benchmarks/lp-mixed2-confirm2.md'
ACCEPTANCE=DATA/'mixed2-confirm2-acceptance-v1.json'
ACCOUNTING=DATA/'mixed2-confirm2-accounting-v1.json'


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
    path=DATA/'mixed2-confirm2-history-v1.json'
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
    target=DATA/'mixed2-confirm2-resources-v1.json.gz'
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
    require(a['status']=='complete-confirmation' and a['sessions']==512 and a['solves']==16384 and not a['missing_cells'] and not a['failed_blocks'],'complete confirmation required')
    from lp_mixed2_confirm2_confirmation import bindings
    require(f['sources']==bindings() and f['binary']==ref(BINARY) and f['image']==ref(IMAGE),'frozen source drift')
    for item in [*f['admissions'],f['models'],f['diagnosis']]:
        require(ref(ROOT/item['path'])==item,'admission binding drift')
    for name in ['native-v1','serial-final-v1','exact-final-v2','analysis-v1','evidence-v1','evidence-check-v1']:
        require(load(BASE/'resources'/(name+'.settlement.json'))['status']=='passed','final admission: '+name)
    log=(BASE/'resources/native-v1.resource.json.log').read_text()
    rust=sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed;',log))
    require(rust==666 and 'Ran 781 tests' in log and
            'committed run records re-executed and verified: passed' in log,'full native coverage')
    serial=load(BASE/'serial-final-v1/result.json');prior=load(BASE/'serial-admission-v1/result.json')
    diagnosis=load(DATA/'mixed2-confirm2-diagnosis-v1.json')
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
    portable=load(BASE/'portable-v1.json')
    require(load(BASE/'resources/portable-v1.settlement.json')['status']=='passed' and
            portable['status']=='passed' and portable['original_artifacts_absent'],'portable replay admission')
    for item in portable['bindings']:
        require(ref(ROOT/item['path'])==item,'portable replay source/evidence drift')
    put(ACCEPTANCE,dict(status='passed',scientific_confirmation=a['status'],production_adoption=False,
        binary=ref(BINARY),image=ref(IMAGE),analysis=ref(ANALYSIS),archive=ref(ARCHIVE),evidence=ref(EVIDENCE),
        history=ref(DATA/'mixed2-confirm2-history-v1.json'),historical_files=len(h['preserved']),
        rust_tests=638,python_tests=781,isolated_rust_tests=28,supervisor_contracts=39,
        serial=ref(BASE/'serial-final-v1/result.json'),serial_responses=serial['responses'],
        serial_requests=serial['assessment_requests'],serial_unique=serial['unique_assessments'],
        exact_trajectories=ref(BASE/'exact-final-v1.json'),all_original_endpoint_and_certificate_bytes_match_admission=True,
        portable_replay=True,portable_replay_receipt=ref(BASE/'portable-v1.json'),
        cleanup_empty=True,native=ref(BASE/'resources/native-v1.settlement.json')))
    print(dict(status='passed',historical_files=len(h['preserved']),serial_responses=serial['responses']),flush=True)

POLICY='''## Sampling policy and diagnosis

The user authorized changing or waiving an inappropriate 100 ms limit. This
cohort adopts a **one-second maximum sampling gap, scan duration and heartbeat
freshness limit**, retains the 5–10 ms sampling target and records every observed
100 ms exceedance. Both lanes use the same policy and every elapsed delay remains
in the complete-session endpoint. The change is prospective: earlier 100 ms
refusals, their sources and full charges remain exact.

The original [ADR-0044](../decisions/ADR-0044-tensor-cost-continuation.md) threshold
was a resource-observation rule. It was not a numerical tolerance. RSS sampling
cannot enclose peaks between samples at either threshold. A one-second bound
accepts a longer possible observation gap; it does not guarantee continuous memory
enforcement. The 16 GiB sampled RSS stop, swap checks, four-CPU limit, 12 GiB
owned-device-buffer ceiling, independent death detection, wall budget and cleanup
remain in force. Per-process high-water observations supplement sampled RSS and
are not a true simultaneous aggregate peak.

The isolated supervisor is byte-exact with its predecessor after removing the
explicit policy, metadata and CLI changes. All 39 supervision contracts pass,
including a recorded 150 ms delay accepted under the new rule and a stall beyond
one second that still refuses and cleans up. The one-second limit is a finite
operational policy choice, not a scheduling guarantee derived from measurements.

Two fixed CPU experiment-library probes each pass all 72 tests. The first has a
13.397 ms maximum sample-start gap. The second reaches 97.715 ms, with an 81.685 ms
scan using 6.489 ms of process CPU. Shared-cgroup throttling counters increase by
ten events / 4.516513 seconds during the second probe. Neither reproduces an
actual interval above 100 ms. Wall time minus process CPU and aggregate shared
counters do not establish the cause of an individual interval or an old refusal.
Bounded in-memory phase tracing is diagnostic only and is absent from science.
Its exported summaries retain counts, extrema, the largest 32 spans per phase
and up to 4096 spans above 100 ms; they are not a complete raw scheduling trace.

Linux documents that [select timeouts may overrun due to scheduling](https://www.man7.org/linux/man-pages/man2/select.2.html).
The [kernel 5.19 cgroup documentation](https://www.kernel.org/doc/html/v5.19/admin-guide/cgroup-v2.html)
describes the shared quota and counters; those counters do not isolate this task.
These references explain measurement limits, not the cause of the prior failures.

Admission requires full native checks, exact same-image smoke and **three**
full-size 16-session / 512-solve operational pilots before the new source freeze.
Passing these pilots does not establish universal availability. The first policy
record contained a wrong ADR filename; a source-preserved second version corrects
that metadata before admission. No numerical or scientific record was changed.

The full uninstrumented native gate then records a 160.026 ms maximum sample gap,
145.680 ms maximum scan duration and 18 gap/scan events above 100 ms. These events
can overlap. Peak sampled RSS is 4.802 GiB against the 16 GiB stop; cleanup is empty.
This is direct evidence of delays admitted by the new rule, not an uninterrupted
sampling claim or a causal diagnosis of the earlier cohort.
'''


def report():
    lines=['# MIXED2 complete independent confirmation','',
        '[SPEC-0041](../specifications/SPEC-0041-mixed2-confirm2.md) / [ADR-0074](../decisions/ADR-0074-mixed2-confirm2.md).','']
    if not ANALYSIS.exists():
        lines += ['Status: admission in progress; no new scientific result is claimed.','',POLICY]
        REPORT.write_text('\n'.join(lines)+'\n');return
    a=load(ANALYSIS);d=load(DATA/'mixed2-confirm2-diagnosis-v1.json');f=load(BASE/'confirmation-freeze.json')
    passing=[r for r in a['rows'] if r.get('useful_scoped_gain')]
    provisional=[r for r in a['rows'] if r.get('provisional_110_lower_pass')]
    lines += [f"Status: **{a['status']}**. **{a['sessions']} / 512 complete sessions and {a['solves']} certified solves**.",
        f"All 32 blocks are retained; {len(a['failed_blocks'])} resource refusals and {len(a['missing_cells'])} missing complete-session cells.",
        f"The predeclared scoped value criterion passes in {len(passing)} of eight family/tier comparisons; {len(provisional)} pass the separate provisional 1.10x lower-bound comparison.",
        'Public solver defaults remain unchanged. The constructed four-scenario streams do not establish production adoption.','',
        '## Complete session results','',
        'Each fresh session cycles four original-model RHS/objective scenarios eight times. The complete',
        'endpoint includes parsing, checker/cache/representation setup, model switching, all 32 solves,',
        'independent certification, durable output, EOF and destruction. FP64 state resets each solve.',
        'Native window32 and FP4x2 window16 use the unchanged admitted numerical executable/image.',
        'Both lanes receive the same preparation overlap, delivery and three-worker CPU placement.','',
        '| Family | Tier | Native ms | FP4 ms | Paired speedup [simultaneous interval] | Saved ms [interval] | Scoped value |',
        '| --- | --- | ---: | ---: | --- | --- | --- |']
    fmt=lambda x:'unbounded' if x is None else f'{x:.3f}'
    ratiofmt=lambda x:'unbounded' if x is None else f'{x:.4f}'
    for r in a['rows']:
        if 'speedup' not in r:continue
        v=r['speedup'];s=r['saved_ms'];n=r['summaries']['native'];x=r['summaries']['fp4x2']
        lines.append(f"| {r['family']} | {r['tier']} | {n['session_ms']:.3f} | {x['session_ms']:.3f} | {v['median']:.4f} [{ratiofmt(v['lower'])}, {ratiofmt(v['upper'])}] | {s['median']:.3f} [{fmt(s['lower'])}, {fmt(s['upper'])}] | {'passes' if r['useful_scoped_gain'] else 'not established'} |")
    lines += ['',f"Frozen seed {f['seed']}; 32 blocks, balanced 16/16 lane order per family/tier.",
        'Exact binomial median intervals use Bonferroni alpha 0.05/16 across eight paired ratios and eight',
        'absolute savings. Rank 8 gives at least 95% simultaneous coverage conditional on independent blocks;',
        'at least 25/32 blocks must exceed a threshold for its lower bound to exceed that threshold.',
        'Within-session solves are not independent samples. Shared host/device activity and temporal',
        'dependence limit the interpretation. Marginal medians need not divide to the paired speedup.',
        'The scoped criterion requires full coverage, original-model certificates, ratio lower bound above',
        '1.0 and savings lower bound above 10 ms/session (0.3125 ms/request). This exploratory value floor',
        'is not a production SLO. The separate 1.10x comparison is provisional. All block, pair-order and',
        'first-16 sensitivity results remain in the machine-readable analysis. No old data are pooled.','',
        '## Measured cost partitions','',
        '| Family / tier | Native / FP4 setup ms | Native / FP4 request ms | Native / FP4 GPU phase ms | Native / FP4 physical updates |',
        '| --- | ---: | ---: | ---: | --- |']
    for r in a['rows']:
        if 'summaries' not in r:continue
        n=r['summaries']['native'];x=r['summaries']['fp4x2']
        lines.append(f"| {r['family']} / {r['tier']} | {n['setup_ms']:.3f} / {x['setup_ms']:.3f} | {n['request_ms']:.3f} / {x['request_ms']:.3f} | {n['gpu_ms']:.3f} / {x['gpu_ms']:.3f} | {n['work']} / {x['work']} |")
    lines += ['', 'Setup is per session; request and nested GPU times are medians per solve. Updates include',
        'correction work. Lower GPU time alone does not establish a complete-session benefit.']
    strict=next(r for r in a['rows'] if r['family']=='dense-coupled-2048' and r['tier']=='certified-1e-9')
    n=strict['summaries']['native'];x=strict['summaries']['fp4x2'];parts=x['aggregate_cost_ns'];total=x['aggregate_session_ns']
    lines += ['', '## Performance diagnosis and limits','',
        f"Strict coupled2048 GPU phase time falls from {n['gpu_ms']:.3f} to {x['gpu_ms']:.3f} ms/request ({n['gpu_ms']/x['gpu_ms']:.3f}x), while both lanes retain {n['work']} physical updates per request. Complete-session medians fall from {n['session_ms']/1000:.3f} to {x['session_ms']/1000:.3f} seconds; the paired median gain is {strict['speedup']['median']:.4f}x.",
        f"In aggregate FP4 complete-session cost, independent checking occupies {100*parts['solver/checker']/total:.2f}%, setup {100*parts['setup']/total:.2f}%, audit {100*parts['solver/audit']/total:.2f}% and iteration {100*parts['solver/iteration']/total:.2f}%. These disjoint host spans explain why the larger GPU gain produces a modest delivered gain. Nested GPU time is not added again.",
        f"Strict coupled2048 setup medians are {n['setup_ms']:.3f} ms native and {x['setup_ms']:.3f} ms FP4. This is an observed complete setup difference, not isolated attribution to representation construction. Scenario switching is only about {x['switch_ms']:.3f} ms/request in the FP4 lane.",
        f"All {a['physical_updates']} physical updates and {a['unique_endpoints']} distinct final model/tier endpoints are retained. No recovery event occurs in this cohort; that does not establish recovery behavior outside these admitted streams.",
        'All four coupled comparisons pass the scoped value criterion. Generic1024 at 1e-9 also passes;',
        'generic1024 at 1e-7 has a ratio lower bound above parity but fails the 10 ms savings floor.',
        'Both generic2048 intervals include parity. No comparison passes the provisional 1.10x lower bound.',
        'The generic1024 tiers both take 200 updates and have nearly identical GPU phase times; their',
        'different complete-session decisions do not establish a tolerance-dependent arithmetic effect.',
        'The first-16 intervals for generic1024/1e-9 and coupled2048/1e-7 include parity, while their',
        'predeclared full 32-block decisions pass. All first-16 medians and both pair-order medians remain',
        'above parity, but these descriptive sensitivities do not establish temporal independence or a cause.',
        'Further complete-cost work should target exact checker and preparation costs while preserving',
        'original-model authority. These observations do not authorize a public preset or follow-on study.', '', POLICY,
        '## Observed resource behavior','',
        f"Maximum sample-start gap: {d['max_sample_gap_ns']/1e6:.3f} ms; maximum scan duration: {d['max_sample_work_ns']/1e6:.3f} ms; maximum guardian loop gap: {d['max_guardian_gap_ns']/1e6:.3f} ms.",
        f"The coordinator records {sum(len(r['timing_exceedances']) for r in d['blocks'])} gap/scan events above 100 ms. Their intervals may overlap and counts must not be added as elapsed time.",
        f"{sum(bool(r['timing_exceedances']) for r in d['blocks'])} of 32 blocks contain such an event. Maximum heartbeat delivery lag is {d['max_delivery_lag_ns']/1e6:.3f} ms. These distinct timing boundaries describe actual observations and do not identify the cause of a delayed scan.",
        f"Peak observed aggregate RSS is {max((r['peak_rss_bytes'] or 0) for r in d['blocks'])/(1<<30):.3f} GiB; this is a sampled observation, not a hard maximum.",
        'All coarse environment snapshots and resource receipts remain visible without block exclusions.','',
        '## Validation and reproducibility','',
        'Full native gate: 638 repository Rust / 781 Python tests plus 28 isolated Rust tests, Clippy,',
        'dependency audit, committed-record replay, artifact/documentation checks and smoke. The new',
        'supervisor has 39 contracts. Same-image admission compares 64 smoke and 1536 full-pilot outputs',
        'with the exact original scenarios. Existing device/four-sanitizer admissions are reused only for',
        'the exact unchanged numerical source/image. Six analysis corruption guards reject changed work,',
        'configuration, response bytes, original authority, cost partitions and duplicate cells; missing',
        'sessions or resource failures suppress confirmation. Final acceptance additionally requires',
        'all 512 complete sessions / 16384 certified solves.','',
        'The first full trajectory-verification reservation was undersized: the historical 10648-output',
        'check took about 207 seconds, so a 240-second reserve did not provide adequate margin for',
        '16384 outputs. It was stopped cleanly, its full 960 CPU seconds and source were retained,',
        'and the same retained records were checked under a new 600-second CPU-only reservation.',
        'This correction repeats verification, not scientific execution or timing.','',
        '[Analysis](data/mixed2-confirm2-analysis-v1.json), [block diagnosis](data/mixed2-confirm2-diagnosis-v1.json),',
        '[portable response archive](data/mixed2-confirm2-records-v1.json).',
        'Replay: `python3 tools/lp_mixed2_confirm2_analysis.py verify`.']
    if ACCEPTANCE.exists():
        x=load(ACCEPTANCE);lines += ['',f"The original independent serial checker covers {x['serial_responses']} response files / {x['serial_requests']} assessments / {x['serial_unique']} distinct endpoint/tier pairs. Every trajectory, endpoint, audit, recovery, checkpoint and physical-work record matches admission. Portable replay passes without the original artifacts tree. All {x['historical_files']} historical tracked files and prior handoff/backlog entries remain exact."]
    if ACCOUNTING.exists():
        x=load(ACCOUNTING);lines += ['',f"Independent allocation closed at {x['cpu_seconds']:.9f} / 96000 CPU and {x['gpu_seconds']:.9f} / 12000 GPU seconds, including 128 closing CPU seconds. Failed reservations: {x['failed_jobs']}; all retain sources and full charges. Cleanup is empty; historical transfers are zero.",
            '[Acceptance](data/mixed2-confirm2-acceptance-v1.json), [accounting](data/mixed2-confirm2-accounting-v1.json),',
            '[development evidence](data/mixed2-confirm2-evidence-v1.json), [resource receipts](data/mixed2-confirm2-resources-v1.json.gz).']
    if (DATA/'mixed2-confirm2-closing-admin-v1.json').exists():
        lines += ['', '[Closing verification](data/mixed2-confirm2-closing-admin-v1.json).']
    lines += ['', 'GPUP-8 remains incomplete and GPUP-9 gated. Commit locally only.']
    REPORT.write_text('\n'.join(lines)+'\n')


def handoff():
    a=load(ANALYSIS);x=load(ACCEPTANCE);c=load(ACCOUNTING)
    require(a['status']=='complete-confirmation' and a['sessions']==512 and a['solves']==16384 and
            x['status']=='passed' and c['status']=='closed','complete closed delivery required')
    passing=sum(r.get('useful_scoped_gain',False) for r in a['rows'])
    coupled=[r['speedup']['median'] for r in a['rows'] if r['family'].startswith('dense-coupled-')]
    strict=next(r for r in a['rows'] if r['family']=='dense-coupled-2048' and r['tier']=='certified-1e-9')
    n=strict['summaries']['native'];f=strict['summaries']['fp4x2']
    entry=f'''## MIXED2 confirmation complete under revised sampling policy (2026-11-14)

SPEC-0041 / ADR-0074 complete all 32 independent frozen blocks, 512 sessions and
16384 original-model certified solves. Scoped value passes {passing}/8 comparisons;
full results, uncertainty, order sensitivity and cost partitions are in the report.
No historical pooling, retry, regrading or public-default change.
Coupled session speedups are {min(coupled):.4f}–{max(coupled):.4f}x; generic1024/1e-9
also passes, while the other generic value comparisons remain unestablished.
No comparison passes the provisional 1.10x lower bound. Strict coupled2048 GPU
time falls {n['gpu_ms']:.3f} -> {f['gpu_ms']:.3f} ms/request with the same 800 updates;
complete-session medians are {n['session_ms']/1000:.3f} -> {f['session_ms']/1000:.3f} seconds.
FP4 independent checking occupies about 46% and setup 34% of complete cost.
The useful next targets are exact checking and preparation; no follow-on study
is released by this confirmation. All unfavorable and sensitivity results remain.

The user authorizes revising the 100 ms resource rule. A one-second finite hard
sampling/freshness/scan bound retains a 5–10 ms target and all 100 ms exceedances.
All 39 supervisor contracts pass, including beyond-bound refusal/cleanup. Exact
source comparison preserves other enforcement. Sampled RSS is not a hard memory
enclosure. CPU phase observations support limited margin at 100 ms but do not
establish the cause of historical stalls; detailed findings and limits are retained.

Full native acceptance: 638 repository Rust / 781 Python plus 28 isolated Rust.
Fresh smoke and three full-size pilots compare 1600 outputs exactly. All 16384
scientific trajectories match admission; independent serial checking covers
{x['serial_responses']} responses / {x['serial_requests']} assessments /
{x['serial_unique']} distinct endpoint/tier pairs. Portable replay passes; all
{x['historical_files']} historical files and prior handoffs/backlog entries remain exact.

Independent allocation closed at {c['cpu_seconds']:.9f} CPU /
{c['gpu_seconds']:.9f} GPU seconds, including 128 closing CPU seconds.
All {c['failed_jobs']} failed reservations/full charges/sources are retained and cleanup is empty. No funding
transfer, GPUP-8 completion or GPUP-9 release. Commit locally only.
Report: [complete confirmation](docs/benchmarks/lp-mixed2-confirm2.md).

'''
    for name in ('AGENTS.md','docs/plans/gpu-lp-precision-roadmap.md'):
        p=ROOT/name;s=p.read_text();title,tail=s.split('\n',1)
        value=entry if name=='AGENTS.md' else entry.replace('(docs/benchmarks/','(../benchmarks/')
        require(entry.splitlines()[0] not in s,'handoff already published')
        p.write_text(title+'\n\n'+value+tail.lstrip('\n'))
    p=ROOT/'state/backlog.yaml';s=p.read_text();start=s.index('  - id: GPUP-MIXED2-CONFIRM2\n');end=s.index('  - id: GPUP-MIXED2-CONFIRM\n',start)
    task=f'''  - id: GPUP-MIXED2-CONFIRM2
    title: Complete independent MIXED2 confirmation after availability diagnosis
    status: complete
    depends_on: [GPUP-MIXED2-CONFIRM]
    specification: docs/specifications/SPEC-0041-mixed2-confirm2.md
    acceptance: "All 32 frozen blocks, 512 complete sessions and 16384 certified solves; scoped value passes {passing}/8 comparisons. Revised finite one-second sampling policy retains all 100 ms exceedances and sampled-memory limitations. 39 supervisor contracts, full native checks, three full-size pilots, exact trajectories, independent serial checking, portable replay and historical preservation pass. Old results/charges remain exact. No public default or GPUP-9 release. Report: docs/benchmarks/lp-mixed2-confirm2.md."
'''
    s=s[:start]+task+s[end:];s=s.replace('next_ready_task: GPUP-MIXED2-CONFIRM2','next_ready_task: GPUP-8-DISPOSITION',1);p.write_text(s)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['report','preserve','verify','close','handoff'])
    globals()[p.parse_args().action]()
