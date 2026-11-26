"""Report and settle the preparation/interval/synchronous-search follow-up."""
import argparse
import collections
import csv
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import unittest
from lp_sp_pricing_budget import BASE,ROOT,CPU,GPU,NS,accounting,binding,put
from lp_sp_pricing_gpu_opt_report import bindings,pairs
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_wave_compare import validate_freeze,LANES
from lp_sp_pricing_report import resource_summary


def median(values):return statistics.median(values) if values else None


def report(identity,freeze):
    f=validate_freeze(freeze);out=BASE/identity;out.mkdir(exist_ok=False)
    evidence=freeze.parent/'result.json';data=read(evidence);rows=data['rows'];checked=bindings(data)
    if len(rows)!=len(f['cells']) or {r['cell'] for r in rows}!={c['id'] for c in f['cells']}:
        raise RuntimeError('frozen comparison coverage differs')
    archive=read(BASE/'wave-baseline-v1/baseline.json');verify(archive['preceding_checkpoint'])
    for item in archive['sources']:
        verify(item['retained']);checked+=1
        if any(item['original'][k]!=item['retained'][k] for k in ('bytes','sha256')):raise RuntimeError('preceding source archive changed')
    lanes={};profiles={}
    for lane in LANES:
        group=[r for r in rows if r['lane']==lane];responses=[read(r['response']['path']) for r in group if r['response']]
        lanes[lane]=dict(attempts=len(group),timely_exact=sum(r['timely'] and r['exact_accepted'] for r in group),
            timely_strict=sum(r['timely'] and r['strict_accepted'] for r in group),
            vendor_optimal=sum(r['status']==1 for r in group),statuses=dict(collections.Counter(str(r['status']) for r in group)),
            complete_seconds=sum(r['complete_ns'] for r in group)/NS,median_complete_seconds=median([r['complete_ns']/NS for r in group]))
        events=[e['gpu'] for response in responses for e in response.get('events',[]) if e.get('gpu')]
        batches=[b for e in events for b in e.get('batches',[])]
        profiles[lane]=dict(device_seconds=sum(b['device_iteration_ms'] for b in batches)/1000,
            host_check_seconds=sum(b['exact_check_ns'] for b in batches)/NS,
            exposed_preparation_seconds=sum(e.get('preparation_ns',0) for e in events)/NS,
            actual_async_initialization_seconds=sum(r.get('wave_session',{}).get('initialization_ns',0) or 0 for r in responses)/NS,
            initialization_wait_seconds=sum(r.get('wave_session',{}).get('initialization_wait_ns',0) for r in responses)/NS,
            gmp_fallbacks=sum(e.get('gmp_fallbacks',0) for e in events),gpu_labels=sum(e['gpu_labels'] for e in events),
            auxiliary_calls=sum(e.get('auxiliary_calls',0) for r in responses for e in r.get('events',[])),
            auxiliary_phase_seconds=sum(r.get('phase_ns',{}).get('auxiliary_labels',0) for r in responses)/NS)
    comparisons=[pairs(rows,left,'wave',tier) for tier in ('exact','strict') for left in ('cpu','lean','copt_scale_off')]
    micro=read(BASE/'wave-micro-v1/result.json');kernels=[]
    for case in sorted({r['case'] for r in micro['rows']}):
        for sparse in (False,True):
            group=[r for r in micro['rows'] if r['case']==case and r['sparse']==sparse and r['width']==256]
            times={lane:median([r['device_ms'] for r in group if r['lane']==lane]) for lane in ('lean','wave')}
            kernels.append(dict(case=case,sparse=sparse,width=256,device_ms=times,lean_over_wave=times['lean']/times['wave']))
    diagnostic=read(BASE/'wave-preparation-diagnostic-v1/result.json');prep=[]
    for lane in ['old','aot-static','aot-shared']:
        group=[r for r in diagnostic['rows'] if r['lane']==lane]
        cold=[r for r in group if not r['explicit_initialization']];explicit=[r for r in group if r['explicit_initialization']]
        prep.append(dict(lane=lane,cold_preparation_ms=median([r['records'][0]['preparation_ns']/1e6 for r in cold]),
            explicit_runtime_init_ms=median([r['runtime_initialization_ns']/1e6 for r in explicit]),
            warm_preparation_ms=median([r['records'][1]['preparation_ns']/1e6 for r in cold]),
            complete_ms=median([r['complete_ns']/1e6 for r in cold])))
    result=dict(schema=1,status='wave_followup_complete',lanes=lanes,pairs=comparisons,rows=rows,profiles=profiles,
        preparation_diagnostic=prep,preparation_evidence=binding(BASE/'wave-preparation-diagnostic-v1/result.json'),
        micro=micro,micro_summary=kernels,micro_evidence=binding(BASE/'wave-micro-v1/result.json'),
        selection=f['selection'],selected_steps=f['steps'],freeze=binding(freeze),comparison=binding(evidence),
        admission=f['admission'],resources=resource_summary(),verified_bindings=checked,
        limitations=f['caveats'],literal_reference_validated=False,billion_nonzero_solves=0)
    put(out/'result.json',result)
    (ROOT/'docs/benchmarks/lp-sp-pricing-wave-results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    fields=[k for k in rows[0] if k not in ('response','audit')]
    with (ROOT/'docs/benchmarks/lp-sp-pricing-wave-comparison.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in rows)
    lines=['# GPU preparation, rigorous checks and synchronized auxiliary searches','',
        'This follow-up retains the preceding [lean candidate evaluation](lp-sp-pricing-gpu.md) and adds solve-scoped preparation, rigorous interval/GMP decisions and synchronized auxiliary iteration. The final original-model certificates and independent 1e-9 checker remain unchanged.','',
        'See the [full evidence](lp-sp-pricing-wave-results.json), [all comparison cells](lp-sp-pricing-wave-comparison.csv), [interval argument](../../research/lp-sp-pricing/interval-notes.md), and [settled checkpoint](lp-sp-pricing-wave-checkpoint.json).','',
        '## Preparation diagnosis','',
        'The prior binary contains sm_75 code; the new build explicitly targets sm_120 and uses shared cudart. A controlled three-rotation diagnostic separates first-use CUDA initialization from matrix preparation. Its complete time includes two preparations and two 64-step proposals; warm timing uses the second preparation in the same process.','',
        '| Build | Cold preparation ms | Explicit runtime initialization ms | Warm preparation ms | Complete diagnostic ms |',
        '| --- | ---: | ---: | ---: | ---: |']
    for p in prep:lines.append(f"| {p['lane']} | {p['cold_preparation_ms']:.3f} | {p['explicit_runtime_init_ms']:.3f} | {p['warm_preparation_ms']:.3f} | {p['complete_ms']:.3f} |")
    lines+=['','The dominant first-use cost is runtime initialization. Native architecture selection helps modestly; it does not remove that cost. COPT keeps internal device preparation inside its opaque solve timer, so the separate COPT model-import/preparation field is not a directly comparable measure. No unmeasured COPT device-setup advantage is assumed.','',
        '## Implemented changes','',
        '- Start CUDA initialization concurrently with CPU geometry and market work. Record both initialization duration and exposed waiting time; all work remains inside cold end-to-end timing.',
        '- Retain one stream, event pair and growing device arena across pricing queries. Upload matrix/control data once and zero numerical states on device, avoiding transfers of host-generated zeros.',
        '- Advance all signed auxiliary objectives through common iteration checkpoints. Larger-matrix kernels reuse each coefficient and CSR index across four right-hand sides. Active indices remove resolved searches without rebuilding the CUDA graph.',
        '- Pass contiguous native proposal buffers directly to a batched interval checker. Avoid Python list reconstruction and per-proposal rational-string conversion.',
        '- Enclose original rational coefficients exactly and widen floating operations outward. Accept only proved quarter-threshold decisions; resolve uncertainty with the original GMP checker. Stop a dual residual scan as soon as its lower bound proves that proposal cannot certify the target.', '',
        'Independent auxiliary searches share matrix work. Successive pricing rounds still depend on previous labels and wealth updates. The larger diagnostic matrices test auxiliary throughput only; they do not establish large original-LP scalability.','',
        '## Fixed-work iteration and host-check costs','',
        'Both implementations use the same diagonal FP64 PDHG equations, 256 target states and 256 steps. Medians use three rotated repetitions. The lean control processes four batches of 64; the wave candidate processes all 256 states together. Ratios use CUDA-event iteration time. The wave diagnostic reuses a packed host basis and session, while the control rebuilds its per-query context; the retained auxiliary complete_ns fields therefore have different preparation reuse and are not cold-preparation comparisons.','',
        '| Auxiliary | Format | Lean device ms | Wave device ms | Lean / wave |','| --- | --- | ---: | ---: | ---: | ---: |']
    for k in kernels:lines.append(f"| {k['case']} | {'CSR' if k['sparse'] else 'dense'} | {k['device_ms']['lean']:.3f} | {k['device_ms']['wave']:.3f} | {k['lean_over_wave']:.3f}× |")
    lines+=['','Host-check diagnostics use identical raw proposals and compare compact GMP decisions with interval/GMP decisions. Context preparation is excluded from this checker-only table and retained separately in complete solve costs.','',
        '| Auxiliary | GMP ms | Interval/GMP ms | Median paired speedup |','| --- | ---: | ---: | ---: |']
    for case in sorted({r['case'] for r in micro['checks']}):
        group=[r for r in micro['checks'] if r['case']==case]
        lines.append(f"| {case} | {median([r['gmp_ns']/1e6 for r in group]):.3f} | {median([r['interval_ns']/1e6 for r in group]):.3f} | {median([r['gmp_ns']/r['interval_ns'] for r in group]):.3f}× |")
    lines+=['','## Fresh original-LP comparison','',
        f"Development selected a {f['steps']}-step ceiling by timely exact certificates and then capped cost. Seven fresh seed-99173 models cover all seven families. Four lanes and two cyclic rotations give 56 cold processes. Every lane has ten native seconds and fifteen process seconds. Complete cost includes common model encoding, process startup, all initialization and teardown, solving, output and the independent endpoint audits. Idle observation and resource settlement remain charged outside comparable cost.", '',
        '| Lane | Timely exact | Timely strict 1e-9 | Vendor optimal | Total complete seconds | Median complete seconds |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for lane,d in lanes.items():lines.append(f"| {lane} | {d['timely_exact']}/{d['attempts']} | {d['timely_strict']}/{d['attempts']} | {d['vendor_optimal'] if lane=='copt_scale_off' else '—'} | {d['complete_seconds']:.3f} | {d['median_complete_seconds']:.3f} |")
    lines+=['','Totals and medians include unsuccessful attempts and do not measure equal certified work. COPT uses the retained scale-off GPU-PDLP configuration, not automatic defaults. Its numerical optimal status and strict independent acceptance remain distinct. A nonzero floating dual residual on free variables can prevent a finite rigorous bound without establishing that the vendor optimum is wrong.','',
        '| Tier | Comparator / wave | Paired models / repetitions | Median ratio | Range |',
        '| --- | --- | ---: | ---: | ---: |']
    for p in comparisons:
        ratio='—' if p['median_left_over_right'] is None else f"{p['median_left_over_right']:.3f}×"
        span='—' if p['minimum_left_over_right'] is None else f"{p['minimum_left_over_right']:.3f}–{p['maximum_left_over_right']:.3f}×"
        lines.append(f"| {p['tier']} | {p['left']} / wave | {p['paired_models']} / {p['paired_repetitions']} | {ratio} | {span} |")
    lines+=['','Only jointly timely accepted pairs receive ratios; values above one favor wave. All outcomes and unmatched certificates remain in the CSV. This small two-repetition cohort does not establish broad solver superiority.','',
        'The following totals are internal GPU diagnostics across the candidate runs. Exposed preparation includes waiting, conversion and upload; asynchronous initialization duration overlaps CPU work and is not additive with complete solve time.','',
        '| Lane | Exposed preparation s | Actual asynchronous initialization s | Host proposal checks s | Device iterations s | CPU auxiliary calls |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for lane in ('lean','wave'):
        p=profiles[lane];lines.append(f"| {lane} | {p['exposed_preparation_seconds']:.4f} | {p['actual_async_initialization_seconds']:.4f} | {p['host_check_seconds']:.4f} | {p['device_seconds']:.4f} | {p['auxiliary_calls']} |")
    lines+=['','The zero asynchronous-initialization entry for lean means it performs initialization synchronously inside preparation, not that its startup is free. The complete process stopwatch includes both implementations\' startup work.','',
        '## Admission and retained failures','',
        'CPU tests cover exact rational enclosures, equality at the threshold, cancellation, subnormal values, box clipping, malformed inputs and non-default rounding. ASan/UBSan checks 128 native interval/GMP cases. GPU quality covers 54 configurations and 2,464 exact proposals, continued state, inactive searches, scalar equations and comparison with the preceding FP64 engine. All four CUDA sanitizer smoke checks and a cold asynchronous original-LP smoke solve pass.','',
        'The first GPU admission stopped during sanitizer finalization with a supervised “No such process” error after numerical quality and memcheck completed. Its failed receipt, empty cleanup and full 960 CPU / 240 GPU-second charge remain. The study-local process mapper now handles ProcessLookupError as well as FileNotFoundError for an already observed exiting process. Permission failures and foreign GPU processes still fail admission; the shared resource-critical files and limits remain exact. A fresh source-bound CPU gate passes before continuation of only the unfinished sanitizer work. The missing full traceback limits attribution of the original error to this exit-race explanation.','',
        'All earlier failures, source archives and numerical results remain. The final checkpoint records CPU/GPU usage, test results, source verification and exact process cleanup. Public defaults, literal-reference limitations and billion-case capacity refusals remain unchanged.','']
    (ROOT/'docs/benchmarks/lp-sp-pricing-wave.md').write_text('\n'.join(lines))
    print(json.dumps(dict(status=result['status'],lanes=lanes,pairs=[{k:v for k,v in p.items() if k!='rows'} for p in comparisons])),flush=True)


def final_verify(identity,freeze):
    report(identity,freeze)
    paths=list((ROOT/'research/lp-sp-pricing/python').rglob('*.py'))+list((ROOT/'tools').glob('lp_sp_pricing_*.py'))+list((ROOT/'tests/integration').glob('test_lp_sp_pricing*.py'))
    for p in paths:compile(p.read_text(),str(p),'exec')
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing*.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun<63 or result.skipped:raise RuntimeError('final acceptance failed')
    docs=subprocess.run([sys.executable,'-B',str(ROOT/'tools/build_docs.py')],cwd=ROOT,check=True,text=True,capture_output=True)
    print(docs.stdout,end='',flush=True);pages=re.search(r'documentation built: (\d+) pages',docs.stdout)
    if not pages:raise RuntimeError('documentation receipt missing')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT);count=0
    for raw in untracked.split(b'\0'):
        if not raw:continue
        p=ROOT/raw.decode()
        if p.suffix not in {'.py','.rs','.cu','.cpp','.h','.toml','.md','.json','.csv'}:continue
        for i,line in enumerate(p.read_text().splitlines(),1):
            if line.rstrip()!=line:raise RuntimeError(f'trailing whitespace: {p}:{i}')
        count+=1
    put(BASE/identity/'verification.json',dict(status='passed',tests=result.testsRun,documentation_pages=int(pages[1]),
        python_sources=len(paths),untracked_text_files=count,checked_bindings=bindings(read(BASE/identity/'result.json')),
        result=binding(BASE/identity/'result.json'),outputs=[binding(ROOT/'docs/benchmarks'/n) for n in [
            'lp-sp-pricing-wave.md','lp-sp-pricing-wave-results.json','lp-sp-pricing-wave-comparison.csv']]))


def settle(identity,reservation):
    from lp_sp_pricing_finish import identities,still_same_process
    summary=resource_summary()
    if summary['pending_at_snapshot']:raise RuntimeError('active reservation')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if any(cpu[p]>CPU[p]*NS or gpu[p]>GPU[p]*NS for p in CPU):raise RuntimeError('phase ceiling exceeded')
    owned=set()
    for pattern in ('*.resource.json','*.journal.json'):
        for path in (BASE/'resources').glob(pattern):owned.update(identities(read(path)))
    if any(still_same_process(*p) for p in owned):raise RuntimeError('owned process still present')
    receipt=BASE/'resources'/(reservation+'.settlement.json');verification=BASE/identity/'verification.json'
    if read(receipt)['status']!='passed':raise RuntimeError('reporting did not settle successfully')
    bindings(read(verification));result=read(BASE/identity/'result.json')
    checkpoint=dict(status='wave_followup_settled',resources=summary,cpu_phase_ns=cpu,gpu_phase_ns=gpu,
        tests=read(verification)['tests'],documentation_pages=read(verification)['documentation_pages'],
        lanes=result['lanes'],pairs=[{k:v for k,v in p.items() if k!='rows'} for p in result['pairs']],
        owned_identities=len(owned),live_owned_identities=[],active_reservations=[],
        verification=binding(verification),reporting_settlement=binding(receipt))
    put(BASE/identity/'settled-checkpoint.json',checkpoint)
    target=ROOT/'docs/benchmarks/lp-sp-pricing-wave-checkpoint.json'
    target.write_text(json.dumps(checkpoint,indent=2,sort_keys=True)+'\n')
    preview=ROOT/'book/docs/benchmarks/lp-sp-pricing-wave-checkpoint.json'
    if preview.parent.exists():preview.write_bytes(target.read_bytes())
    print(json.dumps(dict(status=checkpoint['status'],cpu_seconds=summary['cpu_ns']/NS,gpu_seconds=summary['gpu_ns']/NS,
        owned_identities=len(owned))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','settle']);p.add_argument('identity')
    p.add_argument('--freeze',type=Path);p.add_argument('--reservation');a=p.parse_args()
    if a.action=='verify':final_verify(a.identity,a.freeze.resolve())
    else:settle(a.identity,a.reservation)
