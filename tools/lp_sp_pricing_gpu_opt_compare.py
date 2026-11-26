"""Fresh cold-process comparison; all lanes share models, deadlines and audits."""
import argparse
import json
from pathlib import Path
import sys
import time
from lp_sp_pricing_budget import ROOT,BASE,binding,put,run,CPU,GPU,NS,accounting
from lp_sp_pricing_baselines import PYTHON,portable,audit,images
from lp_sp_pricing_gpu_opt_measure import admission
from lp_sp_pricing_gpu_opt_quality import LIBRARY,OLD,validate
from lp_sp_pricing_study import generated,FAMILIES
from lp_billion_owned_process import execute as owned_execute

LANES=['cpu','legacy_gpu','lean_gpu']


def read(path):return json.loads(Path(path).read_text())


def verify(item):
    if binding(item['path'])!=item:raise RuntimeError('comparison binding changed: '+item['path'])


def confirmation_usage(gpu=False):
    """Read the future phase while this CPU-only admission reservation is active."""
    total=0
    for path in (BASE/'resources').glob('*.reservation.json'):
        if read(path)['phase']!='confirmation':continue
        settled=path.with_name(path.name.replace('.reservation.','.settlement.'))
        if not settled.exists():raise RuntimeError('confirmation reservation still active')
        receipt=read(settled)
        if receipt['overrun'] or not receipt['cleanup_empty']:
            raise RuntimeError('unresolved confirmation supervision')
        total+=receipt['gpu_ns' if gpu else 'cpu_ns']
    return total


def launch(lane,model,out,configuration,seconds=10,outer=20):
    if not out.parent.is_dir():raise RuntimeError('output parent missing before scientific launch')
    out.mkdir(exist_ok=False)
    if lane in ('lean_gpu','cpu'):
        command=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_gpu_lean_run.py'),str(model),str(out/'response.json'),
            '--library',str(LIBRARY),'--seconds',str(seconds),'--width',str(configuration['width']),
            '--steps',str(configuration['steps'])]
        if not configuration['sparse']:command.append('--dense')
        if lane=='cpu':command.append('--cpu')
    else:
        command=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_run.py'),str(model),str(out/'response.json'),
            '--seconds',str(seconds),'--operations','200000000','--market','flow']
        if lane=='legacy_gpu':command+=['--gpu-library',str(OLD),'--precision','fp32x2','--sparse','--batch','32']
    put(out/'started.json',dict(lane=lane,model=binding(model),command=command,seconds=seconds,outer_seconds=outer))
    result=owned_execute(command,out/'stdout.jsonl',out/'stderr',outer,None)
    put(out/'process.json',result)
    return result


def freeze(identity,configuration):
    admitted=admission()
    selection=[]
    for name,steps in [('gpu-opt-ladder-v3',1000),('gpu-opt-ladder-v4',256)]:
        path=BASE/name/'result.json';rows=read(path)['rows']
        timely=sum(r['accepted'] and read(r['result']['path'])['solve_ns']<=10*NS for r in rows)
        selection.append(dict(steps=steps,timely_certificates=timely,
            capped_ns=sum(min(r['elapsed_ns'],10*NS) for r in rows),evidence=binding(path)))
    selected=min(selection,key=lambda r:(-r['timely_certificates'],r['capped_ns']))
    if configuration['steps']!=selected['steps'] or configuration['width']!=64 or not configuration['sparse']:
        raise RuntimeError('configuration does not match development selection')
    out=BASE/identity;out.mkdir(exist_ok=False);(out/'cells').mkdir()
    roster=[dict(id=f'{family}-8-88371',family=family,columns=8,
        rows=4 if family=='wide' else 32 if family=='tall' else 16,seed=88371) for family in FAMILIES]
    roster.append(dict(id='wide-16-88371',family='wide',columns=16,rows=8,seed=88371))
    models=[];cells=[]
    for index,cell in enumerate(roster):
        directory=out/'models'/cell['id'];directory.mkdir(parents=True)
        begin=time.perf_counter_ns();model,construction=generated(cell)
        put(directory/'rational.json',model);put(directory/'construction.json',construction)
        portable(model,directory/'portable.json')
        models.append(dict(**cell,rational=binding(directory/'rational.json'),portable=binding(directory/'portable.json'),
            encoding_ns=time.perf_counter_ns()-begin))
        for repetition in range(2):
            shift=(index+repetition)%3
            for lane in LANES[shift:]+LANES[:shift]:
                cells.append(dict(id=f"{cell['id']}-r{repetition}-{lane}",model_index=index,lane=lane,repetition=repetition))
    if confirmation_usage()+4*(1100+120)*NS>CPU['confirmation']*NS:
        raise RuntimeError('whole comparison CPU reservation does not fit')
    if confirmation_usage(True)+1100*NS>GPU['confirmation']*NS:
        raise RuntimeError('whole comparison GPU reservation does not fit')
    sources=list((ROOT/'research/lp-sp-pricing/python').rglob('*.py'))
    sources+=list((ROOT/'research/lp-sp-pricing/native').glob('*.*'))
    sources+=[ROOT/'tools'/n for n in ['lp_sp_pricing_run.py','lp_sp_pricing_gpu_lean_run.py',
        'lp_sp_pricing_gpu_opt_compare.py','lp_sp_pricing_budget.py','lp_sp_pricing_cleanup.py',
        'lp_sp_pricing_baselines.py','lp_sp_pricing_verify.py']]
    sources+=[LIBRARY,OLD,ROOT/'research/lp-sp-pricing/target/cpu/libsp_proof.so',
        ROOT/'research/lp-sp-pricing/target/cpu/libsp_auxiliary.so',ROOT/'research/lp-sp-pricing/target/cpu/libsp_market.so']
    put(out/'freeze.json',dict(status='frozen',models=models,cells=cells,configuration=configuration,
        admission=admitted,sources=[binding(p) for p in sorted(set(sources))],images=images(),
        native_seconds=10,process_seconds=20,repetitions=2,
        order='cyclic lane rotations, fresh process per cell; no cache flushing',
        timing='model encoding + cold process including final exact check and output + independent exact and unchanged 1e-9 audit',
        selection='maximize timely development exact certificates, then minimize capped development cost',
        selection_evidence=selection,
        reserved_gpu_seconds=1100,reserved_cpu_seconds=4880,
        comparison='ratios only for jointly timely accepted certificates; exact and historical-strict tiers separate'))
    print(json.dumps(dict(status='frozen',models=len(models),cells=len(cells))),flush=True)


