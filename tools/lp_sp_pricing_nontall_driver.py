"""Finite reservation sequence; never retries an attempted identity."""
import datetime as dt
import subprocess
from lp_sp_pricing_budget import BASE,ROOT,binding,put
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_nontall_experiment import validate,STUDY,SPECS


def run():
    validate();out=BASE/'nontall-driver-v1';out.mkdir(exist_ok=False);groups=[]
    for index in range(len(SPECS)):
        for kind in (('gpu','cpu') if index%2==0 else ('cpu','gpu')):
            groups.append(dict(index=index,kind=kind,identity=f'nontall-{kind}-{index}-v1',seconds=600 if kind=='gpu' else 360))
    put(out/'plan.json',dict(source=binding(__file__),freeze=binding(STUDY/'freeze.json'),groups=groups,
        rule='Stop on any nonpassing reservation. No LP repeats. GPU groups need a fresh 30-second idle window; CPU groups use no GPU. Actual settled usage releases unused reserves.'))
    for group in groups:
        identity=group['identity']
        if (BASE/'resources'/f'{identity}.reservation.json').exists():raise RuntimeError('identity already attempted')
        command=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_budget.py'),'--id',identity,'--phase','confirmation','--seconds',str(group['seconds']),'--host-gib','32']
        if group['kind']=='gpu':command.append('--gpu')
        command+=['--',str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_experiment.py'),'run','--group',str(group['index']),'--kind',group['kind']]
        put(out/(identity+'.started.json'),dict(command=command,utc=dt.datetime.now(dt.timezone.utc).isoformat()))
        code=subprocess.call(command,cwd=ROOT);receipt=BASE/'resources'/f'{identity}.settlement.json'
        put(out/(identity+'.completed.json'),dict(returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        if code:
            put(out/'stopped.json',dict(identity=identity,returncode=code));return 1
    put(out/'completed.json',dict(status='all_72_slots_disposed'));return 0


if __name__=='__main__':raise SystemExit(run())
