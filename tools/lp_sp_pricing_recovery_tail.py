"""Retain the failed final group; finish untouched cells and add new square seeds."""
import argparse
import datetime as dt
import subprocess
import unittest
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put,accounting
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_finish import identities,still_same_process
from lp_sp_pricing_recovery_budget import allocation,CPU,GPU
import lp_sp_pricing_recovery_parallel_experiment as prior

SEAL=BASE/'recovery-parallel-seal-v1';STUDY=BASE/'recovery-mixed-supplement-v1';DRIVER=BASE/'recovery-parallel-tail-v1';ENVELOPE=BASE/'recovery-tail-envelope-v1.json'
SEEDS=[126901,126923,126949]

def sources():return [binding(__file__),binding(ROOT/'tools/lp_sp_pricing_recovery_exit.py'),binding(ROOT/'tests/integration/test_lp_sp_pricing_recovery_exit.py')]

def seal():
    prior.frozen();prefix=BASE/'resources/recovery-parallel-gpu-3-v1';r=read(str(prefix)+'.settlement.json');resource=read(str(prefix)+'.resource.json')
    if r['status']!='refused' or not r['cleanup_empty'] or r['overrun'] or r['cpu_ns']!=600*NS or r['gpu_ns']!=150*NS or resource['result']['reason']!='coordinator_lost':raise RuntimeError('unexpected failure disposition')
    verify(r['resource']);reservation=read(str(prefix)+'.reservation.json')
    for source in reservation['sources']:
        retained=binding(source['retained'])
        if retained['bytes']!=source['bytes'] or retained['sha256']!=source['sha256']:raise RuntimeError('retained source mismatch')
    owned=set(identities(resource))|set(identities(read(str(prefix)+'.journal.json')))
    if any(still_same_process(*item) for item in owned):raise RuntimeError('owned identity remains')
    group=read(prior.STUDY/'gpu-group-3.json');count=bindings(group)
    expected={f'mixed-square-1m-{seed}-{lane}' for seed in prior.SEEDS for lane in ('candidate','copt-gpu-default')}
    if group['status']!='all_slots_disposed' or len(group['rows'])!=6 or {row['id'] for row in group['rows']}!=expected:raise RuntimeError('failed group roster')
    for kind in ('gpu','cpu'):
        if (BASE/'resources'/f'recovery-parallel-{kind}-4-v1.reservation.json').exists() or (prior.STUDY/f'{kind}-group-4.json').exists():raise RuntimeError('tail already attempted')
    SEAL.mkdir(exist_ok=False);suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing_recovery_exit.py');tests=unittest.TextTestRunner(verbosity=2).run(suite)
    if not tests.wasSuccessful() or tests.testsRun!=3 or tests.skipped:raise RuntimeError('exit tests')
    subprocess.run([str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_exit.py'),'--receipt',str(SEAL/'exit-smoke.json'),'--',str(PYTHON),'-c','pass'],cwd=ROOT,check=True)
    put(SEAL/'result.json',dict(status='failure_sealed_cycle_exit_admitted',sources=sources(),original_failure=binding(str(prefix)+'.settlement.json'),
        group=binding(prior.STUDY/'gpu-group-3.json'),checked_bindings=count,owned_identities=len(owned),live_owned_identities=[],timing_excluded_ids=sorted(expected),
        numerical_recomputation=False,supervision_regraded=False,full_cpu_seconds=600,full_gpu_seconds=150,preceding_trigger='unknown',tests=3,smoke=binding(SEAL/'exit-smoke.json'),
        mitigation='Observe one actual complete owned inventory cycle before command exit, bounded by fifteen seconds inside the unchanged reservation. No signals or sampling changes. Inventory race remains a hypothesis, not an established failure cause.'))

def checked():
    prior.frozen();s=read(SEAL/'result.json');bindings(s)
    if s['sources']!=sources() or read(BASE/'resources/recovery-parallel-seal-v1.settlement.json')['status']!='passed':raise RuntimeError('seal admission')
    return s

def envelope():
    checked();a=allocation();cpu,gpu=accounting(BASE),accounting(BASE,True)
    if cpu['confirmation']+4080*NS>CPU['confirmation']*NS or gpu['confirmation']+300*NS>GPU['confirmation']*NS:raise RuntimeError('tail full reserves do not fit')
    if (dt.datetime.fromisoformat(a['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<1600:raise RuntimeError('tail/report wall envelope')
    put(ENVELOPE,dict(status='full_reserves_fit',sources=sources(),cpu_phase_ns=cpu,gpu_phase_ns=gpu,full_reserves=dict(cpu_seconds=4080,gpu_seconds=300),
        seal=binding(SEAL/'result.json'),settlements=[binding(p) for p in sorted((BASE/'resources').glob('*.settlement.json'))],
        rule='Only two untouched original groups plus nine separately frozen mixed-square slots with new seeds. Preserve failed group and all six timing exclusions.'))

def freeze():
    checked();e=read(ENVELOPE)
    if e['sources']!=sources():raise RuntimeError('tail source changed')
    verify(e['seal'])
    for r in e['settlements']:verify(r)
    STUDY.mkdir(exist_ok=False);spec=prior.previous.SPECS[3]
    models=[prior.previous.generate(spec,seed,STUDY/'models'/f'{spec["name"]}-{seed}') for seed in SEEDS]
    put(STUDY/'freeze.json',dict(status='frozen',sources=sources(),envelope=binding(ENVELOPE),preceding=binding(prior.STUDY/'freeze.json'),models=models,
        backend='auto',wall_deadline_utc=allocation()['wall_deadline_utc'],native_seconds=60,process_seconds=90,reconstruction_seconds=90,proof_seconds=120,
        rule='Same generator, numerical sources, native settings, rotated order and common parallel proof. New seeds do not replace or regrade failed supervision.'))

def frozen():
    checked();f=read(STUDY/'freeze.json')
    if f['sources']!=sources():raise RuntimeError('supplement sources changed')
    for key in ('envelope','preceding'):verify(f[key])
    for m in f['models']:verify(m['model']);verify(m['construction_audit'])
    return f

def group(kind):
    f=frozen();rows=[]
    for i,model in enumerate(f['models']):
        lanes=['copt-auto'] if kind=='cpu' else (['candidate','copt-gpu-default'] if i%2==0 else ['copt-gpu-default','candidate'])
        for lane in lanes:
            if (dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<500:raise TimeoutError('report envelope')
            rows.append(prior.cell(model,lane,STUDY/'runs'/f'{model["name"]}-{model["seed"]}-{lane}','auto'))
    put(STUDY/f'{kind}-group.json',dict(status='all_slots_disposed',rows=rows))

def run():
    frozen();DRIVER.mkdir(exist_ok=False)
    groups=[dict(id=f'recovery-parallel-{k}-4-v1',kind=k,seconds=150 if k=='gpu' else 360,cmd=[str(ROOT/'tools/lp_sp_pricing_recovery_parallel_experiment.py'),'group','--index','4','--kind',k]) for k in ('gpu','cpu')]
    groups += [dict(id=f'recovery-mixed-supplement-{k}-v1',kind=k,seconds=150 if k=='gpu' else 360,cmd=[__file__,'group','--kind',k]) for k in ('gpu','cpu')]
    put(DRIVER/'plan.json',dict(sources=sources(),seal=binding(SEAL/'result.json'),freeze=binding(STUDY/'freeze.json'),stopped=binding(BASE/'recovery-parallel-driver-v1/stopped.json'),groups=groups))
    for g in groups:
        identity=g['id']
        if (BASE/'resources'/f'{identity}.reservation.json').exists():raise RuntimeError('attempted identity')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_budget.py'),'--id',identity,'--phase','confirmation','--seconds',str(g['seconds']),'--host-gib','32']
        if g['kind']=='gpu':cmd.append('--gpu')
        cmd+=['--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_exit.py'),'--receipt',str(DRIVER/(identity+'.exit.json')),'--',str(PYTHON),'-B']+g['cmd']
        put(DRIVER/(identity+'.started.json'),dict(command=cmd));code=subprocess.call(cmd,cwd=ROOT);receipt=BASE/'resources'/f'{identity}.settlement.json'
        put(DRIVER/(identity+'.completed.json'),dict(returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        if code:put(DRIVER/'stopped.json',dict(identity=identity,returncode=code));return 1
    put(DRIVER/'completed.json',dict(status='all_45_original_and_9_supplement_slots_disposed_failure_retained'));return 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['seal','envelope','freeze','group','run']);p.add_argument('--kind',choices=['gpu','cpu']);a=p.parse_args()
    if a.action=='group':group(a.kind)
    elif a.action=='run':raise SystemExit(run())
    else:globals()[a.action]()
