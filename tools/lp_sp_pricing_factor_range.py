"""Common adaptive dyadic-dual extension; no repeated LP solves."""
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import numpy as np
from lp_sp_pricing_budget import ROOT,BASE,NS,put,binding,accounting
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_factor_budget import CPU,GPU,allocation
from lp_sp_pricing_factor_report import pairs
from lp_sp_pricing_transform_experiment import STUDY,validate
from lp_sp_pricing_factor_proof import exact_primal_proposal,inverse_proposal
from lp_sp_pricing_factor_parallel_proof import check as independent,verify_arrays
from lp_sp_pricing_geometry_run import load
from lp_sp_pricing_baselines import PYTHON
from lp_billion_arrays import read as read_array,write
from lp_billion_owned_process import execute
from lp_sp_pricing_report import resource_summary
from lp_sp_pricing_finish import identities,still_same_process

OUT=BASE/'factor-range-extension-v1'
MAIN=BASE/'factor-report-v2'


def build(a,b,c,x,y):
    start=time.perf_counter_ns();primal=exact_primal_proposal(a,b,c,x)
    if primal is None:return None,dict(reason='no_exact_active_primal')
    if not np.isfinite(y).all():return None,dict(reason='nonfinite_dual')
    xp,active,px=primal;n=a.shape[1];maximum=float(np.max(np.maximum(y,0.),initial=0))
    exponent=math.frexp(maximum)[1] if maximum else 0
    if maximum>2**52:return None,dict(reason='adaptive_dual_range_limit')
    py=max(0,min(48,52-exponent))
    rounded=np.rint(np.ldexp(np.maximum(y,0.),py))
    if not np.isfinite(rounded).all() or np.max(rounded,initial=0)>2**52:return None,dict(reason='adaptive_dual_range_limit')
    y0=np.ldexp(rounded,-py);y0[~active]=0.;available=np.flatnonzero(active&(y0>0))
    if len(available)<n:return None,dict(reason='insufficient_positive_active_rows')
    attempts=[]
    for selected in (available[np.argsort(-y0[available],kind='stable')[:n]],available[np.linspace(0,len(available)-1,n,dtype=int)]):
        try:
            inverse=inverse_proposal(a[selected].toarray().T,gpu=False)
            if not np.isfinite(inverse).all():raise ArithmeticError('nonfinite inverse')
        except (ArithmeticError,ValueError,np.linalg.LinAlgError) as error:attempts.append(str(error));continue
        refined=y0.copy();steps=0
        for _ in range(2):
            residual=c-np.asarray(a.T@refined).ravel();proposed=np.rint(np.ldexp(refined[selected]+inverse@residual,py))
            if not np.isfinite(proposed).all() or np.min(proposed,initial=0)<0 or np.max(proposed,initial=0)>2**52:break
            refined[selected]=np.ldexp(proposed,-py);steps+=1
        return dict(x=xp,y0=refined,basis=selected.astype(np.uint32),inverse=inverse),dict(
            method='adaptive_exponent_implicit_dual_proposal',primal_exponent=px,dual_base_exponent=py,maximum_returned_dual=maximum,
            numerical_dual_refinement_steps=steps,gpu_inverse=False,attempts=attempts,elapsed_ns=time.perf_counter_ns()-start)
    return None,dict(reason='inverse_proposal_failed',attempts=attempts)


def child(model,response,output):
    start=time.perf_counter_ns();original=read(response);a,b,c,_,_=load(model)
    x=read_array(BASE,original['endpoint']['primal']);y=-read_array(BASE,original['endpoint']['dual'])
    cert,detail=build(a,b,c,x,y);result=dict(status='implicit_exact_proposal' if cert else 'no_certificate',model=binding(model),original_response=binding(response),construction=detail)
    if cert:result['implicit_certificate']=dict(primal=write(BASE,cert['x']),dual_base=write(BASE,cert['y0']),basis=write(BASE,cert['basis'],'u32le'),inverse=write(BASE,cert['inverse'].ravel()))
    result['elapsed_ns']=time.perf_counter_ns()-start;put(output,result)


def admitted():
    validate();verification=read(MAIN/'verification.json')
    if verification['status']!='passed' or verification['tests']!=112 or read(BASE/'resources/factor-final-verify-v2.settlement.json')['status']!='passed':raise RuntimeError('range CPU test admission')
    reservation=read(BASE/'resources/factor-final-verify-v2.reservation.json')
    for path in (Path(__file__).resolve(),ROOT/'tests/integration/test_lp_sp_pricing_factor_range.py'):
        source=next(item for item in reservation['sources'] if item['path']==str(path))
        if binding(path)['sha256']!=source['sha256']:raise RuntimeError('range tested source changed')
    return binding(MAIN/'verification.json')


