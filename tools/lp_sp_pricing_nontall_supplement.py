"""Fresh inputs for families whose original timings lost supervision eligibility."""
import argparse
import datetime as dt
import subprocess
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put,accounting
from lp_sp_pricing_baselines import PYTHON,images
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_nontall_experiment import SPECS,generate,cell,validate as primary,STUDY as PRIMARY
from lp_sp_pricing_nontall_tail import checked as admission
from lp_sp_pricing_nontall_budget import CPU,GPU,allocation

STUDY=BASE/'nontall-supplement-v1';DRIVER=BASE/'nontall-supplement-driver-v1';SEEDS=[125701,125723,125749]
ENVELOPE=BASE/'nontall-supplement-envelope-v1.json'


def envelope():
    primary();admission();alloc=allocation()
    if read(BASE/'nontall-driver-v3/completed.json')['status']!='all_72_slots_disposed_with_failures_retained':raise RuntimeError('primary unfinished')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    if gpu['confirmation']+1200*NS>GPU['confirmation']*NS or cpu['confirmation']+7680*NS>CPU['confirmation']*NS:raise RuntimeError('complete supplement reserve does not fit')
    if (dt.datetime.fromisoformat(alloc['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<2400:raise RuntimeError('supplement and report envelope')
    put(ENVELOPE,dict(status='complete_reserve_fits_before_launch',source=binding(__file__),cpu_phase_ns=cpu,gpu_phase_ns=gpu,
        settlements=[binding(p) for p in sorted((BASE/'resources').glob('*.settlement.json'))],
        full_reserves=dict(cpu_seconds=7680,gpu_seconds=1200),
        retained_prelaunch_failure=binding(BASE/'resources/nontall-supplement-freeze-v1.settlement.json')))


def freeze():
    primary();admission();alloc=allocation();budget=read(ENVELOPE);verify(budget['source'])
    for receipt in budget['settlements']:verify(receipt)
    if (dt.datetime.fromisoformat(alloc['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<2400:raise RuntimeError('supplement and report envelope')
    STUDY.mkdir(exist_ok=False);models=[]
    for spec in (SPECS[1],SPECS[2]):
        for seed in SEEDS:models.append(generate(spec,seed,STUDY/'models'/f"{spec['name']}-{seed}"))
    put(STUDY/'freeze.json',dict(status='frozen',source=binding(__file__),primary=binding(PRIMARY/'freeze.json'),models=models,images=images(),
        native_seconds=60,process_seconds=90,lanes=['candidate','copt-gpu-default','copt-auto'],wall_deadline_utc=alloc['wall_deadline_utc'],
        disclosure='Separate prospective follow-up after two completed groups lost timing eligibility. Three entirely new seeds per affected family; same candidate, controls, certificate policy and limits. Earlier failed charges/outcomes/exclusions remain. No model or solve is repeated; these data do not replace or regrade the original group.',
        full_reserves=dict(cpu_seconds=7680,gpu_seconds=1200),envelope=binding(ENVELOPE)))


def validate():
    primary();admission();f=read(STUDY/'freeze.json');verify(f['source']);verify(f['primary']);verify(f['envelope'])
    for model in f['models']:verify(model['model']);verify(model['construction_audit'])
    if f['images']!=images():raise RuntimeError('images changed')
    return f


def group(index,kind):
    f=validate();rows=[]
    for i,model in enumerate(f['models'][3*index:3*index+3]):
        lanes=['copt-auto'] if kind=='cpu' else (['candidate','copt-gpu-default'] if (i+index)%2==0 else ['copt-gpu-default','candidate'])
        for lane in lanes:
            if (dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<500:raise TimeoutError('reporting envelope')
            rows.append(cell(model,lane,STUDY/'runs'/f"{model['name']}-{model['seed']}-{lane}"))
    put(STUDY/f'{kind}-group-{index}.json',dict(status='all_slots_disposed',rows=rows))


def run():
    validate();DRIVER.mkdir(exist_ok=False);groups=[dict(index=i,kind=k,identity=f'nontall-supplement-{k}-{i}-v1',seconds=600 if k=='gpu' else 360) for i in range(2) for k in (('gpu','cpu') if i==0 else ('cpu','gpu'))]
    put(DRIVER/'plan.json',dict(source=binding(__file__),freeze=binding(STUDY/'freeze.json'),groups=groups,rule='Each fresh scientific identity once; stop on any reservation failure.'))
    for item in groups:
        name=item['identity']
        if (BASE/'resources'/f'{name}.reservation.json').exists():raise RuntimeError('attempted identity')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_budget.py'),'--id',name,'--phase','confirmation','--seconds',str(item['seconds']),'--host-gib','32']
        if item['kind']=='gpu':cmd.append('--gpu')
        cmd+=['--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_exit.py'),'--receipt',str(DRIVER/(name+'.exit.json')),'--',str(PYTHON),'-B',__file__,'group','--index',str(item['index']),'--kind',item['kind']]
        put(DRIVER/(name+'.started.json'),dict(command=cmd));code=subprocess.call(cmd,cwd=ROOT);receipt=BASE/'resources'/f'{name}.settlement.json'
        put(DRIVER/(name+'.completed.json'),dict(returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        if code:put(DRIVER/'stopped.json',dict(identity=name,returncode=code));return 1
    put(DRIVER/'completed.json',dict(status='all_18_fresh_slots_disposed'));return 0


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['envelope','freeze','group','run']);p.add_argument('--index',type=int);p.add_argument('--kind',choices=['gpu','cpu']);a=p.parse_args()
    if a.action=='envelope':envelope()
    elif a.action=='freeze':freeze()
    elif a.action=='group':group(a.index,a.kind)
    else:raise SystemExit(run())
