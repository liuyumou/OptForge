"""Audit and report the fresh lean-GPU comparison without replacing history."""
import argparse
import csv
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import unittest

from lp_sp_pricing_budget import BASE,ROOT,CPU,GPU,NS,accounting,binding,put
from lp_sp_pricing_gpu_opt_compare import LANES,read,verify,validate_freeze
from lp_sp_pricing_gpu_opt_measure import admission
from lp_sp_pricing_report import resource_summary


def bindings(value):
    if isinstance(value,dict):
        if set(value)=={'path','bytes','sha256'}:
            verify(value)
            return 1
        return sum(bindings(v) for v in value.values())
    if isinstance(value,list):return sum(bindings(v) for v in value)
    return 0


def development():
    names=['cpu-ladder-v4','gpu-ladder-v2']+[f'gpu-opt-ladder-v{i}' for i in range(1,5)]
    rows=[]
    for name in names:
        path=BASE/name/'result.json';data=read(path)['rows']
        rows.append(dict(identity=name,cells=len(data),certified=sum(r['accepted'] for r in data),
            capped_seconds=sum(min(r['elapsed_ns']/NS,10) for r in data),evidence=binding(path)))
    return rows


def pairs(rows,left,right,tier):
    indexed={(r['model'],r['repetition'],r['lane']):r for r in rows}
    results=[]
    for key,l in indexed.items():
        if key[2]!=left:continue
        r=indexed[key[:2]+(right,)]
        if all(v['timely'] and v[tier+'_accepted'] for v in (l,r)):
            results.append(dict(model=l['model'],repetition=l['repetition'],
                left_complete_seconds=l['complete_ns']/NS,right_complete_seconds=r['complete_ns']/NS,
                left_over_right=l['complete_ns']/r['complete_ns']))
    ratios=[r['left_over_right'] for r in results]
    return dict(left=left,right=right,tier=tier,paired_repetitions=len(results),
        paired_models=len({r['model'] for r in results}),median_left_over_right=statistics.median(ratios) if ratios else None,
        minimum_left_over_right=min(ratios) if ratios else None,maximum_left_over_right=max(ratios) if ratios else None,
        right_faster_repetitions=sum(r>1 for r in ratios),rows=results)


