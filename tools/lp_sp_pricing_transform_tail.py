"""Continue only untouched stages after the completed sweep's failed settlement."""
import subprocess
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_baselines import PYTHON


def run():
    out=BASE/'transform-driver-v2';out.mkdir(exist_ok=False)
    stages=[('transform-selection-seal-v1','reporting',60,False,['lp_sp_pricing_transform_resume.py','seal']),
        ('transform-freeze-v2','confirmation',180,False,['lp_sp_pricing_transform_resume.py','freeze'])]
    stages += [(f'transform-comparison-{i}-v1','confirmation',600,True,['lp_sp_pricing_transform_experiment.py','run','--group',str(i)]) for i in range(3)]
    stages += [('factor-certificate-challenge-v1','reporting',600,False,['lp_sp_pricing_factor_challenge.py']),
        ('factor-final-verify-v1','reporting',600,False,['lp_sp_pricing_factor_report.py','verify'])]
    put(out/'plan.json',dict(source=binding(__file__),failed_driver=binding(BASE/'transform-driver-v1/stopped.json'),stages=stages,
        rule='No repeated scientific cell or completed driver. Original failed development charge and timing exclusion retained. Stop on any nonpassing new stage.'))
    for identity,phase,seconds,gpu,command in stages:
        if (BASE/'resources'/f'{identity}.reservation.json').exists():raise RuntimeError('attempted stage')
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_factor_budget.py'),'--id',identity,'--phase',phase,'--seconds',str(seconds),'--host-gib','32']
        if gpu:cmd.append('--gpu')
        cmd+=['--',str(PYTHON),'-B',str(ROOT/'tools'/command[0]),*command[1:]]
        put(out/(identity+'.started.json'),dict(command=cmd));code=subprocess.call(cmd,cwd=ROOT)
        receipt=BASE/'resources'/f'{identity}.settlement.json';record=dict(identity=identity,returncode=code,settlement=binding(receipt) if receipt.exists() else None)
        put(out/(identity+'.completed.json'),record)
        if code:put(out/'stopped.json',record);return 1
    code=subprocess.call([str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_factor_report.py'),'settle','--reservation','factor-final-verify-v1'],cwd=ROOT)
    put(out/'completed.json',dict(status='settled' if code==0 else 'settlement_failed',returncode=code));return code


if __name__=='__main__':raise SystemExit(run())
