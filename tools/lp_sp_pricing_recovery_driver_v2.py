"""Finite once-only sequential driver for the frozen recovery holdouts."""
import subprocess
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_recovery_experiment_v2 import frozen,STUDY
DRIVER=BASE/'recovery-driver-v2'

def run():
    frozen();DRIVER.mkdir(exist_ok=False)
    groups=[dict(index=i,kind='control',seconds=180) for i in range(2)]
    groups += [dict(index=i,kind=k,seconds=(300 if i==4 else 180) if k=='gpu' else 360) for i in range(5) for k in (('gpu','cpu') if i%2==0 else ('cpu','gpu'))]
    put(DRIVER/'plan.json',dict(source=binding(__file__),freeze=binding(STUDY/'freeze.json'),groups=groups,rule='Each frozen scientific identity once; stop on reservation failure.'))
    for item in groups:
        identity=f"recovery-{item['kind']}-{item['index']}-v1"
        if (BASE/'resources'/f'{identity}.reservation.json').exists():raise RuntimeError('attempted identity')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_budget.py'),'--id',identity,'--phase','confirmation','--seconds',str(item['seconds']),'--host-gib','32']
        if item['kind']=='gpu':cmd.append('--gpu')
        cmd+=['--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_exit.py'),'--receipt',str(DRIVER/(identity+'.exit.json')),'--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_experiment_v2.py'),'group','--index',str(item['index']),'--kind',item['kind']]
        put(DRIVER/(identity+'.started.json'),dict(command=cmd));code=subprocess.call(cmd,cwd=ROOT);receipt=BASE/'resources'/f'{identity}.settlement.json'
        put(DRIVER/(identity+'.completed.json'),dict(returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        if code:put(DRIVER/'stopped.json',dict(identity=identity,returncode=code));return 1
    put(DRIVER/'completed.json',dict(status='all_57_slots_disposed'));return 0

if __name__=='__main__':raise SystemExit(run())