def report(identity,freeze):
    frozen=validate_freeze(freeze);out=BASE/identity;out.mkdir(exist_ok=False)
    source=freeze.parent/'result.json';data=read(source);checked=bindings(data);rows=data['rows']
    expected={c['id'] for c in frozen['cells']}
    if len(rows)!=len(expected) or {r['cell'] for r in rows}!=expected:raise RuntimeError('comparison roster mismatch')
    historical=read(BASE/'gpu-optimization-baseline-v1/binding.json')
    verify(historical['previous_checkpoint'])
    for item in historical['sources']:
        verify(item['retained']);checked+=1
        if any(item['original'][k]!=item['retained'][k] for k in ('bytes','sha256')):
            raise RuntimeError('baseline archive changed')
    lanes={lane:dict(slots=len(subset),timely_exact=sum(r['timely'] and r['exact_accepted'] for r in subset),
        timely_strict=sum(r['timely'] and r['strict_accepted'] for r in subset),
        late_exact=sum(not r['timely'] and r['exact_accepted'] for r in subset),
        total_complete_seconds=sum(r['complete_ns'] for r in subset)/NS)
        for lane in LANES for subset in [[r for r in rows if r['lane']==lane]]}
    comparisons=[pairs(rows,left,'lean_gpu',tier) for tier in ('exact','strict') for left in ('legacy_gpu','cpu')]
    profiles=[]
    for row in rows:
        if not row['response']:continue
        response=read(row['response']['path'])
        events=[e['gpu'] for e in response['events'] if e.get('gpu')]
        batches=[b for e in events for b in e['batches']]
        profiles.append(dict(cell=row['cell'],model=row['model'],repetition=row['repetition'],lane=row['lane'],
            response_bytes=row['response']['bytes'],native_seconds=response['solve_ns']/NS,
            device_seconds=sum(b['device_iteration_ms'] for b in batches)/1000,
            exact_proposal_seconds=sum(b['exact_check_ns'] for b in batches)/NS,
            auxiliary_phase_seconds=response['phase_ns'].get('auxiliary_labels',0)/NS,
            gpu_labels_per_query=[e['gpu_labels'] for e in events],
            cpu_auxiliary_calls=[e['auxiliary_calls'] for e in response['events'] if 'auxiliary_calls' in e]))
    micro_path=BASE/'gpu-opt-micro-v3/result.json';micro=read(micro_path);kernels=[]
    for case in sorted({r['case'] for r in micro['rows']}):
        group=dict(case=case,format='csr',width=64)
        for implementation in ('legacy_fp32x2','legacy_fp64','lean_fp64'):
            subset=[r for r in micro['rows'] if r['case']==case and r['sparse'] and r['width']==64 and r['implementation']==implementation]
            group[implementation]={k.replace('_ns','_ms'):statistics.median(r[k] for r in subset)/1e6 for k in ('device_ns','complete_ns')}
        kernels.append(group)
    old_path=BASE/'gpu-ladder-v2/coupled-8-73011/result.json';old=read(old_path)
    batches=[b for e in old['events'] for b in e.get('gpu',{}).get('batches',[])]
    diagnosis=dict(evidence=binding(old_path),complete_seconds=old['complete_ns']/NS,
        device_seconds=sum(b['device_iteration_ms'] for b in batches)/1000,
        exact_check_seconds=sum(b['exact_check_ns'] for b in batches)/NS,
        per_query=[dict(gpu_labels=e['gpu']['gpu_labels'],cpu_auxiliary_calls=e['auxiliary_calls']) for e in old['events'] if 'gpu' in e])
    result=dict(schema=1,status='fresh_lean_gpu_comparison_complete',models=len(frozen['models']),slots=len(rows),
        selected_configuration=frozen['configuration'],lanes=lanes,pairs=comparisons,rows=rows,profiles=profiles,
        development=development(),diagnosis=diagnosis,micro=dict(evidence=binding(micro_path),
            completed_cells=len(micro['rows']),rows=micro['rows'],csr_width64=kernels,checker=micro['checker_comparison']),
        admission=admission(),comparison=binding(source),freeze=binding(freeze),
        resources=resource_summary(),verified_bindings=checked,
        limitations=['Eight small generated models, two rotated repetitions, one GPU, unflushed caches.',
            'CPU and lean GPU both use compact traces; the archived legacy GPU retains its full traces.',
            'Microbenchmark fixes targets/steps; diagonal preconditioning changes candidate iterates.',
            'Microbenchmark full proof output differs from the compact proof decisions used in complete solves.',
            'Exact rational acceptance and the unchanged original-model 1e-9 checker are separate tiers.',
            'No new vendor comparison, full literal strongly-polynomial validation, or billion-nonzero solve.'],
        broad_end_to_end_superiority=False)
    put(out/'result.json',result)
    compact=ROOT/'docs/benchmarks/lp-sp-pricing-gpu-results.json'
    compact.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    csv_path=ROOT/'docs/benchmarks/lp-sp-pricing-gpu-comparison.csv'
    fields=[k for k in rows[0] if k not in ('response','audit')]
    with csv_path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in rows)
    lines=['# Lean GPU pricing candidate: diagnosis and measured results','',
        'This follow-up removes measured overhead from the practical pricing candidate. It preserves the final original-model certificate and exact CPU fallback. The original [completed study](lp-sp-pricing.md) remains historical.','',
        'See the [compact evidence](lp-sp-pricing-gpu-results.json), [complete cell table](lp-sp-pricing-gpu-comparison.csv), and [implementation](../../research/lp-sp-pricing/README.md).','',
        '## Why the previous GPU path was slower','',
        f"The retained coupled eight-variable case took {diagnosis['complete_seconds']:.3f} seconds. Device iterations used {diagnosis['device_seconds']:.3f} seconds, while Python exact proposal checking used {diagnosis['exact_check_seconds']:.3f} seconds. Its last query obtained no GPU labels and still needed {diagnosis['per_query'][-1]['cpu_auxiliary_calls']} exact CPU auxiliary solves.", '',
        'The old path repeated rational matrix products, constructed large intermediate witnesses, checked already resolved targets, restarted state for precision escalation, and launched several kernels per iteration. FP32 component cross-products used CUDA cores and FP64 accumulation; they did not exploit tensor cores. The difficult final query also had a convergence problem: its large calibration box amplified dual stationarity error, so more mantissa bits alone did not produce exact negative labels.','',
        '## Components removed from the candidate hot path','',
        '- FP32/FP4 component decomposition and precision restarts: the selected candidate uses native FP64.',
        '- Repeated GPU state allocation: matrix, transpose, workspaces and events are reused across stages.',
        '- Separate projection launches: small matrices use a persistent kernel; larger matrices use fused products and projections with four row warps per block and replayed CUDA graphs.',
        '- Resolved searches: active indices compact the launch grid, and exact labels also resolve companion targets.',
        '- Full intermediate witness strings and Python Fraction parsing: a native GMP checker returns compact label decisions. It computes the primal product once and skips an unnecessary dual bound.',
        '- Unproductive full passes: a stratified pilot stops after 256 steps if it establishes no exact label, handing the remaining work to the exact CPU oracle.', '',
        'Diagonal steps use 0.9 divided by absolute row/column sums. Weighted Cauchy–Schwarz bounds the scaled operator norm by 0.9. Zero rows/columns use unit steps. This improves numerical proposals without granting them acceptance authority. Exact final certificates, strict independent checking, resource limits and failure records remain. Historical implementations stay available for differential tests and reproduction.','',
        '## Fixed-work diagnostics','',
        'Each cell performs 64 target searches at 1,000 steps. The table uses CSR, width 64, and medians of three rotated repetitions. Times are device iteration milliseconds; complete auxiliary timings, dense results and all 108 cells are retained in the compact evidence. Candidate preconditioning changes iterates, so these are equal-step cost comparisons, not equal-convergence speedups.','',
        '| Auxiliary | Old FP32×2 | Old FP64 | Lean FP64 |','| --- | ---: | ---: | ---: |']
    for k in kernels:lines.append('| '+k['case']+' | '+' | '.join(f"{k[v]['device_ms']:.3f}" for v in ('legacy_fp32x2','legacy_fp64','lean_fp64'))+' |')
    c=micro['checker_comparison']
    lines+=['',f"On the same {c['proposals']} raw proposals, Python exact checks took {c['python_ns']/1e6:.3f} ms, native full proofs {c['native_ns']/1e6:.3f} ms, and compact native decisions {c['native_compact_ns']/1e6:.3f} ms ({c['python_ns']/c['native_compact_ns']:.2f}× faster than Python). All decisions match the independent Python checker.", '',
        '## Development and frozen confirmation','',
        '| Development version | Exact certificates | Capped seconds |','| --- | ---: | ---: |']
    for d in result['development']:lines.append(f"| {d['identity']} | {d['certified']}/{d['cells']} | {d['capped_seconds']:.3f} |")
    lines+=['','Development uses seed 73011 and ten-second per-case caps. Selection maximizes timely exact certificates, then minimizes capped cost. Held-out seed 88371 was frozen after selection. The fresh comparison has eight models across seven families, three lanes and two cyclic order rotations: 48 cold processes. Every lane gets ten native seconds and twenty process seconds. Complete cost includes common model encoding, cold startup, preparation, solving, output and the separate independent exact/strict audit. Idle observation and supervision settlement remain charged but are outside comparable cost.','',
        '| Lane | Timely exact | Timely strict 1e-9 | All-cell complete seconds |','| --- | ---: | ---: | ---: |']
    for name,d in lanes.items():lines.append(f"| {name} | {d['timely_exact']}/{d['slots']} | {d['timely_strict']}/{d['slots']} | {d['total_complete_seconds']:.3f} |")
    lines+=['','All-cell totals include failures and are descriptive; they do not imply equal certified work. Ratios below include only jointly timely certified model/repetition pairs. Values above one favor the lean GPU candidate.','',
        '| Tier | Comparator / lean GPU | Paired models / repetitions | Median ratio | Range |','| --- | --- | ---: | ---: | ---: |']
    for p in comparisons:
        ratio='—' if p['median_left_over_right'] is None else f"{p['median_left_over_right']:.3f}×"
        span='—' if p['minimum_left_over_right'] is None else f"{p['minimum_left_over_right']:.3f}–{p['maximum_left_over_right']:.3f}×"
        lines.append(f"| {p['tier']} | {p['left']} / lean_gpu | {p['paired_models']} / {p['paired_repetitions']} | {ratio} | {span} |")
    lines+=['','The first dense confirmation repetition illustrates where time was removed. These are internal diagnostic phases, not additive complete-cost components; the device time excludes host transfers and checking. Output size includes the retained final certificate.','',
        '| Lane | Device seconds | Exact proposal-check seconds | Auxiliary phase seconds | Response bytes |',
        '| --- | ---: | ---: | ---: | ---: |']
    for p in profiles:
        if p['model']=='dense-8-88371' and p['repetition']==0:
            lines.append(f"| {p['lane']} | {p['device_seconds']:.4f} | {p['exact_proposal_seconds']:.4f} | {p['auxiliary_phase_seconds']:.4f} | {p['response_bytes']} |")
    lines+=['','CPU and lean GPU share compact trace output; improvements from that change are not credited exclusively to GPU arithmetic. The old GPU retains its archived full-trace implementation. All deadlines, missing endpoints, late certificates, unmatched outcomes and regressions remain in the CSV. These small generated cases and two repetitions do not establish broad solver superiority or replace the earlier vendor comparison.','',
        '## Correctness and retained operational failures','',
        'The final candidate passes 64 dense/CSR/width configurations and 1,680 exact differential proposal comparisons. Tests cover continued state, inactive targets, scalar diagonal-PDHG equations, full and compact exact decisions, malformed inputs and lifetime handling. All four CUDA sanitizer smoke processes pass on both persistent and graph paths. The native proof checker passes ASan/UBSan on 96 cases. Final CPU and documentation results appear in the settled checkpoint.','',
        'Three failed GPU admission reservations remain: v2 lost its coordinator (empty cleanup), v3 recorded cleanup_incomplete, and v5 failed an overly strong synthetic-label assertion. The first two preceding causes are unavailable; no GPU OOM attribution is made. All seven exact identities from v3 subsequently exited; an additive read-only cleanup proof and source-bound CPU readmission permit continuation without changing the failed receipt. Sanitizer smoke sizes were reduced while retaining both kernel paths. The synthetic fixture now uses epsilon = 1/(1024N); a regression also checks when opposite-slot label inference is unjustified. The first CPU freeze reservation failed because its accounting query included its own active admission reservation; the corrected future-phase query preserves full failed charges and rejects an unsettled confirmation reservation. No LP had started in that failure. All full failure charges remain.','',
        'The study allocation and phase caps are unchanged. The final [settled checkpoint](lp-sp-pricing-gpu-checkpoint.json) records usage, failures and process cleanup. The full literal paper run and billion-nonzero evaluation retain their earlier capacity limitations. No tensor-core, arbitrary-precision GPU, or strongly polynomial runtime claim is made.','']
    (ROOT/'docs/benchmarks/lp-sp-pricing-gpu.md').write_text('\n'.join(lines))
    print(json.dumps(dict(status=result['status'],lanes=lanes,pairs=[{k:v for k,v in p.items() if k!='rows'} for p in comparisons])),flush=True)