def run():
    gate=admitted();f=validate();main=read(MAIN/'result.json');OUT.mkdir(exist_ok=False)
    selected=[]
    for row in main['rows']:
        if not row['accepted'] and row.get('reconstructed'):
            metadata=read(row['reconstructed']['path'])
            if metadata.get('implicit_construction',{}).get('reason')=='dual_base_range':selected.append(row)
    put(OUT/'plan.json',dict(source=binding(__file__),admission=gate,main=binding(MAIN/'result.json'),selected_ids=[r['id'] for r in selected],
        common_policy='For every main roster endpoint, retain an existing accepted certificate. Retry only dual_base_range with exponent max(0,min(48,52-frexp(max_positive_dual).exponent)), rejecting magnitude above 2^52. All other outcomes unchanged. Add every extra construction/proof cost; never rerun a solver.',
        disclosure='Post-hoc format extension after the default-scaling COPT range rejection was observed. Original outcomes remain immutable.'))
    updated=[];records=[]
    for source in main['rows']:
        row=dict(source);row['range_extension_ns']=0
        if source not in selected:updated.append(row);continue
        out=OUT/'runs'/row['id'];out.mkdir(parents=True,exist_ok=False);original=read(row['reconstructed']['path']);model=Path(original['model']['path'])
        retry_start=time.perf_counter_ns()
        cmd=[str(PYTHON),'-B',__file__,'child','--model',str(model),'--response',source['response']['path'],'--output',str(out/'response.json')]
        proc=execute(cmd,out/'stdout',out/'stderr',90,None);put(out/'process.json',proc)
        result=read(out/'response.json') if (out/'response.json').exists() else {};proof={};checkproc=None
        if result.get('implicit_certificate'):
            cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_factor_parallel_proof.py'),str(model),str(out/'response.json'),str(out/'proof.json')]
            checkproc=execute(cmd,out/'proof-stdout',out/'proof-stderr',120,None);put(out/'proof-process.json',checkproc)
            if (out/'proof.json').exists():proof=read(out/'proof.json')
        accepted=bool(proc['returncode']==0 and not proc['timed_out'] and checkproc and checkproc['returncode']==0 and not checkproc['timed_out'] and proof.get('accepted'))
        added=time.perf_counter_ns()-retry_start
        row.update(accepted=accepted,original_accepted=source['accepted'],range_extension_ns=added,complete_ns=source['complete_ns']+added,
            range_response=binding(out/'response.json') if result else None,range_proof=binding(out/'proof.json') if proof else None)
        if accepted:
            a,b,c,_,_=load(model);data=result['implicit_certificate'];x=read_array(BASE,data['primal']);y=read_array(BASE,data['dual_base']);basis=read_array(BASE,data['basis']);inverse=read_array(BASE,data['inverse']).reshape(len(c),len(c))
            negative=y.copy();negative[int(basis[0])]=-1
            bad=verify_arrays(a.indptr,a.indices,a.data,b,c,x,negative,basis,inverse)
            zero=verify_arrays(a.indptr,a.indices,a.data,b,c,x,y,basis,np.zeros_like(inverse))
            if bad['accepted'] or zero['accepted'] or zero.get('visited_nonzeros')!=a.nnz:raise ArithmeticError('range corruption challenge')
            put(out/'challenges.json',dict(negative_dual=bad,zero_inverse=zero))
        put(out/'result.json',row);records.append(binding(out/'result.json'));updated.append(row)
        print(json.dumps({k:row[k] for k in ('id','accepted','range_extension_ns','complete_ns')}),flush=True)
    alternate_pairs=pairs(updated,[m for m in f['models'] if m['scaled']],'optimized',['copt-gpu-scaling-auto'])
    put(OUT/'result.json',dict(status='all_range_limited_endpoints_disposed',source=binding(__file__),plan=binding(OUT/'plan.json'),rows=updated,
        corrected_records=records,default_scaling_pairs=alternate_pairs,solver_reexecutions=0))


