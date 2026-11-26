"""Finite sequential reservation driver; never retries an attempted group."""
import datetime as dt
import json
import subprocess
from lp_sp_pricing_budget import BASE,ROOT,binding,put
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_factor_experiment import STUDY,validate


def run():
    f=validate();out=BASE/'factor-driver-v1';out.mkdir(exist_ok=False)
    groups=[dict(index=i,identity=f'factor-comparison-{i:02d}-v1',seconds=600 if i<3 else 350) for i in range(len(f['models']))]
    put(out/'plan.json',dict(source=binding(__file__),freeze=binding(STUDY/'freeze.json'),groups=groups,
        rule='One attempt per immutable group, stop on a nonpassing reservation; completed or attempted cells are never relaunched. Each new reservation must fit the original hard wall envelope.'))
    results=[]
    for group in groups:
        if (BASE/'resources'/f"{group['identity']}.reservation.json").exists():raise RuntimeError('group already attempted')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_factor_budget.py'),'--id',group['identity'],
             '--phase','confirmation','--seconds',str(group['seconds']),'--host-gib','32','--gpu','--',
             str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_factor_experiment.py'),'run','--index',str(group['index'])]
        put(out/f"started-{group['index']}.json",dict(command=cmd,utc=dt.datetime.now(dt.timezone.utc).isoformat()))
        code=subprocess.call(cmd,cwd=ROOT);receipt=BASE/'resources'/f"{group['identity']}.settlement.json"
        results.append(dict(**group,returncode=code,settlement=binding(receipt) if receipt.exists() else None))
        put(out/f"completed-{group['index']}.json",results[-1])
        if code:
            put(out/'stopped.json',dict(reason='nonpassing_group',groups=results));return 1
    put(out/'completed.json',dict(groups=results,status='all_groups_disposed'));return 0


if __name__=='__main__':raise SystemExit(run())
