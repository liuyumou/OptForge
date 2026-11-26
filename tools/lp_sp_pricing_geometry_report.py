"""Report exact geometry diagnosis and fresh preparation-inclusive COPT pairs."""
import argparse
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
from lp_sp_pricing_budget import ROOT,BASE,NS,CPU,GPU,put,binding,accounting
from lp_sp_pricing_geometry_experiment import STUDY,validate
from lp_sp_pricing_geometry_copt_auto import AUTO,checked as validate_auto
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_report import resource_summary
from lp_sp_pricing_finish import identities,still_same_process


def historical_sources():
    """Verify the development CPU measurements against their actual old sources."""
    d=read(BASE/'geometry-development-v1/result.json')
    reservation=read(BASE/'resources/geometry-development-v1.reservation.json')
    retained={s['path']:s for s in reservation['sources']};checked=[]
    for item in d['sources']:
        path=Path(item['path']);current=binding(path)
        if current==item:checked.append(current);continue
        if path.suffix=='.so':target=BASE/'geometry-cpu-admit-v2'/path.name
        else:target=Path(retained[str(path)]['retained'])
        actual=binding(target)
        if any(actual[k]!=item[k] for k in ('bytes','sha256')):raise RuntimeError('historical development source changed')
        checked.append(actual)
    return checked