def final_verify(identity,freeze):
    report(identity,freeze)
    sources=list((ROOT/'research/lp-sp-pricing/python').rglob('*.py'))+list((ROOT/'tools').glob('lp_sp_pricing_*.py'))+list((ROOT/'tests/integration').glob('test_lp_sp_pricing*.py'))
    for path in sources:compile(path.read_text(),str(path),'exec')
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing*.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun<51 or result.skipped:
        raise RuntimeError('final component acceptance failed or skipped required native tests')
    docs=subprocess.run([sys.executable,'-B',str(ROOT/'tools/build_docs.py')],cwd=ROOT,check=True,text=True,capture_output=True)
    print(docs.stdout,end='',flush=True)
    pages=re.search(r'documentation built: (\d+) pages',docs.stdout)
    if not pages:raise RuntimeError('missing documentation receipt')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT)
    text_count=0
    for raw in untracked.split(b'\0'):
        if not raw:continue
        path=ROOT/raw.decode()
        if path.suffix not in {'.py','.rs','.cu','.cpp','.h','.toml','.md','.json','.csv'}:continue
        for i,line in enumerate(path.read_text().splitlines(),1):
            if line.rstrip()!=line:raise RuntimeError(f'trailing whitespace: {path}:{i}')
        text_count+=1
    put(BASE/identity/'verification.json',dict(status='passed',tests=result.testsRun,documentation_pages=int(pages[1]),
        compiled_sources=len(sources),untracked_text_files_checked=text_count,
        checked_bindings=bindings(read(BASE/identity/'result.json')),
        result=binding(BASE/identity/'result.json'),report=binding(ROOT/'docs/benchmarks/lp-sp-pricing-gpu.md'),
        compact=binding(ROOT/'docs/benchmarks/lp-sp-pricing-gpu-results.json'),csv=binding(ROOT/'docs/benchmarks/lp-sp-pricing-gpu-comparison.csv')))


