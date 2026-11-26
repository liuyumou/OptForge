"""Prospective bounded rectangular refinement, independent holdouts and controls."""
import argparse
import datetime as dt
import subprocess
from unittest.mock import patch
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put,accounting
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_recovery_budget import CPU,GPU,allocation
import lp_sp_pricing_recovery_parallel_experiment as common
import lp_sp_pricing_recovery_tail as tail

OUT=BASE/'rectangular-refinement-v1';DEV=BASE/'rectangular-development-v1';ADMIT=BASE/'rectangular-cpu-v1';DRIVER=BASE/'rectangular-driver-v1';ENVELOPE=BASE/'rectangular-envelope-v1.json'

def sources():return [binding(ROOT/'tools/lp_sp_pricing_rectangular_run.py'),binding(__file__),binding(ROOT/'tests/integration/test_lp_sp_pricing_rectangular.py')]

def envelope():
    tail.frozen()
    if read(tail.DRIVER/'completed.json')['status']!='all_45_original_and_9_supplement_slots_disposed_failure_retained':raise RuntimeError('preceding study unfinished')
    cpu,gpu=accounting(BASE),accounting(BASE,True)
    required_cpu=dict(admission=480,development=600,confirmation=2280,reporting=2400);required_gpu=dict(admission=0,development=150,confirmation=270,reporting=0)
    if any(cpu[k]+v*NS>CPU[k]*NS for k,v in required_cpu.items()) or any(gpu[k]+v*NS>GPU[k]*NS for k,v in required_gpu.items()):raise RuntimeError('refinement full envelope does not fit')
    if (dt.datetime.fromisoformat(allocation()['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<1800:raise RuntimeError('refinement/report wall envelope')
    put(ENVELOPE,dict(status='complete_reserves_fit',sources=sources(),cpu_phase_ns=cpu,gpu_phase_ns=gpu,required_cpu=required_cpu,required_gpu=required_gpu,
        settlements=[binding(p) for p in sorted((BASE/'resources').glob('*.settlement.json'))],
        rule='One development input: old path and direct GPU projection at rho16/64/256/1024. Select fastest exact timely complete result only if at least 10% faster than old. Three new rectangular holdouts with old/new candidate and both COPT lanes; two old/new square/irregular controls. All preceding cohorts/failures remain exact. No new CUDA kernel or proof rule.'))

def admit():
    common.frozen();e=read(ENVELOPE)
    if e['sources']!=sources():raise RuntimeError('source changed')
    for r in e['settlements']:verify(r)
    ADMIT.mkdir(exist_ok=False)
    subprocess.run([str(PYTHON),'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing_rectangular.py','-v'],cwd=ROOT,check=True)
    put(ADMIT/'result.json',dict(status='passed',sources=sources(),previous=binding(common.STUDY/'freeze.json'),tests=3,envelope=binding(ENVELOPE),gpu_kernel_changed=False,acceptance_changed=False))

def validate():
    common.frozen();d=read(ADMIT/'result.json');bindings(d)
    if d['sources']!=sources() or read(BASE/'resources/rectangular-cpu-v1.settlement.json')['status']!='passed':raise RuntimeError('rectangular CPU admission')
    return binding(ADMIT/'result.json')

def cell(model,lane,out,multiplier=None):
    execute=common.previous.execute
    def command(cmd,*args,**kwargs):
        effective=list(cmd)
        if multiplier is not None and len(effective)>2 and effective[2]==str(ROOT/'tools/lp_sp_pricing_recovery_run_fast.py'):
            effective[2]=str(ROOT/'tools/lp_sp_pricing_rectangular_run.py');effective+=['--rho-multiplier',str(multiplier)]
        return execute(effective,*args,**kwargs)
    with patch.object(common.previous,'execute',command):row=common.cell(model,lane,out,'cpu')
    row['rectangular_multiplier']=multiplier;put(out/'result.json',row);return row

def development():
    validate();DEV.mkdir(exist_ok=False);model=common.previous.generate(common.previous.SPECS[4],127001,DEV/'model');rows=[]
    for lane,multiplier in [('candidate-before',None)]+[(f'candidate-rho-{r}',r) for r in (16,64,256,1024)]:rows.append(cell(model,lane,DEV/'runs'/lane,multiplier))
    put(DEV/'result.json',dict(status='all_slots_disposed',sources=sources(),models=[model],rows=rows))

def freeze():
    gate=validate();d=read(DEV/'result.json')
    if d['sources']!=sources() or read(BASE/'resources/rectangular-development-v1.settlement.json')['status']!='passed':raise RuntimeError('development supervision')
    eligible=[r for r in d['rows'] if r['accepted'] and r['timely']];old=next(r for r in eligible if r['lane']=='candidate-before');best=min((r for r in eligible if r['rectangular_multiplier']),key=lambda r:r['complete_ns'])
    if best['complete_ns']>=.9*old['complete_ns']:raise RuntimeError('no admitted complete improvement')
    OUT.mkdir(exist_ok=False);models=[common.previous.generate(common.previous.SPECS[4],seed,OUT/'models'/f'rectangular-{seed}') for seed in (127101,127123,127149)]
    controls=[common.previous.generate(spec,127201+2*i,OUT/'models'/f'control-{i}') for i,spec in enumerate(common.previous.CONTROLS)]
    put(OUT/'freeze.json',dict(status='frozen',sources=sources(),admission=gate,development=binding(DEV/'result.json'),models=models,controls=controls,
        selected_multiplier=best['rectangular_multiplier'],selection='fastest timely exact complete development result, at least 10% faster than before',wall_deadline_utc=allocation()['wall_deadline_utc']))

def frozen():
    validate();f=read(OUT/'freeze.json')
    if f['sources']!=sources():raise RuntimeError('frozen rectangular source changed')
    for k in ('admission','development'):verify(f[k])
    for m in f['models']+f['controls']:verify(m['model']);verify(m['construction_audit'])
    return f

def group(kind):
    f=frozen();rows=[]
    for i,model in enumerate(f['controls'] if kind=='control' else f['models']):
        lanes=['copt-auto'] if kind=='cpu' else (['candidate-before','candidate'] if kind=='control' else ['candidate-before','candidate','copt-gpu-default'])
        lanes=lanes[i%len(lanes):]+lanes[:i%len(lanes)]
        for lane in lanes:
            if (dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<500:raise TimeoutError('report envelope')
            rows.append(cell(model,lane,OUT/'runs'/f'{model["name"]}-{model["seed"]}-{lane}',f['selected_multiplier'] if lane=='candidate' else None))
    put(OUT/f'{kind}-group.json',dict(status='all_slots_disposed',rows=rows))

def run():
    frozen();DRIVER.mkdir(exist_ok=False);groups=[('gpu',150),('cpu',180),('control',120)]
    put(DRIVER/'plan.json',dict(source=binding(__file__),freeze=binding(OUT/'freeze.json'),groups=groups))
    for kind,seconds in groups:
        identity=f'rectangular-{kind}-v1'
        if (BASE/'resources'/f'{identity}.reservation.json').exists():raise RuntimeError('attempted identity')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_budget.py'),'--id',identity,'--phase','confirmation','--seconds',str(seconds),'--host-gib','32']
        if kind!='cpu':cmd+=['--gpu']
        cmd+=['--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_exit.py'),'--receipt',str(DRIVER/(identity+'.exit.json')),'--',str(PYTHON),'-B',__file__,'group','--kind',kind]
        put(DRIVER/(identity+'.started.json'),dict(command=cmd));code=subprocess.call(cmd,cwd=ROOT);receipt=BASE/'resources'/f'{identity}.settlement.json';put(DRIVER/(identity+'.completed.json'),dict(returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        if code:put(DRIVER/'stopped.json',dict(identity=identity,returncode=code));return 1
    put(DRIVER/'completed.json',dict(status='all_16_slots_disposed'));return 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['envelope','admit','development','freeze','group','run']);p.add_argument('--kind',choices=['gpu','cpu','control']);a=p.parse_args()
    if a.action=='group':group(a.kind)
    elif a.action=='run':raise SystemExit(run())
    else:globals()[a.action]()