def report(identity):
    f=validate();out=BASE/identity;out.mkdir(exist_ok=False)
    audit=read(STUDY/'audits.json');rows=audit['rows']
    if len(rows)!=len(f['cells']) or {r['id'] for r in rows}!={r['id'] for r in f['cells']}:raise RuntimeError('incomplete comparison roster')
    automatic=validate_auto();auto_audit=read(AUTO/'audits.json')
    if len(auto_audit['rows'])!=3 or {r['model'] for r in auto_audit['rows']}!={m['name'] for m in f['models']}:raise RuntimeError('incomplete automatic-method roster')
    rows=rows+auto_audit['rows']
    supplemental=BASE/'geometry-native-sanitizer-v1/result.json'
    if read(supplemental)['status']!='passed' or read(BASE/'resources/geometry-native-sanitizer-v1.settlement.json')['status']!='passed':raise RuntimeError('native RREF sanitizer incomplete')
    development=read(BASE/'geometry-development-v1/result.json');rank=read(BASE/'geometry-rank-development-v1/result.json')
    geometry=[]
    for name in sorted({r['case'] for r in development['geometry']}):
        group={r['lane']:r for r in development['geometry'] if r['case']==name}
        a,b=group['fraction'],group['native'];both=all(r['status']=='completed' for r in (a,b))
        geometry.append(dict(case=name,fraction_seconds=a['elapsed_ns']/NS,native_seconds=b['elapsed_ns']/NS,
            matched_complete=both,ratio=a['elapsed_ns']/b['elapsed_ns'] if both else None))
    comparison=[]
    for model in f['models']:
        pair={r['lane']:r for r in rows if r['model']==model['name']}
        for vendor in ('copt','copt-auto'):
            a,b=pair['candidate'],pair[vendor];joint=all(r['timely'] and r['strict_accepted'] for r in (a,b))
            comparison.append(dict(model=model['name'],vendor=vendor,candidate_complete_seconds=a['complete_ns']/NS,
                copt_complete_seconds=b['complete_ns']/NS,jointly_timely_strict=joint,
                copt_over_candidate=b['complete_ns']/a['complete_ns'] if joint else None))
    phases=[]
    for row in rows:
        d=read(row['response']['path']) if row['response'] else {}
        phases.append(dict(id=row['id'],lane=row['lane'],input_ns=d.get('input_ns'),proposal=d.get('proposal'),
            geometry=d.get('geometry_diagnostics'),phase_ns=d.get('phase_ns'),vendor_profile=d.get('profile'),
            queries=d.get('queries'),hwm_bytes=d.get('process_hwm_bytes'),gpu_confirmed=d.get('gpu_confirmed'),
            native_exact=d.get('audit',{}).get('accepted',False),native_seconds=row['native_ns']/NS if row['native_ns'] else None))
    result=dict(status='geometry_and_fresh_million_comparison_audited',freeze=binding(STUDY/'freeze.json'),
        profile=binding(BASE/'geometry-profile-v1/result.json'),development=binding(BASE/'geometry-development-v1/result.json'),
        historical_development_sources=historical_sources(),rank_development=binding(BASE/'geometry-rank-development-v1/result.json'),
        supplemental_sanitizer=binding(supplemental),audits=binding(STUDY/'audits.json'),automatic_audits=binding(AUTO/'audits.json'),
        geometry=geometry,rank=rank['rows'],rows=rows,comparisons=comparison,phases=phases,
        checked_bindings=bindings(audit)+bindings(auto_audit)+bindings(read(supplemental))+bindings(rank)
            +bindings(read(BASE/'geometry-profile-v1/result.json'))+bindings({k:v for k,v in development.items() if k!='sources'}),resources=resource_summary(),
        automatic_control_disclosure=automatic['disclosure'],limitations=f['limitations'])
    put(out/'result.json',result);docs=ROOT/'docs/benchmarks'
    (docs/'lp-sp-pricing-geometry-results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    csvrows=[{k:r[k] for k in ['id','model','lane','status','reason','route','timely','strict_accepted','native_ns','process_ns','encoding_ns','audit_ns','complete_ns']} for r in rows]
    with (docs/'lp-sp-pricing-geometry-comparison.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(csvrows[0]));writer.writeheader();writer.writerows(csvrows)
    lines=['# Exact geometry acceleration and fresh million-scale COPT comparison','',
        'The new opt-in candidate combines native exact row reduction, a GPU exact modular full-space proof, and numerical factor proposals that can skip pricing only after exact original-model certification. The last path is a practical certified presolve; success there does not demonstrate completion of the paper pricing algorithm.','',
        'See the [results](lp-sp-pricing-geometry-results.json), [all comparison cells](lp-sp-pricing-geometry-comparison.csv), [settled checkpoint](lp-sp-pricing-geometry-checkpoint.json), and [preceding compact path](lp-sp-pricing-compact.md). The isolated entry point is `tools/lp_sp_pricing_geometry_run.py MODEL OUTPUT`; `--no-presolve` retains pricing construction, and `--cpu` disables the modular GPU proof and GPU auxiliary proposals. All runs require the unchanged study reservation wrapper.','',
        '## Diagnosis','',
        'Fresh seed-122101 million-nonzero profiles all stop in `slack_rref`, before calibration, expert construction or a GPU query. Each eight-second instrumented attempt makes about 18 million Python calls. Fraction construction, multiplication/subtraction, negation of one million input entries, and per-scalar resource checks dominate. GCD and rational bit growth are also real costs; sparse storage alone does not remove them. cProfile overhead prevents interpreting these eight-second traces as uninstrumented throughput.','',
        'The native sparse GMP backend avoids Python arithmetic objects and scalar callbacks inside elimination. It retains rational arithmetic, actual fill/bit/deadline limits and independent output comparisons. The bounded integer certificate kernel proves original primal feasibility, dual nonnegativity, exact dual equations and zero gap; its input/range guards keep every signed 128-bit intermediate below overflow. Unsupported ranges fall back, rather than weakening proof.','',
        'Dense square factor proposals use LAPACK LU; sparse square proposals use SuperLU with the same factorization for primal and transposed dual solves. Rectangular proposals use bounded LSMR. A fixed dyadic quantization ladder is followed by exact checking. Floating residual screens can reject a proposal but cannot accept one. The unchanged supervisor supplies single-thread BLAS; model loading and factorization are timed.','',
        '## Matched exact CPU geometry','',
        'Fresh small development matrices have identical exact RREF outputs. Times include Python/native marshaling and output reconstruction. Operation counters use different update units, so they are not fixed-work throughput counters. There is one diagnostic repetition.','',
        '| Case | Fraction implementation s | Native GMP s | Speedup |','| --- | ---: | ---: | ---: |']
    for g in geometry:lines.append(f"| {g['case']} | {g['fraction_seconds']:.3f} | {g['native_seconds']:.3f} | {g['ratio']:.3f}× |")
    lines+=['','## Exact GPU geometry','',
        'The GPU computes over the prime 65521 using bounded unsigned integer multiplication and reduction. Full modular column rank proves full rational rank because every input denominator is invertible modulo that prime. Only then may the full-space identity replace rational elimination. Rank deficiency modulo this prime is inconclusive and falls back to exact GMP. No floating pivot threshold, probabilistic rank acceptance or rounded basis is used.','',
        'The kernel visits only the active trailing matrix with a two-dimensional launch, eliminating unused threads and per-element integer division. Geometry matrix storage is capped at one GiB and released before auxiliary work. Rank timings below include rational-to-field packing, transfer and per-call teardown, but exclude fixture generation. The first GPU call includes CUDA initialization; the second reuses the initialized context in the same process. CPU attempts have five-second work windows; GPU proofs have 45 seconds. They are capacity/completion diagnostics, not equal-deadline speedup ratios.','',
        '| Matrix | Path | Result | Full space proved | Complete diagnostic s |','| --- | --- | --- | --- | ---: |']
    for r in rank['rows']:lines.append(f"| {r['case']} | {r['lane']} | {r['status']} | {r['full_space_proved']} | {r['elapsed_ns']/NS:.3f} |")
    lines+=['','CPU/GPU modular results agree on ten small configurations, including row swaps and deficient matrices. All four CUDA sanitizers pass. Large rank diagnostics use that admitted exact kernel; no completed large CPU rank comparison is claimed when the CPU attempt times out.','',
        '## Fresh million-nonzero comparison','',
        'Seed 122141 supplies dense 1000×1000, tall 4000×1000 (250 entries per row), and sparse 8000×8000 (125 per row) models, each with exactly one million nonzeros. Unlike the preceding uniform-witness cohort, primal coordinates and positive dual weights vary. All rows are active at the planted optimum, and coefficients/witnesses are short dyadic rationals. This structure can favor certified reconstruction; broader LP superiority is not established. Construction certificates pass the unchanged strict checker and are never passed to a solver.','',
        'Each lane gets 30 native seconds and a 45-second process allowance. The six primary cold attempts use alternating candidate/COPT order. The `copt` lane is the retained scale-off GPU-PDLP configuration. Three supplemental `copt-auto` cells use automatic CPU LP-method selection with default presolve/scaling/dualization/crossover, four threads, common 1e-9 tolerances and unchanged original coefficients. Their exact returned parameter defaults are retained. This stronger supplemental control was frozen after the primary roster and its first candidate timing were visible; the candidate was not retuned or repeated.','',
        'Complete cost includes common model encoding, process startup, input validation, import/CSR conversion, factorization or GPU preparation, solve, internal exact proof where used, output, teardown, and a cold independent original-model 1e-9 endpoint check. GPU idle observation and resource settlement are separately charged. COPT internal GPU setup remains inside its opaque solve call.','',
        '| Model | Lane | Result | Route | Native s | Complete s | Timely strict |','| --- | --- | --- | --- | ---: | ---: | --- |']
    for r in rows:
        native='—' if r['native_ns'] is None else f"{r['native_ns']/NS:.3f}"
        lines.append(f"| {r['model']} | {r['lane']} | {r['status']} | {r['route'] or 'COPT'} | {native} | {r['complete_ns']/NS:.3f} | {r['timely'] and r['strict_accepted']} |")
    lines+=['','| Model | COPT configuration | Jointly timely strict | COPT / candidate complete ratio |','| --- | --- | --- | ---: |']
    for c in comparison:
        ratio='—' if c['copt_over_candidate'] is None else f"{c['copt_over_candidate']:.3f}×"
        lines.append(f"| {c['model']} | {c['vendor']} | {c['jointly_timely_strict']} | {ratio} |")
    lines+=['','Ratios are reported only for jointly timely strict-certified endpoints. Vendor numerical optimality, an exact native certificate, and independent strict acceptance remain separate fields. A failure to obtain a finite strict dual bound is not a proof that a vendor numerical optimum is wrong. Deadlines and missing endpoints remain visible; no ratio is inferred from unequal or unsuccessful work.','',
        'In this roster, the candidate strictly certifies dense and sparse through CPU presolve. Tall remains a geometry deadline. GPU-PDLP COPT returns numerical optimality only on tall; automatic CPU COPT returns numerical optimality on dense and tall. Their floating endpoints have no finite strict dual bound. Automatic COPT sparse returns after 36.958 native seconds despite a requested 30-second limit and owned interruption; it remains late and has no endpoint. Its process stays within the separate 45-second outer allowance. All nine dispositions remain in the table.','',
        'The raw phase evidence identifies whether a candidate returns through certified presolve or enters pricing geometry. A successful CPU presolve does not initialize CUDA, and its GPU preparation cost is zero because no GPU work is needed. This is visible in the route, not hidden outside the stopwatch. GPU rank acceleration is evaluated separately.','',
        '## Validation and limitations','',
        'Eight new integration tests cover native/reference RREF, augmented inconsistency, resource refusals, modular rank semantics, exact certificate checks against an independent rational verifier, malformed/overflow inputs, nonuniform proposal recovery, and original optimal/infeasible/unbounded pricing outcomes. Native ASan/UBSan additionally covers 64 certificate cases and 64 RREF lifetime cases plus malformed/fill/overflow refusals. The final suite and document build are recorded in the settled checkpoint.','',
        'The first CPU admission retains its full 720 CPU-second failure charge for an unavailable optional thread-control import; the dependency was removed. The first successful GPU kernel and its source/binary receipts remain historical after the trailing-matrix optimization and fresh admission. No scientific identity is repeated. All resource caps, failures, original numerical/checker sources and public defaults remain unchanged.','',
        'One repetition, three synthetic all-active models, short dyadic certificates and unflushed caches limit generalization. Tall rectangular problems can still need expensive exact elimination and dense rational fill. The fast factor path is optional and falls back when it cannot prove an endpoint; it is not a complete LP algorithm by itself.','']
    (docs/'lp-sp-pricing-geometry.md').write_text('\n'.join(lines))


def verify_all(identity):
    report(identity)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing*.py')
    outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful() or outcome.skipped or outcome.testsRun!=91:raise RuntimeError('incomplete final tests')
    for path in (ROOT/'tools').glob('lp_sp_pricing_geometry*.py'):compile(path.read_text(),str(path),'exec')
    docs=subprocess.run([sys.executable,'-B',str(ROOT/'tools/build_docs.py')],cwd=ROOT,text=True,capture_output=True,check=True)
    print(docs.stdout,end='',flush=True);match=re.search(r'documentation built: (\d+) pages',docs.stdout)
    if not match:raise RuntimeError('documentation receipt')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    put(BASE/identity/'verification.json',dict(status='passed',tests=outcome.testsRun,documentation_pages=int(match[1]),
        result=binding(BASE/identity/'result.json'),outputs=[binding(ROOT/'docs/benchmarks'/name) for name in
        ['lp-sp-pricing-geometry.md','lp-sp-pricing-geometry-results.json','lp-sp-pricing-geometry-comparison.csv']]))


def settle(identity,reservation):
    validate();verification=BASE/identity/'verification.json';bindings(read(verification));summary=resource_summary()
    if summary['pending_at_snapshot']:raise RuntimeError('pending reservation')
    receipt=BASE/'resources'/(reservation+'.settlement.json')
    if read(receipt)['status']!='passed':raise RuntimeError('final verification supervision failed')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if any(cpu[p]>CPU[p]*NS or gpu[p]>GPU[p]*NS for p in CPU):raise RuntimeError('phase cap')
    owned=set()
    for pattern in ('*.resource.json','*.journal.json'):
        for path in (BASE/'resources').glob(pattern):owned.update(identities(read(path)))
    if any(still_same_process(*item) for item in owned):raise RuntimeError('owned process remains')
    d=dict(status='exact_geometry_comparison_settled',verification=binding(verification),reporting_settlement=binding(receipt),
        resources=summary,cpu_phase_ns=cpu,gpu_phase_ns=gpu,owned_identities=len(owned),live_owned_identities=[],active_reservations=[],
        tests=read(verification)['tests'],documentation_pages=read(verification)['documentation_pages'])
    put(BASE/identity/'settled-checkpoint.json',d);target=ROOT/'docs/benchmarks/lp-sp-pricing-geometry-checkpoint.json'
    target.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');(ROOT/'book/docs/benchmarks'/target.name).write_bytes(target.read_bytes())
    print(json.dumps(dict(status=d['status'],cpu_seconds=summary['cpu_ns']/NS,gpu_seconds=summary['gpu_ns']/NS,owned_identities=len(owned))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','settle']);p.add_argument('identity');p.add_argument('--reservation');a=p.parse_args()
    if a.action=='verify':verify_all(a.identity)
    else:settle(a.identity,a.reservation)
