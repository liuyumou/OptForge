"""Fresh frozen cold-process comparison including the retained COPT configuration."""
import argparse
import json
from pathlib import Path
import time
from lp_sp_pricing_budget import ROOT,BASE,CPU,GPU,NS,binding,put
from lp_sp_pricing_gpu_opt_compare import confirmation_usage,read,verify
from lp_sp_pricing_wave_measure import admission
from lp_sp_pricing_wave_quality import validate
from lp_sp_pricing_baselines import PYTHON,portable,images,audit,launch as baseline_launch
from lp_sp_pricing_study import generated,FAMILIES
from lp_billion_owned_process import execute

LANES=['cpu','lean','wave','copt_scale_off']


def freeze(identity):
    admitted=admission();choices=[]
    for name in ['wave-ladder-v1','wave-ladder-v2']:
        path=BASE/name/'result.json';d=read(path)
        choices.append(dict(steps=d['steps'],timely=sum(r['accepted'] and r['timely'] for r in d['rows']),
            capped_ns=sum(min(r['elapsed_ns'],10*NS) for r in d['rows']),evidence=binding(path)))
    selected=min(choices,key=lambda x:(-x['timely'],x['capped_ns']))
    if confirmation_usage()+4*(940+120)*NS>CPU['confirmation']*NS or confirmation_usage(True)+940*NS>GPU['confirmation']*NS:
        raise RuntimeError('whole confirmation does not fit the unchanged phase allocation')
    out=BASE/identity;out.mkdir(exist_ok=False);(out/'cells').mkdir();models=[];cells=[]
    for index,family in enumerate(FAMILIES):
        cell=dict(id=f'{family}-8-99173',family=family,columns=8,rows=4 if family=='wide' else 32 if family=='tall' else 16,seed=99173)
        directory=out/'models'/cell['id'];directory.mkdir(parents=True)
        start=time.perf_counter_ns();model,witness=generated(cell)
        put(directory/'rational.json',model);put(directory/'construction.json',witness);portable(model,directory/'portable.json')
        models.append(dict(**cell,rational=binding(directory/'rational.json'),portable=binding(directory/'portable.json'),
            encoding_ns=time.perf_counter_ns()-start))
        for repetition in range(2):
            shift=(index+repetition)%len(LANES)
            for lane in LANES[shift:]+LANES[:shift]:
                cells.append(dict(id=f"{cell['id']}-r{repetition}-{lane}",lane=lane,model_index=index,repetition=repetition))
    sources=list((ROOT/'research/lp-sp-pricing/python').rglob('*.py'))
    sources+=list((ROOT/'research/lp-sp-pricing/native').glob('*.*'))
    sources+=list((ROOT/'tools').glob('lp_sp_pricing_wave*.py'))
    sources+=[ROOT/'tools'/n for n in ['lp_sp_pricing_run.py','lp_sp_pricing_baselines.py','lp_sp_pricing_verify.py',
        'lp_sp_pricing_budget.py','lp_sp_pricing_guard.py','lp_sp_pricing_cleanup.py']]
    sources+=[ROOT/'research/lp-sp-pricing/target'/n for n in ['release/libsp_wave.so','release/libsp_batch_optimized.so',
        'cpu/libsp_proof.so','cpu/libsp_interval.so','cpu/libsp_auxiliary.so','cpu/libsp_market.so']]
    put(out/'freeze.json',dict(status='frozen',models=models,cells=cells,steps=selected['steps'],selection=choices,
        admission=admitted,sources=[binding(p) for p in sorted(set(sources))],images=images(),
        native_seconds=10,process_seconds=15,rotated_repetitions=2,sparse=True,
        async_initialization=True,lean_control_steps=1000,roster_slots=len(cells),
        timing='common model encoding + cold process including asynchronous GPU initialization and teardown + mandatory independent audit',
        caveats=['seven small generated models, two cyclic repetitions, no cache flush',
            'COPT device preparation remains inside opaque solve time',
            'ratios require joint timely certification; vendor optimal statuses reported separately']))


def validate_freeze(path):
    f=read(path);verify(f['admission']);validate(f['admission']['path'])
    for source in f['sources']:verify(source)
    for m in f['models']:verify(m['rational']);verify(m['portable'])
    for option in f['selection']:verify(option['evidence'])
    if f['images']!=images():raise RuntimeError('baseline/checker image changed')
    return f


def worker(path):
    f=validate_freeze(path)
    for cell in f['cells']:
        model=f['models'][cell['model_index']];out=path.parent/'cells'/cell['id']
        if cell['lane']=='copt_scale_off':
            result=baseline_launch('copt_scale_off',Path(model['portable']['path']),Path(model['rational']['path']),out,
                f['native_seconds'],f['process_seconds'])
        else:
            out.mkdir(exist_ok=False)
            command=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_wave_run.py'),model['rational']['path'],str(out/'response.json'),
                '--lane',cell['lane'],'--seconds',str(f['native_seconds']),
                '--steps',str(f['steps'] if cell['lane']=='wave' else f['lean_control_steps'])]
            put(out/'started.json',dict(model=model['rational'],command=command,lane=cell['lane']))
            result=execute(command,out/'stdout.jsonl',out/'stderr',f['process_seconds'],None);put(out/'process.json',result)
        print(json.dumps(dict(cell=cell['id'],process=result)),flush=True)
    put(path.parent/'solves-completed.json',dict(status='all_frozen_cells_attempted'))


def audits(path):
    f=validate_freeze(path);rows=[]
    if not (path.parent/'solves-completed.json').exists():raise RuntimeError('solve roster incomplete')
    for cell in f['cells']:
        model=f['models'][cell['model_index']];out=path.parent/'cells'/cell['id'];process=read(out/'process.json')
        response=read(out/'response.json') if (out/'response.json').exists() else {}
        proof=audit('copt_scale_off' if cell['lane']=='copt_scale_off' else 'practical',
            Path(model['portable']['path']),Path(model['rational']['path']),out)
        native=response.get('native_ns' if cell['lane']=='copt_scale_off' else 'solve_ns')
        timely=(not process['timed_out'] and process['returncode']==0 and native is not None and native<=f['native_seconds']*NS
                and process['elapsed_ns']<=f['process_seconds']*NS and response.get('returned_before_deadline',True))
        rows.append(dict(cell=cell['id'],lane=cell['lane'],model=model['id'],family=model['family'],repetition=cell['repetition'],
            status=response.get('status','missing_response'),timely=timely,exact_accepted=bool(proof.get('exact') and proof['exact']['accepted']),
            strict_accepted=proof['accepted'],native_ns=native,process_ns=process['elapsed_ns'],audit_ns=proof['elapsed_ns'],
            encoding_ns=model['encoding_ns'],complete_ns=model['encoding_ns']+process['elapsed_ns']+proof['elapsed_ns'],
            response=binding(out/'response.json') if response else None,audit=binding(out/'audit.json')))
    put(path.parent/'result.json',dict(status='all_frozen_cells_audited',rows=rows,freeze=binding(path)))
    print(json.dumps(dict(status='passed',cells=len(rows),strict=sum(r['strict_accepted'] for r in rows))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','worker','audit']);p.add_argument('target');a=p.parse_args()
    if a.action=='freeze':freeze(a.target)
    elif a.action=='worker':worker(Path(a.target).resolve())
    else:audits(Path(a.target).resolve())
