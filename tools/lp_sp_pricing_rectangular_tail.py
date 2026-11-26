"""Finish two untouched groups after detecting an admission/CPU-group name collision."""
import argparse
import subprocess
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_finish import identities,still_same_process
import lp_sp_pricing_rectangular_study_v2 as study
OUT=BASE/'rectangular-driver-tail-v1'

def prepare():
    f=study.frozen();receipt=BASE/'resources/rectangular-gpu-v2.settlement.json'
    if read(receipt)['status']!='passed':raise RuntimeError('completed GPU supervision')
    admit=read(BASE/'resources/rectangular-cpu-v2.reservation.json')
    if admit['phase']!='admission':raise RuntimeError('unexpected CPU identity owner')
    rows=read(study.OUT/'gpu-group.json');bindings(rows)
    if len(rows['rows'])!=9 or rows['status']!='all_slots_disposed':raise RuntimeError('GPU roster')
    for kind in ('cpu','control'):
        if (study.OUT/f'{kind}-group.json').exists():raise RuntimeError('remaining group already disposed')
    for model in f['models']:
        if (study.OUT/'runs'/f'{model["name"]}-{model["seed"]}-copt-auto').exists():raise RuntimeError('CPU cell already attempted')
    for model in f['controls']:
        for lane in ('candidate-before','candidate'):
            if (study.OUT/'runs'/f'{model["name"]}-{model["seed"]}-{lane}').exists():raise RuntimeError('control cell already attempted')
    owned=set()
    for identity in ('rectangular-cpu-v2','rectangular-gpu-v2'):
        for suffix in ('.resource.json','.journal.json'):owned.update(identities(read(BASE/'resources'/(identity+suffix))))
    if any(still_same_process(*v) for v in owned):raise RuntimeError('preceding owned identity remains')
    OUT.mkdir(exist_ok=False);put(OUT/'plan.json',dict(source=binding(__file__),freeze=binding(study.OUT/'freeze.json'),completed_gpu=binding(receipt),
        original_driver_plan=binding(study.DRIVER/'plan.json'),admission_identity=binding(BASE/'resources/rectangular-cpu-v2.reservation.json'),
        trigger='Driver refused to reuse rectangular-cpu-v2, already the completed CPU admission identity. No scientific CPU/control cell or reservation began.',
        groups=[dict(kind='cpu',identity='rectangular-holdout-cpu-v1',seconds=180),dict(kind='control',identity='rectangular-holdout-control-v1',seconds=120)],
        owned_identities=len(owned),live_owned_identities=[],numerical_source_changes=False,completed_cells_repeated=False))

def checked():
    study.frozen();p=read(OUT/'plan.json');bindings(p)
    if p['source']!=binding(__file__) or read(BASE/'resources/rectangular-tail-plan-v1.settlement.json')['status']!='passed':raise RuntimeError('tail plan supervision')
    return p

def run():
    p=checked()
    for g in p['groups']:
        identity=g['identity']
        if (BASE/'resources'/f'{identity}.reservation.json').exists():raise RuntimeError('attempted remaining identity')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_rectangular_budget.py'),'--id',identity,'--phase','confirmation','--seconds',str(g['seconds']),'--host-gib','32']
        if g['kind']=='control':cmd+=['--gpu']
        cmd+=['--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_exit.py'),'--receipt',str(OUT/(identity+'.exit.json')),'--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_rectangular_study_v2.py'),'group','--kind',g['kind']]
        put(OUT/(identity+'.started.json'),dict(command=cmd));code=subprocess.call(cmd,cwd=ROOT);receipt=BASE/'resources'/f'{identity}.settlement.json';put(OUT/(identity+'.completed.json'),dict(returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        if code:put(OUT/'stopped.json',dict(identity=identity,returncode=code));return 1
    put(OUT/'completed.json',dict(status='all_16_slots_disposed_original_driver_collision_retained'));return 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);a=p.parse_args()
    if a.action=='prepare':prepare()
    else:raise SystemExit(run())
