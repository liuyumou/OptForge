"""Finite follow-up chain after the primary driver settles; no retries."""
import datetime as dt
import subprocess
import time
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_factor_budget import allocation


def run():
    out=BASE/'transform-driver-v1';out.mkdir(exist_ok=False);deadline=dt.datetime.fromisoformat(allocation()['wall_deadline_utc'])
    stages=[('transform-build-v1','admission',60,False,['lp_sp_pricing_transform_admit.py','build','transform-build-v1']),
        ('transform-cpu-admit-v1','admission',60,False,['lp_sp_pricing_transform_admit.py','cpu','transform-cpu-admit-v1']),
        ('transform-gpu-admit-v1','admission',120,True,['lp_sp_pricing_transform_admit.py','gpu','transform-gpu-admit-v1']),
        ('transform-selection-v1','confirmation',600,True,['lp_sp_pricing_transform_selection.py']),
        ('transform-freeze-v1','confirmation',180,False,['lp_sp_pricing_transform_experiment.py','freeze'])]
    stages += [(f'transform-comparison-{i}-v1','confirmation',600,True,['lp_sp_pricing_transform_experiment.py','run','--group',str(i)]) for i in range(3)]
    stages += [('factor-certificate-challenge-v1','reporting',600,False,['lp_sp_pricing_factor_challenge.py']),
               ('factor-final-verify-v1','reporting',600,False,['lp_sp_pricing_factor_report.py','verify'])]
    put(out/'plan.json',dict(source=binding(__file__),stages=stages,deadline_utc=deadline.isoformat(),
        rule='Wait only for primary completion files, then execute each fresh guarded stage once. Stop on any nonpassing stage. No concurrent numerical reservations.'))
    while not (BASE/'factor-driver-v1/completed.json').exists():
        if (BASE/'factor-driver-v1/stopped.json').exists():raise RuntimeError('primary stopped')
        if dt.datetime.now(dt.timezone.utc)>=deadline:raise TimeoutError('hard campaign deadline')
        time.sleep(5)
    put(out/'primary-completed.json',dict(primary=binding(BASE/'factor-driver-v1/completed.json')))
    for identity,phase,seconds,gpu,command in stages:
        if (BASE/'resources'/f'{identity}.reservation.json').exists():raise RuntimeError('stage already attempted')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_factor_budget.py'),'--id',identity,'--phase',phase,'--seconds',str(seconds),'--host-gib','32']
        if gpu:cmd.append('--gpu')
        cmd+=['--',str(PYTHON),'-B',str(ROOT/'tools'/command[0]),*command[1:]]
        put(out/(identity+'.started.json'),dict(command=cmd,utc=dt.datetime.now(dt.timezone.utc).isoformat()))
        code=subprocess.call(cmd,cwd=ROOT);receipt=BASE/'resources'/f'{identity}.settlement.json'
        record=dict(identity=identity,returncode=code,settlement=binding(receipt) if receipt.exists() else None)
        put(out/(identity+'.completed.json'),record)
        if code:put(out/'stopped.json',record);return 1
    code=subprocess.call([str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_factor_report.py'),'settle','--reservation','factor-final-verify-v1'],cwd=ROOT)
    put(out/'completed.json',dict(status='settled' if code==0 else 'settlement_failed',returncode=code));return code


if __name__=='__main__':raise SystemExit(run())
