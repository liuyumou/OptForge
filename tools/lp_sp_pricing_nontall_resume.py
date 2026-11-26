"""Seal completed failed-supervision results; continue only untouched families."""
import argparse
import subprocess
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
from lp_sp_pricing_finish import identities,still_same_process
from lp_sp_pricing_nontall_experiment import validate,STUDY

SEAL=BASE/'nontall-wide-seal-v2'


def seal():
    validate();prefix=BASE/'resources/nontall-gpu-1-v1';receipt=read(str(prefix)+'.settlement.json');resource=read(str(prefix)+'.resource.json')
    if receipt['status']!='refused' or not receipt['cleanup_empty'] or receipt['overrun'] or receipt['cpu_ns']!=2400*NS or receipt['gpu_ns']!=600*NS or resource['result']['reason']!='coordinator_lost':raise RuntimeError('unexpected failure disposition')
    verify(receipt['resource']);reservation=read(str(prefix)+'.reservation.json')
    for item in reservation['sources']:
        retained=binding(item['retained'])
        if retained['bytes']!=item['bytes'] or retained['sha256']!=item['sha256']:raise RuntimeError('retained source mismatch')
    owned=set(identities(resource))|set(identities(read(str(prefix)+'.journal.json')))
    if any(still_same_process(*item) for item in owned):raise RuntimeError('owned identity remains')
    path=STUDY/'gpu-group-1.json';group=read(path);checked=bindings(group)
    expected={f'sparse-wide-1m-{seed}-{lane}' for seed in (125101,125123,125149) for lane in ('candidate','copt-gpu-default')}
    if group['status']!='all_slots_disposed' or len(group['rows'])!=6 or {r['id'] for r in group['rows']}!=expected:raise RuntimeError('incomplete completed roster')
    SEAL.mkdir(exist_ok=False);put(SEAL/'result.json',dict(status='completed_results_sealed_supervision_not_regraded',source=binding(__file__),
        original_failure=binding(str(prefix)+'.settlement.json'),group=binding(path),checked_bindings=checked,owned_identities=len(owned),live_owned_identities=[],
        timing_excluded_ids=sorted(expected),numerical_recomputation=False,original_failure_regraded=False,full_cpu_seconds=2400,full_gpu_seconds=600,preceding_cause='not established'))


def checked():
    d=read(SEAL/'result.json');bindings(d)
    if read(BASE/'resources/nontall-wide-seal-v2.settlement.json')['status']!='passed':raise RuntimeError('seal supervision')
    return d


def run():
    validate();checked();out=BASE/'nontall-driver-v2';out.mkdir(exist_ok=False);groups=[]
    for index in range(2,8):
        for kind in (('gpu','cpu') if index%2==0 else ('cpu','gpu')):
            groups.append(dict(index=index,kind=kind,identity=f'nontall-{kind}-{index}-v1',seconds=600 if kind=='gpu' else 360))
    put(out/'plan.json',dict(source=binding(__file__),seal=binding(SEAL/'result.json'),freeze=binding(STUDY/'freeze.json'),
        stopped_driver=binding(BASE/'nontall-driver-v1/stopped.json'),groups=groups,
        rule='Only untouched frozen families continue. No repeated LP, no source/default/certificate/guard change. Original failed full charge and timing exclusion remain. Stop on any new nonpassing reservation.'))
    for group in groups:
        identity=group['identity']
        if (BASE/'resources'/f'{identity}.reservation.json').exists():raise RuntimeError('attempted identity')
        command=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_budget.py'),'--id',identity,'--phase','confirmation','--seconds',str(group['seconds']),'--host-gib','32']
        if group['kind']=='gpu':command.append('--gpu')
        command+=['--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_experiment.py'),'run','--group',str(group['index']),'--kind',group['kind']]
        put(out/(identity+'.started.json'),dict(command=command));code=subprocess.call(command,cwd=ROOT);receipt=BASE/'resources'/f'{identity}.settlement.json'
        put(out/(identity+'.completed.json'),dict(returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        if code:put(out/'stopped.json',dict(identity=identity,returncode=code));return 1
    put(out/'completed.json',dict(status='all_72_slots_disposed_with_failed_group_retained'));return 0


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['seal','run']);a=p.parse_args()
    if a.action=='seal':seal()
    else:raise SystemExit(run())