def validate_freeze(path):
    f=read(path);verify(f['admission']);validate(Path(f['admission']['path']))
    for item in f['sources']:verify(item)
    if images()!=f['images']:raise RuntimeError('strict checker image changed')
    for model in f['models']:verify(model['rational']);verify(model['portable'])
    return f


def worker(path):
    f=validate_freeze(path);out=path.parent
    if not (out/'cells').is_dir():raise RuntimeError('missing output parent')
    for cell in f['cells']:
        directory=out/'cells'/cell['id']
        if directory.exists():raise RuntimeError('scientific identity already attempted')
        model=f['models'][cell['model_index']]
        result=launch(cell['lane'],Path(model['rational']['path']),directory,f['configuration'],f['native_seconds'],f['process_seconds'])
        print(json.dumps(dict(cell=cell['id'],process=result)),flush=True)
    put(out/'solves-completed.json',dict(status='all_frozen_attempts_returned'))


def audits(path):
    f=validate_freeze(path);out=path.parent;rows=[]
    if not (out/'solves-completed.json').exists():raise RuntimeError('solve roster unfinished')
    for cell in f['cells']:
        model=f['models'][cell['model_index']];directory=out/'cells'/cell['id']
        process=read(directory/'process.json');response=read(directory/'response.json') if (directory/'response.json').exists() else {}
        proof=audit('practical',Path(model['portable']['path']),Path(model['rational']['path']),directory)
        timely=(process['returncode']==0 and not process['timed_out'] and process['elapsed_ns']<=f['process_seconds']*NS
                and response.get('solve_ns',float('inf'))<=f['native_seconds']*NS)
        rows.append(dict(cell=cell['id'],lane=cell['lane'],model=model['id'],family=model['family'],repetition=cell['repetition'],
            status=response.get('status','missing_response'),reason=response.get('reason'),timely=timely,
            exact_accepted=bool(proof.get('exact') and proof['exact']['accepted']),strict_accepted=proof['accepted'],
            native_ns=response.get('solve_ns'),process_ns=process['elapsed_ns'],audit_ns=proof['elapsed_ns'],
            encoding_ns=model['encoding_ns'],complete_ns=model['encoding_ns']+process['elapsed_ns']+proof['elapsed_ns'],
            response=binding(directory/'response.json') if response else None,audit=binding(directory/'audit.json')))
    put(out/'result.json',dict(status='all_frozen_cells_independently_audited',rows=rows,freeze=binding(path)))
    print(json.dumps(dict(status='passed',cells=len(rows),strict=sum(r['strict_accepted'] for r in rows))),flush=True)


def smoke(identity,configuration):
    admission();out=BASE/identity;out.mkdir(exist_ok=False);(out/'cells').mkdir()
    model=dict(A=[[1,1],[-1,0],[0,-1]],b=[2,0,0],c=[1,1])
    put(out/'rational.json',model);portable(model,out/'portable.json');rows=[]
    for lane in LANES:
        directory=out/'cells'/lane
        process=launch(lane,out/'rational.json',directory,configuration,10,20)
        proof=audit('practical',out/'portable.json',out/'rational.json',directory)
        if process['returncode'] or process['timed_out'] or not proof['accepted']:
            raise RuntimeError('cold comparison smoke failed: '+lane)
        rows.append(dict(lane=lane,process=process,audit=binding(directory/'audit.json')))
    put(out/'result.json',dict(status='passed',rows=rows))
    print(json.dumps(dict(status='passed',lanes=3)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','worker','audit','smoke']);p.add_argument('target')
    p.add_argument('--width',type=int,default=64);p.add_argument('--steps',type=int,default=1000);p.add_argument('--dense',action='store_true')
    a=p.parse_args();configuration=dict(width=a.width,steps=a.steps,sparse=not a.dense,backend='lean',precision='fp64',compact_trace=True)
    if a.action=='freeze':freeze(a.target,configuration)
    elif a.action=='smoke':smoke(a.target,configuration)
    elif a.action=='worker':worker(Path(a.target).resolve())
    else:audits(Path(a.target).resolve())