def report():
    admitted();receipt=BASE/'resources/factor-range-extension-v1.settlement.json'
    if read(receipt)['status']!='passed':raise RuntimeError('range extension supervision')
    result=read(OUT/'result.json');checked=bindings(result);target=ROOT/'docs/benchmarks/lp-sp-pricing-factor-range-results.json'
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    affected=[r for r in result['rows'] if r['range_extension_ns']]
    lines=['# Adaptive dual-range certificate extension','',
        'The [main factorized-geometry study](lp-sp-pricing-factor.md) retains all original outcomes. Its fixed exponent 48 limited the dual base to magnitude 16, which rejected returned default-scaling COPT duals before proof construction. This additional common policy chooses a smaller exponent when needed, preserving at most 52 integer magnitude bits. The unchanged independent exact checker decides acceptance.','',
        'The policy applies to every original roster endpoint: accepted certificates are retained; only dual_base_range failures receive adaptive reconstruction; all other outcomes remain unchanged. No LP solver is rerun. This extension was specified after the range limitation was observed. Every extra cold construction and proof process is added to the original complete cost, including the original unsuccessful reconstruction. These are composed pipeline totals from phases measured at different times, without cache flushing. Corruption challenges remain separate research validation costs.','',
        f'{len(affected)} endpoints trigger the common rule; {sum(r["accepted"] for r in affected)} receive exact certificates. See [full alternative-pipeline evidence](lp-sp-pricing-factor-range-results.json).','',
        '| Seed | Both timely and exact | Optimized candidate complete s | Default-scaling COPT plus certificate complete s | COPT / candidate |',
        '| ---: | --- | ---: | ---: | ---: |']
    for pair in result['default_scaling_pairs']:
        ratio='—' if not pair['eligible'] else f'{pair["control_over_candidate"]:.3f}×'
        lines.append(f'| {pair["seed"]} | {pair["eligible"]} | {pair["candidate_seconds"]:.3f} | {pair["control_seconds"]:.3f} | {ratio} |')
    lines+=['','Original raw 1e-9 assessments and native solver statuses are unchanged. These results concern a rigorously corrected implicit dual, not raw COPT certification. The additional negative-dual and zero-inverse challenges reject every accepted extension certificate; zero-inverse checks scan the full original matrix.','',
        'The main regression suite includes three adaptive-range tests: large positive null-space duals, a non-dyadic exact dual, and invalid/extreme inputs. Final resource accounting includes both studies, all failures and this extension.','']
    doc=ROOT/'docs/benchmarks/lp-sp-pricing-factor-range.md';doc.write_text('\n'.join(lines))
    docs=subprocess.run([sys.executable,'-B',str(ROOT/'tools/build_docs.py')],cwd=ROOT,text=True,capture_output=True,check=True)
    print(docs.stdout,end='',flush=True);pages=int(re.search(r'documentation built: (\d+) pages',docs.stdout)[1])
    put(OUT/'verification.json',dict(status='passed',tests=112,documentation_pages=pages,checked_bindings=checked,
        main_verification=binding(MAIN/'verification.json'),extension_settlement=binding(receipt),source=binding(__file__),
        outputs=[binding(doc),binding(target)],result=binding(OUT/'result.json')))


def settle():
    admitted();verification=read(OUT/'verification.json');bindings(verification)
    receipt=BASE/'resources/factor-range-report-v1.settlement.json'
    if read(receipt)['status']!='passed':raise RuntimeError('range report supervision')
    summary=resource_summary()
    if summary['pending_at_snapshot']:raise RuntimeError('active reservation')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if any(cpu[p]>CPU[p]*NS or gpu[p]>GPU[p]*NS for p in CPU):raise RuntimeError('phase cap')
    owned=set()
    for pattern in ('*.resource.json','*.journal.json'):
        for path in (BASE/'resources').glob(pattern):owned.update(identities(read(path)))
    if any(still_same_process(*item) for item in owned):raise RuntimeError('owned process remains')
    now=dt.datetime.now(dt.timezone.utc);deadline=dt.datetime.fromisoformat(allocation()['wall_deadline_utc'])
    result=dict(status='factorized_geometry_and_range_extension_settled',verification=binding(OUT/'verification.json'),main_checkpoint=binding(MAIN/'settled-checkpoint.json'),
        reporting_settlement=binding(receipt),resources=summary,cpu_phase_ns=cpu,gpu_phase_ns=gpu,tests=112,documentation_pages=verification['documentation_pages'],
        owned_identities=len(owned),live_owned_identities=[],active_reservations=[],settled_utc=now.isoformat(),
        elapsed_from_campaign_start_seconds=(now-(deadline-dt.timedelta(hours=2))).total_seconds(),within_two_hours=now<=deadline)
    put(OUT/'settled-checkpoint.json',result);target=ROOT/'docs/benchmarks/lp-sp-pricing-factor-range-checkpoint.json'
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');(ROOT/'book/docs/benchmarks'/target.name).write_bytes(target.read_bytes())
    print(json.dumps(dict(status=result['status'],cpu_seconds=summary['cpu_ns']/NS,gpu_seconds=summary['gpu_ns']/NS,within_two_hours=result['within_two_hours'],elapsed_seconds=result['elapsed_from_campaign_start_seconds'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','child','report','settle']);p.add_argument('--model',type=Path);p.add_argument('--response',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.action=='run':run()
    elif a.action=='child':child(a.model,a.response,a.output)
    elif a.action=='report':report()
    else:settle()
