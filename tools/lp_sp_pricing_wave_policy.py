"""Prospective nonblocking-start policy test, retaining the completed wave cohort."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from lp_sp_pricing_budget import BASE,ROOT,CPU,GPU,NS,binding,put
from lp_sp_pricing_gpu_opt_compare import confirmation_usage,read,verify
from lp_sp_pricing_wave_measure import admission
from lp_sp_pricing_wave_quality import validate
from lp_sp_pricing_baselines import PYTHON,portable,audit,images
from lp_sp_pricing_study import FAMILIES,generated
from lp_billion_owned_process import execute

LANES=['cpu','wave','opportunistic']


def policy_sources():
    return [binding(ROOT/p) for p in ['research/lp-sp-pricing/python/sp_pricing/gpu_wave_policy.py',
        'tools/lp_sp_pricing_wave_policy_run.py','tests/integration/test_lp_sp_pricing_wave_policy.py']]


def cpu(identity):
    out=BASE/identity;out.mkdir(exist_ok=False)
    gate=admission()
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing*.py'],check=True)
    put(out/'result.json',dict(status='passed',sources=policy_sources(),numerical_admission=gate,
        scope='Python startup scheduling only; admitted GPU/interval/GMP numerical sources remain exact'))


def validate_policy():
    path=BASE/'wave-policy-cpu-v1/result.json';d=read(path)
    if d['status']!='passed' or d['sources']!=policy_sources():raise RuntimeError('startup policy CPU gate changed')
    verify(d['numerical_admission']);validate(d['numerical_admission']['path'])
    if read(BASE/'resources/wave-policy-cpu-v1.settlement.json')['status']!='passed':raise RuntimeError('policy CPU reservation did not pass')
    return binding(path)


def launch(lane,model,out):
    out.mkdir(exist_ok=False)
    tool='lp_sp_pricing_wave_policy_run.py' if lane=='opportunistic' else 'lp_sp_pricing_wave_run.py'
    command=[str(PYTHON),'-B',str(ROOT/'tools'/tool),str(model),str(out/'response.json'),'--steps','1000','--seconds','10']
    if lane!='opportunistic':command+=['--lane',lane]
    put(out/'started.json',dict(model=binding(model),lane=lane,command=command,native_seconds=10,process_seconds=15))
    process=execute(command,out/'stdout.jsonl',out/'stderr',15,None);put(out/'process.json',process)
    return process


def development(identity):
    gate=validate_policy();out=BASE/identity;out.mkdir(exist_ok=False);(out/'cells').mkdir();rows=[]
    cells=[dict(id=f'{f}-8-73011',family=f,columns=8,rows=4 if f=='wide' else 32 if f=='tall' else 16,seed=73011) for f in FAMILIES]
    put(out/'plan.json',dict(cells=cells,lanes=['wave','opportunistic'],native_seconds=10,process_seconds=15,
        cold_process=True,heldout=False,selection='maximize timely exact certificates, then minimize capped cold process cost',gate=gate))
    for index,cell in enumerate(cells):
        directory=out/'models'/cell['id'];directory.mkdir(parents=True);model,witness=generated(cell)
        put(directory/'model.json',model);put(directory/'construction.json',witness)
        for lane in (['wave','opportunistic'] if index%2==0 else ['opportunistic','wave']):
            target=out/'cells'/(cell['id']+'-'+lane);process=launch(lane,directory/'model.json',target)
            response=read(target/'response.json') if (target/'response.json').exists() else {}
            from lp_sp_pricing_verify import verify as exact_verify
            proof=exact_verify(model,response) if response.get('certificate') else dict(accepted=False)
            timely=process['returncode']==0 and not process['timed_out'] and response.get('solve_ns',float('inf'))<=10*NS
            row=dict(model=cell['id'],lane=lane,exact_accepted=proof['accepted'],timely=timely,process_ns=process['elapsed_ns'],
                response=binding(target/'response.json') if response else None);rows.append(row);print(json.dumps(row),flush=True)
    put(out/'result.json',dict(status='completed',rows=rows,gate=gate))


def freeze(identity):
    gate=validate_policy();development_path=BASE/'wave-policy-development-v1/result.json';d=read(development_path);scores=[]
    for lane in ['wave','opportunistic']:
        rows=[r for r in d['rows'] if r['lane']==lane]
        scores.append(dict(lane=lane,certified=sum(r['timely'] and r['exact_accepted'] for r in rows),
            capped_ns=sum(min(r['process_ns'],15*NS) for r in rows)))
    selected=min(scores,key=lambda s:(-s['certified'],s['capped_ns']))['lane']
    if confirmation_usage()+4*(740+120)*NS>CPU['confirmation']*NS or confirmation_usage(True)+740*NS>GPU['confirmation']*NS:
        raise RuntimeError('policy confirmation does not fit unchanged phase caps')
    out=BASE/identity;out.mkdir(exist_ok=False);(out/'cells').mkdir();models=[];cells=[]
    for index,family in enumerate(FAMILIES):
        cell=dict(id=f'{family}-8-111359',family=family,columns=8,rows=4 if family=='wide' else 32 if family=='tall' else 16,seed=111359)
        directory=out/'models'/cell['id'];directory.mkdir(parents=True);start=time.perf_counter_ns()
        model,witness=generated(cell);put(directory/'rational.json',model);put(directory/'construction.json',witness);portable(model,directory/'portable.json')
        models.append(dict(**cell,rational=binding(directory/'rational.json'),portable=binding(directory/'portable.json'),encoding_ns=time.perf_counter_ns()-start))
        for repetition in range(2):
            shift=(index+repetition)%3
            for lane in LANES[shift:]+LANES[:shift]:cells.append(dict(id=f"{cell['id']}-r{repetition}-{lane}",lane=lane,model_index=index,repetition=repetition))
    sources=list((ROOT/'research/lp-sp-pricing/python').rglob('*.py'))+list((ROOT/'research/lp-sp-pricing/native').glob('*.*'))
    sources+=list((ROOT/'tools').glob('lp_sp_pricing_wave*.py'))
    sources+=[ROOT/'tools'/n for n in ['lp_sp_pricing_run.py','lp_sp_pricing_budget.py','lp_sp_pricing_guard.py','lp_sp_pricing_baselines.py','lp_sp_pricing_verify.py']]
    put(out/'freeze.json',dict(status='frozen',models=models,cells=cells,selected=selected,selection=scores,
        development=binding(development_path),sources=[binding(p) for p in sorted(set(sources))],gate=gate,images=images(),
        numerical_admission=admission(),native_seconds=10,process_seconds=15,
        caveats=['seven small generated models, two repetitions, no cache flushing',
            'policy was motivated by the preceding held-out cohort; this confirmation uses a new seed',
            'all initialization and final teardown remain inside cold complete cost']))


def validate_freeze(path):
    f=read(path);verify(f['gate']);validate_policy();verify(f['development']);verify(f['numerical_admission']);validate(f['numerical_admission']['path'])
    for item in f['sources']:verify(item)
    for model in f['models']:verify(model['rational']);verify(model['portable'])
    if images()!=f['images']:raise RuntimeError('checker image changed')
    return f


def worker(path):
    f=validate_freeze(path)
    for cell in f['cells']:
        model=f['models'][cell['model_index']];out=path.parent/'cells'/cell['id']
        process=launch(cell['lane'],Path(model['rational']['path']),out)
        print(json.dumps(dict(cell=cell['id'],process=process)),flush=True)
    put(path.parent/'solves-completed.json',dict(status='all_policy_cells_attempted'))


def audits(path):
    f=validate_freeze(path);rows=[]
    if not (path.parent/'solves-completed.json').exists():raise RuntimeError('policy solve roster incomplete')
    for cell in f['cells']:
        model=f['models'][cell['model_index']];out=path.parent/'cells'/cell['id'];process=read(out/'process.json')
        response=read(out/'response.json') if (out/'response.json').exists() else {}
        proof=audit('practical',Path(model['portable']['path']),Path(model['rational']['path']),out)
        timely=process['returncode']==0 and not process['timed_out'] and process['elapsed_ns']<=15*NS and response.get('solve_ns',float('inf'))<=10*NS
        rows.append(dict(cell=cell['id'],lane=cell['lane'],model=model['id'],family=model['family'],repetition=cell['repetition'],
            status=response.get('status','missing_response'),timely=timely,exact_accepted=bool(proof.get('exact') and proof['exact']['accepted']),
            strict_accepted=proof['accepted'],native_ns=response.get('solve_ns'),process_ns=process['elapsed_ns'],audit_ns=proof['elapsed_ns'],
            encoding_ns=model['encoding_ns'],complete_ns=model['encoding_ns']+process['elapsed_ns']+proof['elapsed_ns'],
            response=binding(out/'response.json') if response else None,audit=binding(out/'audit.json')))
    put(path.parent/'result.json',dict(status='all_policy_cells_audited',rows=rows,freeze=binding(path)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu','development','freeze','worker','audit']);p.add_argument('target');a=p.parse_args()
    if a.action=='cpu':cpu(a.target)
    elif a.action=='development':development(a.target)
    elif a.action=='freeze':freeze(a.target)
    elif a.action=='worker':worker(Path(a.target).resolve())
    else:audits(Path(a.target).resolve())
