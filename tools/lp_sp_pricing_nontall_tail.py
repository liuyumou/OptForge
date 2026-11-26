"""Second additive seal, exit coordination admission, untouched roster tail."""
import argparse
import subprocess
import sys
import unittest
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_finish import identities,still_same_process
from lp_sp_pricing_nontall_experiment import validate,STUDY
from lp_sp_pricing_nontall_resume import checked as previous_seal

SEAL=BASE/'nontall-second-seal-v1';OUT=BASE/'nontall-driver-v3'


def sources():return [binding(ROOT/'tools/lp_sp_pricing_nontall_exit.py'),binding(__file__),binding(ROOT/'tests/integration/test_lp_sp_pricing_nontall_exit.py')]


def admit():
    validate();previous_seal();prefix=BASE/'resources/nontall-gpu-2-v1';receipt=read(str(prefix)+'.settlement.json');resource=read(str(prefix)+'.resource.json')
    if receipt['status']!='refused' or not receipt['cleanup_empty'] or receipt['overrun'] or receipt['cpu_ns']!=2400*NS or receipt['gpu_ns']!=600*NS or resource['result']['reason']!='coordinator_lost':raise RuntimeError('unexpected second failure')
    verify(receipt['resource']);reservation=read(str(prefix)+'.reservation.json')
    for item in reservation['sources']:
        retained=binding(item['retained'])
        if retained['bytes']!=item['bytes'] or retained['sha256']!=item['sha256']:raise RuntimeError('retained source mismatch')
    owned=set(identities(resource))|set(identities(read(str(prefix)+'.journal.json')))
    if any(still_same_process(*item) for item in owned):raise RuntimeError('owned identity remains')
    group=read(STUDY/'gpu-group-2.json');checked=bindings(group)
    expected={f'mixed-square-1m-{seed}-{lane}' for seed in (125101,125123,125149) for lane in ('candidate','copt-gpu-default')}
    if group['status']!='all_slots_disposed' or len(group['rows'])!=6 or {r['id'] for r in group['rows']}!=expected:raise RuntimeError('completed roster mismatch')
    SEAL.mkdir(exist_ok=False)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing_nontall_exit.py');result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun!=2 or result.skipped:raise RuntimeError('exit coordination tests')
    cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_exit.py'),'--receipt',str(SEAL/'exit-smoke.json'),'--',str(PYTHON),'-c','import time; time.sleep(6)']
    subprocess.run(cmd,cwd=ROOT,check=True)
    put(SEAL/'result.json',dict(status='sealed_and_exit_coordination_checked',sources=sources(),original_failure=binding(str(prefix)+'.settlement.json'),
        group=binding(STUDY/'gpu-group-2.json'),checked_bindings=checked,owned_identities=len(owned),live_owned_identities=[],timing_excluded_ids=sorted(expected),
        numerical_recomputation=False,supervision_regraded=False,full_cpu_seconds=2400,full_gpu_seconds=600,tests=2,smoke=binding(SEAL/'exit-smoke.json'),
        preceding_trigger='unknown; source inspection identifies inventory-helper cleanup as a plausible race, not an established historical cause',
        mitigation='Untouched commands wait at most 15 seconds for an already active owned inventory helper to finish naturally; no signals, fake heartbeats, sampling changes or exceptions. Entire wait charged inside existing outer allowance.'))


def checked():
    validate();previous_seal();d=read(SEAL/'result.json');bindings(d)
    if d['sources']!=sources() or read(BASE/'resources/nontall-second-seal-v1.settlement.json')['status']!='passed':raise RuntimeError('second seal/coordination admission')
    return d


def run():
    checked();OUT.mkdir(exist_ok=False);groups=[dict(index=2,kind='cpu',identity='nontall-cpu-2-v1',seconds=360)]
    for index in range(3,8):
        for kind in (('gpu','cpu') if index%2==0 else ('cpu','gpu')):groups.append(dict(index=index,kind=kind,identity=f'nontall-{kind}-{index}-v1',seconds=600 if kind=='gpu' else 360))
    put(OUT/'plan.json',dict(source=binding(__file__),seal=binding(SEAL/'result.json'),freeze=binding(STUDY/'freeze.json'),groups=groups,
        stopped_driver=binding(BASE/'nontall-driver-v2/stopped.json'),rule='Only untouched frozen cells. Preserve both failed groups/full charges/timing exclusions. No change to numerical or resource source. Stop on any failure.'))
    for group in groups:
        identity=group['identity']
        if (BASE/'resources'/f'{identity}.reservation.json').exists():raise RuntimeError('attempted identity')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_budget.py'),'--id',identity,'--phase','confirmation','--seconds',str(group['seconds']),'--host-gib','32']
        if group['kind']=='gpu':cmd.append('--gpu')
        cmd+=['--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_exit.py'),'--receipt',str(OUT/(identity+'.exit.json')),'--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_experiment.py'),'run','--group',str(group['index']),'--kind',group['kind']]
        put(OUT/(identity+'.started.json'),dict(command=cmd));code=subprocess.call(cmd,cwd=ROOT);receipt=BASE/'resources'/f'{identity}.settlement.json'
        put(OUT/(identity+'.completed.json'),dict(returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        if code:put(OUT/'stopped.json',dict(identity=identity,returncode=code));return 1
    put(OUT/'completed.json',dict(status='all_72_slots_disposed_with_failures_retained'));return 0


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['admit','run']);a=p.parse_args()
    if a.action=='admit':admit()
    else:raise SystemExit(run())
