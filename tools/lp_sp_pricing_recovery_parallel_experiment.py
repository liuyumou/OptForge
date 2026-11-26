"""Fresh holdouts for the unchanged solver with faster common primal checking."""
import argparse
import datetime as dt
from pathlib import Path
from unittest.mock import patch
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put,accounting
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_baselines import images
from lp_sp_pricing_recovery_budget import allocation,CPU,GPU
from lp_sp_pricing_primal_parallel_admit import validate
import lp_sp_pricing_recovery_experiment_v2 as previous

STUDY=BASE/'recovery-parallel-evaluation-v1';ENVELOPE=BASE/'recovery-parallel-envelope-v1.json';SEEDS=[126401,126423,126449]

def sources():
    return [binding(__file__),binding(ROOT/'tools/lp_sp_pricing_recovery_parallel_driver.py')]

def envelope():
    validate();previous.frozen();a=allocation()
    if read(BASE/'recovery-driver-v2/completed.json')['status']!='all_57_slots_disposed':raise RuntimeError('preceding cohort unfinished')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if cpu['confirmation']+10200*NS>CPU['confirmation']*NS or gpu['confirmation']+750*NS>GPU['confirmation']*NS:raise RuntimeError('complete final cohort reserve does not fit')
    if (dt.datetime.fromisoformat(a['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<3100:raise RuntimeError('final cohort/report envelope')
    profile=read(BASE/'primal-parallel-cpu-v1/result.json')
    for family in ('dense-wide-1m','dense-wide-4m','sparse-wide-1m'):
        rows={r['lane']:r for r in profile['rows'] if r['family']==family}
        if rows['parallel']['cold_process_ns']>=.9*rows['serial']['cold_process_ns']:raise RuntimeError('parallel checker performance admission')
    put(ENVELOPE,dict(status='complete_reserve_fits_before_launch',source=binding(__file__),sources=sources(),cpu_phase_ns=cpu,gpu_phase_ns=gpu,
        full_reserves=dict(cpu_seconds=10200,gpu_seconds=750),profile=binding(BASE/'primal-parallel-cpu-v1/result.json'),
        preceding=binding(previous.STUDY/'freeze.json'),settlements=[binding(p) for p in sorted((BASE/'resources').glob('*.settlement.json'))],
        rule='Same numerical solver, postprocessor, controls, 60-second native limits and exact acceptance. Only common CPU proof scheduling changes. Three new seeds per focus family; retain preceding results without replacement.'))

def freeze():
    gate=validate();f=previous.frozen();a=allocation();e=read(ENVELOPE)
    if e['sources']!=sources():raise RuntimeError('final cohort source changed')
    for key in ('source','profile','preceding'):verify(e[key])
    for receipt in e['settlements']:verify(receipt)
    STUDY.mkdir(exist_ok=False);models=[]
    for spec in previous.SPECS:
        for seed in SEEDS:models.append(previous.generate(spec,seed,STUDY/'models'/f"{spec['name']}-{seed}"))
    put(STUDY/'freeze.json',dict(status='frozen',sources=sources(),admission=gate,envelope=binding(ENVELOPE),backend=f['backend'],models=models,
        images=images(),wall_deadline_utc=a['wall_deadline_utc'],native_seconds=60,process_seconds=90,reconstruction_seconds=90,proof_seconds=120,
        lanes=['candidate','copt-gpu-default','copt-auto'],preceding=binding(previous.STUDY/'freeze.json'),
        scope='45 fresh solver slots. Same complete cost definition, acceptance and native settings as the 57-slot primary cohort; independent parallel primal proof for every applicable lane.'))

def frozen():
    validate();previous.frozen();f=read(STUDY/'freeze.json')
    if f['sources']!=sources() or f['images']!=images():raise RuntimeError('final cohort changed')
    for key in ('admission','envelope','preceding'):verify(f[key])
    for model in f['models']:verify(model['model']);verify(model['construction_audit'])
    return f

def cell(model,lane,out,backend):
    execute=previous.execute
    def command(cmd,*args,**kwargs):
        effective=list(cmd)
        if len(effective)>2 and effective[2]==str(ROOT/'tools/lp_sp_pricing_primal_proof.py'):
            effective[2]=str(ROOT/'tools/lp_sp_pricing_primal_parallel_proof.py')
            put(out/'postprocess/checker-command.json',dict(command=effective,source=binding(effective[2]),policy='independent parallel exact primal proof'))
        return execute(effective,*args,**kwargs)
    with patch.object(previous,'execute',command):row=previous.cell(model,lane,out,backend)
    path=out/'postprocess/checker-command.json'
    if path.exists():row['checker_command']=binding(path)
    return row

def group(index,kind):
    f=frozen();rows=[]
    for i,model in enumerate(f['models'][3*index:3*index+3]):
        lanes=['copt-auto'] if kind=='cpu' else (['candidate','copt-gpu-default'] if (i+index)%2==0 else ['copt-gpu-default','candidate'])
        for lane in lanes:
            if (dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<500:raise TimeoutError('report envelope')
            rows.append(cell(model,lane,STUDY/'runs'/f"{model['name']}-{model['seed']}-{lane}",f['backend'].get(model['name'],'auto')))
    put(STUDY/f'{kind}-group-{index}.json',dict(status='all_slots_disposed',rows=rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['envelope','freeze','group']);p.add_argument('--index',type=int);p.add_argument('--kind',choices=['gpu','cpu']);a=p.parse_args()
    if a.action=='envelope':envelope()
    elif a.action=='freeze':freeze()
    else:group(a.index,a.kind)