def settle(identity,reservation):
    from lp_sp_pricing_finish import identities,still_same_process
    summary=resource_summary()
    if summary['pending_at_snapshot']:raise RuntimeError('unsettled reservation')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if any(cpu[p]>CPU[p]*NS or gpu[p]>GPU[p]*NS for p in CPU):raise RuntimeError('allocation exceeded')
    owned=set()
    for pattern in ('*.resource.json','*.journal.json'):
        for path in (BASE/'resources').glob(pattern):owned.update(identities(read(path)))
    if any(still_same_process(*i) for i in owned):raise RuntimeError('recorded process still active')
    receipt=BASE/'resources'/(reservation+'.settlement.json')
    if read(receipt)['status']!='passed':raise RuntimeError('final reporting failed')
    verification=BASE/identity/'verification.json';bindings(read(verification))
    result=read(BASE/identity/'result.json')
    checkpoint=dict(status='lean_gpu_followup_settled',cpu_phase_ns=cpu,gpu_phase_ns=gpu,
        resources=summary,recorded_owned_identities=len(owned),recorded_owned_identities_still_live=[],
        tests=read(verification)['tests'],documentation_pages=read(verification)['documentation_pages'],
        lanes=result['lanes'],pairs=[{k:v for k,v in p.items() if k!='rows'} for p in result['pairs']],
        verification=binding(verification),reporting_settlement=binding(receipt),active_reservations=[])
    put(BASE/identity/'settled-checkpoint.json',checkpoint)
    (ROOT/'docs/benchmarks/lp-sp-pricing-gpu-checkpoint.json').write_text(json.dumps(checkpoint,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(status=checkpoint['status'],cpu_seconds=summary['cpu_ns']/NS,
        gpu_seconds=summary['gpu_ns']/NS,owned_identities=len(owned))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['report','verify','settle']);p.add_argument('identity')
    p.add_argument('--freeze',type=Path);p.add_argument('--reservation');a=p.parse_args()
    if a.action=='settle':settle(a.identity,a.reservation)
    elif a.action=='verify':final_verify(a.identity,a.freeze.resolve())
    else:report(a.identity,a.freeze.resolve())
